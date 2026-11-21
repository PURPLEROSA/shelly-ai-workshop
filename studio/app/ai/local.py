"""Models that are not Claude: Ollama on this computer, or any OpenAI-compatible API."""
from __future__ import annotations

import json
import os
import re
import ssl
import urllib.error
import urllib.request

from ..jobs import UserError


def _ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    if not os.environ.get("SSL_CERT_FILE"):
        try:
            import certifi
            ctx.load_verify_locations(certifi.where())
        except Exception:
            pass
    return ctx


def _request(url: str, body: dict | None = None, key: str = "", timeout: float = 600):
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method="POST" if data else "GET")
    ctx = _ssl_context() if url.lower().startswith("https") else None
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as res:
        return json.loads(res.read().decode("utf-8"))


def _detail(e: urllib.error.HTTPError) -> str:
    try:
        raw = e.read().decode("utf-8", "replace")
        data = json.loads(raw)
        err = data.get("error")
        return (err.get("message") if isinstance(err, dict) else str(err or raw))[:300]
    except Exception:
        return ""


def _strip_thinking(text: str) -> str:
    return re.sub(r"<think>.*?</think>", "", text or "", flags=re.S).strip()


# ----------------------------------------------------------------- Ollama

def _ollama_host(cfg: dict) -> str:
    host = (cfg.get("base_url") or "http://localhost:11434").rstrip("/")
    return host[:-3] if host.endswith("/v1") else host


def ollama_models(cfg: dict) -> list[str]:
    data = _request(_ollama_host(cfg) + "/api/tags", timeout=4)
    return sorted(m["name"] for m in data.get("models", []))


def ollama_complete(cfg: dict, system: str, user: str, want_json: bool) -> str:
    if not cfg.get("model"):
        raise UserError("לא נבחר מודל של Ollama. בוחרים אחד בהגדרות.")
    # Ollama's default context is tiny and silently drops the start of long transcripts
    need = (len(system) + len(user)) // 2 + 4096
    body = {"model": cfg["model"], "stream": False,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "options": {"num_ctx": int(min(65536, max(8192, need)))}}
    if want_json:
        body["format"] = "json"
    try:
        data = _request(_ollama_host(cfg) + "/api/chat", body, timeout=1800)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise UserError(f"המודל {cfg['model']} לא מותקן ב-Ollama. מריצים: ollama pull {cfg['model']}")
        raise UserError(f"שגיאה מ-Ollama ({e.code}). {_detail(e)}")
    except (urllib.error.URLError, OSError):
        raise UserError("Ollama לא רץ במחשב. מפעילים את Ollama ומנסים שוב.")
    return _strip_thinking((data.get("message") or {}).get("content", ""))


# ------------------------------------------------------ OpenAI-compatible

def openai_models(cfg: dict) -> list[str]:
    data = _request((cfg.get("base_url") or "").rstrip("/") + "/models", key=cfg.get("api_key", ""), timeout=10)
    return sorted(m["id"] for m in data.get("data", []) if isinstance(m, dict) and m.get("id"))


def openai_complete(cfg: dict, system: str, user: str, want_json: bool) -> str:
    base = (cfg.get("base_url") or "").rstrip("/")
    if not base or not cfg.get("model"):
        raise UserError("חסרים כתובת או שם מודל. משלימים אותם בהגדרות.")
    body = {"model": cfg["model"],
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    variants = [{**body, "response_format": {"type": "json_object"}}, body] if want_json else [body]
    for i, payload in enumerate(variants):
        try:
            data = _request(base + "/chat/completions", payload, cfg.get("api_key", ""))
            return _strip_thinking(data["choices"][0]["message"]["content"])
        except urllib.error.HTTPError as e:
            if e.code == 400 and i + 1 < len(variants):
                continue  # this server does not know response_format
            if e.code in (401, 403):
                raise UserError("מפתח ה-API לא תקין או חסר הרשאה. כדאי לבדוק אותו בהגדרות.")
            if e.code == 404:
                raise UserError(f"המודל {cfg['model']} לא נמצא בשירות הזה.")
            if e.code == 429:
                raise UserError("הגענו למגבלת הקצב של השירות. מחכים רגע ומנסים שוב.")
            raise UserError(f"שגיאה מהשירות ({e.code}). {_detail(e)}")
        except (urllib.error.URLError, OSError):
            raise UserError("אין חיבור לשירות ה-AI. בודקים את הכתובת ואת האינטרנט.")
        except (KeyError, IndexError, TypeError):
            raise UserError("התקבלה תשובה לא צפויה משירות ה-AI.")
    raise UserError("שירות ה-AI לא החזיר תשובה.")
