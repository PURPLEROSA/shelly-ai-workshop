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


# ------------------------------------------------------------ translation

LANG_NAMES = {"he": "Hebrew", "en": "English", "ar": "Arabic", "ru": "Russian", "fr": "French", "es": "Spanish"}

TRANSLATE_SYSTEM = """You translate the subtitles of a video. You receive numbered lines, each one a sentence spoken in the video. Translate every line into {language}, keeping the speaker's tone and register: natural spoken language, not a literal word-for-word rendering. Keep names and product names as they are. Do not merge, split, drop or reorder lines.

Reply with JSON only, in this shape:
{{"lines": [{{"n": 0, "text": "..."}}]}}"""

LINES_SCHEMA = {
    "type": "object",
    "properties": {"lines": {"type": "array", "items": {
        "type": "object", "properties": {"n": {"type": "integer"}, "text": {"type": "string"}},
        "required": ["n", "text"], "additionalProperties": False}}},
    "required": ["lines"], "additionalProperties": False,
}


def sentences(words: list[dict]) -> list[dict]:
    """Group words into sentences: {s, e, text, first, last}."""
    out, cur = [], []
    for i, w in enumerate(words):
        if not w["t"].strip():
            continue
        if cur:
            prev = words[cur[-1]]
            if prev["t"].rstrip("\"'”’)")[-1:] in ".?!…" or w["s"] - prev["e"] > 1.2 or len(cur) >= 28:
                out.append(cur)
                cur = []
        cur.append(i)
    if cur:
        out.append(cur)
    return [{"s": words[ix[0]]["s"], "e": words[ix[-1]]["e"], "first": ix[0], "last": ix[-1],
             "text": " ".join(words[i]["t"] for i in ix)} for ix in out]


def spread_words(text: str, s: float, e: float) -> list[dict]:
    """Give the words of a translated sentence timings spread across the sentence's span."""
    parts = text.split()
    if not parts:
        return []
    weights = [len(p) + 1.5 for p in parts]
    total = sum(weights)
    out, t = [], s
    for part, wgt in zip(parts, weights):
        d = (e - s) * wgt / total
        out.append({"t": part, "s": round(t, 3), "e": round(t + d, 3)})
        t += d
    return out


def translate_words(words: list[dict], lang: str, on_progress=None) -> list[dict]:
    """Translate a transcript. Returns timed words in the target language."""
    sents = sentences(words)
    if not sents:
        return []
    system = TRANSLATE_SYSTEM.format(language=LANG_NAMES.get(lang, lang))
    out: list[dict] = []
    batch = 40
    for start in range(0, len(sents), batch):
        chunk = sents[start:start + batch]
        user = "\n".join(f"{n}: {s['text']}" for n, s in enumerate(chunk))
        data = extract_json(complete(system, user, LINES_SCHEMA))
        got = {}
        for line in data.get("lines") or []:
            try:
                got[int(line["n"])] = " ".join(str(line["text"]).split())
            except (KeyError, TypeError, ValueError):
                continue
        if len(got) < max(1, len(chunk) // 2):
            raise UserError("המודל לא החזיר תרגום מלא. מנסים שוב, או בוחרים מודל חזק יותר.")
        for n, s in enumerate(chunk):
            out.extend(spread_words(got.get(n, ""), s["s"], s["e"]))
        if on_progress:
            on_progress(min(1.0, (start + batch) / len(sents)))
    return out


# ------------------------------------------------------- the in-app editor

PLAN_SYSTEM = """You are the editor inside a video editing studio. The person tells you what they want, and you answer with the list of studio operations that does it. The studio runs your operations in order.

You get a description of the project (tracks, items, timing), the transcript as numbered words (index|word) per media file, and the catalogue of operations with their parameters. Times are timeline seconds unless a parameter says otherwise.

How to work:
- Use only operations from the catalogue, with only the parameters they list.
- Prefer the fewest operations that fully do the job. For cutting speech, use delete_words with the word indices and include the exact words in "text" so the cut can be verified.
- When the person names a target length, land as close to it as you can without going over, and keep what remains coherent.
- What is left around every cut must still sound like natural speech.
- If the request cannot be done with these operations, return no steps and say why in the summary.

Write "summary" (one or two sentences on what you did and why) in the language the person wrote in.

Reply with JSON only, in this shape:
{"summary": "...", "steps": [{"op": "operation_name", "args_json": "{\\"param\\": value}"}]}
"args_json" is the operation's arguments as a JSON object written as a string."""

PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "steps": {"type": "array", "items": {
            "type": "object", "properties": {"op": {"type": "string"}, "args_json": {"type": "string"}},
            "required": ["op", "args_json"], "additionalProperties": False}},
    },
    "required": ["summary", "steps"], "additionalProperties": False,
}


def plan(instruction: str, project_description: dict, transcripts: list[dict], catalogue: list[dict]) -> dict:
    """Ask the model for a list of operations. Returns {"summary", "steps": [{"op", "args"}]}."""
    cat = "\n".join(f"- {c['name']}({', '.join(c['params'])}): {c['desc']}" for c in catalogue)
    tx = "\n\n".join(f"Media {t['media']} ({t['name']}):\n{t['text']}" for t in transcripts) or "(no transcript)"
    user = (f"Request: {instruction.strip()}\n\nProject:\n{json.dumps(project_description, ensure_ascii=False)}\n\n"
            f"Transcript:\n{tx}\n\nOperations:\n{cat}")
    data = extract_json(complete(PLAN_SYSTEM, user, PLAN_SCHEMA))
    steps = []
    for s in data.get("steps") or []:
        if not isinstance(s, dict) or not s.get("op"):
            continue
        raw = s.get("args_json", s.get("args", {}))
        if isinstance(raw, str):
            try:
                raw = json.loads(raw) if raw.strip() else {}
            except ValueError:
                raise UserError("המודל החזיר פעולה במבנה לא תקין. מנסים שוב, או בוחרים מודל חזק יותר.")
        steps.append({"op": str(s["op"]), "args": raw if isinstance(raw, dict) else {}})
    return {"summary": str(data.get("summary", ""))[:800], "steps": steps}
