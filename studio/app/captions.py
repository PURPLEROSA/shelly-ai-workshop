"""Caption rendering. One renderer feeds both the live preview and the export,
so what is seen while editing is exactly what gets burned into the video."""
from __future__ import annotations

import hashlib
import io
import json
import math
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from . import bidi
from .config import FONTS_DIR

SS = 2       # supersampling, for smooth pill edges
REF = 1080   # line breaks are decided at this frame size, so every scale agrees
MAX_LINES = 3
FRAME_USE = 0.88  # share of the frame width a caption may occupy

_FONT_LABELS = {
    "Heebo-Black": "Heebo", "Rubik-ExtraBold": "Rubik", "Assistant-ExtraBold": "Assistant",
    "SecularOne-Regular": "Secular One", "Karantina-Bold": "Karantina",
    "FrankRuhlLibre-Black": "Frank Ruhl Libre", "Fredoka-Bold": "Fredoka", "SuezOne-Regular": "Suez One",
}

DEFAULT_STYLE = {
    "preset": "pill",
    "font": "Heebo-Black",
    "size": 0.062,           # font size as a share of the frame's short side
    "y": 0.72,               # vertical centre of the caption, 0 = top, 1 = bottom
    "max_words": 4,
    "color": "#1E1E24",
    "highlight": "color",    # none | color | box
    "active_color": "#D6246E",
    "active_bg": "#D6246E",
    "bg": "pill",            # none | pill | block
    "bg_color": "#FFFFFF",
    "bg_opacity": 1.0,
    "stroke": 0.0,           # outline width as a share of the font size
    "stroke_color": "#000000",
    "shadow": 0.5,
    "strip_punct": False,
    "upper": False,
}

PRESETS = [
    {"id": "pill", "name": "פיל לבן", "style": {}},
    {"id": "pop", "name": "פופ", "style": {
        "font": "Rubik-ExtraBold", "size": 0.07, "max_words": 3, "color": "#FFFFFF",
        "active_color": "#FFE14D", "bg": "none", "stroke": 0.13, "shadow": 0.6}},
    {"id": "marker", "name": "מרקר", "style": {
        "color": "#FFFFFF", "highlight": "box", "active_color": "#FFFFFF", "active_bg": "#C2337A",
        "bg": "none", "shadow": 0.8, "size": 0.066}},
    {"id": "ink", "name": "דיו ורוד", "style": {
        "font": "Assistant-ExtraBold", "color": "#FFFFFF", "active_color": "#F4B8CA",
        "bg_color": "#303039", "size": 0.064}},
    {"id": "clean", "name": "נקי", "style": {
        "font": "Assistant-ExtraBold", "size": 0.05, "max_words": 6, "color": "#FFFFFF",
        "highlight": "none", "bg": "block", "bg_color": "#000000", "bg_opacity": 0.55,
        "shadow": 0.0, "y": 0.8}},
    {"id": "drama", "name": "דרמה", "style": {
        "font": "Karantina-Bold", "size": 0.105, "max_words": 2, "color": "#FFFFFF",
        "active_color": "#FF4D6D", "bg": "none", "stroke": 0.07, "shadow": 0.7,
        "strip_punct": True}},
    {"id": "serif", "name": "אלגנט", "style": {
        "font": "FrankRuhlLibre-Black", "color": "#FFF6E8", "active_color": "#F4B8CA",
        "bg": "none", "shadow": 0.9, "size": 0.066}},
    {"id": "bubble", "name": "בועה", "style": {
        "font": "Fredoka-Bold", "color": "#FFFFFF", "active_color": "#FFE14D",
        "bg_color": "#8E3FB8", "size": 0.064}},
]

RENDER_KEYS = ("font", "size", "y", "color", "highlight", "active_color", "active_bg", "bg",
               "bg_color", "bg_opacity", "stroke", "stroke_color", "shadow")


def clean_style(style: dict | None) -> dict:
    """Merge user style over the defaults and clamp every value to a safe range."""
    s = dict(DEFAULT_STYLE)
    for k, v in (style or {}).items():
        if k in DEFAULT_STYLE and v is not None:
            s[k] = v

    def num(key: str, lo: float, hi: float) -> None:
        try:
            s[key] = min(hi, max(lo, float(s[key])))
        except (TypeError, ValueError):
            s[key] = DEFAULT_STYLE[key]

    num("size", 0.025, 0.16)
    num("y", 0.05, 0.95)
    num("bg_opacity", 0.0, 1.0)
    num("stroke", 0.0, 0.25)
    num("shadow", 0.0, 1.0)
    try:
        s["max_words"] = min(8, max(1, int(s["max_words"])))
    except (TypeError, ValueError):
        s["max_words"] = DEFAULT_STYLE["max_words"]
    if s["highlight"] not in ("none", "color", "box"):
        s["highlight"] = "color"
    if s["bg"] not in ("none", "pill", "block"):
        s["bg"] = "none"
    for key in ("color", "active_color", "active_bg", "bg_color", "stroke_color"):
        if not _valid_hex(s[key]):
            s[key] = DEFAULT_STYLE[key]
    s["strip_punct"] = bool(s["strip_punct"])
    s["upper"] = bool(s["upper"])
    s["font"] = str(s["font"])
    s["preset"] = str(s.get("preset") or "")
    return s


def _valid_hex(v) -> bool:
    if not isinstance(v, str) or len(v) != 7 or v[0] != "#":
        return False
    try:
        int(v[1:], 16)
        return True
    except ValueError:
        return False


def _rgba(hex_color: str, alpha: float = 1.0) -> tuple[int, int, int, int]:
    v = int(hex_color[1:], 16)
    return (v >> 16) & 255, (v >> 8) & 255, v & 255, int(round(255 * alpha))


# ------------------------------------------------------------------ fonts

def _font_files() -> dict[str, Path]:
    files: dict[str, Path] = {}
    for folder in (FONTS_DIR, FONTS_DIR / "custom"):
        if folder.is_dir():
            for p in sorted(folder.iterdir()):
                if p.suffix.lower() in (".ttf", ".otf") and p.stem != "brand":
                    files.setdefault(p.stem, p)
    return files


def list_fonts() -> list[dict]:
    out = []
    for stem, path in _font_files().items():
        out.append({"id": stem, "label": _FONT_LABELS.get(stem, stem.replace("-", " ")),
                    "hebrew": _has_hebrew(str(path)), "custom": path.parent.name == "custom"})
    return out


def font_path(font_id: str) -> str:
    files = _font_files()
    if font_id in files:
        return str(files[font_id])
    return str(files.get(DEFAULT_STYLE["font"]) or next(iter(files.values())))


@lru_cache(maxsize=96)
def _font(path: str, px: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, px, layout_engine=ImageFont.Layout.BASIC)


@lru_cache(maxsize=64)
def _has_hebrew(path: str) -> bool:
    try:
        f = _font(path, 40)
        return f.getmask("א").getbbox() != f.getmask("￿").getbbox() or \
            bytes(f.getmask("א")) != bytes(f.getmask("￿"))
    except Exception:
        return False


@lru_cache(maxsize=256)
def _body_center(path: str, px: int, hebrew: bool) -> float:
    """Vertical centre of the letter bodies, relative to the baseline (negative = above)."""
    f = _font(path, px)
    _, top, _, bottom = f.getbbox("הבדרת" if hebrew else "HXE", anchor="ls")
    return (top + bottom) / 2


# ----------------------------------------------------------------- layout

def _metrics(style: dict) -> tuple[float, float, float]:
    """(line height, gap between lines, horizontal padding) in font-size units."""
    if style["bg"] == "pill":
        return 1.46, 0.14, 0.46
    if style["bg"] == "block":
        return 1.24, 0.0, 0.5
    if style["highlight"] == "box":
        return 1.3, 0.04, 0.2
    return 1.18, 0.0, 0.1


def band_geometry(style: dict, w: int, h: int) -> tuple[int, int]:
    """(top, height) of the strip of the frame that captions are drawn into."""
    f = style["size"] * min(w, h)
    lh, gap, _ = _metrics(style)
    band_h = int(math.ceil((MAX_LINES * lh + (MAX_LINES - 1) * gap + 1.3) * f))
    band_h = min(h, band_h + band_h % 2)
    top = int(round(style["y"] * h - band_h / 2))
    return max(0, min(h - band_h, top)), band_h


def _layout(texts: tuple[str, ...], path: str, style: dict, w: int, h: int):
    """Decide line breaks and a shrink factor at the reference frame size."""
    scale = min(w, h) / REF
    f_ref = max(8, round(style["size"] * REF))
    font = _font(path, f_ref)
    space = font.getlength(" ")
    widths = [font.getlength(t) for t in texts]
    _, _, pad = _metrics(style)
    max_w = (w / scale) * FRAME_USE - 2 * pad * f_ref - 2 * style["stroke"] * f_ref
    n = len(texts)

    def width(a: int, b: int) -> float:
        return sum(widths[a:b]) + space * (b - a - 1)

    best = None
    for lines in range(1, min(n, MAX_LINES) + 1):
        if lines == 1:
            options = [[(0, n)]]
        elif lines == 2:
            options = [[(0, i), (i, n)] for i in range(1, n)]
        else:
            options = [[(0, i), (i, j), (j, n)] for i in range(1, n - 1) for j in range(i + 1, n)]
        cand = min(options, key=lambda o: max(width(a, b) for a, b in o))
        widest = max(width(a, b) for a, b in cand)
        best = (cand, widest)
        if widest <= max_w:
            return cand, 1.0
    cand, widest = best
    return cand, max(0.35, max_w / widest) if widest > 0 else 1.0


def render(texts: tuple[str, ...], active: int, style: dict, w: int, h: int) -> Image.Image:
    """Draw one caption state as a transparent strip (see band_geometry for its place)."""
    path = font_path(style["font"])
    _, band_h = band_geometry(style, w, h)
    cw, ch = w * SS, band_h * SS
    canvas = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    texts = tuple(t for t in texts if t)
    if not texts:
        return canvas.reduce(SS)
    if style["highlight"] == "none":
        active = -1

    lines, shrink = _layout(texts, path, style, w, h)
    f = style["size"] * min(w, h) * shrink * SS
    font = _font(path, max(6, int(round(f))))
    f = float(font.size)
    lh_k, gap_k, pad_k = _metrics(style)
    lh, gap, pad = lh_k * f, gap_k * f, pad_k * f
    stroke = int(round(style["stroke"] * f))
    rtl = bidi.has_rtl(" ".join(texts))
    center = _body_center(path, font.size, rtl)
    block_h = len(lines) * lh + (len(lines) - 1) * gap
    y = (ch - block_h) / 2

    boxes = []        # background shapes, one per line
    active_box = None
    runs = []         # (x, baseline, text, is_active)
    for a, b in lines:
        line = " ".join(texts[a:b])
        owner = []    # word index for every character of the line, -1 for spaces
        for k in range(a, b):
            owner.extend([k] * len(texts[k]))
            if k < b - 1:
                owner.append(-1)
        visual = bidi.reorder(line, rtl)
        groups: list[list] = []
        for idx, chr_ in visual:
            is_active = owner[idx] == active and active >= 0
            if groups and groups[-1][1] == is_active:
                groups[-1][0] += chr_
            else:
                groups.append([chr_, is_active])
        sizes = [font.getlength(g[0]) for g in groups]
        total = sum(sizes)
        x = (cw - total) / 2
        baseline = y + lh / 2 - center
        boxes.append((x - pad, y, x + total + pad, y + lh))
        for (text, is_active), size in zip(groups, sizes):
            runs.append((x, baseline, text, is_active))
            if is_active and style["highlight"] == "box":
                lo, hi = x, x + size
                if active_box:
                    lo, hi = min(lo, active_box[0]), max(hi, active_box[2])
                half = 0.6 * f
                mid = y + lh / 2
                active_box = (lo, mid - half, hi, mid + half)
            x += size
        y += lh + gap

    draw = ImageDraw.Draw(canvas)
    shapes = []       # (box, radius, colour)
    if style["bg"] == "pill":
        col = _rgba(style["bg_color"], style["bg_opacity"])
        shapes += [(bx, lh / 2, col) for bx in boxes]
    elif style["bg"] == "block":
        col = _rgba(style["bg_color"], style["bg_opacity"])
        x0 = min(bx[0] for bx in boxes)
        x1 = max(bx[2] for bx in boxes)
        m = 0.22 * f
        shapes.append(((x0, boxes[0][1] - m, x1, boxes[-1][3] + m), 0.3 * f, col))
    if active_box:
        m = 0.2 * f
        box = (active_box[0] - m, active_box[1], active_box[2] + m, active_box[3])
        shapes.append((box, 0.24 * f, _rgba(style["active_bg"])))

    if style["shadow"] > 0:
        sil = Image.new("L", (cw, ch), 0)
        sd = ImageDraw.Draw(sil)
        solid = [s for s in shapes if s[2][3] > 120]
        if solid:
            for box, radius, _ in solid:
                sd.rounded_rectangle(box, radius=radius, fill=255)
            dy, blur, alpha = 0.09 * f, 0.13 * f, 0.42 * style["shadow"]
        else:
            for x, baseline, text, _ in runs:
                sd.text((x, baseline), text, font=font, fill=255, anchor="ls",
                        stroke_width=stroke, stroke_fill=255)
            dy, blur, alpha = 0.05 * f, 0.075 * f, 0.85 * style["shadow"]
        sil = sil.filter(ImageFilter.GaussianBlur(blur))
        sil = sil.point(lambda v: int(v * alpha))
        shadow = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        shadow.paste((0, 0, 0, 255), (0, int(round(dy))), sil)
        canvas = Image.alpha_composite(canvas, shadow)
        draw = ImageDraw.Draw(canvas)

    for box, radius, col in shapes:
        if col[3] >= 255:
            draw.rounded_rectangle(box, radius=radius, fill=col)
        else:
            layer = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
            ImageDraw.Draw(layer).rounded_rectangle(box, radius=radius, fill=col)
            canvas = Image.alpha_composite(canvas, layer)
            draw = ImageDraw.Draw(canvas)

    if stroke:
        sc = _rgba(style["stroke_color"])
        for x, baseline, text, _ in runs:
            draw.text((x, baseline), text, font=font, fill=sc, anchor="ls",
                      stroke_width=stroke, stroke_fill=sc)
    normal, hot = _rgba(style["color"]), _rgba(style["active_color"])
    for x, baseline, text, is_active in runs:
        draw.text((x, baseline), text, font=font, fill=hot if is_active else normal, anchor="ls")
    return canvas.reduce(SS)


def cue_key(texts, active: int, style: dict, w: int, h: int) -> str:
    payload = [list(texts), active if style["highlight"] != "none" else -1,
               [style[k] for k in RENDER_KEYS], w, h]
    return hashlib.sha1(json.dumps(payload, ensure_ascii=False).encode("utf-8")).hexdigest()[:20]


def png_bytes(img: Image.Image, level: int = 3) -> bytes:
    buf = io.BytesIO()
    img.save(buf, "PNG", compress_level=level)
    return buf.getvalue()
