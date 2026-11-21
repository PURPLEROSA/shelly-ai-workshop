"""The web server: API and static files."""
from __future__ import annotations

import ipaddress
import re
import secrets
import socket
import threading
import urllib.parse
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from . import ai, captions, cleanup, config, export, media, project, timeline, transcribe
from .ai import local as ai_local
from .jobs import UserError, jobs

app = FastAPI(title=config.APP_NAME, docs_url=None, redoc_url=None, openapi_url=None)
PORT = {"value": 8765}
COOKIE = "studio_k"
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".webm", ".mkv", ".avi", ".3gp", ".mts", ".ts", ".wmv", ".flv"}
_FORWARD_HEADERS = ("x-forwarded-for", "x-forwarded-host", "x-real-ip", "forwarded", "cf-connecting-ip")
_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


# ------------------------------------------------------------ access gate

def _hostname(host_header: str) -> str:
    host = (host_header or "").strip().lower()
    if host.startswith("["):
        return host[1:host.find("]")] if "]" in host else host
    return host.rsplit(":", 1)[0] if ":" in host else host


def is_local(request: Request) -> bool:
    """True only for a browser on this very computer talking to localhost directly."""
    client = request.client.host if request.client else ""
    try:
        if not ipaddress.ip_address(client).is_loopback:
            return False
    except ValueError:
        return False
    if any(h in request.headers for h in _FORWARD_HEADERS):
        return False
    return _hostname(request.headers.get("host", "")) in _LOCAL_HOSTS


_DENIED = """<!doctype html><html lang="he" dir="rtl"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>הסטודיו שלי</title>
<body style="font-family:system-ui,sans-serif;background:#DDF4FF;color:#303039;display:grid;place-items:center;min-height:100vh;margin:0;text-align:center;padding:24px">
<div><h1 style="font-size:28px;margin:0 0 12px">הגישה נעולה</h1>
<p style="font-size:17px;line-height:1.6;max-width:420px">%s</p></div></body></html>"""


@app.middleware("http")
async def gate(request: Request, call_next):
    local = is_local(request)
    request.state.local = local
    path = request.url.path
    if not local:
        s = config.load_settings()
        api = path.startswith("/api/")
        if not s.get("mobile_access"):
            msg = "הגישה ממכשירים אחרים כבויה. מפעילים אותה בהגדרות הסטודיו שבמחשב."
            return JSONResponse({"detail": msg}, 403) if api else HTMLResponse(_DENIED % msg, 403)
        token = s["token"]
        given = request.query_params.get("k", "")
        cookie = request.cookies.get(COOKIE, "")
        if given and secrets.compare_digest(given, token):
            if request.method == "GET" and not api:
                res = RedirectResponse(path, status_code=303)
                res.set_cookie(COOKIE, token, max_age=60 * 60 * 24 * 365, httponly=True, samesite="lax")
                return res
        elif not (cookie and secrets.compare_digest(cookie, token)):
            msg = "כדי להיכנס מהנייד סורקים את קוד ה-QR שמופיע בסטודיו במחשב, תחת ״גישה מהנייד״."
            return JSONResponse({"detail": msg}, 403) if api else HTMLResponse(_DENIED % msg, 403)
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        origin = request.headers.get("origin")
        if origin and urllib.parse.urlparse(origin).netloc.lower() != request.headers.get("host", "").lower():
            return JSONResponse({"detail": "cross-origin request refused"}, 403)
    response = await call_next(request)
    if path == "/" or path.startswith(("/static/", "/api/")):
        response.headers.setdefault("Cache-Control", "no-cache")
    return response


def require_local(request: Request) -> None:
    if not request.state.local:
        raise HTTPException(403, "את ההגדרות אפשר לשנות רק מהמחשב שהסטודיו רץ עליו.")


@app.exception_handler(UserError)
async def user_error(_request: Request, exc: UserError):
    return JSONResponse({"detail": str(exc)}, 400)


# ------------------------------------------------------------------ pages

@app.get("/")
def index():
    return FileResponse(config.WEB_DIR / "index.html", media_type="text/html; charset=utf-8")


app.mount("/static", StaticFiles(directory=str(config.WEB_DIR)), name="static")


@app.get("/fonts/brand")
def brand_font():
    """Optional display font for the interface headings."""
    for cand in [*(config.FONTS_DIR / "custom").glob("brand.*"),
                 config.ROOT.parent / "assets" / "bamberger-black.otf"]:
        if cand.is_file() and cand.suffix.lower() in (".otf", ".ttf", ".woff2", ".woff"):
            return FileResponse(cand, headers={"Cache-Control": "max-age=86400"})
    raise HTTPException(404)


# ------------------------------------------------------------------ state

def lan_ip() -> str | None:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
    except OSError:
        ip = None
    finally:
        s.close()
    if not ip or ip.startswith("127."):
        try:
            ip = next((a for a in socket.gethostbyname_ex(socket.gethostname())[2] if not a.startswith("127.")), None)
        except OSError:
            ip = None
    return ip


def mobile_url() -> str | None:
    ip = lan_ip()
    if not ip:
        return None
    return f"http://{ip}:{PORT['value']}/?k={config.load_settings()['token']}"


@app.get("/api/state")
def state(request: Request):
    downloaded = {k: transcribe.is_downloaded(k) for k in transcribe.MODELS}
    return {
        "app": config.APP_NAME, "version": config.VERSION, "local": request.state.local,
        "settings": config.public_settings(),
        "models": [{"id": k, "label": v["label"], "gb": v["gb"], "downloaded": downloaded[k]}
                   for k, v in transcribe.MODELS.items()],
        "languages": [{"id": a, "label": b} for a, b in transcribe.LANGUAGES],
        "claude_models": config.CLAUDE_MODELS,
        "ai": ai.status(),
        "fonts": captions.list_fonts(),
        "presets": [{"id": p["id"], "name": p["name"],
                     "style": captions.clean_style({**p["style"], "preset": p["id"]})} for p in captions.PRESETS],
        "ratios": list(project.RATIOS),
        "mobile_url": mobile_url() if request.state.local else None,
        "text_kinds": [{"id": "caption", "label": "קפשן לאינסטגרם"}, {"id": "hooks", "label": "הוקים וכותרות"},
                       {"id": "youtube", "label": "כותרת ותיאור ליוטיוב"}, {"id": "linkedin", "label": "פוסט ללינקדאין"}],
    }


@app.put("/api/settings")
async def put_settings(request: Request):
    require_local(request)
    body = await request.json()
    allowed = {k: body[k] for k in ("mobile_access", "transcribe", "ai") if k in body}
    config.update_settings(allowed)
    return {"settings": config.public_settings(), "ai": ai.status()}


@app.get("/api/ai/models")
def ai_models(request: Request, provider: str):
    require_local(request)
    cfg = config.load_settings()["ai"]
    try:
        if provider == "ollama":
            return {"models": ai_local.ollama_models(cfg["ollama"])}
        if provider == "openai":
            return {"models": ai_local.openai_models(cfg["openai"])}
    except Exception:
        hint = "Ollama לא רץ במחשב." if provider == "ollama" else "לא הצלחנו להתחבר לשירות. בודקים כתובת ומפתח."
        raise HTTPException(400, hint)
    raise HTTPException(400, "unknown provider")


@app.get("/api/qr.svg")
def qr(request: Request):
    require_local(request)
    url = mobile_url()
    if not url:
        raise HTTPException(404, "המחשב לא מחובר לרשת.")
    import io
    import segno
    buf = io.BytesIO()
    segno.make(url, error="m").save(buf, kind="svg", scale=8, border=2, dark="#303039", light="#ffffff")
    return Response(buf.getvalue(), media_type="image/svg+xml", headers={"Cache-Control": "no-store"})


# --------------------------------------------------------------- projects

def get_project(pid: str) -> dict:
    p = project.load(pid)
    if not p:
        raise HTTPException(404, "הפרויקט לא נמצא.")
    return p


def _full(p: dict) -> dict:
    d = project.derive(p) if p.get("status") == "ready" else None
    pd = project.pdir(p["id"])
    out = {k: v for k, v in p.items() if k != "words"}
    out["words"] = [{"t": w["t"], "s": w["s"], "e": w["e"], "p": w.get("p", 1), "b": bool(w.get("b")),
                     "d": bool(w.get("d")), "o": w.get("o")} for w in p.get("words", [])]
    out["derived"] = project.public_derived(d) if d else None
    out["jobs"] = [j.public() for j in jobs.active(p["id"])]
    out["has_proxy"] = (pd / "proxy.mp4").exists()
    return out


@app.get("/api/projects")
def list_projects():
    items = project.list_all()
    for it in items:
        active = jobs.active(it["id"])
        it["job"] = active[0].public() if active else None
    return {"projects": items}


def _process(job, pid: str, do_proxy: bool, model: str, language: str):
    """Prepare a preview copy, then transcribe. Runs in the background."""
    pd = project.pdir(pid)
    with project.lock(pid):
        p = project.load(pid)
    if not p:
        return None
    src = pd / p["source"]
    info = p["media"]
    try:
        if do_proxy:
            job.update(0.0, "מכין תצוגה מקדימה…")
            media.make_thumb(src, pd / "thumb.jpg", info["duration"])
            tmp = pd / "proxy.tmp.mp4"
            media.make_proxy(src, tmp, info, lambda f: job.update(f * 0.9, "מכין תצוגה מקדימה…"), job.cancel)
            tmp.replace(pd / "proxy.mp4")
            if info.get("has_audio"):
                config.write_json(pd / "peaks.json", media.make_peaks(src, info["duration"]))
            with project.lock(pid):
                p = project.load(pid)
                p["status"] = "ready"
                project.save(p)
        if not info.get("has_audio"):
            with project.lock(pid):
                p = project.load(pid)
                p["transcript"].update(status="error", error="בסרטון אין פס קול, אז אין מה לתמלל.")
                project.save(p)
            return {"words": 0}
        with project.lock(pid):
            p = project.load(pid)
            p["transcript"].update(status="running", model=model, language=language, error=None)
            project.save(p)
        job.update(0.0, "מתחיל תמלול…")
        words = transcribe.transcribe(src, model, language, info["duration"], job)
        words = timeline.normalize_words(words, info["duration"])
        with project.lock(pid):
            p = project.load(pid)
            p["words"] = words
            p["transcript"].update(status="done", error=None)
            project.save(p)
        return {"words": len(words)}
    except media.Cancelled:
        with project.lock(pid):
            p = project.load(pid)
            if p:
                if p["status"] != "ready":
                    p.update(status="error", error="ההכנה בוטלה.")
                if p["transcript"]["status"] == "running":
                    p["transcript"].update(status="none" if not p["words"] else "done")
                project.save(p)
        raise
    except Exception as e:
        msg = str(e) if isinstance(e, UserError) else f"{type(e).__name__}: {e}"[:300]
        with project.lock(pid):
            p = project.load(pid)
            if p:
                if p["status"] != "ready":
                    p.update(status="error", error=msg)
                else:
                    p["transcript"].update(status="error" if not p["words"] else "done", error=msg)
                project.save(p)
        raise


@app.post("/api/projects")
async def create_project(request: Request, name: str = "video.mp4"):
    """Upload a video as the raw request body; it is written straight to disk."""
    name = Path(urllib.parse.unquote(name)).name
    ext = Path(name).suffix.lower()
    if ext not in VIDEO_EXT:
        ext = ".mp4"
    config.ensure_dirs()
    p = project.create(Path(name).stem, ext)
    pd = project.pdir(p["id"])
    dst = pd / p["source"]
    try:
        size = 0
        with open(dst, "wb") as fh:
            async for chunk in request.stream():
                size += len(chunk)
                fh.write(chunk)
        if size == 0:
            raise UserError("הקובץ שהועלה ריק.")
        info = media.probe(dst)
        if not info["has_video"] or info["duration"] <= 0:
            raise UserError("לא הצלחנו לקרוא את הקובץ כסרטון. נתמכים קבצי וידאו כמו MP4 ו-MOV.")
    except BaseException:
        project.delete(p["id"])
        raise
    p["media"] = info
    p["status"] = "preparing"
    project.save(p)
    s = config.load_settings()["transcribe"]
    job = jobs.submit("process", p["id"], _process, p["id"], True, s["model"], s["language"])
    return {"project": project.summary(p), "job": job.public()}


@app.get("/api/projects/{pid}")
def read_project(pid: str):
    return _full(get_project(pid))


@app.patch("/api/projects/{pid}")
async def rename_project(pid: str, request: Request):
    body = await request.json()
    with project.lock(pid):
        p = get_project(pid)
        name = " ".join(str(body.get("name", "")).split())[:120]
        if name:
            p["name"] = name
            project.save(p)
    return project.summary(p)


@app.delete("/api/projects/{pid}")
def delete_project(pid: str):
    get_project(pid)
    jobs.cancel_project(pid)
    with project.lock(pid):
        project.delete(pid)
    return {"ok": True}


@app.put("/api/projects/{pid}/edit")
async def edit_project(pid: str, request: Request):
    body = await request.json()
    with project.lock(pid):
        p = get_project(pid)
        project.apply_edit(p, body)
        project.save(p)
        d = project.derive(p)
    return {"derived": project.public_derived(d), "captions": p["captions"], "tighten": p["tighten"],
            "ratio": p["ratio"], "rev": body.get("rev")}


@app.post("/api/projects/{pid}/transcribe")
async def retranscribe(pid: str, request: Request):
    body = await request.json()
    p = get_project(pid)
    if p["status"] != "ready":
        raise HTTPException(409, "הסרטון עדיין בהכנה.")
    if jobs.active(pid, "process"):
        raise HTTPException(409, "תמלול כבר רץ על הסרטון הזה.")
    s = config.load_settings()["transcribe"]
    model = body.get("model") if body.get("model") in transcribe.MODELS else s["model"]
    language = body.get("language") or s["language"]
    job = jobs.submit("process", pid, _process, pid, False, model, language)
    return {"job": job.public()}


def _attachment(name: str) -> str:
    """Content-Disposition for a download whose name may be in Hebrew."""
    suffix = Path(name).suffix
    plain = re.sub(r"[^A-Za-z0-9_-]+", "", Path(name).stem).strip("-_") or "studio"
    if plain[0].isdigit():
        plain = "studio-" + plain
    return f"attachment; filename=\"{plain}{suffix}\"; filename*=UTF-8''{urllib.parse.quote(name)}"


def _file(path: Path, media_type: str | None = None, download: str | None = None):
    if not path.is_file():
        raise HTTPException(404)
    headers = {"Cache-Control": "private, max-age=3600"}
    if download:
        headers["Content-Disposition"] = _attachment(download)
    return FileResponse(path, media_type=media_type, headers=headers)


@app.get("/api/projects/{pid}/proxy.mp4")
def proxy(pid: str):
    get_project(pid)
    return _file(project.pdir(pid) / "proxy.mp4", "video/mp4")


@app.get("/api/projects/{pid}/thumb.jpg")
def thumb(pid: str):
    get_project(pid)
    return _file(project.pdir(pid) / "thumb.jpg", "image/jpeg")


@app.get("/api/projects/{pid}/peaks")
def peaks(pid: str):
    get_project(pid)
    return {"peaks": config.read_json(project.pdir(pid) / "peaks.json", []) or []}


@lru_cache(maxsize=3000)
def _cue_png(key: str, width: int, spec: tuple) -> bytes:
    texts, active, style_items, w, h = spec
    height = max(2, int(round(h * width / w)))
    return captions.png_bytes(captions.render(texts, active, dict(style_items), width, height))


@app.get("/api/cap/{key}.png")
def cue_image(key: str, w: int = 540):
    if not re.fullmatch(r"[a-f0-9]{20}", key):
        raise HTTPException(404)
    spec = project.cue_spec(key)
    if not spec:
        raise HTTPException(404)
    texts, active, style, fw, fh = spec
    width = max(180, min(1440, int(w) // 2 * 2))
    data = _cue_png(key, width, (texts, active, tuple(sorted(style.items())), fw, fh))
    return Response(data, media_type="image/png", headers={"Cache-Control": "private, max-age=86400, immutable"})


@app.post("/api/preview-style")
async def preview_style(request: Request):
    """A sample caption for a style card: lets every preset show its true look."""
    body = await request.json()
    style = captions.clean_style(body.get("style"))
    style["y"] = 0.5
    texts = tuple(str(t)[:30] for t in (body.get("texts") or ["ככה", "זה", "נראה"]))[:6]
    w = max(180, min(900, int(body.get("w", 420))))
    h = int(round(w * 16 / 9))
    img = captions.render(texts, int(body.get("active", 1)), style, w, h)
    box = img.getbbox() or (0, 0, w, 10)
    pad = int(w * 0.03)
    img = img.crop((0, max(0, box[1] - pad), w, min(img.height, box[3] + pad)))
    return Response(captions.png_bytes(img), media_type="image/png")


# ----------------------------------------------------- clean-up and AI

@app.post("/api/projects/{pid}/suggest")
async def suggest(pid: str, request: Request):
    body = await request.json()
    p = get_project(pid)
    kind = body.get("kind")
    if kind == "fillers":
        idx = cleanup.find_fillers(p["words"])
        return {"indices": idx, "summary": f"נמצאו {len(idx)} מילות מילוי." if idx else "לא נמצאו מילות מילוי."}
    if kind == "repeats":
        idx = cleanup.find_repeats(p["words"])
        return {"indices": idx, "summary": f"נמצאו {len(idx)} מילים שנאמרו פעמיים ברצף." if idx else "לא נמצאו חזרות."}
    raise HTTPException(400, "unknown kind")


def _ai_edit(job, pid: str, instruction: str):
    job.update(0.1, "המודל קורא את התמלול…")
    with project.lock(pid):
        p = project.load(pid)
    if not p:
        raise UserError("הפרויקט לא נמצא.")
    d = project.derive(p)
    return ai.suggest_cuts(p, d["_tmap"], instruction)


def _ai_text(job, pid: str, kind: str, instruction: str):
    job.update(0.1, "המודל כותב…")
    with project.lock(pid):
        p = project.load(pid)
    if not p:
        raise UserError("הפרויקט לא נמצא.")
    return {"text": ai.write_text(p, kind, instruction)}


@app.post("/api/projects/{pid}/ai")
async def ai_job(pid: str, request: Request):
    body = await request.json()
    get_project(pid)
    if not ai.status()["ready"]:
        raise UserError("עדיין לא חובר מודל AI. מחברים אחד בהגדרות.")
    instruction = str(body.get("instruction", ""))[:2000]
    if body.get("mode") == "text":
        job = jobs.submit("ai", pid, _ai_text, pid, str(body.get("kind", "custom")), instruction)
    else:
        if not instruction.strip():
            raise UserError("כותבים הנחיה קצרה: מה לעשות עם הסרטון.")
        job = jobs.submit("ai", pid, _ai_edit, pid, instruction)
    return {"job": job.public()}


# ----------------------------------------------------------------- export

@app.post("/api/projects/{pid}/export")
async def start_export(pid: str, request: Request):
    body = await request.json()
    p = get_project(pid)
    if p["status"] != "ready":
        raise HTTPException(409, "הסרטון עדיין בהכנה.")
    if jobs.active(pid, "export"):
        raise HTTPException(409, "ייצוא כבר רץ על הסרטון הזה.")
    job = jobs.submit("export", pid, export.export_video, pid, body)
    return {"job": job.public()}


@app.get("/api/projects/{pid}/exports/{name}")
def get_export(pid: str, name: str, dl: int = 0):
    get_project(pid)
    if not re.fullmatch(r"[\w֐-׿ .-]+\.mp4", name) or ".." in name:
        raise HTTPException(404)
    return _file(project.pdir(pid) / "exports" / name, "video/mp4", name if dl else None)


@app.delete("/api/projects/{pid}/exports/{name}")
def delete_export(pid: str, name: str):
    with project.lock(pid):
        p = get_project(pid)
        if not any(e["file"] == name for e in p.get("exports", [])):
            raise HTTPException(404)
        p["exports"] = [e for e in p["exports"] if e["file"] != name]
        project.save(p)
        try:
            (project.pdir(pid) / "exports" / name).unlink()
        except OSError:
            pass
    return {"ok": True}


@app.get("/api/projects/{pid}/text.{kind}")
def text_export(pid: str, kind: str):
    if kind not in ("srt", "vtt", "txt"):
        raise HTTPException(404)
    p = get_project(pid)
    body = project.subtitles(p, kind)
    stem = re.sub(r"[^\w֐-׿ -]+", "", p["name"]).strip() or "video"
    return PlainTextResponse(body, headers={"Content-Disposition": _attachment(f"{stem}.{kind}")})


# ------------------------------------------------------------------- jobs

@app.get("/api/jobs/{job_id}")
def job_status(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404)
    return job.public()


@app.post("/api/jobs/{job_id}/cancel")
def job_cancel(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404)
    job.cancel.set()
    return job.public()


def recover_interrupted() -> None:
    """Projects that were mid-work when the app was closed should not look stuck."""
    def work() -> None:
        for item in project.list_all():
            with project.lock(item["id"]):
                p = project.load(item["id"])
                if not p:
                    continue
                changed = False
                if p["status"] in ("new", "preparing"):
                    if (project.pdir(p["id"]) / "proxy.mp4").exists():
                        p["status"] = "ready"
                    else:
                        p.update(status="error", error="ההכנה נקטעה כשהסטודיו נסגר. מעלים את הסרטון שוב.")
                    changed = True
                if p["transcript"]["status"] == "running":
                    p["transcript"].update(status="done" if p["words"] else "none")
                    changed = True
                if changed:
                    project.save(p)
            for stale in project.pdir(item["id"]).glob("work-*"):
                import shutil
                shutil.rmtree(stale, ignore_errors=True)

    threading.Thread(target=work, daemon=True).start()
