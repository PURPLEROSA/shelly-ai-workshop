"""Narration: text to speech, and cloning a voice from a recording.

Works with Cartesia or ElevenLabs, using the person's own API key.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

from . import config
from .ai.local import _ssl_context
from .jobs import UserError

CARTESIA = "https://api.cartesia.ai"
CARTESIA_VERSION = "2025-04-16"
ELEVEN = "https://api.elevenlabs.io"
PROVIDERS = {"cartesia": "Cartesia", "elevenlabs": "ElevenLabs"}


def _http(url: str, method: str = "GET", headers: dict | None = None, data: bytes | None = None,
          timeout: float = 120) -> bytes:
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_ssl_context()) as res:
            return res.read()
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:300]
        if e.code in (401, 403):
            raise UserError("מפתח ה-API של שירות הקול לא תקין. כדאי לבדוק אותו בהגדרות.")
        if e.code == 402:
            raise UserError("הפעולה הזו לא כלולה בתוכנית הנוכחית שלך בשירות הקול. שיבוט קול דורש בדרך כלל מנוי בתשלום.")
        if e.code == 429:
            raise UserError("הגענו למגבלת השימוש של שירות הקול. מנסים שוב בעוד רגע.")
        raise UserError(f"שירות הקול החזיר שגיאה ({e.code}). {detail}")
    except (urllib.error.URLError, OSError):
        raise UserError("אין חיבור לשירות הקול. בודקים את האינטרנט.")


def _multipart(fields: dict, files: dict) -> tuple[bytes, str]:
    boundary = uuid.uuid4().hex
    parts = []
    for name, value in fields.items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    for name, (filename, content, ctype) in files.items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'
                     f'Content-Type: {ctype}\r\n\r\n'.encode() + content + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def _settings() -> tuple[str, dict, dict]:
    v = config.load_settings()["voice"]
    prov = v.get("provider", "none")
    if prov not in PROVIDERS:
        raise UserError("עדיין לא חובר שירות קול. מחברים אחד בהגדרות, תחת ״קול״.")
    cfg = v[prov]
    if not cfg.get("api_key") and not os.environ.get("STUDIO_VOICE_KEYLESS"):
        raise UserError("חסר מפתח API של שירות הקול. מוסיפים אותו בהגדרות.")
    return prov, cfg, v


def status() -> dict:
    v = config.load_settings()["voice"]
    prov = v.get("provider", "none")
    ok = prov in PROVIDERS and (bool(v[prov].get("api_key")) or bool(os.environ.get("STUDIO_VOICE_KEYLESS")))
    return {"provider": prov, "ready": ok, "label": PROVIDERS.get(prov, ""),
            "voice": v[prov].get("voice_id", "") if prov in PROVIDERS else "",
            "cloned": [c for c in v.get("cloned", []) if c.get("provider") == prov]}


def _cartesia_headers(cfg: dict, extra: dict | None = None) -> dict:
    h = {"Cartesia-Version": CARTESIA_VERSION, **(extra or {})}
    if cfg.get("api_key"):
        h["X-API-Key"] = cfg["api_key"]
    return h


def voices(language: str = "he") -> list[dict]:
    """Voices to choose from: the person's cloned voices first, then the service's own."""
    prov, cfg, v = _settings()
    out = [{"id": c["id"], "name": c["name"], "mine": True} for c in v.get("cloned", []) if c.get("provider") == prov]
    mine = {c["id"] for c in out}
    if prov == "cartesia":
        q = urllib.parse.urlencode({"limit": 100, "language": language})
        data = json.loads(_http(f"{CARTESIA}/voices?{q}", headers=_cartesia_headers(cfg), timeout=20))
        rows = data.get("data", data) if isinstance(data, dict) else data
        for r in rows:
            if r.get("id") not in mine and r.get("language", language) == language:
                out.append({"id": r["id"], "name": r.get("name", ""), "mine": bool(r.get("is_owner")),
                            "gender": r.get("gender", "")})
    else:
        data = json.loads(_http(f"{ELEVEN}/v1/voices", headers={"xi-api-key": cfg["api_key"]}, timeout=20))
        for r in data.get("voices", []):
            if r.get("voice_id") not in mine:
                out.append({"id": r["voice_id"], "name": r.get("name", ""), "mine": r.get("category") == "cloned",
                            "gender": (r.get("labels") or {}).get("gender", "")})
    return out


def synthesize(text: str, out_dir: Path, voice_id: str | None = None, language: str = "he") -> Path:
    """Speak `text` and save it as an audio file in `out_dir`. Returns the file's path."""
    text = " ".join(text.split())
    if not text:
        raise UserError("חסר טקסט לקריינות.")
    if len(text) > 5000:
        raise UserError("הטקסט ארוך מדי לקריינות אחת. מחלקים אותו לכמה קטעים.")
    prov, cfg, _ = _settings()
    vid = voice_id or cfg.get("voice_id")
    if not vid:
        raise UserError("לא נבחר קול. בוחרים קול בלשונית הקריינות.")
    if prov == "cartesia":
        body = {"model_id": "sonic-3", "transcript": text, "voice": {"mode": "id", "id": vid}, "language": language,
                "output_format": {"container": "wav", "encoding": "pcm_s16le", "sample_rate": 44100}}
        audio = _http(f"{CARTESIA}/tts/bytes", "POST",
                      _cartesia_headers(cfg, {"Content-Type": "application/json"}), json.dumps(body).encode(), 300)
        path = out_dir / "narration.wav"
    else:
        body = {"text": text, "model_id": "eleven_v3"}
        audio = _http(f"{ELEVEN}/v1/text-to-speech/{urllib.parse.quote(vid)}?output_format=mp3_44100_128", "POST",
                      {"xi-api-key": cfg["api_key"], "Content-Type": "application/json"}, json.dumps(body).encode(), 300)
        path = out_dir / "narration.mp3"
    if len(audio) < 800:
        raise UserError("שירות הקול החזיר קובץ ריק.")
    path.write_bytes(audio)
    return path


def clone(sample: Path, name: str, language: str = "he") -> dict:
    """Create a voice from a recording and remember it in the settings."""
    prov, cfg, v = _settings()
    name = " ".join(name.split())[:60] or "הקול שלי"
    content = sample.read_bytes()
    if prov == "cartesia":
        body, ctype = _multipart({"name": name, "language": language, "mode": "similarity",
                                  "description": "Cloned in the studio"},
                                 {"clip": (sample.name, content, "audio/wav")})
        data = json.loads(_http(f"{CARTESIA}/voices/clone", "POST", _cartesia_headers(cfg, {"Content-Type": ctype}),
                                body, 300))
        vid = data.get("id")
    else:
        body, ctype = _multipart({"name": name}, {"files": (sample.name, content, "audio/wav")})
        data = json.loads(_http(f"{ELEVEN}/v1/voices/add", "POST",
                                {"xi-api-key": cfg["api_key"], "Content-Type": ctype}, body, 300))
        vid = data.get("voice_id")
    if not vid:
        raise UserError("שיבוט הקול לא הצליח. מנסים עם קטע דיבור נקי וארוך יותר.")
    entry = {"provider": prov, "id": vid, "name": name}
    cloned = [c for c in v.get("cloned", []) if c.get("id") != vid] + [entry]
    config.update_settings({"voice": {"cloned": cloned, prov: {"voice_id": vid}}})
    return entry


def forget(voice_id: str, delete_remote: bool = True) -> None:
    """Remove a cloned voice from the settings and from the service."""
    v = config.load_settings()["voice"]
    entry = next((c for c in v.get("cloned", []) if c.get("id") == voice_id), None)
    if not entry:
        return
    config.update_settings({"voice": {"cloned": [c for c in v["cloned"] if c.get("id") != voice_id]}})
    if delete_remote:
        cfg = v[entry["provider"]]
        try:
            if entry["provider"] == "cartesia":
                _http(f"{CARTESIA}/voices/{urllib.parse.quote(voice_id)}", "DELETE", _cartesia_headers(cfg), timeout=30)
            else:
                _http(f"{ELEVEN}/v1/voices/{urllib.parse.quote(voice_id)}", "DELETE",
                      {"xi-api-key": cfg["api_key"]}, timeout=30)
        except UserError:
            pass
