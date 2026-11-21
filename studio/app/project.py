"""Project storage and everything derived from a project's edit state."""
from __future__ import annotations

import re
import shutil
import threading
import time
import uuid
from collections import OrderedDict
from pathlib import Path

from . import captions, timeline
from .config import PROJECTS_DIR, read_json, write_json

_locks: dict[str, threading.RLock] = {}
_locks_guard = threading.Lock()
RATIOS = {"source": None, "9:16": (9, 16), "1:1": (1, 1), "4:5": (4, 5), "16:9": (16, 9)}

# caption images are addressed by content hash; this remembers what each hash means
_cue_specs: "OrderedDict[str, tuple]" = OrderedDict()
_cue_guard = threading.Lock()


def lock(pid: str) -> threading.RLock:
    with _locks_guard:
        return _locks.setdefault(pid, threading.RLock())


def valid_id(pid: str) -> bool:
    return bool(re.fullmatch(r"[a-f0-9]{12}", pid or ""))


def pdir(pid: str) -> Path:
    return PROJECTS_DIR / pid


def load(pid: str) -> dict | None:
    if not valid_id(pid):
        return None
    return read_json(pdir(pid) / "project.json")


def save(p: dict) -> None:
    p["updated"] = time.time()
    write_json(pdir(p["id"]) / "project.json", p)


def create(name: str, ext: str) -> dict:
    pid = uuid.uuid4().hex[:12]
    pdir(pid).mkdir(parents=True, exist_ok=True)
    p = {
        "id": pid, "name": name[:120] or "סרטון חדש", "created": time.time(),
        "source": f"source{ext}", "status": "new", "error": None,
        "media": {}, "transcript": {"status": "none", "model": None, "language": None, "error": None},
        "words": [], "tighten": None, "ratio": "source",
        "captions": {"enabled": True, "style": captions.clean_style({})},
        "exports": [],
    }
    save(p)
    return p


def delete(pid: str) -> None:
    if valid_id(pid):
        shutil.rmtree(pdir(pid), ignore_errors=True)


def list_all() -> list[dict]:
    out = []
    if PROJECTS_DIR.is_dir():
        for d in PROJECTS_DIR.iterdir():
            p = read_json(d / "project.json") if d.is_dir() else None
            if p:
                out.append(summary(p))
    return sorted(out, key=lambda x: -x["created"])


def summary(p: dict) -> dict:
    return {"id": p["id"], "name": p["name"], "created": p["created"], "status": p["status"],
            "error": p.get("error"), "duration": p.get("media", {}).get("duration", 0),
            "width": p.get("media", {}).get("width", 0), "height": p.get("media", {}).get("height", 0),
            "transcript": p["transcript"]["status"], "words": len(p.get("words", [])),
            "exports": len(p.get("exports", []))}


def target_size(mw: int, mh: int, ratio: str, quality: str = "1080") -> tuple[int, int]:
    """Output frame size for a ratio and quality. Never upscales the source ratio."""
    short = {"720": 720, "1080": 1080}.get(quality)
    rt = RATIOS.get(ratio)
    if rt is None:
        w, h = mw, mh
        if short and min(w, h) > short:
            k = short / min(w, h)
            w, h = w * k, h * k
    else:
        s = short or 1080
        a, b = rt
        w, h = (s, s * b / a) if a <= b else (s * a / b, s)
    return max(2, int(round(w / 2)) * 2), max(2, int(round(h / 2)) * 2)


def derive(p: dict, quality: str = "1080") -> dict:
    """Keep ranges, edited duration and caption cues for the project's current state.

    Caption images are laid out for the frame size that `quality` produces."""
    media = p.get("media") or {}
    duration = float(media.get("duration") or 0)
    fps = timeline.norm_fps(media.get("fps"))
    words = p.get("words") or []
    frames = timeline.keep_frames(words, duration, fps, p.get("tighten"))
    tmap = timeline.TimeMap(frames, fps)
    style = captions.clean_style((p.get("captions") or {}).get("style"))
    w, h = target_size(media.get("width") or 1080, media.get("height") or 1920,
                        p.get("ratio") or "source", quality)
    cap_words = []
    for wd in words:
        t = "" if wd.get("d") else timeline.caption_text(wd["t"], style["strip_punct"], style["upper"])
        cap_words.append({"t": t, "s": wd["s"], "e": wd["e"], "d": wd.get("d") or not t})
    max_chars = max(10, int(1.55 / style["size"]) if style["bg"] != "none" else int(1.7 / style["size"]))
    chunks = timeline.build_chunks(cap_words, tmap, style["max_words"], max_chars)
    cues = timeline.build_cues(cap_words, tmap, chunks, style["highlight"] != "none")
    out_cues = []
    with _cue_guard:
        for c in cues:
            texts = tuple(cap_words[i]["t"] for i in chunks[c["chunk"]])
            key = captions.cue_key(texts, c["active"], style, w, h)
            _cue_specs[key] = (texts, c["active"], style, w, h)
            _cue_specs.move_to_end(key)
            out_cues.append({"s": c["s"], "e": c["e"], "k": key})
        while len(_cue_specs) > 6000:
            _cue_specs.popitem(last=False)
    top, band_h = captions.band_geometry(style, w, h)
    return {
        "fps": [fps.numerator, fps.denominator], "frames": frames,
        "keep": [[round(a, 4), round(b, 4)] for a, b in tmap.ranges],
        "out_duration": round(tmap.duration, 3),
        "cues": out_cues, "frame": {"w": w, "h": h},
        "band": {"top": top / h, "height": band_h / h},
        "_tmap": tmap, "_style": style,
    }


def public_derived(d: dict) -> dict:
    return {k: v for k, v in d.items() if not k.startswith("_") and k != "frames"}


def cue_spec(key: str):
    with _cue_guard:
        return _cue_specs.get(key)


def apply_edit(p: dict, body: dict) -> None:
    """Apply an edit payload from the browser to the project (in place)."""
    words = p["words"]
    d = body.get("d")
    if isinstance(d, str) and len(d) == len(words):
        for w, flag in zip(words, d):
            if flag == "1":
                w["d"] = True
            else:
                w.pop("d", None)
    texts = body.get("t")
    if isinstance(texts, dict):
        for key, val in texts.items():
            try:
                i = int(key)
            except (TypeError, ValueError):
                continue
            if 0 <= i < len(words) and isinstance(val, str):
                val = " ".join(val.split())[:80]
                w = words[i]
                orig = w.get("o", w["t"])
                if val == orig:
                    w["t"] = orig
                    w.pop("o", None)
                elif val != w["t"]:
                    w.setdefault("o", w["t"])
                    w["t"] = val
    if "tighten" in body:
        t = body["tighten"]
        p["tighten"] = None if t in (None, 0, False, "") else max(0.1, min(2.0, float(t)))
    if body.get("ratio") in RATIOS:
        p["ratio"] = body["ratio"]
    cap = body.get("captions")
    if isinstance(cap, dict):
        if "enabled" in cap:
            p["captions"]["enabled"] = bool(cap["enabled"])
        if isinstance(cap.get("style"), dict):
            p["captions"]["style"] = captions.clean_style({**p["captions"]["style"], **cap["style"]})


def fmt_time(t: float, sep: str = ",") -> str:
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def subtitles(p: dict, kind: str) -> str:
    """The edited video's captions as SRT or VTT, or its transcript as plain text."""
    d = derive(p)
    tmap = d["_tmap"]
    style = d["_style"]
    words = p["words"]
    live = [w for w in words if not w.get("d") and w["t"].strip()]
    if kind == "txt":
        parts, line = [], []
        for w in live:
            if w.get("b") and line and line[-1].rstrip("\"'”’)")[-1:] in ".?!…":
                parts.append(" ".join(line))
                line = []
            line.append(w["t"])
        if line:
            parts.append(" ".join(line))
        return "\n".join(parts) + "\n"
    cap = [{"t": timeline.caption_text(w["t"], False, False) if not w.get("d") else "",
            "s": w["s"], "e": w["e"], "d": w.get("d") or not w["t"].strip()} for w in words]
    chunks = timeline.build_chunks(cap, tmap, max(style["max_words"], 6), 42)
    cues = timeline.build_cues(cap, tmap, chunks, False)
    sep = "," if kind == "srt" else "."
    out = [] if kind == "srt" else ["WEBVTT", ""]
    for n, c in enumerate(cues, 1):
        text = " ".join(cap[i]["t"] for i in chunks[c["chunk"]])
        if kind == "srt":
            out.append(str(n))
        out.append(f"{fmt_time(c['s'], sep)} --> {fmt_time(c['e'], sep)}")
        out.append(text)
        out.append("")
    return "\n".join(out)
