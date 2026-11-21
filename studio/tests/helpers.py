"""Shared builders for tests: small projects with real or pretend media."""
import subprocess

from app import ingest, media, model

FPS = 30


def fake_media(p, name="clip", duration=20.0, words=None, kind="video", w=1080, h=1920):
    """A media record that needs no file on disk (enough for editing logic)."""
    m = model.new_media(name, kind, ".mp4" if kind == "video" else ".wav")
    m.update(status="ready", duration=duration, width=w if kind != "audio" else 0, height=h if kind != "audio" else 0,
             fps=30.0, has_audio=True, has_video=kind == "video", words=words or [])
    if words:
        m["transcript"]["status"] = "done"
    p["media"][m["id"]] = m
    return m


def project_with_clip(duration=20.0, words=None):
    p = model.new_project("test")
    m = fake_media(p, duration=duration, words=words)
    it = model.new_video_item(m)
    model.main_track(p)["items"].append(it)
    model.save(p)
    return p["id"], m["id"], it["id"]


def spoken(n=40, step=0.5, length=0.3, start=0.5):
    return [{"t": f"w{i}", "s": round(start + i * step, 3), "e": round(start + i * step + length, 3)} for i in range(n)]


def make_clip(path, seconds=12, size="320x180"):
    """White flash plus a beep at the start of every second: a lip-sync ruler."""
    flash = f"color=black:s={size}:r={FPS}:d={seconds},drawbox=x=0:y=0:w=iw:h=ih:color=white:t=fill:enable='lt(mod(t\\,1)\\,0.1)'"
    beep = f"sine=frequency=1000:sample_rate=48000:duration={seconds},volume='lt(mod(t\\,1)\\,0.1)':eval=frame"
    subprocess.run([media.ffmpeg(), "-v", "error", "-y", "-f", "lavfi", "-i", flash, "-f", "lavfi", "-i", beep,
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k", "-t", str(seconds), str(path)], check=True)


def real_project(words, seconds=12, **doc):
    """A project whose main clip is a real generated video file."""
    p = model.new_project("sync test")
    m, dest = ingest.register(p["id"], "ruler.mp4", "upload")
    make_clip(dest, seconds)
    p = model.load(p["id"])
    rec = p["media"][m["id"]]
    info = media.probe(dest)
    rec.update(status="ready", duration=info["duration"], width=info["width"], height=info["height"], fps=info["fps"],
               has_audio=True, has_video=True, words=words)
    model.main_track(p)["items"].append(model.new_video_item(rec))
    p.update(doc)
    model.save(p)
    return p["id"], m["id"]
