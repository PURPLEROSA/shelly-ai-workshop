import random

import pytest

from app import ai, bidi, cleanup

MIRROR = str.maketrans("()[]{}<>", ")(][}{><")


def reference(text, rtl):
    from bidi import get_display  # python-bidi: dev dependency used as an oracle
    return get_display(text, base_dir="R" if rtl else "L")


CASES = ["שלום לכולם", "אני אוהב Claude Code מאוד.", "ה-AI משנה הכל!", "עלה 3.5% ב-2024, נכון?",
         "CapCut ו-Captions", "hello world", "מחיר: 1,000 ₪ בלבד", "100% חינם", "ב-10:30 בבוקר",
         'אמרתי "שלום" והלכתי', "iPhone 15 Pro שלי", "AI זה העתיד", "GPT-4 או Claude?", "שלב 1: העלאה",
         "3 דברים", "e-mail שלי", "Hello, world! 123", "קנו 2 קבלו 3", "#1 בישראל", "זה 50/50"]


@pytest.mark.parametrize("text", CASES)
def test_bidi_matches_reference(text):
    rtl = bidi.has_rtl(text)
    assert bidi.display(text, rtl) == reference(text, rtl)


def test_bidi_random_mixes_match_reference():
    rng = random.Random(7)
    vocab = ["שלום", "עולם", "AI", "Claude", "2024", "3.5%", "כן,", "לא.", "ו-GPT", "ה-CEO", "10:30", "test!", "מה?", "₪50"]
    for _ in range(400):
        text = " ".join(rng.choice(vocab) for _ in range(rng.randint(1, 7)))
        rtl = bidi.has_rtl(text)
        assert bidi.display(text, rtl) == reference(text, rtl), text


def test_bidi_mirrors_brackets_for_direct_drawing():
    # the reference leaves mirroring to the font engine; we draw glyphs ourselves
    out = bidi.display("זה (באמת) עובד", True)
    assert out == "דבוע (תמאב) הז"
    assert out.translate(MIRROR) == reference("זה (באמת) עובד", True)


def test_bidi_keeps_every_character_once():
    text = "אני אוהב Claude Code מאוד, באמת (100%)!"
    order = bidi.reorder(text)
    assert sorted(i for i, _ in order) == list(range(len(text)))


def test_fillers():
    assert all(cleanup.is_filler(t) for t in ["אה", "אהה,", "אממ", "אמ", "אהמ", "um", "Uh,", "hmm", "ממ"])
    assert not any(cleanup.is_filler(t) for t in ["אם", "אמא", "אהבה", "מה", "hum", "umbrella", "אז", "אה-הא!"][:7])


def test_repeats():
    w = [{"t": t, "s": i * 0.4, "e": i * 0.4 + 0.3} for i, t in enumerate(
        "אני אני חושבת שזה מאוד מאוד טוב אני חושבת אני חושבת שכן".split())]
    assert cleanup.find_repeats(w) == [0, 7, 8]


def W(text):
    return [{"t": t, "s": i * 0.5, "e": i * 0.5 + 0.4} for i, t in enumerate(text.split())]


def test_resolve_cuts_accepts_exact_and_fixes_drift():
    w = W("שלום לכולם, אז כאילו רציתי להגיד משהו חשוב. בואו נתחיל עכשיו")
    cuts, bad = ai.resolve_cuts([
        {"from": 2, "to": 3, "text": "אז כאילו", "reason": "מילוי"},
        {"from": 9, "to": 10, "text": "בואו נתחיל", "reason": "אינדקס שגוי"},   # really 8..9
        {"from": 50, "to": 60, "text": "לא קיים", "reason": "מחוץ לטווח"},
        {"from": "x", "to": 1},
    ], w)
    assert [(c["from"], c["to"]) for c in cuts] == [(2, 3), (8, 9)]
    assert bad == 2


def test_resolve_cuts_merges_overlaps():
    w = W("a b c d e f g h")
    cuts, bad = ai.resolve_cuts([{"from": 1, "to": 3, "text": "b c d", "reason": ""},
                                 {"from": 3, "to": 5, "text": "d e f", "reason": ""}], w)
    assert [(c["from"], c["to"]) for c in cuts] == [(1, 5)] and bad == 0


def test_extract_json_tolerates_wrapping():
    assert ai.extract_json('```json\n{"summary": "x", "cuts": []}\n```')["summary"] == "x"
    assert ai.extract_json('Here you go: {"summary": "y", "cuts": []} thanks')["summary"] == "y"
    with pytest.raises(Exception):
        ai.extract_json("no json here")


def test_transcript_for_model_numbers_only_kept_words():
    from fractions import Fraction
    from app import timeline
    w = W("אחת שתיים שלוש. ארבע חמש")
    w[1]["d"] = True
    w[3]["s"], w[3]["e"] = 4.0, 4.4
    w[4]["s"], w[4]["e"] = 4.5, 4.9
    tm = timeline.TimeMap(timeline.keep_frames(w, 6.0, Fraction(30)), Fraction(30))
    text = ai.transcript_for_model(w, tm)
    assert "0|אחת" in text and "2|שלוש." in text and "1|שתיים" not in text
    assert "(pause" in text and text.count("\n") >= 1
