"""Paths, settings and small shared helpers."""
from __future__ import annotations

import json
import os
import secrets
import threading
from copy import deepcopy
from pathlib import Path

APP_NAME = "הסטודיו שלי"
VERSION = "1.0.0"

ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = Path(__file__).resolve().parent / "web"
FONTS_DIR = ROOT / "fonts"
DATA_DIR = Path(os.environ.get("STUDIO_DATA") or ROOT / "data")
PROJECTS_DIR = DATA_DIR / "projects"
MODELS_DIR = DATA_DIR / "models"
SETTINGS_FILE = DATA_DIR / "settings.json"

CLAUDE_MODELS = [
    {"id": "claude-opus-5-5", "label": "Claude Opus 5.5 (מומלץ)"},
    {"id": "claude-sonnet-5-5", "label": "Claude Sonnet 5.5 (מהיר וזול יותר)"},
    {"id": "claude-haiku-5-5", "label": "Claude Haiku 5.5 (הכי מהיר)"},
    {"id": "claude-fable-5-2", "label": "Claude Fable 5.2 (הכי חזק)"},
]

DEFAULT_SETTINGS = {
    "token": "",
    "mobile_access": True,
    "transcribe": {"model": "ivrit-turbo", "language": "he"},
    "ai": {
        "provider": "none",  # none | ollama | claude | openai
        "claude": {"api_key": "", "model": "claude-opus-5-5"},
        "ollama": {"base_url": "http://localhost:11434/v1", "model": ""},
        "openai": {"base_url": "https://api.openai.com/v1", "api_key": "", "model": ""},
    },
}

_lock = threading.RLock()
_cache: dict | None = None


def ensure_dirs() -> None:
    for d in (DATA_DIR, PROJECTS_DIR, MODELS_DIR):
        d.mkdir(parents=True, exist_ok=True)


def _merge(base: dict, extra: dict) -> dict:
    out = deepcopy(base)
    for k, v in (extra or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def write_json(path: Path, data) -> None:
    """Atomic JSON write, so a crash never leaves a half-written file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".{os.getpid()}.{threading.get_ident()}.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def load_settings() -> dict:
    global _cache
    with _lock:
        if _cache is None:
            ensure_dirs()
            stored = read_json(SETTINGS_FILE, {}) or {}
            _cache = _merge(DEFAULT_SETTINGS, stored)
            if not _cache.get("token"):
                _cache["token"] = secrets.token_urlsafe(12)
                _save(_cache)
        return deepcopy(_cache)


def _save(s: dict) -> None:
    write_json(SETTINGS_FILE, s)
    try:
        os.chmod(SETTINGS_FILE, 0o600)
    except OSError:
        pass


def update_settings(patch: dict) -> dict:
    """Merge a patch into the stored settings. Blank secrets keep their old value."""
    global _cache
    with _lock:
        cur = load_settings()
        patch = deepcopy(patch or {})
        patch.pop("token", None)
        for prov in ("claude", "openai"):
            sub = (patch.get("ai") or {}).get(prov)
            if isinstance(sub, dict) and sub.get("api_key") in ("", None, "__keep__"):
                sub.pop("api_key", None)
        new = _merge(cur, patch)
        _cache = new
        _save(new)
        return deepcopy(new)


def public_settings() -> dict:
    """Settings as the browser may see them: secrets are replaced by a flag."""
    s = load_settings()
    s.pop("token", None)
    for prov in ("claude", "openai"):
        key = s["ai"][prov].pop("api_key", "")
        s["ai"][prov]["has_key"] = bool(key)
        s["ai"][prov]["key_hint"] = ("…" + key[-4:]) if len(key) >= 8 else ""
    return s
