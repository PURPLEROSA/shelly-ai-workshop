"""Free stock: B-roll, overlays, images and music from Pexels, Pixabay and Openverse."""
from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import OrderedDict
from pathlib import Path

from . import config
from .ai.local import _ssl_context
from .jobs import UserError

UA = "Mozilla/5.0 (compatible; LocalStudio/2.0)"
KINDS = {"video": "וידאו", "overlay": "אוברליי", "image": "תמונות", "music": "מוזיקה"}
OVERLAY_IDEAS = ["light leak", "film grain", "dust particles", "bokeh lights", "lens flare", "smoke overlay"]
MAX_BYTES = 400 * 1024 * 1024

# search results are remembered so that a download can only fetch a URL a provider gave us
_results: "OrderedDict[str, dict]" = OrderedDict()
_guard = threading.Lock()


def _get(url: str, headers: dict | None = None, timeout: float = 20):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json", **(headers or {})})
    last = "המאגר לא זמין כרגע. מנסים שוב בעוד רגע."
    for attempt in range(3):   # the free libraries hiccup now and then; a retry usually goes through
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=_ssl_context()) as res:
                return json.loads(res.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise UserError("מפתח ה-API של מאגר הסטוק לא תקין. כדאי לבדוק אותו בהגדרות.")
            if e.code == 429:
                raise UserError("הגענו למגבלת החיפושים של המאגר. מנסים שוב בעוד כמה דקות.")
            if e.code < 500:
                raise UserError(f"המאגר החזיר שגיאה ({e.code}).")
        except (urllib.error.URLError, OSError, ValueError):
            last = "אין חיבור למאגר הסטוק. בודקים את האינטרנט."
        time.sleep(1.0 + attempt)
    raise UserError(last)


def status() -> dict:
    s = config.load_settings()["stock"]
    return {"pexels": bool(s.get("pexels_key")), "pixabay": bool(s.get("pixabay_key")), "openverse": True}


def _remember(rows: list[dict]) -> list[dict]:
    with _guard:
        for r in rows:
            _results[r["token"]] = r
            _results.move_to_end(r["token"])
        while len(_results) > 600:
            _results.popitem(last=False)
    return [{k: v for k, v in r.items() if k != "url"} for r in rows]


def lookup(token: str) -> dict | None:
    with _guard:
        return _results.get(token)


def _pexels_videos(q: str, page: int, key: str, portrait: bool) -> list[dict]:
    params = {"query": q, "per_page": 18, "page": page}
    if portrait:
        params["orientation"] = "portrait"
    data = _get("https://api.pexels.com/videos/search?" + urllib.parse.urlencode(params), {"Authorization": key})
    out = []
    for v in data.get("videos", []):
        files = [f for f in v.get("video_files", []) if f.get("link") and (f.get("file_type") or "").endswith("mp4")]
        if not files:
            continue
        good = sorted(files, key=lambda f: abs(min(f.get("width") or 0, f.get("height") or 0) - 1080))[0]
        small = sorted(files, key=lambda f: (f.get("width") or 0) * (f.get("height") or 0))[0]
        out.append({"token": f"pexels-v-{v['id']}", "provider": "Pexels", "kind": "video", "title": f"Pexels {v['id']}",
                    "author": (v.get("user") or {}).get("name", ""), "license": "Pexels License", "page": v.get("url", ""),
                    "thumb": v.get("image", ""), "preview": small["link"], "url": good["link"],
                    "width": good.get("width") or 0, "height": good.get("height") or 0, "duration": v.get("duration") or 0,
                    "ext": ".mp4"})
    return out


def _pexels_photos(q: str, page: int, key: str) -> list[dict]:
    data = _get("https://api.pexels.com/v1/search?" + urllib.parse.urlencode({"query": q, "per_page": 18, "page": page}),
                {"Authorization": key})
    return [{"token": f"pexels-p-{v['id']}", "provider": "Pexels", "kind": "image", "title": v.get("alt") or f"Pexels {v['id']}",
             "author": v.get("photographer", ""), "license": "Pexels License", "page": v.get("url", ""),
             "thumb": v["src"].get("medium", ""), "preview": v["src"].get("large", ""), "url": v["src"].get("large2x", ""),
             "width": v.get("width") or 0, "height": v.get("height") or 0, "duration": 0, "ext": ".jpg"}
            for v in data.get("photos", []) if v.get("src")]


def _pixabay_videos(q: str, page: int, key: str) -> list[dict]:
    data = _get("https://pixabay.com/api/videos/?" + urllib.parse.urlencode({"key": key, "q": q, "per_page": 18, "page": page}))
    out = []
    for v in data.get("hits", []):
        vids = v.get("videos") or {}
        good = vids.get("large") or vids.get("medium") or vids.get("small") or {}
        if not good.get("url"):
            good = vids.get("medium") or vids.get("small") or {}
        small = vids.get("tiny") or vids.get("small") or good
        if not good.get("url"):
            continue
        out.append({"token": f"pixabay-v-{v['id']}", "provider": "Pixabay", "kind": "video", "title": v.get("tags", ""),
                    "author": v.get("user", ""), "license": "Pixabay Content License", "page": v.get("pageURL", ""),
                    "thumb": small.get("thumbnail") or good.get("thumbnail", ""), "preview": small.get("url", ""),
                    "url": good["url"], "width": good.get("width") or 0, "height": good.get("height") or 0,
                    "duration": v.get("duration") or 0, "ext": ".mp4"})
    return out


def _pixabay_photos(q: str, page: int, key: str) -> list[dict]:
    data = _get("https://pixabay.com/api/?" + urllib.parse.urlencode(
        {"key": key, "q": q, "per_page": 18, "page": page, "image_type": "photo", "safesearch": "true"}))
    return [{"token": f"pixabay-p-{v['id']}", "provider": "Pixabay", "kind": "image", "title": v.get("tags", ""),
             "author": v.get("user", ""), "license": "Pixabay Content License", "page": v.get("pageURL", ""),
             "thumb": v.get("webformatURL") or v.get("previewURL", ""), "preview": v.get("webformatURL", ""),
             "url": v.get("largeImageURL", ""), "width": v.get("imageWidth") or 0, "height": v.get("imageHeight") or 0,
             "duration": 0, "ext": ".jpg"} for v in data.get("hits", []) if v.get("largeImageURL")]


def _openverse(kind: str, q: str, page: int) -> list[dict]:
    path = "audio" if kind == "music" else "images"
    # only licences that allow commercial use and changes: safe to cut into a video
    params = {"q": q, "page_size": 18, "page": page, "license_type": "commercial,modification"}
    data = _get(f"https://api.openverse.org/v1/{path}/?" + urllib.parse.urlencode(params))
    out = []
    for v in data.get("results", []):
        lic = str(v.get("license", "")).lower()
        if not v.get("url") or "nc" in lic.split("-") or "nd" in lic.split("-"):
            continue
        ftype = (v.get("filetype") or "").lower().lstrip(".")
        if kind == "music":
            ext = ".ogg" if ftype.startswith("og") else ".wav" if ftype == "wav" else ".flac" if ftype == "flac" else ".mp3"
        else:
            ext = "." + ftype if ftype in ("jpg", "jpeg", "png", "webp", "gif") else ".jpg"
        name = "Public domain" if lic in ("cc0", "pdm") else f"CC {lic.upper()} {v.get('license_version') or ''}".strip()
        out.append({"token": f"openverse-{path[0]}-{v['id']}", "provider": "Openverse", "kind": kind,
                    "title": v.get("title") or "", "author": v.get("creator") or "", "license": name,
                    "page": v.get("foreign_landing_url", ""), "thumb": v.get("thumbnail") or "",
                    "preview": v["url"], "url": v["url"], "width": v.get("width") or 0, "height": v.get("height") or 0,
                    "duration": round((v.get("duration") or 0) / 1000, 1), "ext": ext})
    return out


def search(kind: str, query: str, page: int = 1, portrait: bool = True) -> dict:
    if kind not in KINDS:
        raise UserError("סוג חיפוש לא מוכר.")
    query = " ".join(str(query).split())[:100]
    if not query:
        raise UserError("כותבים מה לחפש.")
    page = max(1, min(20, int(page or 1)))
    s = config.load_settings()["stock"]
    rows: list[dict] = []
    notes: list[str] = []
    errors: list[str] = []

    def attempt(fn, *args):
        try:
            rows.extend(fn(*args))
        except UserError as e:
            errors.append(str(e))

    if kind in ("video", "overlay"):
        if s.get("pexels_key"):
            attempt(_pexels_videos, query, page, s["pexels_key"], portrait and kind == "video")
        if s.get("pixabay_key"):
            attempt(_pixabay_videos, query, page, s["pixabay_key"])
        if not (s.get("pexels_key") or s.get("pixabay_key")):
            notes.append("לחיפוש וידאו צריך מפתח חינמי של Pexels או Pixabay. מוסיפים אותו בהגדרות, תחת ״מאגר״.")
        for r in rows:
            r["kind"] = kind
    elif kind == "image":
        if s.get("pexels_key"):
            attempt(_pexels_photos, query, page, s["pexels_key"])
        if s.get("pixabay_key"):
            attempt(_pixabay_photos, query, page, s["pixabay_key"])
        attempt(_openverse, "image", query, page)
    else:
        attempt(_openverse, "music", query, page)
    if not rows and errors:
        raise UserError(errors[0])
    return {"results": _remember(rows), "notes": notes, "page": page}


def download(token: str, dest_dir: Path, on_progress=None, cancel=None) -> tuple[Path, dict]:
    r = lookup(token)
    if not r:
        raise UserError("תוצאת החיפוש פגה. מחפשים שוב ובוחרים מחדש.")
    url = r["url"]
    if not url.lower().startswith("https://"):
        raise UserError("כתובת ההורדה לא מאובטחת.")
    ext = r.get("ext") or Path(urllib.parse.urlparse(url).path).suffix or ".bin"
    path = dest_dir / f"source{ext}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=60, context=_ssl_context()) as res, open(path, "wb") as fh:
            total = int(res.headers.get("Content-Length") or 0)
            got = 0
            while True:
                if cancel is not None and cancel.is_set():
                    raise UserError("ההורדה בוטלה.")
                chunk = res.read(256 * 1024)
                if not chunk:
                    break
                got += len(chunk)
                if got > MAX_BYTES:
                    raise UserError("הקובץ גדול מדי.")
                fh.write(chunk)
                if on_progress and total:
                    on_progress(got / total)
    except (urllib.error.URLError, OSError):
        path.unlink(missing_ok=True)
        raise UserError("ההורדה מהמאגר נכשלה. מנסים שוב.")
    return path, r
