"""Claude, through the official Anthropic SDK."""
from __future__ import annotations

import anthropic

from ..jobs import UserError

DEFAULT_MODEL = "claude-opus-5-5"
# models whose safety classifiers can decline a request and that support server-side fallback
_FALLBACK_MODELS = {"claude-fable-5-2", "claude-fable-5-1", "claude-opus-5-5", "claude-opus-5",
                    "claude-sonnet-5-5"}


def _text(message) -> str:
    if message.stop_reason == "refusal":
        raise UserError("המודל סירב לבקשה הזו. אפשר לנסח אחרת ולנסות שוב.")
    if message.stop_reason == "max_tokens":
        raise UserError("התשובה של המודל נקטעה באמצע. כדאי לנסות הנחיה ממוקדת יותר.")
    return "".join(b.text for b in message.content if b.type == "text")


def complete(cfg: dict, system: str, user: str, schema: dict | None = None) -> str:
    if not cfg.get("api_key"):
        raise UserError("חסר מפתח API של Claude. מוסיפים אותו בהגדרות.")
    client = anthropic.Anthropic(api_key=cfg["api_key"])
    model = cfg.get("model") or DEFAULT_MODEL
    base = {"model": model, "max_tokens": 16000, "system": system,
            "messages": [{"role": "user", "content": user}]}
    output_config: dict = {"effort": "medium"}
    structured = dict(output_config)
    if schema:
        structured["format"] = {"type": "json_schema", "schema": schema}

    # Most capable request first. A 400 means this account or model does not accept
    # one of the optional features, so the next attempt drops it.
    attempts = []
    if model in _FALLBACK_MODELS:
        attempts.append(("beta", {**base, "output_config": structured,
                                  "betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"}))
    attempts.append(("plain", {**base, "output_config": structured}))
    if schema:
        attempts.append(("plain", {**base, "output_config": output_config}))

    try:
        last: Exception | None = None
        for kind, kwargs in attempts:
            try:
                api = client.beta.messages if kind == "beta" else client.messages
                with api.stream(**kwargs) as stream:
                    return _text(stream.get_final_message())
            except anthropic.BadRequestError as e:
                last = e
        raise UserError(f"Claude דחה את הבקשה: {getattr(last, 'message', last)}"[:400])
    except anthropic.AuthenticationError:
        raise UserError("מפתח ה-API של Claude לא תקין. כדאי לבדוק אותו בהגדרות.")
    except anthropic.PermissionDeniedError:
        raise UserError("למפתח ה-API אין הרשאה למודל הזה.")
    except anthropic.NotFoundError:
        raise UserError(f"המודל {model} לא נמצא בחשבון הזה.")
    except anthropic.RateLimitError:
        raise UserError("הגענו למגבלת הקצב של Claude. מחכים רגע ומנסים שוב.")
    except anthropic.APIStatusError as e:
        if e.status_code >= 500:
            raise UserError("השירות של Claude לא זמין כרגע. מנסים שוב בעוד רגע.")
        raise UserError(f"שגיאה מ-Claude ({e.status_code}): {e.message}"[:400])
    except anthropic.APIConnectionError:
        raise UserError("אין חיבור ל-Claude. צריך אינטרנט בשביל מודל בענן.")
