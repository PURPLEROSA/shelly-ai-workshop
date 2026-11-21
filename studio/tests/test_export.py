"""End-to-end export checks on generated clips. They need ffmpeg but no network."""
import subprocess

import numpy as np
import pytest

from app import compose, export, media, model, ops, ops_jobs
from app.jobs import Job

from helpers import FPS, make_clip, real_project


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
    return idx[np.insert(np.diff(idx) > 1, 0, True)] if idx.size else idx


def run_export(pid, **opts):
    out = export.export_project(Job("export", pid), pid, opts)["exports"]
    return [(e, model.pdir(pid) / "exports" / e["file"]) for e in out]


def sync_error(path):
    luma, audio = decode(path)
    flash = onsets(luma > 100) / FPS
    env = np.abs(audio.astype(np.int32))
    win = 96
    beeps = onsets(env[: len(env) // win * win].reshape(-1, win).max(axis=1) > 2500) * win / 48000
    assert len(flash) >= 4 and len(beeps) >= 4
    return max(float(np.abs(beeps - f).min()) for f in flash), len(luma), len(audio)


def test_probe_reads_the_clip(tmp_path):
    clip = tmp_path / "c.mp4"
    make_clip(clip, 3)
    info = media.probe(clip)
    assert info["has_video"] and info["has_audio"]
    assert (info["width"], info["height"]) == (320, 180)
    assert abs(info["duration"] - 3) < 0.15 and abs(info["fps"] - FPS) < 0.01


def test_picture_and_sound_stay_in_sync_after_many_cuts():
    words, t, k = [], 0.2, 0
    while t + 0.25 < 11.8:
        words.append({"t": f"w{k}", "s": round(t, 3), "e": round(t + 0.25, 3), **({"d": True} if k % 3 == 1 else {})})
        t += 0.37 if k % 5 else 0.9
        k += 1
    pid, mid = real_project(words, tighten=0.2)
    d = compose.derive(model.load(pid))
    assert len(next(iter(d["items"].values()))["segs"]) > 10
    entry, path = run_export(pid, quality="source", captions=False)[0]
    worst, frames, samples = sync_error(path)
    assert abs(frames / FPS - d["duration"]) <= 1.5 / FPS
    assert abs(samples / 48000 - d["duration"]) <= 0.06
    assert worst <= 0.045, f"picture and sound drifted by {worst * 1000:.0f} ms"


def test_sync_survives_splitting_and_reordering_clips():
    pid, mid = real_project([])
    right = ops.run(pid, "split_item", {"at": 6.3})["right"]
    ops.run(pid, "move_item", {"item": right, "index": 0})     # play the second half first
    ops.run(pid, "cut_range", {"from": 1.4, "to": 2.9})
    d = compose.derive(model.load(pid))
    entry, path = run_export(pid, quality="source", captions=False)[0]
    worst, frames, _ = sync_error(path)
    assert abs(frames / FPS - d["duration"]) <= 1.5 / FPS
    assert worst <= 0.045, f"picture and sound drifted by {worst * 1000:.0f} ms"


def test_speed_and_transition_change_the_length_as_planned():
    pid, mid = real_project([])
    right = ops.run(pid, "split_item", {"at": 6.0})["right"]
    ops.run(pid, "set_speed", {"item": right, "speed": 2})
    ops.run(pid, "set_transition", {"item": right, "type": "fade", "duration": 0.5})
    d = compose.derive(model.load(pid))
    assert d["duration"] == pytest.approx(6 + 3 - 0.5, abs=0.05)
    entry, path = run_export(pid, quality="source", captions=False)[0]
    luma, audio = decode(path)
    assert abs(len(luma) / FPS - d["duration"]) <= 1.5 / FPS
    assert abs(len(audio) / 48000 - d["duration"]) <= 0.06
    # at double speed the one-per-second flashes arrive twice as often
    late = onsets(luma[int(6.2 * FPS):] > 100) / FPS
    assert len(late) >= 4 and np.diff(late).mean() == pytest.approx(0.5, abs=0.06)


def test_captions_appear_exactly_when_their_words_are_spoken():
    words = [{"t": "ראשון", "s": 1.0, "e": 1.5}, {"t": "שני", "s": 1.5, "e": 2.0},
             {"t": "שלישי.", "s": 2.0, "e": 2.5}, {"t": "רביעי", "s": 6.0, "e": 6.6}]
    pid, mid = real_project(words, seconds=8)
    ops.run(pid, "set_captions", {"style": {"y": 0.5, "shadow": 0, "max_words": 3}})
    cues = compose.derive(model.load(pid))["cues"]
    entry, path = run_export(pid, quality="source", captions=True)[0]
    assert entry["captions"]
    raw = subprocess.run([media.ffmpeg(), "-v", "error", "-i", str(path), "-vf", "crop=iw:ih*0.2:0:ih*0.4,scale=32:8,format=gray",
                          "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    band = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 32 * 8).max(axis=1)
    for i in range(len(band)):
        t = i / FPS
        if t % 1 < 0.1 + 1 / FPS:
            continue    # the white flash frames hide the caption test
        if any(c["s"] + 1.01 / FPS <= t <= c["e"] - 1.01 / FPS for c in cues):
            assert band[i] > 150, f"caption missing at {t:.2f}s"
        if all(t < c["s"] - 1.01 / FPS or t > c["e"] + 1.01 / FPS for c in cues):
            assert band[i] < 60, f"caption visible at {t:.2f}s with no cue"


def test_everything_at_once_in_two_shapes(tmp_path):
    """Zoom, look, title, sound effect, an image overlay and a blended overlay, exported twice."""
    pid, mid = real_project([], seconds=6)
    p = model.load(pid)
    iid = model.main_track(p)["items"][0]["id"]
    ops.run(pid, "quick_zoom", {"kind": "punch", "at": 1.0, "scale": 1.5, "duration": 1.0})
    ops.run(pid, "set_look", {"item": iid, "look": "bw"})
    ops.run(pid, "add_text", {"text": "כותרת בדיקה", "at": 0.5, "duration": 2, "preset": "tag"})
    ops_jobs.execute(pid, "add_sound_effect", {"name": "ding", "at": 2.5})
    # a still image and a second video as overlays
    from PIL import Image
    from app import ingest
    m_img, dest = ingest.register(pid, "pic.png", "upload")
    Image.new("RGB", (400, 300), (200, 40, 40)).save(dest)
    m_vid, dest2 = ingest.register(pid, "leak.mp4", "upload")
    make_clip(dest2, 3, "160x90")
    for m in (m_img, m_vid):
        doc = model.load(pid)
        fields = ingest.analyse(pid, doc["media"][m["id"]])
        ingest._update(pid, m["id"], status="ready", **fields)
    v2 = ops.run(pid, "add_track", {"kind": "video"})["track"]
    pic = ops.run(pid, "add_clip", {"media": m_img["id"], "track": v2, "at": 3.0, "length": 1.5})["item"]
    leak = ops.run(pid, "add_clip", {"media": m_vid["id"], "track": v2, "at": 0.0})["item"]
    ops.run(pid, "set_item", {"item": leak, "blend": "screen", "opacity": 0.6})
    outs = run_export(pid, ratios=["source", "9:16"], quality="720")
    assert [(e["width"], e["height"]) for e, _ in outs] == [(320, 180), (720, 1280)]
    for entry, path in outs:
        info = media.probe(path)
        assert (info["width"], info["height"]) == (entry["width"], entry["height"])
        assert abs(info["duration"] - 6) < 0.2 and info["has_audio"]
    # the picture overlay is red and covers the frame while it is on
    frame = subprocess.run([media.ffmpeg(), "-v", "error", "-ss", "3.7", "-i", str(outs[0][1]), "-frames:v", "1",
                            "-vf", "scale=4:4", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    r, g, b = np.frombuffer(frame, dtype=np.uint8).reshape(-1, 3).mean(axis=0)
    assert r > 120 and g < 90 and b < 90
    assert model.find_item(model.load(pid), pic)[2] is not None


def test_export_refuses_an_empty_timeline():
    p = model.new_project("empty")
    with pytest.raises(Exception) as err:
        export.export_project(Job("export", p["id"]), p["id"], {})
    assert "ריק" in str(err.value)
