"""Operations that need files, the network or a background job.

Importing this module registers them next to the plain edits in `ops`.
`execute` is the single door every caller uses to run any operation.
"""
from __future__ import annotations

import shutil
import urllib.parse
import urllib.request
from pathlib import Path

from . import ai, compose, config, export, ingest, media, model, ops, sfx, stock, voice
from .jobs import Job, UserError, jobs
from .ops import AT, BOOL, INT, ITEM, MEDIA, NUM, STR, op

# operations the built-in assistant may plan with
PLANNABLE = ("delete_words", "restore_words", "delete_text", "remove_silences", "remove_fillers", "remove_repeats",
             "restore_all_words", "split_item", "remove_item", "cut_range", "keep_range", "set_speed", "set_volume",
             "set_fades", "set_look", "set_transition", "quick_zoom", "add_zoom_keyframe", "set_captions", "add_text",
             "add_sound_effect", "set_canvas", "move_item", "duplicate_item")


def execute(pid: str, name: str, args: dict | None = None, coalesce: str | None = None, local: bool = True) -> dict:
    """Run any operation, then do the follow-up work it implies."""
    result = ops.run(pid, name, args, coalesce, local)
    if name == "add_clip" and result.get("main"):
        job = ingest.maybe_transcribe(pid, result["media"])
        if job:
            result["transcribe_job"] = job.id
    return result


def _start(kind: str, pid: str, fn, *args) -> dict:
    return {"job": jobs.submit(kind, pid, fn, *args).id}


# ------------------------------------------------------------------- media

@op("transcribe", "Transcribe the speech in a media file (runs on this computer). Returns a job id.",
    {"media": MEDIA, "model": STR, "language": STR}, ("media",), mutates=False, group="media")
def transcribe(p, a):
    m = ops._ready(ops._media(p, a["media"]))
    return {"job": ingest.start_transcribe(p["id"], m["id"], a.get("model"), a.get("language")).id}


@op("remove_media", "Delete a media file from the project, along with every item that uses it.",
    {"media": MEDIA}, ("media",), group="media")
def remove_media(p, a):
    m = ops._media(p, a["media"])
    for t in p["tracks"]:
        t["items"] = [it for it in t["items"] if it.get("media") != m["id"]]
    del p["media"][m["id"]]
    shutil.rmtree(model.mdir(p["id"], m["id"]), ignore_errors=True)
    return {"_no_undo": True}


def _import_job(job: Job, pid: str, source: str, add: bool):
    if source.lower().startswith(("http://", "https://")):
        name = Path(urllib.parse.unquote(urllib.parse.urlparse(source).path)).name or "download.mp4"
        m, dest = ingest.register(pid, name, "import")
        job.update(0.02, "מוריד את הקובץ…")
        try:
            req = urllib.request.Request(source, headers={"User-Agent": stock.UA})
            with urllib.request.urlopen(req, timeout=60, context=stock._ssl_context()) as res, open(dest, "wb") as fh:
                total = int(res.headers.get("Content-Length") or 0)
                got = 0
                while chunk := res.read(256 * 1024):
                    got += len(chunk)
                    if got > 8 * 1024 ** 3:
                        raise UserError("הקובץ גדול מדי.")
                    fh.write(chunk)
                    job.update(0.02 + 0.3 * (got / total if total else 0.5), "מוריד את הקובץ…")
        except UserError:
            ingest.remove(pid, m["id"])
            raise
        except Exception:
            ingest.remove(pid, m["id"])
            raise UserError("ההורדה נכשלה. בודקים שהקישור מוביל ישר לקובץ.")
    else:
        src = Path(source).expanduser()
        if not src.is_file():
            raise UserError("הקובץ לא נמצא בנתיב הזה.")
        if not model.kind_for(src.name):
            raise UserError("סוג הקובץ לא נתמך.")
        m, dest = ingest.register(pid, src.name, "import")
        shutil.copyfile(src, dest)
    return ingest.prepare(job, pid, m["id"], {} if add else None)


@op("import_media", "Bring a file into the project from a path on this computer or a direct link. "
                    "With add=true it is also placed on the timeline. Returns a job id.",
    {"source": {"type": "string", "description": "File path or http(s) URL."}, "add": BOOL}, ("source",),
    mutates=False, local_only=True, group="media")
def import_media(p, a):
    return _start("prepare", p["id"], _import_job, p["id"], str(a["source"]).strip(), bool(a.get("add")))


# ------------------------------------------------------------------- sound

@op("add_sound_effect", "Drop a built-in sound effect on the timeline at a given time.",
    {"name": {"type": "string", "enum": [s[0] for s in sfx.SFX]}, "at": AT, "volume": NUM}, ("name", "at"),
    group="sound")
def add_sound_effect(p, a):
    if a["name"] not in sfx.NAMES:
        raise UserError("האפקט לא קיים.")
    m = next((x for x in p["media"].values() if x["origin"] == "sfx" and x["meta"].get("sfx") == a["name"]), None)
    if m is None:
        m = ingest.add_ready_file(p, sfx.path(a["name"]), sfx.NAMES[a["name"]], "sfx", "audio", {"sfx": a["name"]})
    track = _audio_track(p, "sfx")
    it = model.new_audio_item(m, float(a["at"]), sfx.NAMES[a["name"]])
    it["volume"] = ops._f(a.get("volume"), 0, 2, 0.8)
    track["items"].append(it)
    return {"item": it["id"], "track": track["id"], "_keep_free_items": True}


def _audio_track(p: dict, purpose: str) -> dict:
    """An audio track for sound effects, music or narration; made on demand."""
    tracks = [t for t in p["tracks"] if t["kind"] == "audio"]
    want = {"voice": 0, "sfx": 0, "music": 1}[purpose]
    while len(tracks) <= want:
        t = model.new_track("audio")
        p["tracks"].append(t)
        tracks.append(t)
    model.name_tracks(p)
    return tracks[want]


def _narration_job(job: Job, pid: str, text: str, at: float, voice_id: str | None, language: str):
    job.update(0.1, "מקליט קריינות…")
    m, dest = ingest.register(pid, "קריינות " + text[:24], "voice", "audio")
    try:
        path = voice.synthesize(text, dest.parent, voice_id, language)
        final = dest.with_suffix(path.suffix)
        config.replace(path, final)
        ingest._update(pid, m["id"], file=final.name, meta={"text": text})
        with model.lock(pid):
            cur = model.load(pid)
        fields = ingest.analyse(pid, cur["media"][m["id"]])
        ingest._update(pid, m["id"], status="ready", **fields)
    except Exception:
        ingest.remove(pid, m["id"])
        raise
    job.update(0.8, "מוסיף לטיימליין…")

    def apply(p: dict):
        mm = p["media"][m["id"]]
        it = model.new_audio_item(mm, at, "קריינות")
        _audio_track(p, "voice")["items"].append(it)
        return it["id"]

    item = ops.mutate(pid, apply)
    tj = ingest.maybe_transcribe(pid, m["id"])
    return {"media": m["id"], "item": item, "transcribe_job": tj.id if tj else None}


@op("add_narration", "Speak a text in a chosen voice and put it on the timeline. Returns a job id.",
    {"text": STR, "at": AT, "voice": {"type": "string", "description": "Voice id from list_voices."},
     "language": STR}, ("text",), mutates=False, group="sound")
def add_narration(p, a):
    if not voice.status()["ready"]:
        raise UserError("עדיין לא חובר שירות קול. מחברים אחד בהגדרות, תחת ״קול״.")
    text = " ".join(str(a["text"]).split())
    if not text:
        raise UserError("חסר טקסט לקריינות.")
    at = ops._f(a.get("at"), 0, 36000, 0.0)
    return _start("voice", p["id"], _narration_job, p["id"], text, at, a.get("voice"), a.get("language") or "he")


@op("list_voices", "List the voices available for narration, including voices cloned from your recordings.",
    {"language": STR}, mutates=False, group="sound")
def list_voices(p, a):
    return {"voices": voice.voices(a.get("language") or "he"), "status": voice.status()}


def _clone_job(job: Job, pid: str, mid: str, start: float, end: float, name: str, language: str):
    with model.lock(pid):
        p = model.load(pid)
    m = p["media"][mid]
    job.update(0.1, "מכין דגימת קול…")
    sample = model.pdir(pid) / f"voice-sample-{job.id}.wav"
    try:
        media.cut_wav(model.mdir(pid, mid) / m["file"], sample, start, end)
        job.update(0.4, "משבט את הקול…")
        return voice.clone(sample, name, language)
    finally:
        sample.unlink(missing_ok=True)


@op("clone_voice", "Create a narration voice from a stretch of a recording (10 seconds or more of clean speech). "
                   "`from` and `to` are seconds in the source file. Returns a job id.",
    {"media": MEDIA, "from": NUM, "to": NUM, "name": STR, "language": STR}, ("media", "from", "to"),
    mutates=False, local_only=True, group="sound")
def clone_voice(p, a):
    m = ops._ready(ops._media(p, a["media"]))
    if not (m["has_audio"] or m["kind"] == "audio"):
        raise UserError("בקובץ הזה אין אודיו.")
    lo, hi = sorted((float(a["from"]), float(a["to"])))
    hi = min(hi, m["duration"])
    if hi - lo < 5:
        raise UserError("צריך לפחות 5 שניות של דיבור. עדיף 10 עד 30 שניות נקיות.")
    if not voice.status()["ready"]:
        raise UserError("עדיין לא חובר שירות קול. מחברים אחד בהגדרות, תחת ״קול״.")
    return _start("voice", p["id"], _clone_job, p["id"], m["id"], lo, min(hi, lo + 120),
                  str(a.get("name") or "הקול שלי"), a.get("language") or "he")


def _detach_job(job: Job, pid: str, item_id: str):
    with model.lock(pid):
        p = model.load(pid)
    track, _, it = model.find_item(p, item_id)
    if it is None:
        raise UserError("הפריט לא נמצא.")
    m = p["media"][it["media"]]
    lay = compose.Layout(p)
    info = lay.items[item_id]
    work = model.pdir(pid) / f"work-{job.id}"
    work.mkdir(parents=True, exist_ok=True)
    try:
        g = export.Graph(work)
        lab = export._audio_chain(g, pid, m, info, lay.fps, 1.0, 0, 0, job, start=0.0)
        if not lab:
            raise UserError("בקליפ הזה אין אודיו להפריד.")
        (work / "graph.txt").write_text(";\n".join(g.chains), encoding="utf-8")
        flag = ["-/filter_complex", "graph.txt"] if media.ffmpeg_major() >= 7 else ["-filter_complex_script", "graph.txt"]
        media.run(g.inputs + flag + ["-map", f"[{lab}]", "-c:a", "pcm_s16le", "out.wav"], cancel=job.cancel, cwd=work)

        def apply(doc: dict):
            tr, _, cur = model.find_item(doc, item_id)
            if cur is None:
                return None
            am = ingest.add_ready_file(doc, work / "out.wav", m["name"] + " · אודיו", "detached", "audio")
            new = model.new_audio_item(am, compose.Layout(doc).items[item_id]["map"].start, am["name"])
            new["volume"], new["fade_in"], new["fade_out"] = cur["volume"], cur["fade_in"], cur["fade_out"]
            cur["mute"] = True
            _audio_track(doc, "voice")["items"].append(new)
            return new["id"]

        return {"item": ops.mutate(pid, apply)}
    finally:
        shutil.rmtree(work, ignore_errors=True)


@op("detach_audio", "Separate a video clip's sound into its own item on an audio track, so the two can be edited "
                    "independently. Returns a job id.", {"item": ITEM}, ("item",), mutates=False, group="sound")
def detach_audio(p, a):
    track, _, it = ops._item(p, a["item"])
    if track["kind"] != "video":
        raise UserError("אפשר להפריד אודיו רק מקליפ וידאו.")
    if not p["media"][it["media"]]["has_audio"]:
        raise UserError("בקליפ הזה אין אודיו.")
    return _start("detach", p["id"], _detach_job, p["id"], it["id"])


# ------------------------------------------------------------------- stock

@op("search_stock", "Search free stock libraries. kind: video (B-roll), overlay (light leaks, grain), image or music.",
    {"kind": {"type": "string", "enum": list(stock.KINDS)}, "query": STR, "page": INT, "portrait": BOOL},
    ("kind", "query"), mutates=False, group="stock")
def search_stock(p, a):
    return stock.search(a["kind"], a["query"], a.get("page", 1), a.get("portrait", True))


def _stock_job(job: Job, pid: str, token: str, at: float, add: bool):
    r = stock.lookup(token)
    if not r:
        raise UserError("תוצאת החיפוש פגה. מחפשים שוב ובוחרים מחדש.")
    kind = {"video": "video", "overlay": "video", "image": "image", "music": "audio"}[r["kind"]]
    m, dest = ingest.register(pid, (r["title"] or r["provider"])[:60] + r["ext"], "stock", kind)
    try:
        job.update(0.02, "מוריד מהמאגר…")
        path, _ = stock.download(token, dest.parent, lambda f: job.update(0.02 + 0.5 * f, "מוריד מהמאגר…"), job.cancel)
        ingest._update(pid, m["id"], file=path.name,
                       meta={"credit": {k: r.get(k, "") for k in ("provider", "author", "license", "page", "title")},
                             "stock_kind": r["kind"]})
        with model.lock(pid):
            cur = model.load(pid)
        fields = ingest.analyse(pid, cur["media"][m["id"]], lambda f: job.update(0.55 + 0.4 * f, "מכין תצוגה…"), job.cancel)
        fields["meta"] = {**cur["media"][m["id"]]["meta"], **(fields.get("meta") or {})}
        ingest._update(pid, m["id"], status="ready", **fields)
    except Exception:
        ingest.remove(pid, m["id"])
        raise
    if not add:
        return {"media": m["id"]}

    def apply(p: dict):
        mm = p["media"][m["id"]]
        if kind == "audio":
            it = model.new_audio_item(mm, at, mm["name"])
            it["volume"] = 0.35
            # music should not run on past the end of the video
            room = compose.Layout(p).main_f / float(compose.canvas_fps(p)) - at
            if room > 2 and mm["duration"] > room:
                it["out"] = round(room, 3)
                it["fade_out"] = 1.5
            _audio_track(p, "music")["items"].append(it)
        else:
            track = next((t for t in p["tracks"] if t["kind"] == "video" and not t.get("main")), None)
            if track is None:
                track = model.new_track("video")
                p["tracks"].insert(next(i for i, x in enumerate(p["tracks"]) if x["kind"] == "video"), track)
                model.name_tracks(p)
            it = model.new_video_item(mm, at, 4.0 if kind == "image" else min(mm["duration"], 6.0))
            it["mute"] = True
            if r["kind"] == "overlay":
                it["blend"], it["opacity"] = "screen", 0.8
            track["items"].append(it)
        return it["id"]

    return {"media": m["id"], "item": ops.mutate(pid, apply)}


@op("add_stock", "Download a stock search result into the project and place it on the timeline at `at`. "
                 "Video and images go above the main track as B-roll, overlays are blended over the picture, "
                 "music goes to an audio track. Returns a job id.",
    {"token": {"type": "string", "description": "The token of a result from search_stock."}, "at": AT, "add": BOOL},
    ("token",), mutates=False, group="stock")
def add_stock(p, a):
    if not stock.lookup(str(a["token"])):
        raise UserError("תוצאת החיפוש פגה. מחפשים שוב ובוחרים מחדש.")
    return _start("stock", p["id"], _stock_job, p["id"], str(a["token"]), ops._f(a.get("at"), 0, 36000, 0.0),
                  a.get("add", True) is not False)


# ---------------------------------------------------------- AI and captions

def _translate_job(job: Job, pid: str, lang: str, mode: str):
    with model.lock(pid):
        p = model.load(pid)
    todo = [mid for mid in ops._timeline_media(p)]
    if not todo:
        raise UserError("אין תמלול לתרגם.")
    results = {}
    for n, mid in enumerate(todo):
        job.update(0.05 + 0.9 * n / len(todo), "מתרגם כתוביות…")
        words = [w for w in p["media"][mid]["words"] if w["t"].strip()]
        results[mid] = ai.translate_words(words, lang, lambda f: job.update(0.05 + 0.9 * (n + f) / len(todo), "מתרגם כתוביות…"))

    def apply(doc: dict):
        for mid, tr in results.items():
            if mid in doc["media"]:
                doc["media"][mid].setdefault("tr", {})[lang] = tr
        doc["captions"]["lang"] = lang
        doc["captions"]["mode"] = mode
        doc["captions"]["enabled"] = True

    ops.mutate(pid, apply)
    return {"language": lang, "words": sum(len(v) for v in results.values())}


@op("translate_captions", "Translate the captions into another language with the connected AI model, and show them "
                          "translated or next to the original. Returns a job id.",
    {"language": {"type": "string", "description": "Target language code: en, he, ar, ru, fr, es."},
     "mode": {"type": "string", "enum": ["translated", "both"]}}, ("language",), mutates=False, group="captions")
def translate_captions(p, a):
    if not ai.status()["ready"]:
        raise UserError("לתרגום צריך מודל AI. מחברים אחד בהגדרות.")
    mode = a.get("mode") if a.get("mode") in ("translated", "both") else "translated"
    return _start("ai", p["id"], _translate_job, p["id"], str(a["language"])[:8], mode)


def catalogue() -> list[dict]:
    return [{"name": n, "desc": ops.OPS[n].desc,
             "params": [f"{k}{'' if k in ops.OPS[n].required else '?'}" for k in ops.OPS[n].props]}
            for n in PLANNABLE if n in ops.OPS]


def _assistant_job(job: Job, pid: str, instruction: str):
    job.update(0.1, "המודל קורא את הפרויקט…")
    desc = ops.run(pid, "get_project")
    for t in desc["tracks"]:
        t.pop("hidden", None)
    desc.pop("media", None)
    transcripts = ops.run(pid, "get_transcript")["transcripts"]
    result = ai.plan(instruction, desc, transcripts, catalogue())
    done, failed = [], None
    for n, step in enumerate(result["steps"]):
        job.update(0.5 + 0.5 * n / max(1, len(result["steps"])), "מבצע את העריכה…")
        name, args = step["op"], dict(step["args"])
        if name not in PLANNABLE:
            failed = f"פעולה לא מוכרת: {name}"
            break
        try:
            if name == "delete_words" and args.get("text") and args.get("media"):
                with model.lock(pid):
                    words = model.load(pid)["media"].get(str(args["media"]), {}).get("words", [])
                cuts, _bad = ai.resolve_cuts([{"from": args.get("from"), "to": args.get("to"), "text": args["text"]}], words)
                if not cuts:
                    continue
                args["from"], args["to"] = cuts[0]["from"], cuts[0]["to"]
            out = execute(pid, name, args, coalesce=f"assistant-{job.id}")
            done.append({"op": name, "args": {k: v for k, v in args.items() if k != "text"}, "result": out})
        except UserError as e:
            failed = str(e)
            break
    return {"summary": result["summary"], "steps": done, "planned": len(result["steps"]), "failed": failed}


@op("assistant", "Ask the studio's built-in AI editor to carry out a request in plain words. Returns a job id.",
    {"instruction": STR}, ("instruction",), mutates=False, group="ai")
def assistant(p, a):
    if not ai.status()["ready"]:
        raise UserError("עדיין לא חובר מודל AI. מחברים אחד בהגדרות.")
    text = str(a["instruction"]).strip()[:2000]
    if not text:
        raise UserError("כותבים מה לעשות.")
    return _start("ai", p["id"], _assistant_job, p["id"], text)


def _text_job(job: Job, pid: str, kind: str, instruction: str):
    job.update(0.1, "המודל כותב…")
    with model.lock(pid):
        p = model.load(pid)
    words = []
    for mid in ops._timeline_media(p):
        words += p["media"][mid]["words"]
    return {"text": ai.write_text({"words": words}, kind, instruction)}


@op("write_copy", "Write post copy from the video's transcript: caption, hooks, youtube or linkedin. "
                  "Returns a job id.", {"kind": {"type": "string", "enum": list(ai.TEXT_KINDS)}, "instruction": STR},
    ("kind",), mutates=False, group="ai")
def write_copy(p, a):
    if not ai.status()["ready"]:
        raise UserError("עדיין לא חובר מודל AI. מחברים אחד בהגדרות.")
    return _start("ai", p["id"], _text_job, p["id"], str(a["kind"]), str(a.get("instruction", ""))[:1000])


# ------------------------------------------------------------------ export

@op("export", "Render the timeline to video files. `ratios` may list several frame shapes to export at once "
              "(for example 16:9 and 9:16). Returns a job id; the result lists the files.",
    {"ratios": {"type": "array", "items": {"type": "string", "enum": list(model.RATIOS)}},
     "quality": {"type": "string", "enum": ["720", "1080", "source"]},
     "fps": {"description": "auto, 24, 25, 30, 50 or 60."}, "captions": BOOL}, mutates=False, group="export")
def export_op(p, a):
    if jobs.active(p["id"], "export"):
        raise UserError("ייצוא כבר רץ על הפרויקט הזה.")
    if any(m["status"] == "preparing" for m in p["media"].values()):
        raise UserError("יש קובץ שעדיין בהכנה. מחכים רגע ומנסים שוב.")
    opts = dict(a)
    if "fps" in opts:
        try:
            opts["fps"] = int(opts["fps"]) if str(opts["fps"]) != "auto" else "auto"
        except (TypeError, ValueError):
            opts.pop("fps")
    return _start("export", p["id"], export.export_project, p["id"], opts)


@op("list_exports", "List the video files exported from this project.", mutates=False, group="export")
def list_exports(p, a):
    folder = model.pdir(p["id"]) / "exports"
    return {"exports": [{**e, "path": str(folder / e["file"])} for e in p.get("exports", [])]}


@op("job_status", "Check on a background job (transcription, export, narration, download).",
    {"job": STR}, ("job",), mutates=False, group="project")
def job_status(p, a):
    job = jobs.get(str(a["job"]))
    if not job:
        raise UserError("המשימה לא נמצאה.")
    return job.public()
