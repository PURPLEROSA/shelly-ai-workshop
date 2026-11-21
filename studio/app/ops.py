"""Every edit the studio can make, as one registry of named operations.

The browser, the REST API and the MCP server all go through `run`, so an
edit behaves the same whoever asks for it, lands in the same undo history
and shows up live in every open window.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import captions, cleanup, compose, looks, model, sfx
from .jobs import UserError

OPS: dict[str, "Op"] = {}

NUM = {"type": "number"}
STR = {"type": "string"}
BOOL = {"type": "boolean"}
INT = {"type": "integer"}
ITEM = {"type": "string", "description": "Item id, as listed by get_project."}
MEDIA = {"type": "string", "description": "Media id, as listed by list_media."}
AT = {"type": "number", "description": "Timeline time in seconds."}


@dataclass
class Op:
    name: str
    desc: str
    fn: object
    props: dict = field(default_factory=dict)
    required: tuple = ()
    mutates: bool = True
    local_only: bool = False
    group: str = ""

    def schema(self) -> dict:
        return {"type": "object", "properties": self.props, "required": list(self.required),
                "additionalProperties": False}


def op(name: str, desc: str, props: dict | None = None, required: tuple = (), mutates: bool = True,
       local_only: bool = False, group: str = ""):
    def wrap(fn):
        OPS[name] = Op(name, desc, fn, props or {}, required, mutates, local_only, group)
        return fn
    return wrap


def run(pid: str, name: str, args: dict | None = None, coalesce: str | None = None, local: bool = True) -> dict:
    spec = OPS.get(name)
    if not spec:
        raise UserError(f"פעולה לא מוכרת: {name}")
    if spec.local_only and not local:
        raise UserError("את הפעולה הזו אפשר לבצע רק מהמחשב שהסטודיו רץ עליו.")
    args = {k: v for k, v in (args or {}).items() if v is not None and k in spec.props}
    missing = [k for k in spec.required if k not in args]
    if missing:
        raise UserError(f"חסר פרמטר: {', '.join(missing)}")
    with model.lock(pid):
        p = model.load(pid)
        if not p:
            raise UserError("הפרויקט לא נמצא.")
        if not spec.mutates:
            return spec.fn(p, args) or {}
        old = compose.tag_media(compose.Layout(p), p)
        snap = model.snapshot(p)
        result = spec.fn(p, args) or {}
        normalize(p)
        if not result.pop("_keep_free_items", False):
            compose.reflow(p, old)
            normalize(p)
        if not result.pop("_no_undo", False):
            model.push(pid, snap, coalesce)
        p["rev"] = p.get("rev", 0) + 1
        model.save(p)
        return result


def mutate(pid: str, fn, key: str | None = None, undo: bool = True) -> dict | None:
    """Apply a change from a background job, with the same bookkeeping as an operation."""
    with model.lock(pid):
        p = model.load(pid)
        if not p:
            return None
        old = compose.tag_media(compose.Layout(p), p)
        snap = model.snapshot(p)
        result = fn(p)
        normalize(p)
        compose.reflow(p, old)
        normalize(p)
        if undo:
            model.push(pid, snap, key)
        p["rev"] = p.get("rev", 0) + 1
        model.save(p)
        return result


# ----------------------------------------------------------------- helpers

def _f(v, lo: float, hi: float, default: float) -> float:
    try:
        return min(hi, max(lo, float(v)))
    except (TypeError, ValueError):
        return default


def _item(p: dict, item_id) -> tuple[dict, int, dict]:
    track, idx, it = model.find_item(p, str(item_id))
    if it is None:
        raise UserError("הפריט לא נמצא בטיימליין.")
    return track, idx, it


def _media(p: dict, mid) -> dict:
    m = p["media"].get(str(mid))
    if not m:
        raise UserError("קובץ המדיה לא נמצא בפרויקט.")
    return m


def _ready(m: dict) -> dict:
    if m["status"] != "ready":
        raise UserError("הקובץ עדיין בהכנה. מנסים שוב בעוד רגע.")
    return m


def normalize(p: dict) -> None:
    """Clamp every value to something playable and keep derived fields in step."""
    fps = float(compose.canvas_fps(p))
    frame = 1.0 / fps
    if not any(t.get("main") for t in p["tracks"]):
        p["tracks"].append(model.new_track("video", main=True))
    for t in p["tracks"]:
        kept = []
        for it in t["items"]:
            if t["kind"] == "text":
                it["start"] = round(_f(it.get("start"), 0, 36000, 0), 3)
                it["dur"] = round(_f(it.get("dur"), 2 * frame, 3600, 3), 3)
                it["text"] = str(it.get("text", ""))[:300]
                it["style"] = captions.clean_style(it.get("style"))
                it["fade"] = _f(it.get("fade"), 0, 2, 0.25)
                kept.append(it)
                continue
            m = p["media"].get(it.get("media"))
            if not m:
                continue
            limit = 3600.0 if m["kind"] == "image" else max(m["duration"], frame)
            it["in"] = round(_f(it.get("in"), 0, max(0.0, limit - frame), 0), 3)
            it["out"] = round(_f(it.get("out"), it["in"] + frame, limit, limit), 3)
            it["start"] = round(_f(it.get("start"), 0, 36000, 0), 3)
            it["speed"] = 1.0 if m["kind"] == "image" else round(_f(it.get("speed"), 0.25, 4.0, 1.0), 3)
            it["volume"] = round(_f(it.get("volume"), 0, 2, 1), 3)
            it["mute"] = bool(it.get("mute"))
            length = (it["out"] - it["in"]) / it["speed"]
            it["fade_in"] = round(_f(it.get("fade_in"), 0, length / 2, 0), 3)
            it["fade_out"] = round(_f(it.get("fade_out"), 0, length / 2, 0), 3)
            if t["kind"] == "video":
                it["look"] = it.get("look") if it.get("look") in looks.BY_ID else ""
                it["blend"] = "screen" if it.get("blend") == "screen" and not t.get("main") else "normal"
                it["opacity"] = round(_f(it.get("opacity"), 0, 1, 1), 3)
                kfs = []
                for k in it.get("zoom") or []:
                    try:
                        kfs.append({"t": round(_f(k["t"], 0, length, 0), 3), "s": round(_f(k.get("s"), 1, 4, 1), 3),
                                    "x": round(_f(k.get("x"), 0, 1, 0.5), 3), "y": round(_f(k.get("y"), 0, 1, 0.5), 3)})
                    except (KeyError, TypeError):
                        continue
                kfs.sort(key=lambda k: k["t"])
                it["zoom"] = [k for i, k in enumerate(kfs) if i == 0 or k["t"] - kfs[i - 1]["t"] > frame / 2]
                tr = it.get("transition")
                if t.get("main") and isinstance(tr, dict) and tr.get("type") in model.TRANSITIONS:
                    it["transition"] = {"type": tr["type"], "dur": round(_f(tr.get("dur"), 0.1, 3, 0.5), 3)}
                else:
                    it["transition"] = None
            kept.append(it)
        t["items"] = kept
        if not t.get("main"):
            t["items"].sort(key=lambda i: i["start"])
    main = model.main_track(p)
    if main["items"]:
        main["items"][0]["transition"] = None
    lay = compose.Layout(p)
    for it in main["items"]:
        it["start"] = round(lay.items[it["id"]]["start_f"] / fps, 3)
    cap = p.setdefault("captions", {})
    cap["enabled"] = bool(cap.get("enabled", True))
    cap["style"] = captions.clean_style(cap.get("style"))
    cap["mode"] = cap.get("mode") if cap.get("mode") in ("original", "translated", "both") else "original"
    cap["lang"] = str(cap.get("lang") or "en")[:8]
    cv = p.setdefault("canvas", {})
    cv["ratio"] = cv.get("ratio") if cv.get("ratio") in model.RATIOS else "source"
    cv["fps"] = cv.get("fps") if cv.get("fps") in model.FPS_CHOICES else "auto"
    t = p.get("tighten")
    p["tighten"] = None if not t else round(_f(t, 0.1, 2.0, 0.35), 3)
    model.name_tracks(p)


def _local_time(p: dict, it: dict, at: float) -> float:
    """Seconds from the start of an item to a timeline time."""
    info = compose.Layout(p).items[it["id"]]
    return min(max(at - info["map"].start, 0.0), info["map"].dur)


def _main_item_at(p: dict, at: float) -> dict:
    lay = compose.Layout(p)
    iid = lay.main_at(at)
    if not iid:
        raise UserError("אין קליפ בנקודה הזו בטיימליין.")
    return model.find_item(p, iid)[2]


# ----------------------------------------------------------------- project

@op("get_project", "Describe the project: canvas, tracks, every item with its timing, and the media library.",
    mutates=False, group="project")
def get_project(p, a):
    d = compose.derive(p)
    tracks = []
    for t in p["tracks"]:
        items = []
        for it in t["items"]:
            info = d["items"].get(it["id"], {})
            row = {"id": it["id"], "start": info.get("start"), "duration": info.get("dur")}
            if t["kind"] == "text":
                row["text"] = it["text"]
            else:
                m = p["media"][it["media"]]
                row.update(media=it["media"], name=m["name"], source_in=it["in"], source_out=it["out"],
                           speed=it["speed"], volume=it["volume"], muted=it["mute"])
                if t["kind"] == "video":
                    row.update(look=it["look"], zoom_keyframes=len(it["zoom"]),
                               transition=(it["transition"] or {}).get("type"))
            items.append(row)
        tracks.append({"id": t["id"], "kind": t["kind"], "name": t["name"], "main": bool(t.get("main")),
                       "muted": t["muted"], "hidden": t["hidden"], "items": items})
    return {"id": p["id"], "name": p["name"], "duration": d["duration"],
            "canvas": {**p["canvas"], "width": d["frame"]["w"], "height": d["frame"]["h"],
                       "frame_rate": round(d["fps"][0] / d["fps"][1], 3)},
            "tracks": tracks, "media": list_media(p, {})["media"],
            "captions": {"enabled": p["captions"]["enabled"], "preset": p["captions"]["style"].get("preset"),
                         "mode": p["captions"]["mode"], "language": p["captions"]["lang"], "count": len(d["cues"])},
            "pause_tightening": p.get("tighten"), "history": model.history_state(p["id"])}


@op("list_media", "List the media library: uploaded files, stock, narration and sound effects.", mutates=False,
    group="media")
def list_media(p, a):
    return {"media": [{"id": m["id"], "name": m["name"], "kind": m["kind"], "origin": m["origin"], "status": m["status"],
                       "duration": round(m["duration"], 2), "width": m["width"], "height": m["height"],
                       "transcript": m["transcript"]["status"], "words": len(m["words"])} for m in p["media"].values()]}


@op("set_canvas", "Set the frame shape and frame rate of the project.",
    {"ratio": {"type": "string", "enum": list(model.RATIOS)},
     "fps": {"description": "auto, or one of 24, 25, 30, 50, 60."}}, group="project")
def set_canvas(p, a):
    if "ratio" in a:
        if a["ratio"] not in model.RATIOS:
            raise UserError("פורמט לא נתמך.")
        p["canvas"]["ratio"] = a["ratio"]
    if "fps" in a:
        fps = a["fps"]
        try:
            fps = int(fps) if str(fps) != "auto" else "auto"
        except (TypeError, ValueError):
            raise UserError("קצב פריימים לא נתמך.")
        if fps not in model.FPS_CHOICES:
            raise UserError("קצב פריימים לא נתמך.")
        p["canvas"]["fps"] = fps
    return {"canvas": p["canvas"]}


@op("rename_project", "Rename the project.", {"name": STR}, ("name",), group="project")
def rename_project(p, a):
    name = " ".join(str(a["name"]).split())[:120]
    if not name:
        raise UserError("שם ריק.")
    p["name"] = name
    return {"name": name, "_no_undo": True}


@op("undo", "Undo the last edit.", group="project")
def undo(p, a):
    if not model.undo(p):
        raise UserError("אין מה לבטל.")
    return {"_no_undo": True, "_keep_free_items": True}


@op("redo", "Redo the edit that was just undone.", group="project")
def redo(p, a):
    if not model.redo(p):
        raise UserError("אין מה לבצע מחדש.")
    return {"_no_undo": True, "_keep_free_items": True}


# ------------------------------------------------------------------- items

@op("add_clip", "Put a media file on the timeline. Video and images go to the main track by default "
                "(inserted at `at`, the clips after it move over); audio goes to an audio track at `at`.",
    {"media": MEDIA, "track": {"type": "string", "description": "Track id. Omit for the default track."},
     "at": AT, "index": {"type": "integer", "description": "Position on the main track (0 = first)."},
     "length": {"type": "number", "description": "For images: how long to show it, in seconds."}},
    ("media",), group="timeline")
def add_clip(p, a):
    m = _ready(_media(p, a["media"]))
    track = model.track_by_id(p, a["track"]) if a.get("track") else None
    if a.get("track") and not track:
        raise UserError("הערוץ לא נמצא.")
    if track is None:
        track = model.first_track(p, "audio") if m["kind"] == "audio" else model.main_track(p)
        if track is None:
            track = model.new_track("audio")
            p["tracks"].append(track)
    if track["kind"] == "text":
        raise UserError("לערוץ טקסט מוסיפים טקסט, לא מדיה.")
    if track["kind"] == "video" and m["kind"] == "audio":
        raise UserError("קובץ אודיו שייך לערוץ אודיו.")
    if track["kind"] == "audio" and not (m["kind"] == "audio" or m["has_audio"]):
        raise UserError("בקובץ הזה אין אודיו.")
    lay = compose.Layout(p)
    at = _f(a.get("at"), 0, 36000, lay.main_f / float(lay.fps) if track.get("main") else 0.0)
    if track["kind"] == "audio":
        it = model.new_audio_item(m, at, m["name"])
        track["items"].append(it)
    else:
        it = model.new_video_item(m, at, a.get("length"))
        if track.get("main"):
            if "index" in a:
                idx = max(0, min(len(track["items"]), int(a["index"])))
            elif "at" in a:
                idx = sum(1 for x in track["items"]
                          if lay.items[x["id"]]["map"].start + lay.items[x["id"]]["map"].dur / 2 < at)
            else:
                idx = len(track["items"])
            track["items"].insert(idx, it)
        else:
            it["mute"] = True   # B-roll is silent unless asked otherwise
            track["items"].append(it)
    return {"item": it["id"], "track": track["id"], "media": m["id"], "main": bool(track.get("main"))}


@op("remove_item", "Delete an item from the timeline. On the main track the clips after it close the gap.",
    {"item": ITEM}, ("item",), group="timeline")
def remove_item(p, a):
    track, idx, _ = _item(p, a["item"])
    del track["items"][idx]


@op("move_item", "Move an item: to a new position on the main track (`index`), to a new time on a free track "
                 "(`start`), or to another track of the same kind (`track`).",
    {"item": ITEM, "index": INT, "start": NUM, "track": STR}, ("item",), group="timeline")
def move_item(p, a):
    track, idx, it = _item(p, a["item"])
    target = model.track_by_id(p, a["track"]) if a.get("track") else track
    if target is None:
        raise UserError("הערוץ לא נמצא.")
    if target["kind"] != track["kind"]:
        raise UserError("אפשר להעביר פריט רק לערוץ מאותו סוג.")
    lay = compose.Layout(p)
    here = lay.items[it["id"]]["map"].start
    if target is not track:
        del track["items"][idx]
        if not target.get("main"):
            it["start"] = round(_f(a.get("start"), 0, 36000, here), 3)
            it["transition"] = None
            target["items"].append(it)
        else:
            it["blend"], it["opacity"] = "normal", 1.0
            at = _f(a.get("start"), 0, 36000, here)
            pos = int(a["index"]) if "index" in a else sum(
                1 for x in target["items"] if lay.items[x["id"]]["map"].start + lay.items[x["id"]]["map"].dur / 2 < at)
            target["items"].insert(max(0, min(len(target["items"]), pos)), it)
    elif track.get("main"):
        if "index" not in a:
            raise UserError("בערוץ הראשי מזיזים קליפ לפי מיקום (index).")
        del track["items"][idx]
        track["items"].insert(max(0, min(len(track["items"]), int(a["index"]))), it)
    else:
        if "start" not in a:
            raise UserError("חסר זמן התחלה (start).")
        it["start"] = round(_f(a["start"], 0, 36000, 0), 3)
    return {"item": it["id"], "track": target["id"], "_keep_free_items": not (track.get("main") or target.get("main"))}


@op("split_item", "Cut an item in two at a timeline time. Without `item`, splits the main-track clip under that time.",
    {"at": AT, "item": ITEM}, ("at",), group="timeline")
def split_item(p, a):
    at = float(a["at"])
    it = _item(p, a["item"])[2] if a.get("item") else _main_item_at(p, at)
    track, idx, it = _item(p, it["id"])
    lay = compose.Layout(p)
    info = lay.items[it["id"]]
    mp = info["map"]
    frame = 1 / float(lay.fps)
    if not (mp.start + frame <= at <= mp.end - frame):
        raise UserError("נקודת הפיצול צריכה להיות בתוך הקליפ.")
    right = dict(it, id=model.new_id("i"))
    local = at - mp.start
    if track["kind"] == "text":
        it["dur"], right["start"], right["dur"] = round(local, 3), round(at, 3), round(it["dur"] - local, 3)
    else:
        src = round(mp.to_src(at), 3)
        it["out"], right["in"] = src, src
        right["start"] = round(at, 3)
        it["fade_out"], right["fade_in"] = 0.0, 0.0
        if track["kind"] == "video":
            right["zoom"] = [dict(k, t=round(k["t"] - local, 3)) for k in it.get("zoom", []) if k["t"] >= local]
            it["zoom"] = [k for k in it.get("zoom", []) if k["t"] < local]
            right["transition"] = None
    track["items"].insert(idx + 1, right)
    return {"left": it["id"], "right": right["id"]}


@op("trim_item", "Change where an item starts or ends in its source file (`source_in`, `source_out`, in seconds of "
                 "the source). On free tracks `start` moves it in time; for text use `start` and `duration`.",
    {"item": ITEM, "source_in": NUM, "source_out": NUM, "start": NUM, "duration": NUM}, ("item",), group="timeline")
def trim_item(p, a):
    track, _, it = _item(p, a["item"])
    if track["kind"] == "text":
        if "start" in a:
            it["start"] = a["start"]
        if "duration" in a:
            it["dur"] = a["duration"]
        return {"_keep_free_items": True}
    if "source_in" in a:
        it["in"] = float(a["source_in"])
    if "source_out" in a:
        it["out"] = float(a["source_out"])
    if it["out"] <= it["in"]:
        raise UserError("הקליפ לא יכול להיות באורך אפס.")
    if "start" in a and not track.get("main"):
        it["start"] = a["start"]
    return {"_keep_free_items": not track.get("main")}


@op("duplicate_item", "Make a copy of an item, placed right after it.", {"item": ITEM}, ("item",), group="timeline")
def duplicate_item(p, a):
    track, idx, it = _item(p, a["item"])
    import copy
    dup = copy.deepcopy(it)
    dup["id"] = model.new_id("i")
    info = compose.Layout(p).items[it["id"]]
    if not track.get("main"):
        dup["start"] = round(info["map"].end, 3)
    else:
        dup["transition"] = None
    track["items"].insert(idx + 1, dup)
    return {"item": dup["id"]}


_PROPS = {"item": ITEM,
          "speed": {"type": "number", "description": "Playback speed, 0.25 to 4."},
          "volume": {"type": "number", "description": "0 is silent, 1 is original, up to 2."},
          "mute": BOOL,
          "fade_in": {"type": "number", "description": "Audio fade-in, seconds."},
          "fade_out": {"type": "number", "description": "Audio fade-out, seconds."},
          "look": {"type": "string", "description": "Colour look id from list_looks, or empty for none."},
          "blend": {"type": "string", "enum": ["normal", "screen"],
                    "description": "screen lays light leaks and grain over the picture."},
          "opacity": NUM, "label": STR, "text": STR,
          "style": {"type": "object", "description": "Text style fields, as in set_captions."}}


@op("set_item", "Change properties of an item: speed, volume, mute, fades, colour look, blend, opacity, or the "
                "text and style of a text item.", _PROPS, ("item",), group="timeline")
def set_item(p, a):
    track, _, it = _item(p, a["item"])
    if track["kind"] == "text":
        if "text" in a:
            it["text"] = str(a["text"])
        if isinstance(a.get("style"), dict):
            it["style"] = captions.clean_style({**it["style"], **a["style"]})
        return {"_keep_free_items": True}
    for key in ("speed", "volume", "mute", "fade_in", "fade_out", "label"):
        if key in a:
            it[key] = a[key]
    if track["kind"] == "video":
        if "look" in a:
            if a["look"] and a["look"] not in looks.BY_ID:
                raise UserError("הלוק לא קיים.")
            it["look"] = a["look"]
        for key in ("blend", "opacity"):
            if key in a:
                it[key] = a[key]
    return {"_keep_free_items": not (track.get("main") and "speed" in a)}


def _alias(name: str, desc: str, keys: tuple):
    props = {"item": ITEM, **{k: _PROPS[k] for k in keys}}
    op(name, desc, props, ("item",) + keys[:1], group="timeline")(set_item)


_alias("set_speed", "Set an item's playback speed (0.25 to 4). Pitch is preserved.", ("speed",))
_alias("set_volume", "Set an item's volume (0 to 2) and optionally mute it.", ("volume", "mute"))
_alias("set_fades", "Set audio fade-in and fade-out lengths of an item, in seconds.", ("fade_in", "fade_out"))
_alias("set_look", "Apply a colour look to a video item. Empty string removes it.", ("look",))


@op("list_looks", "List the colour looks.", mutates=False, group="timeline")
def list_looks(p, a):
    return {"looks": [{"id": lk["id"], "name": lk["name"]} for lk in looks.LOOKS]}


@op("set_transition", "Set the transition into a main-track clip from the clip before it. type \"none\" removes it.",
    {"item": ITEM, "type": {"type": "string", "enum": ["none", *model.TRANSITIONS]},
     "duration": {"type": "number", "description": "Seconds, 0.1 to 3. Default 0.5."}}, ("item", "type"),
    group="timeline")
def set_transition(p, a):
    track, idx, it = _item(p, a["item"])
    if not track.get("main"):
        raise UserError("מעברים קיימים רק בין קליפים בערוץ הראשי.")
    if a["type"] == "none":
        it["transition"] = None
    elif a["type"] not in model.TRANSITIONS:
        raise UserError("מעבר לא מוכר.")
    elif idx == 0:
        raise UserError("לקליפ הראשון אין קליפ קודם לעבור ממנו.")
    else:
        it["transition"] = {"type": a["type"], "dur": a.get("duration", 0.5)}


@op("add_zoom_keyframe", "Add a zoom keyframe to a video item at a timeline time. The picture eases between "
                         "keyframes. scale 1 is no zoom; x and y (0 to 1) are the point that stays in view.",
    {"item": ITEM, "at": AT, "scale": NUM, "x": NUM, "y": NUM}, ("at", "scale"), group="motion")
def add_zoom_keyframe(p, a):
    it = _item(p, a["item"])[2] if a.get("item") else _main_item_at(p, float(a["at"]))
    track = _item(p, it["id"])[0]
    if track["kind"] != "video":
        raise UserError("זום אפשר להוסיף רק לווידאו או לתמונה.")
    t = round(_local_time(p, it, float(a["at"])), 3)
    kf = {"t": t, "s": a["scale"], "x": a.get("x", 0.5), "y": a.get("y", 0.5)}
    fps = float(compose.canvas_fps(p))
    it["zoom"] = [k for k in it.get("zoom", []) if abs(k["t"] - t) > 0.5 / fps] + [kf]
    return {"item": it["id"], "_keep_free_items": True}


@op("remove_zoom_keyframe", "Remove one zoom keyframe by its index, or all of them with index -1.",
    {"item": ITEM, "index": INT}, ("item", "index"), group="motion")
def remove_zoom_keyframe(p, a):
    it = _item(p, a["item"])[2]
    i = int(a["index"])
    if i < 0:
        it["zoom"] = []
    elif i < len(it.get("zoom", [])):
        del it["zoom"][i]
    return {"_keep_free_items": True}


@op("quick_zoom", "One-step zoom on a video clip. punch: cut in close at `at` for a moment and back. "
                  "in: slow push-in from `at` to the end of the clip. out: the reverse.",
    {"kind": {"type": "string", "enum": ["punch", "in", "out"]}, "at": AT, "item": ITEM,
     "scale": {"type": "number", "description": "How close, 1.05 to 3. Default 1.3."},
     "duration": {"type": "number", "description": "For punch: how long it holds. Default 1.5 seconds."}},
    ("kind", "at"), group="motion")
def quick_zoom(p, a):
    it = _item(p, a["item"])[2] if a.get("item") else _main_item_at(p, float(a["at"]))
    info = compose.Layout(p).items[it["id"]]
    length = info["map"].dur
    t = _local_time(p, it, float(a["at"]))
    s = _f(a.get("scale"), 1.05, 3, 1.3)
    ramp = 0.12
    kfs = list(it.get("zoom", []))
    if a["kind"] == "punch":
        hold = _f(a.get("duration"), 0.3, 30, 1.5)
        end = min(length, t + hold)
        kfs += [{"t": max(0, t - ramp), "s": 1, "x": 0.5, "y": 0.42}, {"t": t, "s": s, "x": 0.5, "y": 0.42},
                {"t": max(t, end - ramp), "s": s, "x": 0.5, "y": 0.42}, {"t": end, "s": 1, "x": 0.5, "y": 0.42}]
    elif a["kind"] == "in":
        kfs += [{"t": t, "s": 1, "x": 0.5, "y": 0.45}, {"t": length, "s": s, "x": 0.5, "y": 0.45}]
    else:
        kfs += [{"t": t, "s": s, "x": 0.5, "y": 0.45}, {"t": length, "s": 1, "x": 0.5, "y": 0.45}]
    it["zoom"] = kfs
    return {"item": it["id"], "_keep_free_items": True}


def _cut(p: dict, a_t: float, b_t: float) -> float:
    """Remove the timeline range [a_t, b_t] from the main track. Returns seconds removed."""
    lay = compose.Layout(p)
    main = model.main_track(p)
    out = []
    removed = 0.0
    for it in main["items"]:
        mp = lay.items[it["id"]]["map"]
        if not lay.items[it["id"]]["dur_f"] or mp.end <= a_t or mp.start >= b_t:
            out.append(it)
            continue
        lo, hi = max(a_t, mp.start), min(b_t, mp.end)
        removed += hi - lo
        keep_head = lo - mp.start > 1e-3
        keep_tail = mp.end - hi > 1e-3
        src_lo, src_hi = round(mp.to_src(lo), 3), round(mp.to_src(hi), 3)
        local_hi = hi - mp.start
        if keep_head:
            head = dict(it, out=src_lo, fade_out=0.0)
            head["zoom"] = [k for k in it.get("zoom", []) if k["t"] < lo - mp.start]
            out.append(head)
        if keep_tail:
            tail = dict(it, fade_in=0.0)
            tail["in"] = src_hi
            tail["zoom"] = [dict(k, t=round(k["t"] - local_hi, 3)) for k in it.get("zoom", []) if k["t"] >= local_hi]
            if keep_head:
                tail["id"] = model.new_id("i")
                tail["transition"] = None
            out.append(tail)
    main["items"] = out
    return removed


@op("cut_range", "Remove a stretch of the timeline, from `from` to `to` seconds. What comes after closes the gap.",
    {"from": AT, "to": AT}, ("from", "to"), group="timeline")
def cut_range(p, a):
    lo, hi = sorted((float(a["from"]), float(a["to"])))
    if hi - lo < 0.02:
        raise UserError("הטווח קצר מדי.")
    return {"removed_seconds": round(_cut(p, lo, hi), 3)}


@op("keep_range", "Keep only the stretch of the timeline between `from` and `to` seconds; remove the rest.",
    {"from": AT, "to": AT}, ("from", "to"), group="timeline")
def keep_range(p, a):
    lo, hi = sorted((float(a["from"]), float(a["to"])))
    total = compose.Layout(p).duration
    removed = _cut(p, hi, total + 1) if hi < total else 0.0
    removed += _cut(p, 0, lo) if lo > 0 else 0.0
    return {"removed_seconds": round(removed, 3)}


@op("close_gaps", "Slide the items of a free track together so there are no gaps between them.",
    {"track": STR}, ("track",), group="timeline")
def close_gaps(p, a):
    track = model.track_by_id(p, a["track"])
    if not track:
        raise UserError("הערוץ לא נמצא.")
    if track.get("main"):
        return {}
    lay = compose.Layout(p)
    t = None
    for it in sorted(track["items"], key=lambda i: i["start"]):
        t = it["start"] if t is None else t
        it["start"] = round(t, 3)
        t += lay.items[it["id"]]["map"].dur
    return {"_keep_free_items": True}


@op("add_track", "Add a track. Video tracks above the main one hold B-roll and overlays.",
    {"kind": {"type": "string", "enum": ["video", "audio", "text"]}}, ("kind",), group="timeline")
def add_track(p, a):
    if a["kind"] not in ("video", "audio", "text"):
        raise UserError("סוג ערוץ לא מוכר.")
    if sum(1 for t in p["tracks"] if t["kind"] == a["kind"]) >= 6:
        raise UserError("הגענו למספר הערוצים המרבי מהסוג הזה.")
    t = model.new_track(a["kind"])
    if a["kind"] == "audio":
        p["tracks"].append(t)
    elif a["kind"] == "text":
        p["tracks"].insert(0, t)
    else:
        first_video = next(i for i, x in enumerate(p["tracks"]) if x["kind"] == "video")
        p["tracks"].insert(first_video, t)
    model.name_tracks(p)
    return {"track": t["id"], "name": t["name"], "_keep_free_items": True}


@op("remove_track", "Delete a track and everything on it. The main track cannot be deleted.",
    {"track": STR}, ("track",), group="timeline")
def remove_track(p, a):
    t = model.track_by_id(p, a["track"])
    if not t:
        raise UserError("הערוץ לא נמצא.")
    if t.get("main"):
        raise UserError("את הערוץ הראשי אי אפשר למחוק.")
    p["tracks"].remove(t)
    return {"_keep_free_items": True}


@op("set_track", "Mute or hide a whole track.", {"track": STR, "muted": BOOL, "hidden": BOOL}, ("track",),
    group="timeline")
def set_track(p, a):
    t = model.track_by_id(p, a["track"])
    if not t:
        raise UserError("הערוץ לא נמצא.")
    for key in ("muted", "hidden"):
        if key in a:
            t[key] = bool(a[key])
    return {"_keep_free_items": True}


# ------------------------------------------------------------------- words

@op("get_transcript", "The transcript of what is on the timeline, as numbered words per media file "
                      "(index|word). Deleted words are left out.", {"media": MEDIA}, mutates=False, group="words")
def get_transcript(p, a):
    out = []
    for mid in ([a["media"]] if a.get("media") else _timeline_media(p)):
        m = _media(p, mid)
        text = " ".join(f"{i}|{w['t']}" for i, w in enumerate(m["words"]) if not w.get("d") and w["t"].strip())
        out.append({"media": mid, "name": m["name"], "words": len(m["words"]),
                    "deleted": sum(1 for w in m["words"] if w.get("d")), "text": text})
    return {"transcripts": out}


def _timeline_media(p: dict) -> list[str]:
    seen: list[str] = []
    for it in model.main_track(p)["items"]:
        if it["media"] not in seen and p["media"][it["media"]]["words"]:
            seen.append(it["media"])
    for t in p["tracks"]:
        if t["kind"] == "audio":
            for it in t["items"]:
                if it["media"] not in seen and p["media"][it["media"]]["words"]:
                    seen.append(it["media"])
    return seen


def _flag(m: dict, lo: int, hi: int, deleted: bool) -> int:
    n = len(m["words"])
    lo, hi = max(0, min(lo, hi)), min(n - 1, max(lo, hi))
    count = 0
    for i in range(lo, hi + 1):
        w = m["words"][i]
        if bool(w.get("d")) != deleted:
            count += 1
            if deleted:
                w["d"] = True
            else:
                w.pop("d", None)
    return count


@op("delete_words", "Cut words out of the video by their index in the transcript (inclusive range).",
    {"media": MEDIA, "from": INT, "to": INT}, ("media", "from", "to"), group="words")
def delete_words(p, a):
    return {"changed": _flag(_media(p, a["media"]), int(a["from"]), int(a["to"]), True)}


@op("restore_words", "Bring back words that were cut, by their index in the transcript (inclusive range).",
    {"media": MEDIA, "from": INT, "to": INT}, ("media", "from", "to"), group="words")
def restore_words(p, a):
    return {"changed": _flag(_media(p, a["media"]), int(a["from"]), int(a["to"]), False)}


@op("set_words", "Set which words of a media file are cut, as a string of 0 and 1 with one character per word.",
    {"media": MEDIA, "flags": STR}, ("media", "flags"), group="words")
def set_words(p, a):
    m = _media(p, a["media"])
    flags = str(a["flags"])
    if len(flags) != len(m["words"]):
        raise UserError("אורך הסימון לא תואם למספר המילים.")
    for w, f in zip(m["words"], flags):
        if f == "1":
            w["d"] = True
        else:
            w.pop("d", None)


@op("edit_word", "Fix the spelling of a transcribed word. Changes the transcript and captions, not the sound.",
    {"media": MEDIA, "index": INT, "text": STR}, ("media", "index", "text"), group="words")
def edit_word(p, a):
    m = _media(p, a["media"])
    i = int(a["index"])
    if not 0 <= i < len(m["words"]):
        raise UserError("המילה לא נמצאה.")
    w = m["words"][i]
    val = " ".join(str(a["text"]).split())[:80]
    orig = w.get("o", w["t"])
    if val == orig:
        w["t"] = orig
        w.pop("o", None)
    elif val != w["t"]:
        w.setdefault("o", w["t"])
        w["t"] = val
    return {"_keep_free_items": True}


@op("delete_text", "Find a phrase in the transcript and cut it out of the video. Cuts every occurrence unless "
                   "`first_only` is true.", {"text": STR, "first_only": BOOL, "media": MEDIA}, ("text",), group="words")
def delete_text(p, a):
    want = [t for t in (cleanup.norm(x) for x in str(a["text"]).split()) if t]
    if not want:
        raise UserError("חסר טקסט לחיפוש.")
    hits = 0
    for mid in ([a["media"]] if a.get("media") else _timeline_media(p)):
        m = _media(p, mid)
        live = [i for i, w in enumerate(m["words"]) if not w.get("d") and cleanup.norm(w["t"])]
        k = 0
        while k + len(want) <= len(live):
            if [cleanup.norm(m["words"][i]["t"]) for i in live[k:k + len(want)]] == want:
                for i in live[k:k + len(want)]:
                    m["words"][i]["d"] = True
                hits += 1
                if a.get("first_only"):
                    return {"occurrences_cut": hits}
                k += len(want)
            else:
                k += 1
    if not hits:
        raise UserError("הטקסט לא נמצא בתמלול.")
    return {"occurrences_cut": hits}


_LEVELS = {"off": None, "gentle": 0.6, "normal": 0.35, "tight": 0.2}


@op("remove_silences", "Shorten pauses between words across the whole main track. level: off, gentle, normal, "
                       "tight, or a number of seconds to leave.",
    {"level": {"description": "off | gentle | normal | tight | seconds"}}, ("level",), group="words")
def remove_silences(p, a):
    lv = a["level"]
    if isinstance(lv, str) and lv in _LEVELS:
        p["tighten"] = _LEVELS[lv]
    else:
        try:
            p["tighten"] = float(lv) or None
        except (TypeError, ValueError):
            raise UserError("רמה לא מוכרת.")
    return {"pause_tightening": p["tighten"]}


def _sweep(p: dict, finder) -> int:
    n = 0
    for mid in _timeline_media(p):
        m = p["media"][mid]
        for i in finder(m["words"]):
            m["words"][i]["d"] = True
            n += 1
    return n


@op("remove_fillers", "Cut filler sounds (um, uh and their Hebrew equivalents) from the transcript.", group="words")
def remove_fillers(p, a):
    return {"words_cut": _sweep(p, cleanup.find_fillers)}


@op("remove_repeats", "Cut words and two-word phrases that were said twice in a row.", group="words")
def remove_repeats(p, a):
    return {"words_cut": _sweep(p, cleanup.find_repeats)}


@op("restore_all_words", "Bring back every word that was cut from the transcript.", group="words")
def restore_all_words(p, a):
    n = 0
    for m in p["media"].values():
        for w in m["words"]:
            if w.pop("d", None):
                n += 1
    return {"words_restored": n}


# ---------------------------------------------------------- captions, text

@op("set_captions", "Turn captions on or off and style them. `preset` picks a ready style; `style` overrides single "
                    "fields (font, size, y, max_words, color, highlight, active_color, bg, bg_color, stroke, shadow). "
                    "`mode` chooses original language, translated, or both.",
    {"enabled": BOOL, "preset": {"type": "string", "enum": [x["id"] for x in captions.PRESETS]},
     "style": {"type": "object"}, "mode": {"type": "string", "enum": ["original", "translated", "both"]},
     "language": {"type": "string", "description": "Target language of the translation, e.g. en or he."}},
    group="captions")
def set_captions(p, a):
    cap = p["captions"]
    if "enabled" in a:
        cap["enabled"] = bool(a["enabled"])
    if "preset" in a:
        pre = next((x for x in captions.PRESETS if x["id"] == a["preset"]), None)
        if not pre:
            raise UserError("הסגנון לא קיים.")
        cap["style"] = captions.clean_style({**pre["style"], "preset": pre["id"]})
    if isinstance(a.get("style"), dict):
        merged = {**cap["style"], **a["style"]}
        if "preset" not in a["style"] and "preset" not in a:
            merged["preset"] = ""
        cap["style"] = captions.clean_style(merged)
    if "mode" in a:
        cap["mode"] = a["mode"]
    if "language" in a:
        cap["lang"] = a["language"]
    return {"_keep_free_items": True}


@op("list_caption_presets", "List the ready-made caption styles.", mutates=False, group="captions")
def list_caption_presets(p, a):
    return {"presets": [{"id": x["id"], "name": x["name"]} for x in captions.PRESETS]}


TITLE_PRESETS = [
    {"id": "headline", "name": "כותרת", "style": {"font": "Heebo-Black", "size": 0.1, "y": 0.2, "color": "#FFFFFF",
                                                   "bg": "none", "shadow": 0.9, "stroke": 0.0}},
    {"id": "tag", "name": "תגית", "style": {"font": "Heebo-Black", "size": 0.062, "y": 0.14, "color": "#1E1E24",
                                             "bg": "pill", "bg_color": "#FFD84D", "shadow": 0.4}},
    {"id": "lower", "name": "שם ותפקיד", "style": {"font": "Assistant-ExtraBold", "size": 0.05, "y": 0.84,
                                                    "color": "#FFFFFF", "bg": "block", "bg_color": "#303039",
                                                    "bg_opacity": 0.9, "shadow": 0.3}},
    {"id": "big", "name": "ענק", "style": {"font": "Karantina-Bold", "size": 0.15, "y": 0.45, "color": "#FFFFFF",
                                            "bg": "none", "stroke": 0.06, "shadow": 0.8}},
    {"id": "brand", "name": "ורוד", "style": {"font": "Rubik-ExtraBold", "size": 0.075, "y": 0.2, "color": "#FFFFFF",
                                               "bg": "pill", "bg_color": "#C2337A", "shadow": 0.5}},
    {"id": "quote", "name": "ציטוט", "style": {"font": "FrankRuhlLibre-Black", "size": 0.07, "y": 0.5,
                                                "color": "#FFF6E8", "bg": "none", "shadow": 0.9}},
]


@op("add_text", "Put a title on screen at a timeline time. `preset` picks a ready title style.",
    {"text": STR, "at": AT, "duration": NUM, "preset": {"type": "string", "enum": [x["id"] for x in TITLE_PRESETS]},
     "style": {"type": "object"}, "track": STR}, ("text", "at"), group="text")
def add_text(p, a):
    track = model.track_by_id(p, a["track"]) if a.get("track") else model.first_track(p, "text")
    if track is None:
        track = model.new_track("text")
        p["tracks"].insert(0, track)
    if track["kind"] != "text":
        raise UserError("טקסט שייך לערוץ טקסט.")
    pre = next((x for x in TITLE_PRESETS if x["id"] == a.get("preset", "headline")), TITLE_PRESETS[0])
    style = {**pre["style"], "preset": pre["id"], **(a.get("style") if isinstance(a.get("style"), dict) else {})}
    it = model.new_text_item(str(a["text"]), float(a["at"]), _f(a.get("duration"), 0.3, 600, 3.0), style)
    track["items"].append(it)
    return {"item": it["id"], "track": track["id"], "_keep_free_items": True}


@op("list_title_presets", "List the ready-made title styles.", mutates=False, group="text")
def list_title_presets(p, a):
    return {"presets": [{"id": x["id"], "name": x["name"]} for x in TITLE_PRESETS]}


@op("list_sound_effects", "List the built-in sound effects.", mutates=False, group="sound")
def list_sound_effects(p, a):
    return {"effects": sfx.listing()}
