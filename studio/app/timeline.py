"""The editing model: which parts of the source survive, and when captions show.

A project is a list of timed words. Each word is kept or deleted, and pauses
can be tightened. Everything else (the ranges of video to keep, the edited
duration, caption timing) is derived here, so the preview and the export can
never disagree.
"""
from __future__ import annotations

import bisect
import math
from fractions import Fraction

PAD = 0.10        # seconds of air left next to a kept word where a cut begins
EDGE_HEAD = 0.15  # lead-in kept before the first word when pauses are tightened
EDGE_TAIL = 0.30  # tail kept after the last word when pauses are tightened
MIN_TRIM = 0.12   # pauses are only tightened if that removes at least this much


def norm_fps(fps: float | None) -> Fraction:
    """Snap a measured frame rate to a standard one (phones report 29.83, 30.02...)."""
    if not fps or fps <= 0 or math.isnan(fps):
        return Fraction(30)
    fps = min(float(fps), 60.0)
    for ntsc in (Fraction(24000, 1001), Fraction(30000, 1001), Fraction(60000, 1001)):
        if abs(float(ntsc) - fps) / fps < 0.0006:
            return ntsc
    best = min((Fraction(24), Fraction(25), Fraction(30), Fraction(48), Fraction(50), Fraction(60)),
               key=lambda f: abs(float(f) - fps))
    if abs(float(best) - fps) / fps < 0.03:
        return best
    return Fraction(max(1, round(fps)))


def normalize_words(words: list[dict], duration: float) -> list[dict]:
    """Make word times sane: inside the clip, in order, never overlapping."""
    out = []
    prev_end = 0.0
    for w in words:
        s = max(0.0, min(float(w["s"]), duration))
        e = max(0.0, min(float(w["e"]), duration))
        s = max(s, prev_end)
        if e < s + 0.02:
            e = min(duration, s + 0.02)
        if e <= s:
            continue
        nw = dict(w)
        nw["s"], nw["e"] = round(s, 3), round(e, 3)
        out.append(nw)
        prev_end = nw["e"]
    return out


def keep_frames(words: list[dict], duration: float, fps: Fraction,
                tighten: float | None = None) -> list[tuple[int, int]]:
    """Frame ranges [start, end) of the source that survive the edit."""
    total = max(1, int(math.floor(duration * fps + 1e-6)))
    n = len(words)
    if n == 0:
        return [(0, total)]
    kept = [not w.get("d") for w in words]
    if not any(kept):
        return []
    if tighten is not None:
        tighten = max(0.05, float(tighten))

    pieces: list[tuple[float, float]] = []

    def add(a: float, b: float) -> None:
        if b > a:
            pieces.append((a, b))

    for i in range(n + 1):
        a = words[i - 1]["e"] if i else 0.0
        b = words[i]["s"] if i < n else duration
        gap = b - a
        if gap <= 0:
            continue
        left = kept[i - 1] if i else None
        right = kept[i] if i < n else None
        if i == 0:  # before the first word
            if right:
                add(a if tighten is None else b - min(gap, max(tighten / 2, EDGE_HEAD)), b)
        elif i == n:  # after the last word
            if left:
                add(a, b if tighten is None else a + min(gap, max(tighten / 2, EDGE_TAIL)))
        elif left and right:
            if tighten is None or gap <= tighten + MIN_TRIM:
                add(a, b)
            else:
                add(a, a + tighten / 2)
                add(b - tighten / 2, b)
        elif left:
            add(a, a + min(PAD, gap / 2))
        elif right:
            add(b - min(PAD, gap / 2), b)

    for i, w in enumerate(words):
        if kept[i]:
            add(w["s"], w["e"])

    pieces.sort()
    frames: list[list[int]] = []
    for a, b in pieces:
        fa = max(0, min(total, int(round(a * fps))))
        fb = max(0, min(total, int(round(b * fps))))
        if frames and fa <= frames[-1][1]:
            frames[-1][1] = max(frames[-1][1], fb)
        elif fb > fa:
            frames.append([fa, fb])
    return [(a, b) for a, b in frames if b > a]


class TimeMap:
    """Converts between source time and edited (output) time."""

    def __init__(self, frames: list[tuple[int, int]], fps: Fraction):
        self.fps = fps
        self.ranges = [(float(a / fps), float(b / fps)) for a, b in frames]
        self.starts = [r[0] for r in self.ranges]
        self.offsets = []
        acc = 0.0
        for a, b in self.ranges:
            self.offsets.append(acc)
            acc += b - a
        self.duration = acc

    def to_out(self, t: float) -> float:
        if not self.ranges:
            return 0.0
        k = bisect.bisect_right(self.starts, t) - 1
        if k < 0:
            return 0.0
        a, b = self.ranges[k]
        return self.offsets[k] + min(max(t - a, 0.0), b - a)

    def to_src(self, t: float) -> float:
        if not self.ranges:
            return 0.0
        k = max(0, bisect.bisect_right(self.offsets, t) - 1)
        a, b = self.ranges[k]
        return min(a + (t - self.offsets[k]), b)


# ---------------------------------------------------------------- captions

_SENT_END = ".?!…"
_TRAIL = "\"'”’)]»״"
_EDGE_PUNCT = ".,!?;:…\"“”„«»()[]"


def caption_text(text: str, strip_punct: bool, upper: bool) -> str:
    t = " ".join(text.split())
    if strip_punct:
        t = " ".join(p for p in (part.strip(_EDGE_PUNCT) for part in t.split(" ")) if p)
    if upper:
        t = t.upper()
    return t


def _ends_sentence(text: str) -> bool:
    t = text.rstrip(_TRAIL)
    return bool(t) and t[-1] in _SENT_END


def _split_even(n: int, max_words: int) -> list[int]:
    k = math.ceil(n / max_words)
    base, rem = divmod(n, k)
    return [base + 1 if i < rem else base for i in range(k)]


def build_chunks(words: list[dict], tmap: TimeMap, max_words: int = 4,
                 max_chars: int = 26) -> list[list[int]]:
    """Group kept words into caption chunks. Returns lists of word indices."""
    max_words = max(1, int(max_words))
    items = [i for i, w in enumerate(words) if not w.get("d") and w["t"].strip()]
    phrases: list[list[int]] = []
    cur: list[int] = []
    for i in items:
        if cur:
            prev = words[cur[-1]]
            pause = tmap.to_out(words[i]["s"]) - tmap.to_out(prev["e"])
            if _ends_sentence(prev["t"]) or pause > 0.7:
                phrases.append(cur)
                cur = []
        cur.append(i)
    if cur:
        phrases.append(cur)

    def too_long(ix: list[int]) -> bool:
        return len(ix) > 1 and sum(len(words[i]["t"]) for i in ix) + len(ix) - 1 > max_chars

    def fits(ix: list[int]) -> bool:
        return len(ix) <= max_words and not too_long(ix)

    def even(ix: list[int]) -> list[list[int]]:
        """Split a run that is too big into parts of near-equal size."""
        if fits(ix):
            return [ix]
        sizes = _split_even(len(ix), max_words) if len(ix) > max_words else [math.ceil(len(ix) / 2), len(ix) // 2]
        out, pos = [], 0
        for size in sizes:
            part = ix[pos:pos + size]
            pos += size
            if part:
                out.extend(even(part) if too_long(part) else [part])
        return out

    chunks: list[list[int]] = []
    for ph in phrases:
        # commas are the natural places to break, so group whole clauses first
        clauses: list[list[int]] = [[]]
        for i in ph:
            clauses[-1].append(i)
            if words[i]["t"].rstrip(_TRAIL)[-1:] in ",;:":
                clauses.append([])
        group: list[int] = []
        for clause in (c for c in clauses if c):
            if group and not fits(group + clause):
                chunks.extend(even(group))
                group = []
            group = group + clause
        if group:
            chunks.extend(even(group))
    return chunks


def build_cues(words: list[dict], tmap: TimeMap, chunks: list[list[int]],
               per_word: bool) -> list[dict]:
    """Caption cues in edited time: {s, e, chunk, active}. active is -1 for none."""
    cues: list[dict] = []
    total = tmap.duration
    for ci, ix in enumerate(chunks):
        start = tmap.to_out(words[ix[0]]["s"])
        natural_end = tmap.to_out(words[ix[-1]]["e"])
        nxt = tmap.to_out(words[chunks[ci + 1][0]]["s"]) if ci + 1 < len(chunks) else total
        end = nxt if nxt - natural_end < 0.5 else min(natural_end + 0.35, nxt)
        end = min(max(end, start + 0.35), max(nxt, start))
        if end <= start:
            continue
        if not per_word:
            cues.append({"s": start, "e": end, "chunk": ci, "active": -1})
            continue
        marks = [start] + [min(max(tmap.to_out(words[i]["s"]), start), end) for i in ix[1:]] + [end]
        for k in range(len(ix)):
            a, b = marks[k], max(marks[k + 1], marks[k])
            if b - a > 1e-3:
                cues.append({"s": a, "e": b, "chunk": ci, "active": k})
    for c in cues:
        c["s"], c["e"] = round(c["s"], 3), round(c["e"], 3)
    return cues
