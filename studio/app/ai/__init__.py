"""AI editing: turns an instruction into cuts, and a transcript into post copy.

The model only ever proposes which words to cut. The cuts are validated against
the real transcript before anything is applied, and the editor can undo them.
"""
from __future__ import annotations

import json
import re

from .. import timeline
from ..cleanup import norm
from ..config import load_settings
from ..jobs import UserError
from . import claude, local

CUTS_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "cuts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "from": {"type": "integer"},
                    "to": {"type": "integer"},
                    "text": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["from", "to", "text", "reason"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["summary", "cuts"],
    "additionalProperties": False,
}

EDIT_SYSTEM = """You are a senior short-form video editor. You edit a talking-head video by choosing which words of its transcript to cut. The words that remain play in their original order: you cannot reorder, rewrite or add anything.

The transcript is a list of numbered words written as index|word, one spoken passage per line. Each line starts with the time of its first word in the current edit. "(pause 1.2s)" marks silence between two words. Silence is trimmed by a separate tool, so never cut words just because a pause follows them.

How to edit:
- Follow the editor's instruction. When it names a target length, land as close to it as you can without going over, and keep what remains coherent.
- Prefer removing whole thoughts: false starts, repeated takes (keep the best one, usually the last complete one), filler, tangents, and anything that delays or weakens the opening.
- What is left on both sides of every cut must still read as natural, grammatical speech.
- If nothing should go, return an empty list. Do not cut for the sake of cutting.

Write "summary" (one or two sentences on what you changed and why) and each "reason" (a few words) in the language of the transcript.

Reply with JSON only, in this shape:
{"summary": "...", "cuts": [{"from": 12, "to": 19, "text": "the exact words being cut", "reason": "..."}]}
"from" and "to" are word indices, inclusive."""

TEXT_SYSTEM = """You write social media copy for a creator, based on the transcript of their own video. Write in the language of the transcript, in the creator's voice as it sounds there: natural and specific, with no hype clichés and no facts that are not in the transcript. Reply with plain text only, without markdown symbols, ready to paste."""

TEXT_KINDS = {
    "caption": "כתוב קפשן לאינסטגרם ולטיקטוק לסרטון הזה: שורת פתיחה שעוצרת גלילה, שתיים עד ארבע שורות קצרות של ערך, קריאה אחת לפעולה, ובסוף חמישה עד שמונה האשטגים רלוונטיים.",
    "hooks": "הצע שמונה הוקים קצרים לפתיחת הסרטון או לכותרת שלו, עד שמונה מילים כל אחד, בסגנונות שונים זה מזה. מספר אותם.",
    "youtube": "כתוב כותרת ותיאור ליוטיוב: כותרת של עד 60 תווים, תיאור של שלוש עד חמש שורות, ובסוף שורת תגיות מופרדות בפסיקים.",
    "linkedin": "כתוב פוסט ללינקדאין שמבוסס על הסרטון: פתיחה חדה, שלוש עד חמש פסקאות קצרות עם תובנה אחת ברורה, ושאלה לסיום שמזמינה תגובות.",
}


def status() -> dict:
    ai = load_settings()["ai"]
    prov = ai.get("provider", "none")
    if prov == "claude":
        ok = bool(ai["claude"].get("api_key"))
        return {"provider": prov, "ready": ok, "label": "Claude", "model": ai["claude"].get("model") or claude.DEFAULT_MODEL,
                "hint": "" if ok else "חסר מפתח API"}
    if prov == "ollama":
        ok = bool(ai["ollama"].get("model"))
        return {"provider": prov, "ready": ok, "label": "Ollama (מקומי)", "model": ai["ollama"].get("model", ""),
                "hint": "" if ok else "לא נבחר מודל"}
    if prov == "openai":
        ok = bool(ai["openai"].get("model") and ai["openai"].get("base_url"))
        return {"provider": prov, "ready": ok, "label": "OpenAI / תואם", "model": ai["openai"].get("model", ""),
                "hint": "" if ok else "לא נבחר מודל"}
    return {"provider": "none", "ready": False, "label": "", "model": "", "hint": "לא חובר מודל"}


def complete(system: str, user: str, schema: dict | None = None) -> str:
    ai = load_settings()["ai"]
    prov = ai.get("provider", "none")
    if prov == "claude":
        return claude.complete(ai["claude"], system, user, schema)
    if prov == "ollama":
        return local.ollama_complete(ai["ollama"], system, user, schema is not None)
    if prov == "openai":
        return local.openai_complete(ai["openai"], system, user, schema is not None)
    raise UserError("עדיין לא חובר מודל AI. מחברים אחד בהגדרות.")


def _clock(t: float) -> str:
    t = max(0, int(t))
    return f"{t // 60}:{t % 60:02d}"


def transcript_for_model(words: list[dict], tmap: timeline.TimeMap) -> str:
    lines: list[str] = []
    cur: list[str] = []
    prev = None
    for i, w in enumerate(words):
        if w.get("d") or not w["t"].strip():
            continue
        if prev is not None:
            pause = w["s"] - prev["e"]
            ended = prev["t"].rstrip("\"'”’)")[-1:] in ".?!…"
            if cur and (ended or pause > 1.5 or len(cur) > 40):
                lines.append(" ".join(cur))
                cur = []
            if pause >= 0.8:
                (cur if cur else lines).append(f"(pause {pause:.1f}s)")
        if not cur:
            cur.append(f"[{_clock(tmap.to_out(w['s']))}]")
        cur.append(f"{i}|{w['t']}")
        prev = w
    if cur:
        lines.append(" ".join(cur))
    return "\n".join(lines)


def plain_transcript(words: list[dict]) -> str:
    return " ".join(w["t"] for w in words if not w.get("d") and w["t"].strip())


def extract_json(text: str) -> dict:
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    try:
        data = json.loads(text)
    except ValueError:
        a, b = text.find("{"), text.rfind("}")
        if a < 0 or b <= a:
            raise UserError("המודל לא החזיר תשובה במבנה הנדרש. כדאי לנסות שוב, או לבחור מודל חזק יותר.")
        try:
            data = json.loads(text[a:b + 1])
        except ValueError:
            raise UserError("המודל לא החזיר תשובה במבנה הנדרש. כדאי לנסות שוב, או לבחור מודל חזק יותר.")
    if not isinstance(data, dict):
        raise UserError("המודל לא החזיר תשובה במבנה הנדרש.")
    return data


def _tokens(text: str) -> list[str]:
    return [t for t in (norm(x) for x in str(text).split()) if t]


def resolve_cuts(raw_cuts, words: list[dict]) -> tuple[list[dict], int]:
    """Check the model's cuts against the transcript. Returns (cuts, number rejected)."""
    n = len(words)
    normed = [norm(w["t"]) for w in words]
    good: list[dict] = []
    rejected = 0
    for c in raw_cuts if isinstance(raw_cuts, list) else []:
        try:
            a, b = int(c["from"]), int(c["to"])
        except (KeyError, TypeError, ValueError):
            rejected += 1
            continue
        if a > b:
            a, b = b, a
        want = _tokens(c.get("text", ""))
        ok = 0 <= a <= b < n
        if ok and want:
            have = [t for t in normed[a:b + 1] if t]
            if have != want and not (have[:1] == want[:1] and have[-1:] == want[-1:]):
                ok = False
        if not ok and want:
            # the indices drifted; find the quoted words near where the model pointed
            lo, hi = max(0, min(a, n - 1) - 25), min(n, max(b, 0) + 26)
            found = None
            for start in range(lo, hi):
                j, k = start, 0
                while j < n and k < len(want):
                    if not normed[j]:
                        j += 1
                        continue
                    if normed[j] != want[k]:
                        break
                    j, k = j + 1, k + 1
                if k == len(want) and (found is None or abs(start - a) < abs(found[0] - a)):
                    found = (start, j - 1)
            if found:
                a, b = found
                ok = True
        if not ok:
            rejected += 1
            continue
        good.append({"from": a, "to": b, "reason": str(c.get("reason", ""))[:200],
                     "text": " ".join(w["t"] for w in words[a:b + 1])})
    good.sort(key=lambda c: c["from"])
    merged: list[dict] = []
    for c in good:
        if merged and c["from"] <= merged[-1]["to"]:
            merged[-1]["to"] = max(merged[-1]["to"], c["to"])
        else:
            merged.append(c)
    return merged, rejected


def suggest_cuts(p: dict, tmap: timeline.TimeMap, instruction: str) -> dict:
    words = p["words"]
    live = [w for w in words if not w.get("d")]
    if not live:
        raise UserError("אין מילים לערוך.")
    user = (f"Current length: {_clock(tmap.duration)} ({tmap.duration:.1f} s). Words: {len(live)}.\n"
            f"Instruction from the editor: {instruction.strip()}\n\nTranscript:\n"
            + transcript_for_model(words, tmap))
    data = extract_json(complete(EDIT_SYSTEM, user, CUTS_SCHEMA))
    cuts, rejected = resolve_cuts(data.get("cuts"), words)
    indices = sorted({i for c in cuts for i in range(c["from"], c["to"] + 1) if not words[i].get("d")})
    return {"summary": str(data.get("summary", ""))[:800], "cuts": cuts, "indices": indices,
            "rejected": rejected}


def write_text(p: dict, kind: str, instruction: str = "") -> str:
    task = TEXT_KINDS.get(kind) or instruction.strip()
    if not task:
        raise UserError("חסרה הנחיה.")
    if kind in TEXT_KINDS and instruction.strip():
        task += "\nדגש נוסף: " + instruction.strip()
    text = plain_transcript(p["words"])
    if not text:
        raise UserError("אין תמלול לעבוד איתו.")
    out = complete(TEXT_SYSTEM, f"{task}\n\nתמלול הסרטון:\n{text}")
    return out.strip()
