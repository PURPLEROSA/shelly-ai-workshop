"""A built-in library of 26 sound effects, synthesised from scratch.

Nothing here is sampled or licensed: every sound is generated with numpy the
first time it is needed and cached as a WAV file.
"""
from __future__ import annotations

import wave
from pathlib import Path

from .config import DATA_DIR

SR = 48000

SFX = [
    ("whoosh", "ווּש", "מעברים"), ("whoosh_fast", "ווּש מהיר", "מעברים"), ("swish", "סוויש", "מעברים"),
    ("riser", "עלייה", "מעברים"), ("downer", "ירידה", "מעברים"), ("swell", "התגברות", "מעברים"),
    ("impact", "בום", "הדגשות"), ("thud", "חבטה", "הדגשות"), ("pop", "פופ", "הדגשות"), ("bubble", "בועה", "הדגשות"),
    ("snap", "אצבע צרידה", "הדגשות"), ("clap", "מחיאת כף", "הדגשות"), ("heartbeat", "דופק", "הדגשות"),
    ("ding", "דינג", "צלילים"), ("chime", "פעמון רוח", "צלילים"), ("bell", "פעמון", "צלילים"),
    ("success", "הצלחה", "צלילים"), ("error", "שגיאה", "צלילים"), ("notify", "התראה", "צלילים"),
    ("coin", "מטבע", "צלילים"), ("sparkle", "נצנוץ", "צלילים"),
    ("click", "קליק", "ממשק"), ("tick", "טיק", "ממשק"), ("type", "הקלדה", "ממשק"), ("shutter", "צמצם מצלמה", "ממשק"),
    ("glitch", "גליץ׳", "ממשק"),
]
NAMES = {s[0]: s[1] for s in SFX}


def _np():
    import numpy as np
    return np


def _t(seconds: float):
    np = _np()
    return np.arange(int(SR * seconds)) / SR


def _noise(n: int, lo: float, hi: float, seed: int):
    """White noise limited to a frequency band."""
    np = _np()
    rng = np.random.default_rng(seed)
    spec = np.fft.rfft(rng.standard_normal(n))
    freqs = np.fft.rfftfreq(n, 1 / SR)
    edge = np.clip((freqs - lo) / max(lo * 0.3, 30), 0, 1) * np.clip((hi - freqs) / max(hi * 0.2, 30), 0, 1)
    out = np.fft.irfft(spec * edge, n)
    return out / (np.abs(out).max() + 1e-9)


def _env(n: int, attack: float, decay: float):
    np = _np()
    t = np.arange(n) / SR
    a = np.clip(t / max(attack, 1e-4), 0, 1)
    return a * np.exp(-np.clip(t - attack, 0, None) / max(decay, 1e-4))


def _bump(n: int, peak: float = 0.5, sharp: float = 2.0):
    """A rise-and-fall shape peaking at `peak` of the way through."""
    np = _np()
    x = np.arange(n) / max(n - 1, 1)
    left = np.clip(x / peak, 0, 1) ** sharp
    right = np.clip((1 - x) / (1 - peak), 0, 1) ** sharp
    return np.minimum(left, right)


def _sweep(n: int, f0: float, f1: float, exp: bool = True):
    np = _np()
    x = np.arange(n) / max(n - 1, 1)
    freq = f0 * (f1 / f0) ** x if exp else f0 + (f1 - f0) * x
    return np.sin(2 * np.pi * np.cumsum(freq) / SR)


def _tone(freq: float, seconds: float, decay: float, attack: float = 0.003, partials=((1, 1.0),)):
    np = _np()
    t = _t(seconds)
    out = sum(a * np.sin(2 * np.pi * freq * k * t) * np.exp(-t * k * 0.6 / max(decay, 1e-4)) for k, a in partials)
    return out * np.clip(t / attack, 0, 1) * np.exp(-t / decay)


def _place(total: float, parts):
    """Mix sounds at given start times (seconds) into one buffer."""
    np = _np()
    out = np.zeros(int(SR * total))
    for start, sig in parts:
        i = int(start * SR)
        seg = sig[: max(0, len(out) - i)]
        out[i:i + len(seg)] += seg
    return out


def _whoosh(seconds: float, seed: int, bright: float):
    np = _np()
    n = int(SR * seconds)
    low, high = _noise(n, 150, 1200, seed), _noise(n, 1200, 9000 * bright, seed + 1)
    x = np.arange(n) / n
    mix = low * (1 - _bump(n, 0.55, 1.0)) * 0.7 + high * _bump(n, 0.55, 1.5)
    return mix * _bump(n, 0.55, 2.2) * (0.9 + 0.1 * np.sin(2 * np.pi * 3 * x))


def _make(name: str):
    np = _np()
    if name == "whoosh":
        return _whoosh(0.9, 11, 1.0)
    if name == "whoosh_fast":
        return _whoosh(0.4, 12, 1.3)
    if name == "swish":
        n = int(SR * 0.28)
        return _noise(n, 2500, 14000, 13) * _bump(n, 0.3, 2.5)
    if name == "riser":
        n = int(SR * 2.0)
        x = np.arange(n) / n
        return (_sweep(n, 180, 2400) * 0.5 + _noise(n, 800, 12000, 14) * 0.6) * x ** 2.2 * np.clip((1 - x) / 0.02, 0, 1)
    if name == "downer":
        n = int(SR * 1.4)
        x = np.arange(n) / n
        return (_sweep(n, 900, 60) * 0.8 + _noise(n, 200, 2000, 15) * 0.2) * (1 - x) ** 1.5 * np.clip(x / 0.01, 0, 1)
    if name == "swell":
        n = int(SR * 1.6)
        x = np.arange(n) / n
        return (_noise(n, 600, 10000, 16) * 0.7 + np.sin(2 * np.pi * 220 * np.arange(n) / SR) * 0.3) * x ** 3 * np.clip((1 - x) / 0.03, 0, 1)
    if name == "impact":
        n = int(SR * 1.3)
        return _sweep(n, 110, 38) * _env(n, 0.002, 0.35) + _noise(n, 60, 900, 17) * _env(n, 0.001, 0.09) * 0.7
    if name == "thud":
        n = int(SR * 0.45)
        return _sweep(n, 150, 55) * _env(n, 0.002, 0.11) + _noise(n, 80, 500, 18) * _env(n, 0.001, 0.03) * 0.4
    if name == "pop":
        n = int(SR * 0.16)
        return _sweep(n, 520, 130) * _env(n, 0.001, 0.035)
    if name == "bubble":
        n = int(SR * 0.2)
        return _sweep(n, 320, 980) * _bump(n, 0.25, 1.2)
    if name == "snap":
        n = int(SR * 0.14)
        return _noise(n, 1800, 6500, 19) * _env(n, 0.0005, 0.018)
    if name == "clap":
        n = int(SR * 0.35)
        burst = _noise(int(SR * 0.05), 900, 5200, 20)
        parts = [(d, burst * _env(len(burst), 0.0005, 0.008)) for d in (0.0, 0.011, 0.022)]
        return _place(0.35, parts + [(0.03, _noise(n - int(0.03 * SR), 800, 4500, 21) * _env(n - int(0.03 * SR), 0.001, 0.07) * 0.8)])
    if name == "heartbeat":
        beat = lambda f: _sweep(int(SR * 0.25), f, f * 0.5) * _env(int(SR * 0.25), 0.004, 0.07)  # noqa: E731
        return _place(1.0, [(0.0, beat(90)), (0.22, beat(75) * 0.8)])
    if name == "ding":
        return _tone(1318.5, 1.2, 0.35, partials=((1, 1.0), (2.76, 0.35), (5.4, 0.12)))
    if name == "chime":
        notes = [(0.0, 1046.5), (0.13, 1318.5), (0.26, 1568.0), (0.39, 2093.0)]
        return _place(1.8, [(s, _tone(f, 1.3, 0.4, partials=((1, 1.0), (3.0, 0.2))) * 0.7) for s, f in notes])
    if name == "bell":
        return _tone(660, 2.2, 0.8, partials=((1, 1.0), (2.0, 0.6), (2.4, 0.4), (3.0, 0.25), (4.5, 0.15), (5.33, 0.1)))
    if name == "success":
        notes = [(0.0, 659.3), (0.11, 830.6), (0.22, 987.8), (0.33, 1318.5)]
        return _place(1.3, [(s, _tone(f, 0.9, 0.25, partials=((1, 1.0), (2, 0.3)))) for s, f in notes])
    if name == "error":
        n = int(SR * 0.42)
        t = np.arange(n) / SR
        buzz = np.sign(np.sin(2 * np.pi * 150 * t)) * 0.5 + np.sign(np.sin(2 * np.pi * 112 * t)) * 0.5
        gate = (np.sin(2 * np.pi * 5 * t) > -0.2).astype(float)
        spec = np.fft.rfft(buzz)
        spec[np.fft.rfftfreq(n, 1 / SR) > 3200] = 0
        return np.fft.irfft(spec, n) * gate * np.clip((n - np.arange(n)) / (0.02 * SR), 0, 1) * np.clip(np.arange(n) / (0.004 * SR), 0, 1)
    if name == "notify":
        return _place(0.9, [(0.0, _tone(880, 0.5, 0.14, partials=((1, 1.0), (4, 0.2)))), (0.16, _tone(1174.7, 0.7, 0.2, partials=((1, 1.0), (4, 0.2))))])
    if name == "coin":
        return _place(0.9, [(0.0, _tone(987.8, 0.12, 0.08)), (0.075, _tone(1318.5, 0.8, 0.22, partials=((1, 1.0), (2, 0.25))))])
    if name == "sparkle":
        rng = np.random.default_rng(22)
        parts = [(i * 0.055 + rng.uniform(0, 0.02), _tone(float(rng.choice([2093, 2637, 3136, 3951, 4186])), 0.5, 0.09) * rng.uniform(0.4, 1))
                 for i in range(14)]
        return _place(1.3, parts)
    if name == "click":
        n = int(SR * 0.05)
        return _noise(n, 1500, 9000, 23) * _env(n, 0.0003, 0.004)
    if name == "tick":
        return _tone(2400, 0.08, 0.012, attack=0.0005)
    if name == "type":
        n = int(SR * 0.09)
        return _noise(n, 1200, 7000, 24) * _env(n, 0.0003, 0.006) + _sweep(n, 180, 90) * _env(n, 0.001, 0.02) * 0.5
    if name == "shutter":
        c = lambda seed: _noise(int(SR * 0.04), 1000, 8000, seed) * _env(int(SR * 0.04), 0.0003, 0.006)  # noqa: E731
        return _place(0.3, [(0.0, c(25)), (0.075, c(26) * 0.9), (0.0, _noise(int(SR * 0.12), 300, 2500, 27) * _bump(int(SR * 0.12), 0.4) * 0.25)])
    if name == "glitch":
        rng = np.random.default_rng(28)
        parts = []
        t = 0.0
        while t < 0.55:
            d = float(rng.uniform(0.015, 0.06))
            n = int(SR * d)
            f = float(rng.choice([220, 440, 880, 1760, 3520]))
            sig = np.sign(np.sin(2 * np.pi * f * np.arange(n) / SR)) * 0.4 if rng.random() < 0.6 else _noise(n, 500, 9000, int(rng.integers(1e6))) * 0.7
            parts.append((t, np.round(sig * 6) / 6))
            t += d + float(rng.uniform(0, 0.03))
        return _place(0.62, parts)
    raise KeyError(name)


def path(name: str) -> Path:
    """The WAV file for an effect, generated on first use."""
    if name not in NAMES:
        raise KeyError(name)
    np = _np()
    folder = DATA_DIR / "sfx"
    out = folder / f"{name}-v1.wav"
    if out.exists():
        return out
    folder.mkdir(parents=True, exist_ok=True)
    sig = np.asarray(_make(name), dtype=np.float64)
    fade = min(len(sig) // 4, int(SR * 0.008))
    sig[-fade:] *= np.linspace(1, 0, fade)
    sig = sig / (np.abs(sig).max() + 1e-9) * 0.8
    pcm = (np.stack([sig, sig], axis=1) * 32767).astype("<i2")
    tmp = out.with_suffix(".tmp")
    with wave.open(str(tmp), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(pcm.tobytes())
    tmp.replace(out)
    return out


def listing() -> list[dict]:
    return [{"id": i, "name": n, "group": g} for i, n, g in SFX]
