"""A small Unicode bidi implementation for single caption lines.

Pillow can only be relied on for left-to-right drawing (its complex-text engine
needs a system library that is missing on most Macs), so captions are reordered
here into visual order and then drawn glyph run by glyph run.

Covers the implicit algorithm (rules W1-W7, N1-N2, I1-I2, L1-L4) for one
paragraph, which is everything a caption needs: Hebrew or Arabic mixed with
Latin words, numbers and punctuation. Explicit embedding controls are dropped.
"""
from __future__ import annotations

import unicodedata

_STRONG_R = ("R", "AL")
_NEUTRAL = ("B", "S", "WS", "ON")
_DROP = ("LRE", "RLE", "LRO", "RLO", "PDF", "LRI", "RLI", "FSI", "PDI", "BN")
_MIRROR = {"(": ")", ")": "(", "[": "]", "]": "[", "{": "}", "}": "{",
           "<": ">", ">": "<", "«": "»", "»": "«"}


def has_rtl(text: str) -> bool:
    return any(unicodedata.bidirectional(c) in _STRONG_R for c in text)


def reorder(text: str, rtl: bool | None = None) -> list[tuple[int, str]]:
    """Return the characters of `text` in visual (left to right) order.

    Each item is (index in the original string, character to draw). The
    character differs from the original only for mirrored brackets.
    """
    if rtl is None:
        rtl = has_rtl(text)
    idx = [i for i, c in enumerate(text) if unicodedata.bidirectional(c) not in _DROP]
    n = len(idx)
    if n == 0:
        return []
    types = [unicodedata.bidirectional(text[i]) or "ON" for i in idx]
    base = 1 if rtl else 0
    sor = "R" if rtl else "L"

    # W1: non-spacing marks take the type of the previous character
    for i in range(n):
        if types[i] == "NSM":
            types[i] = types[i - 1] if i else sor
    # W2: European numbers after Arabic letters become Arabic numbers
    last = sor
    for i in range(n):
        if types[i] in ("L", "R", "AL"):
            last = types[i]
        elif types[i] == "EN" and last == "AL":
            types[i] = "AN"
    # W3
    types = ["R" if t == "AL" else t for t in types]
    # W4: a single separator between two numbers joins them
    for i in range(1, n - 1):
        if types[i] == "ES" and types[i - 1] == "EN" and types[i + 1] == "EN":
            types[i] = "EN"
        elif types[i] == "CS" and types[i - 1] == types[i + 1] and types[i - 1] in ("EN", "AN"):
            types[i] = types[i - 1]
    # W5: terminators next to European numbers join them
    i = 0
    while i < n:
        if types[i] == "ET":
            j = i
            while j < n and types[j] == "ET":
                j += 1
            if (i and types[i - 1] == "EN") or (j < n and types[j] == "EN"):
                for k in range(i, j):
                    types[k] = "EN"
            i = j
        else:
            i += 1
    # W6
    types = ["ON" if t in ("ES", "ET", "CS") else t for t in types]
    # W7: European numbers after Latin text behave like Latin text
    last = sor
    for i in range(n):
        if types[i] in ("L", "R"):
            last = types[i]
        elif types[i] == "EN" and last == "L":
            types[i] = "L"

    # N1 / N2: neutrals take the direction of their surroundings
    def strong(t: str) -> str:
        return "R" if t in ("R", "EN", "AN") else "L"

    i = 0
    while i < n:
        if types[i] in _NEUTRAL:
            j = i
            while j < n and types[j] in _NEUTRAL:
                j += 1
            before = strong(types[i - 1]) if i else sor
            after = strong(types[j]) if j < n else sor
            fill = before if before == after else sor
            for k in range(i, j):
                types[k] = fill
            i = j
        else:
            i += 1

    # I1 / I2: implicit levels
    levels = []
    for t in types:
        if base == 0:
            levels.append(1 if t == "R" else 2 if t in ("EN", "AN") else 0)
        else:
            levels.append(1 if t == "R" else 2)
    # L1: trailing whitespace returns to the paragraph level
    k = n - 1
    while k >= 0 and unicodedata.bidirectional(text[idx[k]]) in ("WS", "B", "S"):
        levels[k] = base
        k -= 1

    # L2: reverse runs from the highest level down to the lowest odd level
    order = list(range(n))
    top = max(levels)
    lowest_odd = min((lv for lv in levels if lv % 2), default=top + 1)
    for lv in range(top, lowest_odd - 1, -1):
        i = 0
        while i < n:
            if levels[order[i]] >= lv:
                j = i
                while j < n and levels[order[j]] >= lv:
                    j += 1
                order[i:j] = reversed(order[i:j])
                i = j
            else:
                i += 1

    out: list[tuple[int, str]] = []
    for pos in order:
        ch = text[idx[pos]]
        if levels[pos] % 2 and ch in _MIRROR:  # L4
            ch = _MIRROR[ch]
        out.append((idx[pos], ch))

    # L3: in right-to-left runs combining marks must follow their base letter
    i = 0
    while i < len(out):
        if unicodedata.combining(out[i][1]):
            j = i
            while j < len(out) and unicodedata.combining(out[j][1]):
                j += 1
            if j < len(out) and out[j][0] == out[j - 1][0] - 1:
                out[i:j + 1] = reversed(out[i:j + 1])
            i = j + 1
        else:
            i += 1
    return out


def display(text: str, rtl: bool | None = None) -> str:
    return "".join(ch for _, ch in reorder(text, rtl))
