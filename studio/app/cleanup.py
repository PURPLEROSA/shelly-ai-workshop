"""Rule-based clean-up that needs no AI: filler sounds and stuttered repeats."""
from __future__ import annotations

import re

_PUNCT = ".,!?;:…\"“”„«»()[]'׳״-–—"
_FILLER_HE = re.compile(r"^(א+ה+מ*|א+מ+|מ+ה*מ+|ה+מ+מ*|א+ה+ם)$")
_FILLER_EN = re.compile(r"^(u+h+m*|u+m+|e+r+m+|h+m+|m+h+m+|m{2,}|u+h+)$")
# doubled on purpose often enough that removing them would hurt
_KEEP_REPEATS = {"מאוד", "כן", "לא", "ממש", "הרבה", "רגע", "בוא", "בואו", "יאללה", "אוי", "וואו",
                 "טוב", "נו", "די", "very", "really", "no", "yes", "so", "wow", "bye", "ha"}


def norm(text: str) -> str:
    return text.strip().strip(_PUNCT).lower()


def is_filler(text: str) -> bool:
    t = norm(text)
    return bool(t) and bool(_FILLER_HE.match(t) or _FILLER_EN.match(t))


def find_fillers(words: list[dict]) -> list[int]:
    return [i for i, w in enumerate(words) if not w.get("d") and is_filler(w["t"])]


def find_repeats(words: list[dict]) -> list[int]:
    """Earlier copies of an immediately repeated word or two-word phrase."""
    live = [i for i, w in enumerate(words) if not w.get("d") and norm(w["t"])]
    drop: set[int] = set()
    k = 0
    while k < len(live):
        # two-word phrase said twice in a row: "אני חושב אני חושב ש"
        if k + 3 < len(live):
            a, b, c, d = (words[live[k + j]] for j in range(4))
            if norm(a["t"]) == norm(c["t"]) and norm(b["t"]) == norm(d["t"]) \
                    and norm(a["t"]) != norm(b["t"]) and c["s"] - b["e"] < 1.0:
                drop.update((live[k], live[k + 1]))
                k += 2
                continue
        if k + 1 < len(live):
            a, b = words[live[k]], words[live[k + 1]]
            t = norm(a["t"])
            if t == norm(b["t"]) and len(t) >= 2 and t not in _KEEP_REPEATS and b["s"] - a["e"] < 1.0:
                drop.add(live[k])
        k += 1
    return sorted(drop)
