"""The web server: API, static files and the MCP endpoint."""
from __future__ import annotations

import contextlib
import ipaddress
import re
import secrets
import shutil
import socket
import threading
import urllib.parse
from functools import lru_cache
from pathlib import Path

import anyio
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.routing import Route

from . import ai, captions, compose, config, ingest, looks, mcp_server, model, ops, ops_jobs, sfx, stock, transcribe, voice
from .ai import local as ai_local
from .jobs import UserError, jobs


@contextlib.asynccontextmanager
async def lifespan(_app):
    async with mcp_server.start().run():
        yield


app = FastAPI(title=config.APP_NAME, docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
PORT = {"value": 8765}
COOKIE = "studio_k"
_FORWARD_HEADERS = ("x-forwarded-for", "x-forwarded-host", "x-real-ip", "forwarded", "cf-connecting-ip")
_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


# ------------------------------------------------------------ access gate

def _hostname(host_header: str) -> str:
    host = (host_header or "").strip().lower()
    if host.startswith("["):
        return host[1:host.find("]")] if "]" in host else host
    return host.rsplit(":", 1)[0] if ":" in host else host


def is_local(request: Request) -> bool:
    """True only for a program on this very computer talking to localhost directly."""
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
        api = path.startswith(("/api/", "/mcp"))
        if not s.get("mobile_access"):
            msg = "הגישה ממכשירים אחרים כבויה. מפעילים אותה בהגדרות הסטודיו שבמחשב."
            return JSONResponse({"detail": msg}, 403) if api else HTMLResponse(_DENIED % msg, 403)
        token = s["token"]
        given = request.query_params.get("k", "")
        bearer = request.headers.get("authorization", "")
        bearer = bearer[7:] if bearer.lower().startswith("bearer ") else ""
        cookie = request.cookies.get(COOKIE, "")
        if given and secrets.compare_digest(given, token):
            if request.method == "GET" and not api:
                res = RedirectResponse(path, status_code=303)
                res.set_cookie(COOKIE, token, max_age=60 * 60 * 24 * 365, httponly=True, samesite="lax")
                return res
        elif not ((cookie and secrets.compare_digest(cookie, token))
                  or (bearer and secrets.compare_digest(bearer, token))):
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
app.router.routes.append(Route("/mcp", endpoint=mcp_server.Endpoint()))


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
        "ai": ai.status(), "voice": voice.status(), "stock": stock.status(),
        "fonts": captions.list_fonts(),
        "presets": [{"id": p["id"], "name": p["name"],
                     "style": captions.clean_style({**p["style"], "preset": p["id"]})} for p in captions.PRESETS],
        "title_presets": [{"id": p["id"], "name": p["name"],
                           "style": captions.clean_style({**p["style"], "preset": p["id"], "highlight": "none"})}
                          for p in ops.TITLE_PRESETS],
        "looks": looks.describe(),
        "transitions": [{"id": k, "name": v} for k, v in model.TRANSITIONS.items()],
        "sfx": sfx.listing(),
        "ratios": list(model.RATIOS), "fps_choices": list(model.FPS_CHOICES),
        "stock_kinds": [{"id": k, "label": v} for k, v in stock.KINDS.items()], "overlay_ideas": stock.OVERLAY_IDEAS,
        "mobile_url": mobile_url() if request.state.local else None,
        "mcp_url": f"http://127.0.0.1:{PORT['value']}/mcp", "tools": len(ops.OPS) + len(mcp_server.EXTRA),
        "text_kinds": [{"id": "caption", "label": "קפשן לאינסטגרם"}, {"id": "hooks", "label": "הוקים וכותרות"},
                       {"id": "youtube", "label": "כותרת ותיאור ליוטיוב"}, {"id": "linkedin", "label": "פוסט ללינקדאין"}],
    }


@app.put("/api/settings")
async def put_settings(request: Request):
    require_local(request)
    body = await request.json()
    allowed = {k: body[k] for k in ("mobile_access", "transcribe", "ai", "voice", "stock", "theme") if k in body}
    config.update_settings(allowed)
    return {"settings": config.public_settings(), "ai": ai.status(), "voice": voice.status(), "stock": stock.status()}


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


@app.get("/api/voices")
def voices_list(language: str = "he"):
    return {"voices": voice.voices(language), "status": voice.status()}


@app.delete("/api/voices/{voice_id}")
def voices_forget(voice_id: str, request: Request):
    require_local(request)
    voice.forget(voice_id)
    return {"status": voice.status()}


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


@app.get("/api/ops")
def ops_catalogue():
    """Every operation, with its parameters: the REST and MCP surface of the studio."""
    return {"ops": [{"name": o.name, "group": o.group, "description": o.desc, "schema": o.schema(),
                     "changes_project": o.mutates} for o in ops.OPS.values()]}


@app.get("/api/sfx/{name}.wav")
def sfx_file(name: str):
    if name not in sfx.NAMES:
        raise HTTPException(404)
    return FileResponse(sfx.path(name), media_type="audio/wav", headers={"Cache-Control": "max-age=86400"})


# --------------------------------------------------------------- projects

def get_project(pid: str) -> dict:
    p = model.load(pid)
    if not p:
        raise HTTPException(404, "הפרויקט לא נמצא.")
    return p


def _state(p: dict, words_for: set[str] | None = None) -> dict:
    """The project as the browser sees it. Word lists are heavy, so they are sent only when asked for."""
    d = compose.derive(p)
    doc = {k: v for k, v in p.items() if k != "media"}
    doc["media"] = {}
    for mid, m in p["media"].items():
        lean = {k: v for k, v in m.items() if k not in ("words", "tr")}
        lean["word_count"] = len(m["words"])
        lean["languages"] = sorted(m.get("tr") or {})
        if words_for is None or mid in words_for:
            lean["words"] = [{"t": w["t"], "s": w["s"], "e": w["e"], "p": w.get("p", 1), "b": bool(w.get("b")),
                              "d": bool(w.get("d")), "o": w.get("o")} for w in m["words"]]
        doc["media"][mid] = lean
    return {"doc": doc, "derived": compose.public(d), "history": model.history_state(p["id"]),
            "jobs": [j.public() for j in jobs.active(p["id"])]}


@app.get("/api/projects")
def list_projects():
    items = model.list_all()
    for it in items:
        active = jobs.active(it["id"])
        it["job"] = active[0].public() if active else None
    return {"projects": items}


@app.post("/api/projects/new")
async def new_project(request: Request):
    body = await request.json()
    config.ensure_dirs()
    p = model.new_project(" ".join(str(body.get("name") or "פרויקט חדש").split()))
    return {"project": model.summary(p)}


async def _receive(request: Request, dest: Path) -> int:
    size = 0
    with open(dest, "wb") as fh:
        async for chunk in request.stream():
            size += len(chunk)
            fh.write(chunk)
    return size


@app.post("/api/projects")
async def create_project(request: Request, name: str = "video.mp4"):
    """Upload a file as the raw request body. Creates a project with the file already on the timeline."""
    name = Path(urllib.parse.unquote(name)).name
    if model.kind_for(name) is None:
        raise UserError("סוג הקובץ לא נתמך. מעלים וידאו, אודיו או תמונה.")
    config.ensure_dirs()
    p = model.new_project(Path(name).stem)
    try:
        m, dest = ingest.register(p["id"], name, "upload")
        if await _receive(request, dest) == 0:
            raise UserError("הקובץ שהועלה ריק.")
    except BaseException:
        model.delete(p["id"])
        raise
    job = ingest.start(p["id"], m["id"], add={})
    return {"project": model.summary(model.load(p["id"])), "job": job.public()}


@app.post("/api/projects/{pid}/media")
async def upload_media(pid: str, request: Request, name: str = "file", add: int = 0, at: float | None = None):
    """Upload a file into an existing project. With add=1 it is placed on the timeline when ready."""
    get_project(pid)
    name = Path(urllib.parse.unquote(name)).name
    if model.kind_for(name) is None:
        raise UserError("סוג הקובץ לא נתמך. מעלים וידאו, אודיו או תמונה.")
    m, dest = ingest.register(pid, name, "upload")
    try:
        if await _receive(request, dest) == 0:
            raise UserError("הקובץ שהועלה ריק.")
    except BaseException:
        ingest.remove(pid, m["id"])
        raise
    job = ingest.start(pid, m["id"], add=({} if at is None else {"at": at}) if add else None)
    return {"media": m["id"], "job": job.public()}


@app.get("/api/projects/{pid}")
def read_project(pid: str, request: Request):
    p = get_project(pid)
    if request.state.local:
        mcp_server.ACTIVE["pid"] = pid
    return _state(p)


@app.get("/api/projects/{pid}/rev")
def project_rev(pid: str):
    p = get_project(pid)
    return {"rev": p.get("rev", 0), "jobs": [j.public() for j in jobs.active(pid)]}


@app.delete("/api/projects/{pid}")
def delete_project(pid: str):
    get_project(pid)
    jobs.cancel_project(pid)
    with model.lock(pid):
        model.delete(pid)
    if mcp_server.ACTIVE["pid"] == pid:
        mcp_server.ACTIVE["pid"] = None
    return {"ok": True}


@app.post("/api/projects/{pid}/ops")
async def run_op(pid: str, request: Request):
    """Run one operation. This is the same call the MCP tools make."""
    body = await request.json()
    name = str(body.get("op", ""))
    spec = ops.OPS.get(name)
    if not spec:
        raise UserError(f"פעולה לא מוכרת: {name}")
    args = body.get("args") if isinstance(body.get("args"), dict) else {}
    local = request.state.local
    result = await anyio.to_thread.run_sync(lambda: ops_jobs.execute(pid, name, args, body.get("coalesce"), local))
    out = {"result": result}
    if spec.mutates:
        p = get_project(pid)
        touched = set(p["media"]) if spec.group == "words" or name in ("undo", "redo") else set()
        out.update(_state(p, touched))
    return out


def _attachment(name: str) -> str:
    """Content-Disposition for a download whose name may be in Hebrew."""
    suffix = Path(name).suffix
    plain = re.sub(r"[^A-Za-z0-9_-]+", "", Path(name).stem).strip("-_") or "studio"
    if plain[0].isdigit():
        plain = "studio-" + plain
    return f"attachment; filename=\"{plain}{suffix}\"; filename*=UTF-8''{urllib.parse.quote(name)}"


def _file(path: Path, media_type: str | None = None, download: str | None = None, cache: int = 3600):
    if not path.is_file():
        raise HTTPException(404)
    headers = {"Cache-Control": f"private, max-age={cache}"}
    if download:
        headers["Content-Disposition"] = _attachment(download)
    return FileResponse(path, media_type=media_type, headers=headers)


def _media_dir(pid: str, mid: str) -> tuple[dict, Path]:
    p = get_project(pid)
    if not model.valid_mid(mid) or mid not in p["media"]:
        raise HTTPException(404)
    return p["media"][mid], model.mdir(pid, mid)


@app.get("/api/projects/{pid}/media/{mid}/play")
def media_play(pid: str, mid: str):
    """The file the browser plays for this media: a preview copy, or the original when it plays as is."""
    m, folder = _media_dir(pid, mid)
    if m["kind"] == "video":
        return _file(folder / "proxy.mp4", "video/mp4")
    if m["kind"] == "audio" and (folder / "proxy.m4a").exists():
        return _file(folder / "proxy.m4a", "audio/mp4")
    return _file(folder / m["file"])


@app.get("/api/projects/{pid}/media/{mid}/thumb.jpg")
def media_thumb(pid: str, mid: str):
    m, folder = _media_dir(pid, mid)
    return _file(folder / (m["file"] if m["kind"] == "image" else "thumb.jpg"))


@app.get("/api/projects/{pid}/media/{mid}/strip.jpg")
def media_strip(pid: str, mid: str):
    _, folder = _media_dir(pid, mid)
    return _file(folder / "strip.jpg", "image/jpeg")


@app.get("/api/projects/{pid}/media/{mid}/peaks")
def media_peaks(pid: str, mid: str):
    _, folder = _media_dir(pid, mid)
    return JSONResponse({"peaks": config.read_json(folder / "peaks.json", []) or []},
                        headers={"Cache-Control": "private, max-age=3600"})


@app.get("/api/projects/{pid}/thumb.jpg")
def project_thumb(pid: str):
    p = get_project(pid)
    mid = model.summary(p)["thumb"]
    if not mid:
        raise HTTPException(404)
    m = p["media"][mid]
    return _file(model.mdir(pid, mid) / (m["file"] if m["kind"] == "image" else "thumb.jpg"), cache=60)


@lru_cache(maxsize=3000)
def _cue_png(key: str, width: int, spec: tuple) -> bytes:
    texts, active, style_items, w, h = spec
    height = max(2, int(round(h * width / w)))
    return captions.png_bytes(captions.render(texts, active, dict(style_items), width, height))


@app.get("/api/cap/{key}.png")
def cue_image(key: str, w: int = 540):
    if not re.fullmatch(r"[a-f0-9]{20}", key):
        raise HTTPException(404)
    spec = compose.cue_spec(key)
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


# ----------------------------------------------------------------- export

@app.get("/api/projects/{pid}/exports/{name}")
def get_export(pid: str, name: str, dl: int = 0):
    get_project(pid)
    if not re.fullmatch(r"[\w֐-׿ .-]+\.mp4", name) or ".." in name:
        raise HTTPException(404)
    return _file(model.pdir(pid) / "exports" / name, "video/mp4", name if dl else None)


@app.delete("/api/projects/{pid}/exports/{name}")
def delete_export(pid: str, name: str):
    with model.lock(pid):
        p = get_project(pid)
        if not any(e["file"] == name for e in p.get("exports", [])):
            raise HTTPException(404)
        p["exports"] = [e for e in p["exports"] if e["file"] != name]
        model.save(p)
        (model.pdir(pid) / "exports" / name).unlink(missing_ok=True)
    return {"ok": True}


@app.get("/api/projects/{pid}/text.{kind}")
def text_export(pid: str, kind: str):
    if kind not in ("srt", "vtt", "txt", "credits"):
        raise HTTPException(404)
    p = get_project(pid)
    stem = re.sub(r"[^\w֐-׿ -]+", "", p["name"]).strip() or "video"
    if kind == "credits":
        return PlainTextResponse(compose.credits(p) or "אין בפרויקט חומרי סטוק שדורשים קרדיט.\n",
                                 headers={"Content-Disposition": _attachment(f"{stem}-credits.txt")})
    return PlainTextResponse(compose.subtitles(p, kind), headers={"Content-Disposition": _attachment(f"{stem}.{kind}")})


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
    """Media that was mid-work when the app was closed should not look stuck."""
    def work() -> None:
        if not config.PROJECTS_DIR.is_dir():
            return
        for folder in config.PROJECTS_DIR.iterdir():
            pid = folder.name
            if not folder.is_dir() or not model.valid_id(pid):
                continue
            with model.lock(pid):
                p = model.load(pid)
                if not p:
                    continue
                changed = False
                for m in p["media"].values():
                    if m["status"] == "preparing":
                        m.update(status="error", error="ההכנה נקטעה כשהסטודיו נסגר. מעלים את הקובץ שוב.")
                        changed = True
                    if m["transcript"]["status"] == "running":
                        m["transcript"]["status"] = "done" if m["words"] else "none"
                        changed = True
                if changed:
                    model.save(p)
            for stale in folder.glob("work-*"):
                shutil.rmtree(stale, ignore_errors=True)

    threading.Thread(target=work, daemon=True).start()
