"""Colour looks. Each look is a set of per-channel curves plus a 3x3 matrix.

The browser applies the very same curves and matrix as an SVG filter, and the
export bakes them into a 3D LUT for ffmpeg, so preview and export match.
"""
from __future__ import annotations

from pathlib import Path

from . import config
from .config import DATA_DIR

N = 17        # points per curve
CUBE = 33     # 3D LUT size
_LUMA = (0.2126, 0.7152, 0.0722)
_SEPIA = ((0.393, 0.769, 0.189), (0.349, 0.686, 0.168), (0.272, 0.534, 0.131))

# gain/lift/gamma are per channel (r, g, b); contrast pivots on mid grey
LOOKS = [
    {"id": "warm", "name": "חמים", "gain": (1.06, 1.0, 0.92), "sat": 1.08, "contrast": 1.05},
    {"id": "cool", "name": "קריר", "gain": (0.94, 1.0, 1.08), "contrast": 1.05},
    {"id": "vivid", "name": "חי", "sat": 1.35, "contrast": 1.12},
    {"id": "punch", "name": "קונטרסט", "sat": 1.2, "contrast": 1.25},
    {"id": "soft", "name": "רך", "sat": 0.92, "contrast": 0.9, "lift": (0.04, 0.04, 0.04)},
    {"id": "matte", "name": "מט", "sat": 0.85, "contrast": 0.95, "lift": (0.08, 0.08, 0.08)},
    {"id": "film", "name": "פילם", "gain": (1.04, 1.0, 0.94), "lift": (0.05, 0.05, 0.06), "sat": 0.9, "contrast": 1.08},
    {"id": "tealorange", "name": "טורקיז וכתום", "gain": (1.07, 1.0, 0.9), "lift": (0.0, 0.015, 0.06), "sat": 1.1, "contrast": 1.08},
    {"id": "golden", "name": "שעת זהב", "gain": (1.08, 1.02, 0.88), "gamma": (0.94, 0.95, 1.0), "sat": 1.12},
    {"id": "pastel", "name": "פסטל", "gain": (1.03, 1.0, 1.02), "lift": (0.1, 0.1, 0.1), "sat": 0.8, "contrast": 0.85},
    {"id": "bw", "name": "שחור לבן", "sat": 0.0, "contrast": 1.15},
    {"id": "noir", "name": "נואר", "sat": 0.0, "contrast": 1.4},
    {"id": "sepia", "name": "ספיה", "sepia": 0.8, "contrast": 1.05},
]
BY_ID = {look["id"]: look for look in LOOKS}


def curve(look: dict, ch: int) -> list[float]:
    gain = look.get("gain", (1, 1, 1))[ch]
    lift = look.get("lift", (0, 0, 0))[ch]
    gamma = look.get("gamma", (1, 1, 1))[ch]
    contrast = look.get("contrast", 1.0)
    out = []
    for i in range(N):
        x = i / (N - 1)
        y = x ** gamma
        y = (y - 0.5) * contrast + 0.5
        y = lift + (1 - lift) * y
        y *= gain
        out.append(round(min(1.0, max(0.0, y)), 5))
    return out


def matrix(look: dict) -> list[list[float]]:
    s = look.get("sat", 1.0)
    m = [[_LUMA[c] * (1 - s) + (s if r == c else 0.0) for c in range(3)] for r in range(3)]
    k = look.get("sepia", 0.0)
    if k:
        m = [[(1 - k) * (1.0 if r == c else 0.0) + k * _SEPIA[r][c] for c in range(3)] for r in range(3)]
    return [[round(v, 5) for v in row] for row in m]


def describe() -> list[dict]:
    """What the browser needs to build the SVG filters."""
    return [{"id": lk["id"], "name": lk["name"], "curves": [curve(lk, 0), curve(lk, 1), curve(lk, 2)],
             "matrix": matrix(lk)} for lk in LOOKS]


def _interp(table: list[float], x: float) -> float:
    pos = min(max(x, 0.0), 1.0) * (N - 1)
    i = min(int(pos), N - 2)
    return table[i] + (table[i + 1] - table[i]) * (pos - i)


def apply(look: dict, rgb: tuple[float, float, float]) -> tuple[float, float, float]:
    t = [curve(look, c) for c in range(3)]
    v = [_interp(t[c], rgb[c]) for c in range(3)]
    m = matrix(look)
    return tuple(min(1.0, max(0.0, sum(m[r][c] * v[c] for c in range(3)))) for r in range(3))


def cube_path(look_id: str) -> Path | None:
    """Path of the look's .cube file, written on first use."""
    look = BY_ID.get(look_id)
    if not look:
        return None
    folder = DATA_DIR / "looks"
    path = folder / f"{look_id}-v1.cube"
    if path.exists():
        return path
    folder.mkdir(parents=True, exist_ok=True)
    t = [curve(look, c) for c in range(3)]
    m = matrix(look)
    pre = [[_interp(t[c], i / (CUBE - 1)) for i in range(CUBE)] for c in range(3)]
    lines = [f"LUT_3D_SIZE {CUBE}"]
    for b in range(CUBE):
        for g in range(CUBE):
            for r in range(CUBE):
                v = (pre[0][r], pre[1][g], pre[2][b])
                lines.append(" ".join(f"{min(1.0, max(0.0, m[row][0] * v[0] + m[row][1] * v[1] + m[row][2] * v[2])):.5f}"
                                      for row in range(3)))
    tmp = path.with_suffix(".tmp")
    tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    config.replace(tmp, path)
    return path
