"""End-to-end export checks on generated clips. They need ffmpeg but no network."""
import subprocess
from fractions import Fraction

import numpy as np
import pytest

from app import export, media, project
from app.jobs import Job

FPS = 30


def make_clip(path, seconds=12):
    """White flash plus a beep at the start of every second: a lip-sync ruler."""
    flash = f"color=black:s=320x180:r={FPS}:d={seconds},drawbox=x=0:y=0:w=iw:h=ih:color=white:t=fill:enable='lt(mod(t\\,1)\\,0.1)'"
    beep = f"sine=frequency=1000:sample_rate=48000:duration={seconds},volume='lt(mod(t\\,1)\\,0.1)':eval=frame"
    subprocess.run([media.ffmpeg(), "-v", "error", "-y", "-f", "lavfi", "-i", flash, "-f", "lavfi", "-i", beep,
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k", "-t", str(seconds), str(path)], check=True)


def make_project(words, seconds=12, **extra):
    p = project.create("sync test", ".mp4")
    src = project.pdir(p["id"]) / p["source"]
    make_clip(src, seconds)
    p["media"] = media.probe(src)
    p["status"] = "ready"
    p["words"] = words
    p.update(extra)
    project.save(p)
    return p


def decode(path):
    exe = media.ffmpeg()
    raw = subprocess.run([exe, "-v", "error", "-i", str(path), "-vf", "scale=16:9,format=gray", "-f", "rawvideo", "-"],
                         capture_output=True, check=True).stdout
    luma = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 16 * 9).mean(axis=1)
    pcm = subprocess.run([exe, "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", "48000", "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    return luma, np.frombuffer(pcm, dtype="<i2")


def onsets(mask):
    idx = np.flatnonzero(mask)
    if idx.size == 0:
        return idx
    return idx[np.insert(np.diff(idx) > 1, 0, True)]


def test_probe_reads_the_clip(tmp_path):
    clip = tmp_path / "c.mp4"
    make_clip(clip, 3)
    info = media.probe(clip)
    assert info["has_video"] and info["has_audio"]
    assert (info["width"], info["height"]) == (320, 180)
    assert abs(info["duration"] - 3) < 0.15 and abs(info["fps"] - FPS) < 0.01


def test_picture_and_sound_stay_in_sync_after_many_cuts():
    # 0.25 s "words" every 0.37 s, a third of them deleted, pauses tightened: ~15 cuts off the beat
    words = []
    t = 0.2
    k = 0
    while t + 0.25 < 11.8:
        words.append({"t": f"w{k}", "s": round(t, 3), "e": round(t + 0.25, 3), **({"d": True} if k % 3 == 1 else {})})
        t += 0.37 if k % 5 else 0.9
        k += 1
    p = make_project(words, tighten=0.2)
    d = project.derive(p)
    assert len(d["keep"]) > 10

    job = Job("export", p["id"])
    entry = export.export_video(job, p["id"], {"quality": "source", "captions": False})
    out = project.pdir(p["id"]) / "exports" / entry["file"]
    luma, audio = decode(out)

    assert abs(len(luma) / FPS - d["out_duration"]) <= 1.5 / FPS
    assert abs(len(audio) / 48000 - d["out_duration"]) <= 0.06

    flash_times = onsets(luma > 100) / FPS
    env = np.abs(audio.astype(np.int32))
    win = 96  # 2 ms
    loud = env[: len(env) // win * win].reshape(-1, win).max(axis=1) > 2500
    beep_times = onsets(loud) * win / 48000
    assert len(flash_times) >= 5
    worst = 0.0
    for ft in flash_times:
        nearest = np.abs(beep_times - ft).min()
        worst = max(worst, float(nearest))
    # a frame is 33 ms; the flash is quantised to frames, the beep is not
    assert worst <= 0.045, f"picture and sound drifted by {worst * 1000:.0f} ms"
    # the last flash is as tight as the first: no accumulating drift
    first = np.abs(beep_times - flash_times[0]).min()
    last = np.abs(beep_times - flash_times[-1]).min()
    assert abs(last - first) <= 0.04


def test_captions_appear_exactly_when_their_words_are_spoken():
    words = [{"t": "ראשון", "s": 1.0, "e": 1.5}, {"t": "שני", "s": 1.5, "e": 2.0},
             {"t": "שלישי.", "s": 2.0, "e": 2.5}, {"t": "רביעי", "s": 6.0, "e": 6.6}]
    p = make_project(words, seconds=8, captions={"enabled": True, "style": {"y": 0.5, "shadow": 0, "max_words": 3}})
    d = project.derive(p)
    cues = d["cues"]
    job = Job("export", p["id"])
    entry = export.export_video(job, p["id"], {"quality": "source", "captions": True})
    out = project.pdir(p["id"]) / "exports" / entry["file"]
    assert entry["captions"]
    raw = subprocess.run([media.ffmpeg(), "-v", "error", "-i", str(out), "-vf", "crop=iw:ih*0.2:0:ih*0.4,scale=32:8,format=gray",
                          "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    band = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 32 * 8).max(axis=1)
    flash = np.array([(i / FPS) % 1 < 0.1 + 1 / FPS for i in range(len(band))])
    shown = (band > 150) & ~flash          # white pill on a black frame
    blank = (band < 60)
    for i in range(len(band)):
        if flash[i]:
            continue
        t = i / FPS
        inside = any(c["s"] + 1.01 / FPS <= t <= c["e"] - 1.01 / FPS for c in cues)
        outside = all(t < c["s"] - 1.01 / FPS or t > c["e"] + 1.01 / FPS for c in cues)
        if inside:
            assert shown[i], f"caption missing at {t:.2f}s"
        if outside:
            assert blank[i], f"caption visible at {t:.2f}s with no cue"
    assert shown.any() and blank.any()


def test_crop_to_square_and_quality():
    words = [{"t": "מילה", "s": 0.5, "e": 1.0}]
    p = make_project(words, seconds=2)
    job = Job("export", p["id"])
    entry = export.export_video(job, p["id"], {"ratio": "1:1", "quality": "720", "captions": True})
    assert (entry["width"], entry["height"]) == (720, 720)
    info = media.probe(project.pdir(p["id"]) / "exports" / entry["file"])
    assert (info["width"], info["height"]) == (720, 720)


def test_export_refuses_an_empty_edit():
    words = [{"t": "מילה", "s": 0.5, "e": 1.0, "d": True}]
    p = make_project(words, seconds=2)
    with pytest.raises(Exception) as err:
        export.export_video(Job("export", p["id"]), p["id"], {})
    assert "לא נשאר" in str(err.value)


def test_audio_builder_is_sample_exact(tmp_path):
    src = tmp_path / "a.pcm"
    ramp = np.arange(48000 * 2, dtype="<i2").repeat(2)   # 2 s stereo, value = sample index (wraps)
    ramp.tofile(src)
    out = tmp_path / "o.pcm"
    export.build_audio(src, out, [(0, 15), (30, 45)], Fraction(30), 60)
    got = np.fromfile(out, dtype="<i2").reshape(-1, 2)
    assert len(got) == 48000        # 30 frames at 30 fps
    assert got[100, 0] == 100       # first range starts at sample 0, unfaded start
    # the second range starts at source second 1.0 (values wrap at 16 bits)
    assert got[24000 + 1000, 0] == np.array([48000 + 1000]).astype("<i2")[0]
