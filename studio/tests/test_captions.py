import numpy as np

from app import captions


def test_every_preset_renders_something():
    for preset in captions.PRESETS:
        style = captions.clean_style(preset["style"])
        img = captions.render(("ככה", "זה", "נראה"), 1, style, 540, 960)
        top, height = captions.band_geometry(style, 540, 960)
        assert img.size == (540, height) and 0 <= top <= 960 - height
        assert np.asarray(img)[..., 3].max() > 200, preset["id"]


def test_empty_caption_is_transparent():
    img = captions.render((), -1, captions.clean_style({}), 540, 960)
    assert np.asarray(img)[..., 3].max() == 0


def test_preview_and_export_break_lines_the_same_way():
    style = captions.clean_style({"size": 0.09, "max_words": 6})
    texts = ("זה", "משפט", "ארוך", "במיוחד", "לכתובית", "אחת")
    path = captions.font_path(style["font"])
    small = captions._layout(texts, path, style, 360, 640)
    big = captions._layout(texts, path, style, 1080, 1920)
    assert small[0] == big[0] and abs(small[1] - big[1]) < 1e-6
    assert len(big[0]) > 1


def test_long_single_word_shrinks_to_fit():
    style = captions.clean_style({"size": 0.14})
    img = captions.render(("supercalifragilisticexpialidocious",), 0, style, 540, 960)
    alpha = np.asarray(img)[..., 3]
    cols = np.where(alpha.max(axis=0) > 0)[0]
    assert cols.min() > 0 and cols.max() < 539


def test_highlight_changes_only_the_active_word():
    style = captions.clean_style({"bg": "none", "shadow": 0, "color": "#FFFFFF", "active_color": "#FF0000"})
    a = np.asarray(captions.render(("אחת", "שתיים"), 0, style, 540, 960)).astype(int)
    b = np.asarray(captions.render(("אחת", "שתיים"), 1, style, 540, 960)).astype(int)
    diff = np.abs(a - b).sum(axis=2).max(axis=0) > 0
    cols = np.where(diff)[0]
    # the two words sit side by side around the centre: right-to-left puts word 0 on the right
    red_a = np.where((a[..., 0] > 200) & (a[..., 1] < 80) & (a[..., 3] > 200))[1]
    red_b = np.where((b[..., 0] > 200) & (b[..., 1] < 80) & (b[..., 3] > 200))[1]
    assert red_a.mean() > red_b.mean()
    assert cols.size > 0


def test_style_is_clamped():
    s = captions.clean_style({"size": 9, "y": -3, "max_words": 99, "color": "red", "bg": "weird", "highlight": 7})
    assert s["size"] <= 0.16 and 0.05 <= s["y"] <= 0.95 and s["max_words"] == 8
    assert s["color"] == captions.DEFAULT_STYLE["color"] and s["bg"] == "none" and s["highlight"] == "color"
