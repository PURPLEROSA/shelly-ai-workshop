import json
import wave

import numpy as np
import pytest

from app import ai, looks, sfx, stock, voice
from app.jobs import UserError


def test_every_sound_effect_is_audible_and_unclipped():
    assert len(sfx.SFX) == 26 and len({s[0] for s in sfx.SFX}) == 26
    for name, label, group in sfx.SFX:
        with wave.open(str(sfx.path(name))) as w:
            assert w.getframerate() == 48000 and w.getnchannels() == 2
            a = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(float) / 32768
        assert 0.03 < len(a) / 2 / 48000 < 3, name
        assert 0.5 < np.abs(a).max() <= 1.0 and np.sqrt((a ** 2).mean()) > 0.005, name


def test_look_cube_matches_the_curves_the_browser_uses():
    for look in looks.LOOKS:
        lines = looks.cube_path(look["id"]).read_text().splitlines()
        assert lines[0] == f"LUT_3D_SIZE {looks.CUBE}" and len(lines) == looks.CUBE ** 3 + 1
        n = looks.CUBE
        for r, g, b in ((0, 0, 0), (n - 1, n - 1, n - 1), (16, 8, 24), (5, 30, 11)):
            got = [float(v) for v in lines[1 + r + g * n + b * n * n].split()]
            want = looks.apply(look, (r / (n - 1), g / (n - 1), b / (n - 1)))
            assert got == pytest.approx(want, abs=2e-4), look["id"]
    d = looks.describe()
    assert all(len(x["curves"]) == 3 and len(x["curves"][0]) == looks.N and len(x["matrix"]) == 3 for x in d)
    assert looks.apply(looks.BY_ID["bw"], (1, 0, 0))[0] == pytest.approx(looks.apply(looks.BY_ID["bw"], (1, 0, 0))[2])


def test_openverse_results_keep_only_video_safe_licences(monkeypatch):
    rows = [{"id": "1", "url": "https://x/a.mp3", "license": "by", "license_version": "4.0", "filetype": "mp32", "duration": 61000, "title": "ok"},
            {"id": "2", "url": "https://x/b.mp3", "license": "by-nc", "filetype": "mp3", "title": "non commercial"},
            {"id": "3", "url": "https://x/c.mp3", "license": "by-nd", "filetype": "mp3", "title": "no derivatives"},
            {"id": "4", "url": "https://x/d.ogg", "license": "cc0", "filetype": "ogg", "title": "public"}]
    seen = {}
    monkeypatch.setattr(stock, "_get", lambda url, headers=None, timeout=20: seen.setdefault("url", url) and {"results": rows})
    out = stock.search("music", "upbeat")["results"]
    assert "license_type=commercial%2Cmodification" in seen["url"]
    assert [r["title"] for r in out] == ["ok", "public"]
    assert all("url" not in r for r in out)            # the download address never reaches the browser
    assert stock.lookup(out[0]["token"])["ext"] == ".mp3" and stock.lookup(out[1]["token"])["ext"] == ".ogg"
    assert stock.lookup(out[0]["token"])["license"] == "CC BY 4.0" and out[0]["duration"] == 61.0


def test_video_search_explains_missing_keys():
    r = stock.search("video", "city")
    assert r["results"] == [] and r["notes"]
    with pytest.raises(UserError):
        stock.search("video", "   ")
    with pytest.raises(UserError):
        stock.download("made-up-token", None)


def test_multipart_body_is_well_formed():
    body, ctype = voice._multipart({"name": "קול"}, {"clip": ("a.wav", b"RIFFdata", "audio/wav")})
    boundary = ctype.split("boundary=")[1]
    assert body.count(f"--{boundary}".encode()) == 3 and body.endswith(f"--{boundary}--\r\n".encode())
    assert 'name="clip"; filename="a.wav"'.encode() in body and "קול".encode() in body and b"RIFFdata" in body


def test_narration_needs_a_connected_service():
    assert voice.status()["ready"] is False
    with pytest.raises(UserError):
        voice.synthesize("שלום", None)


def test_translation_keeps_sentence_timing(monkeypatch):
    words = [{"t": t, "s": i * 0.5, "e": i * 0.5 + 0.4} for i, t in enumerate("שלום לכולם. היום נדבר על עריכה. זה הכל".split())]
    sents = ai.sentences(words)
    assert [s["text"] for s in sents] == ["שלום לכולם.", "היום נדבר על עריכה.", "זה הכל"]
    monkeypatch.setattr(ai, "complete", lambda system, user, schema=None: json.dumps(
        {"lines": [{"n": 0, "text": "Hello everyone."}, {"n": 1, "text": "Today we talk about editing."}, {"n": 2, "text": "That is all"}]}))
    out = ai.translate_words(words, "en")
    assert " ".join(w["t"] for w in out) == "Hello everyone. Today we talk about editing. That is all"
    assert out[0]["s"] == sents[0]["s"] and out[1]["e"] == pytest.approx(sents[0]["e"], abs=0.01)
    assert all(a["e"] <= b["s"] + 1e-6 for a, b in zip(out, out[1:]))


def test_assistant_plan_parsing(monkeypatch):
    reply = {"summary": "קיצרתי", "steps": [{"op": "remove_silences", "args_json": "{\"level\": \"tight\"}"},
                                              {"op": "set_captions", "args_json": ""}, {"nope": 1}]}
    monkeypatch.setattr(ai, "complete", lambda system, user, schema=None: "```json\n" + json.dumps(reply, ensure_ascii=False) + "\n```")
    plan = ai.plan("לקצר", {"name": "x"}, [], [{"name": "remove_silences", "desc": "d", "params": ["level"]}])
    assert plan["summary"] == "קיצרתי"
    assert plan["steps"] == [{"op": "remove_silences", "args": {"level": "tight"}}, {"op": "set_captions", "args": {}}]
    monkeypatch.setattr(ai, "complete", lambda *a, **k: json.dumps({"summary": "", "steps": [{"op": "x", "args_json": "{broken"}]}))
    with pytest.raises(UserError):
        ai.plan("x", {}, [], [])
