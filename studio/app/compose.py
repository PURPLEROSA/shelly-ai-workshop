"""Turns a project document into a concrete timeline.

Everything that plays or exports comes from here: where each item sits in
time, which source frames it shows, and when captions and titles appear.
All positions are whole frames of the canvas frame rate, so the preview and
the export agree to the frame.
"""
from __future__ import annotations

import bisect
import threading
from collections import OrderedDict
from fractions import Fraction

from . import captions, model, timeline

_cue_specs: "OrderedDict[str, tuple]" = OrderedDict()
_cue_guard = threading.Lock()


def canvas_fps(p: dict) -> Fraction:
    choice = p.get("canvas", {}).get("fps", "auto")
    if choice != "auto":
        try:
            return Fraction(max(1, min(60, int(choice))))
        except (TypeError, ValueError):
            pass
    for it in model.main_track(p)["items"]:
        m = p["media"].get(it["media"])
        if m and m["kind"] == "video" and m.get("fps"):
            return timeline.norm_fps(m["fps"])
    for m in p["media"].values():
        if m["kind"] == "video" and m.get("fps"):
            return timeline.norm_fps(m["fps"])
    return Fraction(30)


def _source_dims(p: dict) -> tuple[int, int]:
    for it in model.main_track(p)["items"]:
        m = p["media"].get(it["media"])
        if m and m.get("width") and m.get("height"):
            return m["width"], m["height"]
    for m in p["media"].values():
        if m["kind"] in ("video", "image") and m.get("width") and m.get("height"):
            return m["width"], m["height"]
    return 1080, 1920


def canvas_size(p: dict, quality: str = "1080", ratio: str | None = None) -> tuple[int, int]:
    """Output frame size. `quality` is the short side: 720, 1080 or "source"."""
    ratio = ratio or p.get("canvas", {}).get("ratio", "source")
    short = {"720": 720, "1080": 1080}.get(str(quality))
    rt = model.RATIOS.get(ratio)
    if rt is None:
        w, h = _source_dims(p)
        if short and min(w, h) > short:
            k = short / min(w, h)
            w, h = w * k, h * k
    else:
        s = short or 1080
        a, b = rt
        w, h = (s, s * b / a) if a <= b else (s * a / b, s)
    return max(2, int(round(w / 2)) * 2), max(2, int(round(h / 2)) * 2)


class ItemMap:
    """Converts between an item's source time and timeline time."""

    def __init__(self, start_f: int, dur_f: int, segs: list[tuple[int, int]], speed: float, fps: Fraction):
        f = float(fps)
        self.start = start_f / f
        self.dur = dur_f / f
        self.end = self.start + self.dur
        self.speed = speed
        self.segs = [(a / f, b / f) for a, b in segs]
        self.starts = [s[0] for s in self.segs]
        self.offs = []
        acc = 0.0
        for a, b in self.segs:
            self.offs.append(acc)
            acc += b - a
        self.kept = acc

    def to_tl(self, src: float) -> float:
        if not self.segs:
            return self.start
        k = bisect.bisect_right(self.starts, src) - 1
        if k < 0:
            return self.start
        a, b = self.segs[k]
        pos = self.offs[k] + min(max(src - a, 0.0), b - a)
        return min(self.end, self.start + pos / self.speed)

    def to_src(self, tl: float) -> float:
        if not self.segs:
            return 0.0
        pos = min(max((tl - self.start) * self.speed, 0.0), self.kept)
        k = max(0, bisect.bisect_right(self.offs, pos) - 1)
        a, b = self.segs[k]
        return min(a + (pos - self.offs[k]), b)

    def covers(self, src: float) -> bool:
        k = bisect.bisect_right(self.starts, src) - 1
        return k >= 0 and src < self.segs[k][1]


class Layout:
    def __init__(self, p: dict):
        self.fps = canvas_fps(p)
        self.items: dict[str, dict] = {}
        self.order: list[str] = []          # main track item ids, in play order
        f = self.fps
        main = model.main_track(p)
        t = 0
        prev_d = 0
        for it in main["items"]:
            m = p["media"].get(it["media"])
            segs = item_segments(p, main, it, f) if m else []
            n = sum(b - a for a, b in segs)
            speed = float(it.get("speed") or 1.0)
            d = max(1, int(round(n / speed))) if n else 0
            trans = 0
            tr = it.get("transition")
            if tr and prev_d and d:
                trans = min(int(round(float(tr.get("dur", 0.5)) * f)), prev_d // 2, d // 2)
            start = t - trans
            self.items[it["id"]] = {"track": main["id"], "start_f": start, "dur_f": d, "segs": segs, "speed": speed,
                                    "trans_f": trans, "main": True, "map": ItemMap(start, d, segs, speed, f)}
            self.order.append(it["id"])
            t = start + d
            if d:
                prev_d = d
        self.main_f = t
        total = t
        for tr in p["tracks"]:
            if tr.get("main"):
                continue
            for it in tr["items"]:
                start = max(0, int(round(float(it.get("start", 0)) * f)))
                if tr["kind"] == "text":
                    d = max(1, int(round(float(it.get("dur", 3)) * f)))
                    segs, speed = [], 1.0
                else:
                    m = p["media"].get(it["media"])
                    segs = item_segments(p, tr, it, f) if m else []
                    speed = float(it.get("speed") or 1.0)
                    n = sum(b - a for a, b in segs)
                    d = max(1, int(round(n / speed))) if n else 0
                self.items[it["id"]] = {"track": tr["id"], "start_f": start, "dur_f": d, "segs": segs, "speed": speed,
                                        "trans_f": 0, "main": False, "map": ItemMap(start, d, segs, speed, f)}
                total = max(total, start + d)
        self.total_f = total
        self.duration = float(total / f)

    def main_at(self, t: float) -> str | None:
        """Id of the main item playing at timeline time t (the later one during a transition)."""
        found = None
        for iid in self.order:
            info = self.items[iid]
            if info["dur_f"] and info["map"].start <= t + 1e-6:
                found = iid
        return found


def item_segments(p: dict, track: dict, it: dict, fps: Fraction) -> list[tuple[int, int]]:
    """Source frame ranges an item shows, after trimming and word cuts."""
    m = p["media"][it["media"]]
    fin = max(0, int(round(float(it["in"]) * fps)))
    fout = max(fin + 1, int(round(float(it["out"]) * fps)))
    if m["kind"] == "image":
        return [(0, fout - fin)]
    if track.get("main") and m["words"]:
        keep = timeline.keep_frames(m["words"], m["duration"], fps, p.get("tighten"))
        return [(max(a, fin), min(b, fout)) for a, b in keep if min(b, fout) > max(a, fin)]
    return [(fin, fout)]


class _Identity:
    def __init__(self, duration: float):
        self.duration = duration

    def to_out(self, t: float) -> float:
        return t


def caption_words(p: dict, lay: Layout, lang: str | None, strip: bool, upper: bool) -> list[dict]:
    """Every spoken word that is on the timeline, with its timeline timing."""
    out: list[dict] = []
    sources = []
    for tr in p["tracks"]:
        if tr.get("muted") or (tr["kind"] == "video" and not tr.get("main")) or tr["kind"] == "text":
            continue
        for it in tr["items"]:
            if "media" in it and not it.get("mute"):
                sources.append(it)
    for it in sources:
        m = p["media"].get(it["media"])
        info = lay.items.get(it["id"])
        if not m or not info or not info["dur_f"]:
            continue
        words = m["tr"].get(lang) if lang else m["words"]
        if not words:
            continue
        mp: ItemMap = info["map"]
        lo, hi = float(it["in"]), float(it["out"])
        for w in words:
            if w.get("d") or w["e"] <= lo or w["s"] >= hi:
                continue
            mid = (w["s"] + w["e"]) / 2
            if not mp.covers(min(max(mid, w["s"]), w["e"])):
                continue
            text = timeline.caption_text(w["t"], strip, upper)
            if not text:
                continue
            s, e = mp.to_tl(w["s"]), mp.to_tl(w["e"])
            if e - s < 0.01:
                e = min(mp.end, s + 0.05)
            out.append({"t": text, "s": s, "e": e, "src": it["id"]})
    out.sort(key=lambda w: w["s"])
    return out


def _cues_for(words: list[dict], style: dict, duration: float, w: int, h: int) -> tuple[list[dict], list[dict]]:
    ident = _Identity(duration)
    max_chars = max(10, int((1.55 if style["bg"] != "none" else 1.7) / style["size"]))
    raw: list[tuple[float, float, tuple, int, int]] = []   # start, end, texts, active, chunk number
    n_chunk = 0
    # each speaker is captioned on its own, so two voices never get shuffled into one line
    for src in dict.fromkeys(wd.get("src") for wd in words):
        own = [wd for wd in words if wd.get("src") == src]
        chunks = timeline.build_chunks(own, ident, style["max_words"], max_chars)
        for c in timeline.build_cues(own, ident, chunks, style["highlight"] != "none"):
            raw.append((c["s"], c["e"], tuple(own[i]["t"] for i in chunks[c["chunk"]]), c["active"], n_chunk + c["chunk"]))
        n_chunk += len(chunks)
    raw.sort(key=lambda r: r[0])
    out = []
    spans: dict[int, dict] = {}
    with _cue_guard:
        for k, (s, e, texts, active, chunk) in enumerate(raw):
            if k + 1 < len(raw):
                e = min(e, raw[k + 1][0])   # where voices overlap, the newer line takes over
            if e - s < 0.04:
                continue
            key = captions.cue_key(texts, active, style, w, h)
            _cue_specs[key] = (texts, active, style, w, h)
            _cue_specs.move_to_end(key)
            out.append({"s": round(s, 3), "e": round(e, 3), "k": key})
            span = spans.setdefault(chunk, {"s": round(s, 3), "e": round(e, 3), "t": " ".join(texts)})
            span["e"] = round(e, 3)
        while len(_cue_specs) > 8000:
            _cue_specs.popitem(last=False)
    return out, sorted(spans.values(), key=lambda x: x["s"])


def cue_spec(key: str):
    with _cue_guard:
        return _cue_specs.get(key)


def second_style(style: dict, w: int, h: int) -> dict:
    """Style of the second caption line when two languages are shown together."""
    s = dict(style)
    s["size"] = max(0.025, style["size"] * 0.8)
    s["highlight"] = "none"
    s["y"] = min(0.95, style["y"] + style["size"] * 1.9 * min(w, h) / h)
    return s


def derive(p: dict, quality: str = "1080", ratio: str | None = None) -> dict:
    lay = Layout(p)
    w, h = canvas_size(p, quality, ratio)
    f = float(lay.fps)
    items = {}
    for iid, info in lay.items.items():
        items[iid] = {"start": round(info["start_f"] / f, 4), "dur": round(info["dur_f"] / f, 4),
                      "trans": round(info["trans_f"] / f, 4), "track": info["track"],
                      "segs": [[round(a / f, 4), round(b / f, 4)] for a, b in info["segs"]]}
    cap = p.get("captions") or {}
    style = captions.clean_style(cap.get("style"))
    mode = cap.get("mode", "original")
    lang = cap.get("lang") or "en"
    cues, cues2, caps = [], [], []
    style2 = second_style(style, w, h)
    if cap.get("enabled", True):
        primary_lang = lang if mode == "translated" else None
        words = caption_words(p, lay, primary_lang, style["strip_punct"], style["upper"])
        cues, caps = _cues_for(words, style, lay.duration, w, h)
        if mode == "both":
            words2 = caption_words(p, lay, lang, style["strip_punct"], style["upper"])
            cues2, _ = _cues_for(words2, style2, lay.duration, w, h)
    top, band_h = captions.band_geometry(style, w, h)
    top2, band2_h = captions.band_geometry(style2, w, h)
    titles = []
    for tr in p["tracks"]:
        if tr["kind"] != "text" or tr.get("hidden"):
            continue
        for it in tr["items"]:
            st = captions.clean_style(it.get("style"))
            st["highlight"] = "none"
            texts = tuple(t for t in timeline.caption_text(it.get("text", ""), False, st["upper"]).split(" ") if t)
            if not texts:
                continue
            key = captions.cue_key(texts, -1, st, w, h)
            with _cue_guard:
                _cue_specs[key] = (texts, -1, st, w, h)
            ttop, th = captions.band_geometry(st, w, h)
            info = lay.items[it["id"]]
            titles.append({"id": it["id"], "start": round(info["start_f"] / f, 4), "dur": round(info["dur_f"] / f, 4),
                           "k": key, "top": ttop / h, "height": th / h, "top_px": ttop,
                           "fade": float(it.get("fade", 0.25))})
    return {
        "fps": [lay.fps.numerator, lay.fps.denominator], "frame": {"w": w, "h": h},
        "duration": round(lay.duration, 4), "main_duration": round(lay.main_f / f, 4),
        "items": items, "order": lay.order,
        "cues": cues, "caps": caps, "band": {"top": top / h, "height": band_h / h, "top_px": top},
        "cues2": cues2, "band2": {"top": top2 / h, "height": band2_h / h, "top_px": top2},
        "titles": titles,
        "_layout": lay, "_style": style, "_style2": style2,
    }


def public(d: dict) -> dict:
    return {k: v for k, v in d.items() if not k.startswith("_")}


def reflow(p: dict, old: Layout) -> None:
    """Keep free items attached to the main-track content they sat over.

    After an edit changes the main track's timing, each free item's start is
    mapped from its old timeline time to the source moment underneath it, and
    from there to that moment's new timeline time.
    """
    new = Layout(p)
    if [(i, old.items[i]["start_f"], old.items[i]["dur_f"]) for i in old.order] == \
            [(i, new.items[i]["start_f"], new.items[i]["dur_f"]) for i in new.order]:
        return
    f = float(new.fps)
    main_items = {it["id"]: it for it in model.main_track(p)["items"]}
    by_media: dict[str, list[str]] = {}
    for iid in new.order:
        by_media.setdefault(main_items[iid]["media"], []).append(iid)
    old_end, new_end = old.main_f / float(old.fps), new.main_f / f

    def remap(t: float) -> float:
        if t >= old_end - 1e-6:
            return max(0.0, new_end + (t - old_end))
        src_item = None
        for iid in old.order:
            info = old.items[iid]
            if info["dur_f"] and info["map"].start <= t + 1e-6:
                src_item = iid
        if src_item is None:
            return t
        omap: ItemMap = old.items[src_item]["map"]
        src = omap.to_src(t)
        media = old.items[src_item].get("media_id")
        candidates = [src_item] if src_item in new.items and new.items[src_item].get("main") else []
        candidates += [c for c in by_media.get(media, []) if c != src_item]
        best = None
        for cid in candidates:
            nm: ItemMap = new.items[cid]["map"]
            it = main_items.get(cid)
            if it and float(it["in"]) - 1e-3 <= src <= float(it["out"]) + 1e-3 and new.items[cid]["dur_f"]:
                best = nm.to_tl(src)
                break
        if best is not None:
            return best
        # the content under the item is gone: land on whatever now follows it
        after = old.order[old.order.index(src_item) + 1:]
        for cid in after:
            if cid in new.items and new.items[cid]["dur_f"]:
                return new.items[cid]["map"].start
        return new_end

    for tr in p["tracks"]:
        if tr.get("main"):
            continue
        for it in tr["items"]:
            it["start"] = round(max(0.0, remap(float(it.get("start", 0)))), 3)


def tag_media(lay: Layout, p: dict) -> Layout:
    """Remember which media each main item used, so reflow can follow split clips."""
    for it in model.main_track(p)["items"]:
        if it["id"] in lay.items:
            lay.items[it["id"]]["media_id"] = it["media"]
    return lay


def _clock(t: float, sep: str) -> str:
    ms = int(round(t * 1000))
    hh, ms = divmod(ms, 3600000)
    mm, ms = divmod(ms, 60000)
    ss, ms = divmod(ms, 1000)
    return f"{hh:02d}:{mm:02d}:{ss:02d}{sep}{ms:03d}"


def subtitles(p: dict, kind: str) -> str:
    """The timeline's speech as SRT or VTT captions, or as a plain transcript."""
    lay = Layout(p)
    cap = p.get("captions") or {}
    lang = cap.get("lang") if cap.get("mode") == "translated" else None
    words = caption_words(p, lay, lang, False, False)
    if kind == "txt":
        lines, cur = [], []
        for w in words:
            cur.append(w["t"])
            if w["t"].rstrip("\"'”’)")[-1:] in ".?!…":
                lines.append(" ".join(cur))
                cur = []
        if cur:
            lines.append(" ".join(cur))
        return "\n".join(lines) + "\n"
    ident = _Identity(lay.duration)
    rows = []
    for src in dict.fromkeys(wd.get("src") for wd in words):
        own = [wd for wd in words if wd.get("src") == src]
        chunks = timeline.build_chunks(own, ident, 7, 42)
        for c in timeline.build_cues(own, ident, chunks, False):
            rows.append((c["s"], c["e"], " ".join(own[i]["t"] for i in chunks[c["chunk"]])))
    rows.sort()
    sep = "," if kind == "srt" else "."
    out = [] if kind == "srt" else ["WEBVTT", ""]
    for n, (start, end, text) in enumerate(rows, 1):
        if kind == "srt":
            out.append(str(n))
        out.append(f"{_clock(start, sep)} --> {_clock(end, sep)}")
        out.append(text)
        out.append("")
    return "\n".join(out)


def credits(p: dict) -> str:
    """Attribution lines for the stock media used on the timeline."""
    used = {it["media"] for _, it in model.all_items(p) if "media" in it}
    lines = []
    for mid in used:
        c = (p["media"][mid].get("meta") or {}).get("credit")
        if c:
            who = f" מאת {c['author']}" if c.get("author") else ""
            lines.append(f"{c.get('title') or p['media'][mid]['name']}{who} · {c.get('provider', '')} · "
                         f"{c.get('license', '')} · {c.get('page', '')}".strip(" ·"))
    return "\n".join(sorted(set(lines))) + ("\n" if lines else "")
