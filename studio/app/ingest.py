"""Bringing files into a project: probing, preview copies, waveform, transcription."""
from __future__ import annotations

import shutil
from pathlib import Path

from . import config, media, model, timeline, transcribe
from .jobs import Job, UserError, jobs

BROWSER_AUDIO = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".oga"}


def register(pid: str, name: str, origin: str = "upload", kind: str | None = None) -> tuple[dict, Path]:
    """Create a media record and return it with the path its file should be written to."""
    name = Path(name).name or "file"
    ext = Path(name).suffix.lower()
    kind = kind or model.kind_for(name) or "video"
    if not ext:
        ext = {"video": ".mp4", "audio": ".mp3", "image": ".jpg"}[kind]
    m = model.new_media(Path(name).stem or "file", kind, ext, origin)
    folder = model.mdir(pid, m["id"])
    folder.mkdir(parents=True, exist_ok=True)
    with model.lock(pid):
        p = model.load(pid)
        if not p:
            raise UserError("הפרויקט לא נמצא.")
        p["media"][m["id"]] = m
        p["rev"] = p.get("rev", 0) + 1
        model.save(p)
    return m, folder / m["file"]


def _update(pid: str, mid: str, **fields) -> dict | None:
    with model.lock(pid):
        p = model.load(pid)
        if not p or mid not in p["media"]:
            return None
        p["media"][mid].update(fields)
        p["rev"] = p.get("rev", 0) + 1
        model.save(p)
        return p["media"][mid]


def analyse(pid: str, m: dict, on_progress=None, cancel=None) -> dict:
    """Probe a media file and build everything the editor needs to show and play it."""
    folder = model.mdir(pid, m["id"])
    src = folder / m["file"]
    info = media.probe(src)
    kind = m["kind"]
    if info["has_video"] and info["duration"] > 0.2 and kind != "audio":
        kind = "video"
    elif info["has_video"] and kind != "audio":
        kind = "image"
    elif info["has_audio"]:
        kind = "audio"
    else:
        raise UserError("לא הצלחנו לקרוא את הקובץ. נתמכים וידאו, אודיו ותמונות.")
    fields = {"kind": kind, "width": info["width"], "height": info["height"], "fps": info["fps"],
              "has_audio": info["has_audio"], "has_video": info["has_video"] and kind != "audio",
              "duration": 0.0 if kind == "image" else info["duration"]}
    if kind == "video":
        media.make_thumb(src, folder / "thumb.jpg", info["duration"])
        tmp = folder / "proxy.tmp.mp4"
        media.make_proxy(src, tmp, info, on_progress, cancel)
        tmp.replace(folder / "proxy.mp4")
        strip = media.make_strip(folder / "proxy.mp4", folder / "strip.jpg", info["duration"])
        fields["meta"] = {**m.get("meta", {}), "strip": strip}
    elif kind == "audio" and src.suffix.lower() not in BROWSER_AUDIO:
        media.make_audio_proxy(src, folder / "proxy.m4a")
    if kind != "image" and info["has_audio"]:
        config.write_json(folder / "peaks.json", media.make_peaks(src, info["duration"]))
    return fields


def prepare(job: Job, pid: str, mid: str, add: dict | None = None):
    """Background work after a file arrives: analyse it, then optionally place it on the timeline."""
    with model.lock(pid):
        p = model.load(pid)
    if not p or mid not in p["media"]:
        return None
    m = p["media"][mid]
    try:
        job.update(0.0, "מכין תצוגה מקדימה…")
        fields = analyse(pid, m, lambda f: job.update(f * 0.95, "מכין תצוגה מקדימה…"), job.cancel)
        _update(pid, mid, status="ready", error=None, **fields)
    except media.Cancelled:
        remove(pid, mid)
        raise
    except Exception as e:
        msg = str(e) if isinstance(e, UserError) else f"{type(e).__name__}: {e}"[:300]
        _update(pid, mid, status="error", error=msg)
        raise
    result = {"media": mid}
    if add is not None:
        from . import ops_jobs
        try:
            result.update(ops_jobs.execute(pid, "add_clip", {"media": mid, **add}))
        except UserError as e:
            result["add_error"] = str(e)
    return result


def start(pid: str, mid: str, add: dict | None = None) -> Job:
    return jobs.submit("prepare", pid, prepare, pid, mid, add)


def add_ready_file(p: dict, src: Path, name: str, origin: str, kind: str, meta: dict | None = None) -> dict:
    """Copy a small, already usable file into an open project document (no background job)."""
    ext = src.suffix.lower()
    m = model.new_media(name, kind, ext, origin)
    folder = model.mdir(p["id"], m["id"])
    folder.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, folder / m["file"])
    m.update(analyse(p["id"], m))
    m["status"] = "ready"
    m["meta"] = {**m.get("meta", {}), **(meta or {})}
    p["media"][m["id"]] = m
    return m


def remove(pid: str, mid: str) -> None:
    with model.lock(pid):
        p = model.load(pid)
        if p and mid in p["media"]:
            for t in p["tracks"]:
                t["items"] = [it for it in t["items"] if it.get("media") != mid]
            del p["media"][mid]
            p["rev"] = p.get("rev", 0) + 1
            model.save(p)
    if model.valid_mid(mid):
        shutil.rmtree(model.mdir(pid, mid), ignore_errors=True)


def transcribe_job(job: Job, pid: str, mid: str, model_key: str, language: str):
    with model.lock(pid):
        p = model.load(pid)
    if not p or mid not in p["media"]:
        return None
    m = p["media"][mid]
    if not (m["has_audio"] or m["kind"] == "audio"):
        _update(pid, mid, transcript={"status": "error", "model": model_key, "language": language,
                                      "error": "בקובץ אין פס קול, אז אין מה לתמלל."})
        return {"words": 0}
    had_words = bool(m["words"])
    _update(pid, mid, transcript={"status": "running", "model": model_key, "language": language, "error": None})
    try:
        src = model.mdir(pid, mid) / m["file"]
        words = transcribe.transcribe(src, model_key, language, m["duration"], job)
        words = timeline.normalize_words(words, m["duration"])
    except media.Cancelled:
        _update(pid, mid, transcript={"status": "done" if had_words else "none", "model": model_key,
                                      "language": language, "error": None})
        raise
    except Exception as e:
        msg = str(e) if isinstance(e, UserError) else f"{type(e).__name__}: {e}"[:300]
        _update(pid, mid, transcript={"status": "done" if had_words else "error", "model": model_key,
                                      "language": language, "error": msg})
        raise
    from . import ops

    def apply(doc: dict):
        mm = doc["media"].get(mid)
        if mm:
            mm["words"] = words
            mm["tr"] = {}
            mm["transcript"] = {"status": "done", "model": model_key, "language": language, "error": None}

    ops.mutate(pid, apply, undo=False)
    return {"media": mid, "words": len(words)}


def start_transcribe(pid: str, mid: str, model_key: str | None = None, language: str | None = None) -> Job:
    s = config.load_settings()["transcribe"]
    for j in jobs.active(pid, "transcribe"):
        if getattr(j, "media", None) == mid:
            return j
    job = jobs.submit("transcribe", pid, transcribe_job, pid, mid,
                      model_key if model_key in transcribe.MODELS else s["model"], language or s["language"])
    job.media = mid
    return job


def maybe_transcribe(pid: str, mid: str) -> Job | None:
    """Transcribe speech the first time a recording lands on the timeline."""
    p = model.load(pid)
    m = p["media"].get(mid) if p else None
    if not m or m["transcript"]["status"] != "none" or m["origin"] not in ("upload", "import", "voice"):
        return None
    if not (m["has_audio"] or m["kind"] == "audio") or m["kind"] == "image":
        return None
    return start_transcribe(pid, mid)
