"""Render the edited video: cut the picture, rebuild the sound, burn in captions."""
from __future__ import annotations

import re
import shutil
import time
from fractions import Fraction
from pathlib import Path

from . import captions, media, project
from .jobs import Job, UserError

SR = 48000
CH = 2
FADE = int(SR * 0.004)  # a 4 ms ramp at every cut hides clicks


def build_audio(pcm: Path, out: Path, frames: list[tuple[int, int]], fps: Fraction, total_frames: int) -> None:
    """Assemble the kept ranges of the raw audio, sample-accurate to the video frames."""
    import numpy as np
    raw = np.memmap(pcm, dtype="<i2", mode="r") if pcm.stat().st_size >= 2 * CH else np.zeros(0, dtype="<i2")
    n = raw.size // CH
    src = raw[: n * CH].reshape(n, CH) if n else np.zeros((0, CH), dtype="<i2")
    ramp = np.linspace(0.0, 1.0, FADE, dtype=np.float32)[:, None]
    with open(out, "wb") as fh:
        for a, b in frames:
            sa = int(round(Fraction(a) * SR / fps))
            sb = int(round(Fraction(b) * SR / fps))
            if sb <= sa:
                continue
            seg = np.zeros((sb - sa, CH), dtype="<i2")
            part = src[sa:min(sb, n)]
            seg[: len(part)] = part
            k = min(FADE, len(seg) // 2)
            if k > 0 and a > 0:
                seg[:k] = (seg[:k] * ramp[:k]).astype("<i2")
            if k > 0 and b < total_frames:
                seg[-k:] = (seg[-k:] * ramp[:k][::-1]).astype("<i2")
            fh.write(seg.tobytes())


def _caption_inputs(d: dict, w: int, h: int, fps: Fraction, work: Path, job: Job) -> tuple[Path, int] | None:
    """Render every caption state to a PNG strip and list them for ffmpeg's concat reader."""
    style = d["_style"]
    cues = d["cues"]
    if not cues:
        return None
    top, band_h = captions.band_geometry(style, w, h)
    from PIL import Image
    Image.new("RGBA", (w, band_h), (0, 0, 0, 0)).save(work / "blank.png", compress_level=1)
    half = 0.5 / float(fps)

    def edge(t: float) -> float:
        # boundaries sit half a frame early, so each frame lands firmly on one side
        return max(0.0, round(t * float(fps)) / float(fps) - half)

    lines = ["ffconcat version 1.0"]
    rendered: dict[str, str] = {}
    cursor = 0.0
    for n, c in enumerate(cues):
        s, e = edge(c["s"]), edge(c["e"])
        if e <= s or e <= cursor:
            continue
        s = max(s, cursor)
        if s - cursor > 1e-4:
            lines += ["file 'blank.png'", f"duration {s - cursor:.6f}"]
        name = rendered.get(c["k"])
        if name is None:
            spec = project.cue_spec(c["k"])
            texts, active = spec[0], spec[1]
            name = f"c{len(rendered):05d}.png"
            captions.render(texts, active, style, w, h).save(work / name, compress_level=1)
            rendered[c["k"]] = name
        lines += [f"file '{name}'", f"duration {e - s:.6f}"]
        cursor = e
        if n % 25 == 0:
            job.update(0.04 + 0.11 * n / len(cues), "מצייר כתוביות…")
    tail = max(0.5, d["out_duration"] - cursor + 0.5)
    lines += ["file 'blank.png'", f"duration {tail:.6f}", "file 'blank.png'"]
    path = work / "captions.txt"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path, top


def export_video(job: Job, pid: str, opts: dict) -> dict:
    with project.lock(pid):
        p = project.load(pid)
    if not p or p.get("status") != "ready":
        raise UserError("הפרויקט עדיין לא מוכן לייצוא.")
    mediainfo = p["media"]
    pd = project.pdir(pid)
    src = pd / p["source"]
    ratio = opts.get("ratio") if opts.get("ratio") in project.RATIOS else p.get("ratio", "source")
    quality = opts.get("quality") if opts.get("quality") in ("720", "1080", "source") else "1080"
    with_captions = bool(opts.get("captions", p["captions"]["enabled"]))
    p["ratio"] = ratio

    d = project.derive(p, quality)
    frames, fps = d["frames"], Fraction(*d["fps"])
    if not frames:
        raise UserError("לא נשאר מה לייצא: כל המילים מסומנות למחיקה.")
    out_duration = d["out_duration"]
    total_frames = int(mediainfo["duration"] * fps)
    w, h = d["frame"]["w"], d["frame"]["h"]

    work = pd / f"work-{job.id}"
    work.mkdir(parents=True, exist_ok=True)
    try:
        job.update(0.01, "מכין אודיו…")
        args = ["-i", str(src)]
        has_audio = bool(mediainfo.get("has_audio"))
        if has_audio:
            pcm = pd / "audio.pcm"
            if not pcm.exists():
                tmp = pd / f"audio.{job.id}.tmp"
                media.extract_pcm(src, tmp, job.cancel)
                tmp.replace(pcm)
            build_audio(pcm, work / "edited.pcm", frames, fps, total_frames)
            args += ["-f", "s16le", "-ar", str(SR), "-ac", str(CH), "-i", str(work / "edited.pcm")]

        cap = _caption_inputs(d, w, h, fps, work, job) if with_captions else None
        if cap:
            args += ["-f", "concat", "-safe", "0", "-i", str(cap[0])]

        fps_s = f"{fps.numerator}/{fps.denominator}"
        select = "+".join(f"gte(n\\,{a})*lt(n\\,{b})" for a, b in frames)
        chain = f"[0:v:0]fps={fps_s}:start_time=0,select='{select}',setpts=N/({fps_s})/TB,"
        if project.RATIOS.get(ratio) is None:
            chain += f"scale={w}:{h}"
        else:
            chain += f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}"
        chain += ",setsar=1"
        if cap:
            cap_index = 2 if has_audio else 1
            chain += f"[base];[base][{cap_index}:v]overlay=0:{cap[1]}:eof_action=pass:format=auto"
        chain += ",format=yuv420p[v]"
        script = work / "graph.txt"
        script.write_text(chain, encoding="utf-8")
        args += (["-/filter_complex", str(script)] if media.ffmpeg_major() >= 7
                 else ["-filter_complex_script", str(script)])
        args += ["-map", "[v]"]
        if has_audio:
            args += ["-map", "1:a:0", "-c:a", "aac", "-b:a", "192k"]
        args += ["-c:v", "libx264", "-preset", "fast", "-crf", "19", "-r", fps_s,
                 "-movflags", "+faststart", "-t", f"{out_duration + 0.05:.3f}"]

        stem = re.sub(r"[^\w֐-׿ -]+", "", p["name"]).strip().replace(" ", "-")[:40] or "video"
        name = f"{stem}-{time.strftime('%m%d-%H%M%S')}.mp4"
        (pd / "exports").mkdir(exist_ok=True)
        tmp_out = work / "out.mp4"
        job.update(0.15, "מייצא וידאו…")
        media.run(args + [str(tmp_out)], lambda f: job.update(0.15 + 0.84 * f, "מייצא וידאו…"),
                  out_duration, job.cancel)
        final = pd / "exports" / name
        tmp_out.replace(final)
    finally:
        shutil.rmtree(work, ignore_errors=True)

    entry = {"file": name, "created": time.time(), "duration": out_duration, "width": w, "height": h,
             "size": final.stat().st_size, "captions": bool(cap), "ratio": ratio}
    with project.lock(pid):
        cur = project.load(pid)
        if cur:
            cur.setdefault("exports", []).insert(0, entry)
            project.save(cur)
    return entry

