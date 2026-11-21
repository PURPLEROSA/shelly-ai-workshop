import pytest

from app import compose, model, ops, ops_jobs  # noqa: F401  (ops_jobs registers its operations)
from app.jobs import UserError

from helpers import fake_media, project_with_clip, spoken


def state(pid):
    p = model.load(pid)
    return p, compose.derive(p)


def main_ids(p):
    return [it["id"] for it in model.main_track(p)["items"]]


def test_split_keeps_total_length_and_source_continuity():
    pid, mid, iid = project_with_clip(20.0)
    r = ops.run(pid, "split_item", {"at": 5.0})
    p, d = state(pid)
    a, b = model.main_track(p)["items"]
    assert (a["id"], b["id"]) == (r["left"], r["right"])
    assert a["out"] == b["in"] == 5.0
    assert d["duration"] == pytest.approx(20.0, abs=0.04)
    assert d["items"][b["id"]]["start"] == pytest.approx(5.0, abs=0.04)


def test_split_outside_the_clip_is_refused_and_leaves_no_undo_step():
    pid, _, _ = project_with_clip(10.0)
    with pytest.raises(UserError):
        ops.run(pid, "split_item", {"at": 99})
    assert model.history_state(pid)["undo"] == 0


def test_speed_changes_length_and_later_clips_follow():
    pid, mid, iid = project_with_clip(20.0)
    right = ops.run(pid, "split_item", {"at": 10.0})["right"]
    ops.run(pid, "set_speed", {"item": iid, "speed": 2})
    p, d = state(pid)
    assert d["items"][iid]["dur"] == pytest.approx(5.0, abs=0.04)
    assert d["items"][right]["start"] == pytest.approx(5.0, abs=0.04)
    assert d["duration"] == pytest.approx(15.0, abs=0.05)


def test_transition_overlaps_two_clips():
    pid, mid, iid = project_with_clip(20.0)
    right = ops.run(pid, "split_item", {"at": 10.0})["right"]
    ops.run(pid, "set_transition", {"item": right, "type": "fade", "duration": 1.0})
    p, d = state(pid)
    assert d["items"][right]["trans"] == pytest.approx(1.0, abs=0.04)
    assert d["items"][right]["start"] == pytest.approx(9.0, abs=0.04)
    assert d["duration"] == pytest.approx(19.0, abs=0.05)
    with pytest.raises(UserError):
        ops.run(pid, "set_transition", {"item": iid, "type": "fade"})   # the first clip has nothing before it


def test_reorder_and_remove_on_the_main_track():
    pid, mid, iid = project_with_clip(20.0)
    right = ops.run(pid, "split_item", {"at": 10.0})["right"]
    ops.run(pid, "move_item", {"item": right, "index": 0})
    p, d = state(pid)
    assert main_ids(p) == [right, iid]
    assert d["items"][right]["start"] == 0
    ops.run(pid, "remove_item", {"item": right})
    p, d = state(pid)
    assert main_ids(p) == [iid] and d["duration"] == pytest.approx(10.0, abs=0.05)


def test_cut_range_across_two_clips_and_keep_range():
    pid, mid, iid = project_with_clip(20.0)
    ops.run(pid, "split_item", {"at": 10.0})
    r = ops.run(pid, "cut_range", {"from": 8.0, "to": 12.0})
    p, d = state(pid)
    assert r["removed_seconds"] == pytest.approx(4.0, abs=0.01)
    a, b = model.main_track(p)["items"]
    assert (a["out"], b["in"]) == (8.0, 12.0)
    assert d["duration"] == pytest.approx(16.0, abs=0.05)
    ops.run(pid, "keep_range", {"from": 2.0, "to": 6.0})
    p, d = state(pid)
    assert d["duration"] == pytest.approx(4.0, abs=0.05)
    assert model.main_track(p)["items"][0]["in"] == 2.0


def test_cut_inside_one_clip_makes_two():
    pid, mid, iid = project_with_clip(20.0)
    ops.run(pid, "cut_range", {"from": 5.0, "to": 7.0})
    p, d = state(pid)
    a, b = model.main_track(p)["items"]
    assert (a["out"], b["in"]) == (5.0, 7.0) and a["id"] != b["id"]


def test_undo_and_redo_restore_tracks_and_words():
    pid, mid, iid = project_with_clip(20.0, spoken())
    ops.run(pid, "delete_words", {"media": mid, "from": 3, "to": 6})
    ops.run(pid, "split_item", {"at": 5.0})
    assert len(main_ids(model.load(pid))) == 2
    ops.run(pid, "undo")
    p = model.load(pid)
    assert len(main_ids(p)) == 1 and sum(1 for w in p["media"][mid]["words"] if w.get("d")) == 4
    ops.run(pid, "undo")
    assert not any(w.get("d") for w in model.load(pid)["media"][mid]["words"])
    ops.run(pid, "redo")
    ops.run(pid, "redo")
    p = model.load(pid)
    assert len(main_ids(p)) == 2 and sum(1 for w in p["media"][mid]["words"] if w.get("d")) == 4


def test_word_cuts_shorten_the_clip_and_show_as_segments():
    pid, mid, iid = project_with_clip(20.0, spoken(30))
    before = state(pid)[1]["duration"]
    ops.run(pid, "delete_words", {"media": mid, "from": 10, "to": 12})
    p, d = state(pid)
    assert len(d["items"][iid]["segs"]) == 2
    assert d["duration"] < before - 1.0
    ops.run(pid, "remove_silences", {"level": "tight"})
    assert state(pid)[1]["duration"] < d["duration"]
    ops.run(pid, "restore_all_words")
    ops.run(pid, "remove_silences", {"level": "off"})
    assert state(pid)[1]["duration"] == pytest.approx(before, abs=0.04)


def test_free_items_follow_the_content_under_them():
    pid, mid, iid = project_with_clip(20.0, spoken(30))
    ops.run(pid, "add_text", {"text": "כותרת", "at": 12.0, "duration": 2})
    sfx = ops_jobs.execute(pid, "add_sound_effect", {"name": "pop", "at": 12.0})["item"]
    ops.run(pid, "cut_range", {"from": 2.0, "to": 6.0})          # 4 s removed before them
    p, d = state(pid)
    assert d["items"][sfx]["start"] == pytest.approx(8.0, abs=0.05)
    assert d["titles"][0]["start"] == pytest.approx(8.0, abs=0.05)
    ops.run(pid, "delete_words", {"media": mid, "from": 0, "to": 3})  # more removed, earlier still
    assert state(pid)[1]["items"][sfx]["start"] < 8.0


def test_delete_text_finds_a_phrase():
    words = [{"t": t, "s": i * 0.5, "e": i * 0.5 + 0.4} for i, t in enumerate("שלום לכולם אז כאילו רציתי להגיד אז כאילו".split())]
    pid, mid, iid = project_with_clip(10.0, words)
    r = ops.run(pid, "delete_text", {"text": "אז כאילו"})
    assert r["occurrences_cut"] == 2
    assert [i for i, w in enumerate(model.load(pid)["media"][mid]["words"]) if w.get("d")] == [2, 3, 6, 7]
    with pytest.raises(UserError):
        ops.run(pid, "delete_text", {"text": "לא קיים"})


def test_zoom_keyframes_and_quick_zoom():
    pid, mid, iid = project_with_clip(20.0)
    ops.run(pid, "add_zoom_keyframe", {"item": iid, "at": 2.0, "scale": 1.5, "x": 0.4, "y": 0.6})
    ops.run(pid, "add_zoom_keyframe", {"item": iid, "at": 2.0, "scale": 1.8})   # same moment: replaces
    it = model.find_item(model.load(pid), iid)[2]
    assert [(k["t"], k["s"]) for k in it["zoom"]] == [(2.0, 1.8)]
    ops.run(pid, "remove_zoom_keyframe", {"item": iid, "index": -1})
    ops.run(pid, "quick_zoom", {"kind": "punch", "at": 5.0, "scale": 1.4, "duration": 2})
    it = model.find_item(model.load(pid), iid)[2]
    assert [k["s"] for k in it["zoom"]] == [1, 1.4, 1.4, 1] and it["zoom"][1]["t"] == 5.0


def test_tracks_and_overlays():
    pid, mid, iid = project_with_clip(20.0)
    p = model.load(pid)
    broll = fake_media(p, "broll", 8.0)
    music = fake_media(p, "music", 60.0, kind="audio")
    model.save(p)
    v2 = ops.run(pid, "add_track", {"kind": "video"})["track"]
    ov = ops.run(pid, "add_clip", {"media": broll["id"], "track": v2, "at": 3.0})["item"]
    au = ops.run(pid, "add_clip", {"media": music["id"], "at": 0})["item"]
    ops.run(pid, "set_item", {"item": ov, "blend": "screen", "opacity": 0.5})
    ops.run(pid, "trim_item", {"item": au, "source_out": 20.0})
    ops.run(pid, "set_fades", {"item": au, "fade_in": 1, "fade_out": 2})
    p, d = state(pid)
    over = model.find_item(p, ov)[2]
    assert over["blend"] == "screen" and over["opacity"] == 0.5 and over["mute"] is True
    assert d["items"][ov]["start"] == 3.0 and d["duration"] == pytest.approx(20.0, abs=0.05)
    names = [t["name"] for t in p["tracks"]]
    assert names == ["טקסט 1", "וידאו 2", "וידאו 1", "אודיו 1"]
    with pytest.raises(UserError):
        ops.run(pid, "remove_track", {"track": model.main_track(p)["id"]})
    ops.run(pid, "remove_track", {"track": v2})
    assert model.find_item(model.load(pid), ov)[2] is None


def test_captions_follow_cuts_speed_and_translation():
    pid, mid, iid = project_with_clip(20.0, spoken(30))
    d = state(pid)[1]
    assert len(d["cues"]) == 30 and d["caps"]
    ops.run(pid, "set_speed", {"item": iid, "speed": 2})
    d2 = state(pid)[1]
    assert d2["cues"][-1]["s"] == pytest.approx(d["cues"][-1]["s"] / 2, abs=0.05)   # words arrive twice as fast
    ops.run(pid, "set_captions", {"preset": "clean"})
    assert len(state(pid)[1]["cues"]) < 30            # no per-word highlight in this style
    p = model.load(pid)
    p["media"][mid]["tr"] = {"en": [{"t": f"e{i}", "s": 0.5 + i, "e": 1.4 + i} for i in range(15)]}
    model.save(p)
    ops.run(pid, "set_captions", {"mode": "both", "language": "en"})
    d3 = state(pid)[1]
    assert d3["cues"] and d3["cues2"] and d3["band2"]["top"] > d3["band"]["top"]
    ops.run(pid, "set_captions", {"enabled": False})
    assert not state(pid)[1]["cues"]


def test_values_are_clamped():
    pid, mid, iid = project_with_clip(20.0)
    ops.run(pid, "set_item", {"item": iid, "speed": 99, "volume": -4, "fade_in": 500})
    it = model.find_item(model.load(pid), iid)[2]
    assert it["speed"] == 4.0 and it["volume"] == 0 and it["fade_in"] <= (it["out"] - it["in"]) / it["speed"] / 2
    ops.run(pid, "trim_item", {"item": iid, "source_in": -5, "source_out": 999})
    it = model.find_item(model.load(pid), iid)[2]
    assert (it["in"], it["out"]) == (0.0, 20.0)


def test_every_operation_has_a_usable_schema():
    assert len(ops.OPS) >= 55
    for spec in ops.OPS.values():
        s = spec.schema()
        assert s["type"] == "object" and set(spec.required) <= set(s["properties"]), spec.name
        assert len(spec.desc) > 10, spec.name
