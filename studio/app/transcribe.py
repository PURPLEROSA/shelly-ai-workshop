"""Local speech-to-text with Whisper (faster-whisper). Nothing leaves the computer."""
from __future__ import annotations

import os
import threading
import time
from pathlib import Path

from .config import MODELS_DIR
from .jobs import Job, UserError

os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

MODELS = {
    "ivrit-turbo": {"repo": "ivrit-ai/whisper-large-v3-turbo-ct2", "gb": 1.6,
                    "label": "עברית · מדויק ומהיר (מומלץ)"},
    "ivrit-large": {"repo": "ivrit-ai/whisper-large-v3-ct2", "gb": 3.1,
                    "label": "עברית · הכי מדויק, איטי יותר"},
    "turbo": {"repo": "deepdml/faster-whisper-large-v3-turbo-ct2", "gb": 1.6,
              "label": "כל השפות · מדויק ומהיר"},
    "small": {"repo": "Systran/faster-whisper-small", "gb": 0.5,
              "label": "כל השפות · קל, למחשבים חלשים"},
}
LANGUAGES = [("he", "עברית"), ("en", "אנגלית"), ("ar", "ערבית"), ("ru", "רוסית"),
             ("fr", "צרפתית"), ("es", "ספרדית"), ("auto", "זיהוי אוטומטי")]
_FILES = ["config.json", "model.bin", "tokenizer.json", "vocabulary.json", "vocabulary.txt",
          "preprocessor_config.json"]

_lock = threading.Lock()
_loaded: dict = {"key": None, "model": None, "device": None}


def _repo_dir(repo: str) -> Path:
    return MODELS_DIR / ("models--" + repo.replace("/", "--"))


def is_downloaded(key: str) -> bool:
    from huggingface_hub import snapshot_download
    try:
        snapshot_download(MODELS[key]["repo"], cache_dir=str(MODELS_DIR), local_files_only=True,
                          allow_patterns=_FILES)
        return any(_repo_dir(MODELS[key]["repo"]).glob("snapshots/*/model.bin"))
    except Exception:
        return False


def _dir_size(path: Path) -> int:
    total = 0
    for p in path.rglob("*"):
        try:
            if p.is_file() and not p.is_symlink():
                total += p.stat().st_size
        except OSError:
            pass
    return total


def _download(key: str, job: Job) -> str:
    from huggingface_hub import HfApi, snapshot_download
    repo = MODELS[key]["repo"]
    if is_downloaded(key):
        return snapshot_download(repo, cache_dir=str(MODELS_DIR), local_files_only=True,
                                 allow_patterns=_FILES)
    total = int(MODELS[key]["gb"] * 1e9)
    try:
        info = HfApi().model_info(repo, files_metadata=True)
        total = sum(s.size or 0 for s in info.siblings if s.rfilename in _FILES) or total
    except Exception:
        pass
    done = threading.Event()

    def watch() -> None:
        while not done.wait(0.7):
            got = _dir_size(_repo_dir(repo))
            try:
                job.update(0.02 + 0.28 * min(1.0, got / total),
                           f"מוריד מודל תמלול, פעם אחת בלבד ({got / 1e9:.1f} מתוך {total / 1e9:.1f} GB)")
            except Exception:
                return

    threading.Thread(target=watch, daemon=True).start()
    try:
        return snapshot_download(repo, cache_dir=str(MODELS_DIR), allow_patterns=_FILES)
    except Exception as e:
        raise UserError("הורדת מודל התמלול נכשלה. צריך חיבור לאינטרנט בפעם הראשונה. "
                        f"({type(e).__name__})") from e
    finally:
        done.set()


def _load(key: str, path: str, force_cpu: bool = False):
    from faster_whisper import WhisperModel
    import ctranslate2
    if _loaded["key"] == key and _loaded["model"] is not None and not (force_cpu and _loaded["device"] != "cpu"):
        return _loaded["model"]
    _loaded.update(key=None, model=None, device=None)
    model = None
    device = "cpu"
    if not force_cpu:
        try:
            if ctranslate2.get_cuda_device_count() > 0:
                model = WhisperModel(path, device="cuda", compute_type="float16")
                device = "cuda"
        except Exception:
            model = None
    if model is None:
        threads = max(2, min(8, os.cpu_count() or 4))
        model = WhisperModel(path, device="cpu", compute_type="int8", cpu_threads=threads)
        device = "cpu"
    _loaded.update(key=key, model=model, device=device)
    return model


def _run(model, audio, language: str | None, duration: float, job: Job, lo: float) -> list[dict]:
    segments, _info = model.transcribe(
        audio, language=language, word_timestamps=True, beam_size=5,
        vad_filter=True, vad_parameters={"min_silence_duration_ms": 400},
        condition_on_previous_text=False)
    words: list[dict] = []
    for seg in segments:
        for k, w in enumerate(seg.words or []):
            text = (w.word or "").strip()
            if not text:
                continue
            words.append({"t": text, "s": float(w.start), "e": float(w.end),
                          "p": round(float(w.probability), 2), "b": k == 0})
        job.update(lo + (0.99 - lo) * min(1.0, seg.end / max(duration, 0.1)), "מתמלל…")
    return words


def _tidy(words: list[dict]) -> list[dict]:
    """Glue stray punctuation tokens onto the word before them."""
    out: list[dict] = []
    for w in words:
        if out and not any(c.isalnum() for c in w["t"]):
            out[-1]["t"] += w["t"]
            out[-1]["e"] = max(out[-1]["e"], w["e"])
        else:
            out.append(w)
    return out


def transcribe(src: Path, key: str, language: str, duration: float, job: Job) -> list[dict]:
    if key not in MODELS:
        key = "ivrit-turbo"
    lang = None if language in ("", "auto", None) else language
    job.update(0.02, "מכין את מודל התמלול…")
    path = _download(key, job)
    from . import media
    audio = media.audio_16k(src)
    with _lock:
        job.update(0.3, "טוען את המודל…")
        started = time.time()
        model = _load(key, path)
        try:
            words = _run(model, audio, lang, duration, job, 0.32)
        except RuntimeError:
            if _loaded["device"] == "cpu":
                raise
            # a GPU that is present but missing its runtime libraries: fall back to CPU
            model = _load(key, path, force_cpu=True)
            words = _run(model, audio, lang, duration, job, 0.32)
        print(f"[transcribe] {key} on {_loaded['device']}: {duration:.0f}s of audio "
              f"in {time.time() - started:.0f}s, {len(words)} words")
    return _tidy(words)
