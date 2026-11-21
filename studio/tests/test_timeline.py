from fractions import Fraction

from app import timeline

FPS = Fraction(30)


def words(*spec):
    """spec items: (text, start, end[, deleted])"""
    return [{"t": s[0], "s": s[1], "e": s[2], **({"d": True} if len(s) > 3 and s[3] else {})} for s in spec]


def total(frames):
    return sum(b - a for a, b in frames)


def test_fps_snaps_to_standard_rates():
    assert timeline.norm_fps(29.97) == Fraction(30000, 1001)
    assert timeline.norm_fps(30.02) == Fraction(30)
    assert timeline.norm_fps(29.83) == Fraction(30)
    assert timeline.norm_fps(23.976) == Fraction(24000, 1001)
    assert timeline.norm_fps(120) == Fraction(60)
    assert timeline.norm_fps(None) == Fraction(30)


def test_no_edits_keeps_everything():
    w = words(("a", 1.0, 1.5), ("b", 2.0, 2.5))
    assert timeline.keep_frames(w, 10.0, FPS) == [(0, 300)]
    assert timeline.keep_frames([], 10.0, FPS) == [(0, 300)]


def test_all_deleted_keeps_nothing():
    w = words(("a", 1.0, 1.5, True), ("b", 2.0, 2.5, True))
    assert timeline.keep_frames(w, 10.0, FPS) == []


def test_deleting_a_word_removes_its_audio_but_keeps_air():
    w = words(("a", 1.0, 2.0), ("b", 3.0, 4.0, True), ("c", 5.0, 6.0))
    frames = timeline.keep_frames(w, 10.0, FPS)
    assert frames == [(0, 63), (147, 300)]  # 2.0 + 0.1 pad ... 5.0 - 0.1 pad
    # nothing of the deleted word survives
    assert all(not (a < 4.0 * 30 and b > 3.0 * 30) for a, b in frames)


def test_adjacent_deleted_word_is_cut_exactly():
    w = words(("a", 1.0, 2.0), ("b", 2.0, 3.0, True), ("c", 3.0, 4.0))
    assert timeline.keep_frames(w, 5.0, FPS) == [(0, 60), (90, 150)]


def test_tighten_trims_long_pauses_only():
    w = words(("a", 1.0, 2.0), ("b", 2.2, 3.0), ("c", 5.0, 6.0))
    frames = timeline.keep_frames(w, 8.0, FPS, tighten=0.4)
    # head trimmed to 0.2 s, the 0.2 s pause untouched, the 2 s pause cut to 0.4 s, tail to 0.3 s
    assert frames == [(24, 96), (144, 189)]
    assert total(frames) == total([(24, 96), (144, 189)])


def test_tighten_ignores_pauses_barely_over_the_limit():
    w = words(("a", 1.0, 2.0), ("b", 2.45, 3.0))
    frames = timeline.keep_frames(w, 3.0, FPS, tighten=0.4)
    assert len(frames) == 1


def test_timemap_roundtrip():
    frames = [(30, 90), (150, 240)]
    tm = timeline.TimeMap(frames, FPS)
    assert tm.duration == 5.0
    assert tm.to_out(0.5) == 0.0
    assert tm.to_out(2.0) == 1.0
    assert tm.to_out(4.0) == 2.0      # inside the cut: clamps to the cut point
    assert tm.to_out(6.0) == 3.0
    assert abs(tm.to_src(1.0) - 2.0) < 1e-9
    assert abs(tm.to_src(3.0) - 6.0) < 1e-9


def test_normalize_words_fixes_overlaps():
    w = [{"t": "a", "s": 1.0, "e": 2.0}, {"t": "b", "s": 1.8, "e": 1.9}, {"t": "c", "s": 9.0, "e": 99.0}]
    out = timeline.normalize_words(w, 10.0)
    assert out[1]["s"] >= out[0]["e"]
    assert out[1]["e"] > out[1]["s"]
    assert out[2]["e"] <= 10.0


def test_chunks_respect_limits_and_sentences():
    text = "שלום לכולם, היום אני רוצה להראות לכם משהו חדש. זה ממש פשוט"
    w = [{"t": t, "s": i * 0.4, "e": i * 0.4 + 0.3} for i, t in enumerate(text.split())]
    tm = timeline.TimeMap(timeline.keep_frames(w, 6.0, FPS), FPS)
    chunks = timeline.build_chunks(w, tm, max_words=3, max_chars=30)
    assert [i for c in chunks for i in c] == list(range(len(w)))
    assert all(1 <= len(c) <= 3 for c in chunks)
    # a sentence end always closes a chunk
    ends = [i for i, x in enumerate(w) if x["t"].endswith(".")]
    assert all(any(c[-1] == i for c in chunks) for i in ends)
    # the comma after the second word wins over an even 3-word split
    assert chunks[0] == [0, 1]
    assert [len(c) for c in chunks] == [2, 3, 2, 2, 3]


def test_cues_are_ordered_and_inside_the_video():
    w = [{"t": f"w{i}", "s": 0.5 + i * 0.5, "e": 0.9 + i * 0.5} for i in range(12)]
    w[4]["d"] = True
    w[5]["d"] = True
    frames = timeline.keep_frames(w, 8.0, FPS)
    tm = timeline.TimeMap(frames, FPS)
    cap = [dict(x, d=x.get("d", False)) for x in w]
    chunks = timeline.build_chunks(cap, tm, 3, 30)
    assert all(4 not in c and 5 not in c for c in chunks)
    for per_word in (True, False):
        cues = timeline.build_cues(cap, tm, chunks, per_word)
        assert cues
        for a, b in zip(cues, cues[1:]):
            assert a["e"] <= b["s"] + 1e-6
        assert all(0 <= c["s"] < c["e"] <= tm.duration + 1e-6 for c in cues)


def test_caption_text_strips_edge_punctuation_only():
    assert timeline.caption_text('שלום,', True, False) == "שלום"
    assert timeline.caption_text('צה"ל.', True, False) == 'צה"ל'
    assert timeline.caption_text("hello world!", True, True) == "HELLO WORLD"
    assert timeline.caption_text("...", True, False) == ""
