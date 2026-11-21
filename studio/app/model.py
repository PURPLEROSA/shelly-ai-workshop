"""The project document: media, tracks and items, with storage and undo history.

A project holds media (uploaded files and everything derived from them) and
tracks. The first video track is the main track: its clips play one after the
other with no gaps. Every other track holds items placed freely in time.
"""
from __future__ import annotations

import copy
import re
import shutil
import threading
import time
import uuid
from pathlib import Path

from . import captions
from .config import PROJECTS_DIR, read_json, write_json

VERSION = 2
RATIOS = {"source": None, "9:16": (9, 16), "16:9": (16, 9), "1:1": (1, 1), "4:5": (4, 5)}
FPS_CHOICES = ("auto", 24, 25, 30, 50, 60)
TRANSITIONS = {"fade": "מעבר רך", "fadeblack": "דרך שחור", "fadewhite": "דרך לבן", "slideleft": "החלקה שמאלה",
               "slideright": "החלקה ימינה", "wipeleft": "ניגוב", "zoomin": "זום", "circleopen": "עיגול נפתח"}
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".webm", ".mkv", ".avi", ".3gp", ".mts", ".ts", ".wmv", ".flv"}
AUDIO_EXT = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".oga", ".flac", ".opus", ".wma"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}

_locks: dict[str, threading.RLock] = {}
_guard = threading.Lock()
_history: dict[str, dict] = {}


def lock(pid: str) -> threading.RLock:
    with _guard:
        return _locks.setdefault(pid, threading.RLock())


def new_id(prefix: str = "") -> str:
    return prefix + uuid.uuid4().hex[:8]


def valid_id(pid: str) -> bool:
    return bool(re.fullmatch(r"[a-f0-9]{12}", pid or ""))


def valid_mid(mid: str) -> bool:
    return bool(re.fullmatch(r"m[a-f0-9]{8}", mid or ""))


def pdir(pid: str) -> Path:
    return PROJECTS_DIR / pid


def mdir(pid: str, mid: str) -> Path:
    return PROJECTS_DIR / pid / "media" / mid


def kind_for(name: str) -> str | None:
    ext = Path(name).suffix.lower()
    if ext in VIDEO_EXT:
        return "video"
    if ext in AUDIO_EXT:
        return "audio"
    if ext in IMAGE_EXT:
        return "image"
    return None


# ------------------------------------------------------------------ shape

def new_track(kind: str, name: str | None = None, main: bool = False) -> dict:
    return {"id": new_id("t"), "kind": kind, "name": name or "", "main": main, "muted": False,
            "hidden": False, "items": []}


def new_project(name: str) -> dict:
    pid = uuid.uuid4().hex[:12]
    pdir(pid).mkdir(parents=True, exist_ok=True)
    p = {
        "id": pid, "name": (name or "פרויקט חדש")[:120], "created": time.time(), "updated": time.time(),
        "version": VERSION, "rev": 0,
        "canvas": {"ratio": "source", "fps": "auto"},
        "media": {},
        "tracks": [new_track("text"), new_track("video", main=True), new_track("audio")],
        "captions": {"enabled": True, "style": captions.clean_style({}), "mode": "original", "lang": "en"},
        "tighten": None,
        "exports": [],
    }
    name_tracks(p)
    save(p)
    return p


def name_tracks(p: dict) -> None:
    """Give tracks their display names: Video 1 is the main track, numbers grow upwards."""
    labels = {"video": "וידאו", "audio": "אודיו", "text": "טקסט"}
    for kind in labels:
        same = [t for t in p["tracks"] if t["kind"] == kind]
        order = list(reversed(same)) if kind != "audio" else same
        for n, t in enumerate(order, 1):
            t["name"] = f"{labels[kind]} {n}"


def new_media(name: str, kind: str, ext: str, origin: str = "upload") -> dict:
    return {"id": new_id("m"), "name": name[:120], "kind": kind, "file": f"source{ext}", "origin": origin,
            "status": "preparing", "error": None, "duration": 0.0, "width": 0, "height": 0, "fps": 0.0,
            "has_audio": False, "has_video": False,
            "transcript": {"status": "none", "model": None, "language": None, "error": None},
            "words": [], "tr": {}, "meta": {}}


def new_video_item(m: dict, start: float = 0.0, length: float | None = None) -> dict:
    out = m["duration"] if m["kind"] != "image" else (length or 4.0)
    if length and m["kind"] != "image":
        out = min(out, length)
    return {"id": new_id("i"), "media": m["id"], "start": round(max(0.0, start), 3), "in": 0.0,
            "out": round(out, 3), "speed": 1.0, "volume": 1.0, "mute": False, "fade_in": 0.0, "fade_out": 0.0,
            "look": "", "zoom": [], "transition": None, "blend": "normal", "opacity": 1.0}


def new_audio_item(m: dict, start: float = 0.0, label: str = "") -> dict:
    return {"id": new_id("i"), "media": m["id"], "start": round(max(0.0, start), 3), "in": 0.0,
            "out": round(m["duration"], 3), "speed": 1.0, "volume": 1.0, "mute": False,
            "fade_in": 0.0, "fade_out": 0.0, "label": label}


def new_text_item(text: str, start: float, dur: float = 3.0, style: dict | None = None) -> dict:
    base = {"preset": "", "font": "Heebo-Black", "size": 0.09, "y": 0.22, "color": "#FFFFFF", "highlight": "none",
            "bg": "none", "stroke": 0.0, "shadow": 0.8, "max_words": 8}
    return {"id": new_id("i"), "start": round(max(0.0, start), 3), "dur": round(max(0.3, dur), 3),
            "text": text[:300], "style": captions.clean_style({**base, **(style or {})}), "fade": 0.25}


# ---------------------------------------------------------------- lookups

def main_track(p: dict) -> dict:
    for t in p["tracks"]:
        if t.get("main"):
            return t
    t = new_track("video", main=True)
    p["tracks"].append(t)
    name_tracks(p)
    return t


def track_by_id(p: dict, tid: str) -> dict | None:
    return next((t for t in p["tracks"] if t["id"] == tid), None)


def first_track(p: dict, kind: str, main: bool | None = None) -> dict | None:
    for t in p["tracks"]:
        if t["kind"] == kind and (main is None or bool(t.get("main")) == main):
            return t
    return None


def find_item(p: dict, item_id: str):
    """(track, index, item) for an item id, or (None, -1, None)."""
    for t in p["tracks"]:
        for i, it in enumerate(t["items"]):
            if it["id"] == item_id:
                return t, i, it
    return None, -1, None


def all_items(p: dict):
    for t in p["tracks"]:
        for it in t["items"]:
            yield t, it


# ---------------------------------------------------------------- storage

def load(pid: str) -> dict | None:
    if not valid_id(pid):
        return None
    p = read_json(pdir(pid) / "project.json")
    if p and p.get("version") != VERSION:
        p = migrate(p)
        write_json(pdir(pid) / "project.json", p)
    return p


def save(p: dict) -> None:
    p["updated"] = time.time()
    write_json(pdir(p["id"]) / "project.json", p)


def delete(pid: str) -> None:
    if valid_id(pid):
        shutil.rmtree(pdir(pid), ignore_errors=True)
        _history.pop(pid, None)


def list_all() -> list[dict]:
    out = []
    if PROJECTS_DIR.is_dir():
        for d in PROJECTS_DIR.iterdir():
            if d.is_dir() and valid_id(d.name):
                p = load(d.name)
                if p:
                    out.append(summary(p))
    return sorted(out, key=lambda x: -x["updated"])


def summary(p: dict) -> dict:
    main = main_track(p)
    first = p["media"].get(main["items"][0]["media"]) if main["items"] else None
    if first is None:
        first = next((m for m in p["media"].values() if m["kind"] == "video"), None)
    busy = [m for m in p["media"].values() if m["status"] == "preparing" or m["transcript"]["status"] == "running"]
    return {"id": p["id"], "name": p["name"], "created": p["created"], "updated": p.get("updated", p["created"]),
            "thumb": first["id"] if first else None, "duration": sum(max(0.0, i["out"] - i["in"]) / max(i.get("speed", 1), 0.01)
                                                                      for i in main["items"]),
            "clips": len(main["items"]), "media": len(p["media"]), "exports": len(p.get("exports", [])),
            "busy": bool(busy), "error": next((m["error"] for m in p["media"].values() if m["status"] == "error"), None)
            if not main["items"] else None}


def migrate(old: dict) -> dict:
    """Bring a version 1 project (one video, one list of words) into the track model."""
    pid = old["id"]
    p = {
        "id": pid, "name": old.get("name", "פרויקט"), "created": old.get("created", time.time()),
        "updated": old.get("updated", time.time()), "version": VERSION, "rev": 0,
        "canvas": {"ratio": old.get("ratio", "source"), "fps": "auto"}, "media": {},
        "tracks": [new_track("text"), new_track("video", main=True), new_track("audio")],
        "captions": {"enabled": bool(old.get("captions", {}).get("enabled", True)),
                     "style": captions.clean_style(old.get("captions", {}).get("style")), "mode": "original", "lang": "en"},
        "tighten": old.get("tighten"), "exports": old.get("exports", []),
    }
    src = old.get("source")
    info = old.get("media") or {}
    if src and (pdir(pid) / src).exists():
        m = new_media(old.get("name", "video"), "video", Path(src).suffix)
        m.update({k: info.get(k, m[k]) for k in ("duration", "width", "height", "fps", "has_audio")})
        m["has_video"] = True
        m["status"] = "ready" if old.get("status") == "ready" else "error"
        m["error"] = old.get("error")
        m["transcript"] = old.get("transcript") or m["transcript"]
        m["words"] = old.get("words") or []
        folder = mdir(pid, m["id"])
        folder.mkdir(parents=True, exist_ok=True)
        for name, target in ((src, m["file"]), ("proxy.mp4", "proxy.mp4"), ("thumb.jpg", "thumb.jpg"),
                             ("peaks.json", "peaks.json"), ("audio.pcm", "audio.pcm")):
            f = pdir(pid) / name
            if f.exists():
                f.replace(folder / target)
        p["media"][m["id"]] = m
        if m["status"] == "ready":
            main_track(p)["items"].append(new_video_item(m))
    name_tracks(p)
    return p


# ------------------------------------------------------------------- undo

def _snapshot(p: dict) -> dict:
    words = {}
    for mid, m in p["media"].items():
        words[mid] = ("".join("1" if w.get("d") else "0" for w in m["words"]),
                      {i: (w["t"], w["o"]) for i, w in enumerate(m["words"]) if "o" in w})
    return {"tracks": copy.deepcopy(p["tracks"]), "captions": copy.deepcopy(p["captions"]),
            "canvas": dict(p["canvas"]), "tighten": p.get("tighten"), "words": words}


def _restore(p: dict, snap: dict) -> None:
    p["tracks"] = copy.deepcopy(snap["tracks"])
    p["captions"] = copy.deepcopy(snap["captions"])
    p["canvas"] = dict(snap["canvas"])
    p["tighten"] = snap["tighten"]
    for mid, (flags, texts) in snap["words"].items():
        m = p["media"].get(mid)
        if not m or len(flags) != len(m["words"]):
            continue
        for i, w in enumerate(m["words"]):
            if flags[i] == "1":
                w["d"] = True
            else:
                w.pop("d", None)
            if i in texts:
                w["t"], w["o"] = texts[i]
            elif "o" in w:
                w["t"] = w.pop("o")
    # items may point at media that was removed after the snapshot was taken
    for t in p["tracks"]:
        t["items"] = [it for it in t["items"] if "media" not in it or it["media"] in p["media"]]


def snapshot(p: dict) -> dict:
    return _snapshot(p)


def push(pid: str, snap: dict, key: str | None = None) -> None:
    """Record a state taken before an edit as an undo step. Rapid steps with the same key merge."""
    h = _history.setdefault(pid, {"undo": [], "redo": [], "key": None, "at": 0.0})
    now = time.time()
    if key and h["key"] == key and now - h["at"] < 1.2 and h["undo"]:
        h["at"] = now
        return
    h["undo"].append(snap)
    del h["undo"][:-80]
    h["redo"].clear()
    h["key"], h["at"] = key, now


def undo(p: dict) -> bool:
    h = _history.get(p["id"])
    if not h or not h["undo"]:
        return False
    h["redo"].append(_snapshot(p))
    _restore(p, h["undo"].pop())
    h["key"] = None
    return True


def redo(p: dict) -> bool:
    h = _history.get(p["id"])
    if not h or not h["redo"]:
        return False
    h["undo"].append(_snapshot(p))
    _restore(p, h["redo"].pop())
    h["key"] = None
    return True


def history_state(pid: str) -> dict:
    h = _history.get(pid) or {"undo": [], "redo": []}
    return {"undo": len(h["undo"]), "redo": len(h["redo"])}
