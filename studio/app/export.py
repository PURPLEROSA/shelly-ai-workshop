"""Render the timeline to a video file with ffmpeg.

The picture is assembled clip by clip (trim, word cuts, speed, zoom, colour
look), joined with cuts or transitions, then B-roll, overlays, captions and
titles are laid on top. The sound of every item is cut sample-exactly in
numpy and mixed by ffmpeg.
"""
from __future__ import annotations

import re
import shutil
import time
from fractions import Fraction
from pathlib import Path

from . import captions, compose, looks, media, model
from .jobs import Job, UserError

SR = 48000
CH = 2
FADE = int(SR * 0.004)  # a 4 ms ramp at every cut hides clicks


def build_audio(pcm: Path, out: Path, frames: list[tuple[int, int]], fps: Fraction, total_frames: int) -> int:
    """Assemble the kept ranges of raw audio, sample-accurate to the video frames. Returns samples written."""
    import numpy as np
    raw = np.memmap(pcm, dtype="<i2", mode="r") if pcm.exists() and pcm.stat().st_size >= 2 * CH \
        else np.zeros(0, dtype="<i2")
    n = raw.size // CH
    src = raw[: n * CH].reshape(n, CH) if n else np.zeros((0, CH), dtype="<i2")
    ramp = np.linspace(0.0, 1.0, FADE, dtype=np.float32)[:, None]
    written = 0
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
            written += len(seg)
    return written


def media_pcm(pid: str, m: dict, cancel=None) -> Path:
    """Raw 48 kHz stereo audio of a media file, extracted once and cached."""
    folder = model.mdir(pid, m["id"])
    pcm = folder / "audio.pcm"
    if not pcm.exists():
        tmp = folder / f"audio.{time.time_ns()}.tmp"
        media.extract_pcm(folder / m["file"], tmp, cancel)
        tmp.replace(pcm)
    return pcm


def ease_expr(keys: list[tuple[float, float]], var: str = "t") -> str:
    """An ffmpeg expression that eases smoothly between (time, value) keyframes."""
    if not keys:
        return "1"
    expr = f"{keys[-1][1]:.5f}"
    for (t0, v0), (t1, v1) in reversed(list(zip(keys, keys[1:]))):
        span = max(t1 - t0, 1e-4)
        u = f"(({var}-{t0:.4f})/{span:.4f})"
        seg = f"({v0:.5f}+({v1 - v0:.5f})*{u}*{u}*(3-2*{u}))"
        expr = f"if(lt({var},{t1:.4f}),{seg},{expr})"
    return f"if(lt({var},{keys[0][0]:.4f}),{keys[0][1]:.5f},{expr})"


def _atempo(speed: float) -> list[str]:
    out = []
    s = speed
    while s > 2.0 + 1e-9:
        out.append("atempo=2.0")
        s /= 2.0
    while s < 0.5 - 1e-9:
        out.append("atempo=0.5")
        s /= 0.5
    if abs(s - 1.0) > 1e-4:
        out.append(f"atempo={s:.5f}")
    return out


class Graph:
    """Collects ffmpeg inputs and filter chains."""

    def __init__(self, work: Path):
        self.work = work
        self.inputs: list[str] = []
        self.count = 0
        self.chains: list[str] = []
        self.n = 0

    def input(self, *args: str) -> int:
        self.inputs += list(args)
        self.count += 1
        return self.count - 1

    def label(self, prefix: str = "x") -> str:
        self.n += 1
        return f"{prefix}{self.n}"

    def add(self, chain: str) -> None:
        self.chains.append(chain)


def _fit(m: dict, w: int, h: int) -> tuple[int, int]:
    """Size at which a source covers the frame."""
    mw, mh = max(2, m.get("width") or w), max(2, m.get("height") or h)
    k = max(w / mw, h / mh)
    return max(w, int(round(mw * k / 2)) * 2), max(h, int(round(mh * k / 2)) * 2)


def _video_chain(g: Graph, pid: str, m: dict, it: dict, info: dict, w: int, h: int, fps: Fraction,
                 exact: bool) -> str:
    """Filter chain producing one item's picture, starting at time zero. Returns its output label."""
    f = float(fps)
    fps_s = f"{fps.numerator}/{fps.denominator}"
    segs = info["segs"]
    dur_f = info["dur_f"]
    speed = info["speed"]
    src = model.mdir(pid, m["id"]) / m["file"]
    if m["kind"] == "image":
        idx = g.input("-loop", "1", "-framerate", fps_s, "-t", f"{dur_f / f + 0.5:.3f}", "-i", str(src))
        chain = f"[{idx}:v:0]fps={fps_s}"
    else:
        first, last = segs[0][0], segs[-1][1]
        idx = g.input("-ss", f"{first / f:.6f}", "-t", f"{(last - first) / f + 1.0:.3f}", "-i", str(src))
        sel = "+".join(f"gte(n\\,{a - first})*lt(n\\,{b - first})" for a, b in segs)
        chain = f"[{idx}:v:0]fps={fps_s}:start_time=0,select='{sel}',"
        chain += f"setpts=N/({fps_s})/TB" if abs(speed - 1) < 1e-4 else f"setpts=N/(({fps_s})*{speed:.5f})/TB,fps={fps_s}"
    cw, ch = _fit(m, w, h)
    keys = it.get("zoom") or []
    if keys:
        z = ease_expr([(k["t"], k["s"]) for k in keys])
        cx = ease_expr([(k["t"], k["x"]) for k in keys])
        cy = ease_expr([(k["t"], k["y"]) for k in keys])
        bg = g.label("bg")
        zl = g.label("z")
        g.add(f"color=c=black:s={w}x{h}:r={fps_s}:d={dur_f / f + 1:.3f}[{bg}]")
        g.add(chain + f",scale=w='ceil({cw}*({z})/2)*2':h='ceil({ch}*({z})/2)*2':eval=frame:flags=bicubic[{zl}]")
        chain = (f"[{bg}][{zl}]overlay=x='min(0,max(W-w,W/2-({cx})*w))':y='min(0,max(H-h,H/2-({cy})*h))'"
                 f":eval=frame:shortest=1")
    else:
        chain += f",scale={cw}:{ch}:flags=bicubic,crop={w}:{h}"
    if it.get("look"):
        cube = looks.cube_path(it["look"])
        if cube:
            local = g.work / cube.name
            if not local.exists():
                shutil.copyfile(cube, local)
            chain += f",lut3d=file={cube.name}"
    chain += f",fps={fps_s},format=yuv420p,setsar=1"
    if exact:
        chain += f",tpad=stop_mode=clone:stop_duration=1,trim=end_frame={dur_f},setpts=PTS-STARTPTS"
    chain += ",settb=AVTB"
    out = g.label("v")
    g.add(chain + f"[{out}]")
    return out


def _audio_chain(g: Graph, pid: str, m: dict, info: dict, fps: Fraction, volume: float, fade_in: float,
                 fade_out: float, job: Job, start: float | None = None) -> str | None:
    """Filter chain producing one item's sound, placed on the timeline. Returns its label, or None if silent."""
    if not info["segs"] or not info["dur_f"] or volume <= 0:
        return None
    f = float(fps)
    pcm = media_pcm(pid, m, job.cancel)
    part = g.work / f"a{g.label('')}.pcm"
    total = int(m["duration"] * fps)
    if not build_audio(pcm, part, info["segs"], fps, total):
        return None
    idx = g.input("-f", "s16le", "-ar", str(SR), "-ac", str(CH), "-i", str(part))
    dur = info["dur_f"] / f
    steps = _atempo(info["speed"]) + ["apad", f"atrim=0:{dur:.5f}", "asetpts=N/SR/TB"]
    if abs(volume - 1) > 1e-3:
        steps.append(f"volume={volume:.3f}")
    if fade_in > 1e-3:
        steps.append(f"afade=t=in:st=0:d={min(fade_in, dur):.4f}")
    if fade_out > 1e-3:
        d = min(fade_out, dur)
        steps.append(f"afade=t=out:st={dur - d:.4f}:d={d:.4f}")
    at = info["start_f"] / f if start is None else start
    if at > 1e-4:
        steps.append(f"adelay={int(round(at * 1000))}:all=1")
    out = g.label("a")
    g.add(f"[{idx}:a:0]" + ",".join(steps) + f"[{out}]")
    return out


def _caption_list(cues: list[dict], style: dict, w: int, h: int, fps: Fraction, work: Path, tag: str,
                  duration: float) -> tuple[Path, int] | None:
    if not cues:
        return None
    top, band_h = captions.band_geometry(style, w, h)
    from PIL import Image
    blank = f"{tag}blank.png"
    Image.new("RGBA", (w, band_h), (0, 0, 0, 0)).save(work / blank, compress_level=1)
    f = float(fps)

    def edge(t: float) -> float:
        # boundaries sit half a frame early, so each frame lands firmly on one side
        return max(0.0, round(t * f) / f - 0.5 / f)

    lines = ["ffconcat version 1.0"]
    rendered: dict[str, str] = {}
    cursor = 0.0
    for c in cues:
        s, e = edge(c["s"]), edge(c["e"])
        if e <= s or e <= cursor:
            continue
        s = max(s, cursor)
        if s - cursor > 1e-4:
            lines += [f"file '{blank}'", f"duration {s - cursor:.6f}"]
        name = rendered.get(c["k"])
        if name is None:
            spec = compose.cue_spec(c["k"])
            name = f"{tag}{len(rendered):05d}.png"
            captions.render(spec[0], spec[1], style, w, h).save(work / name, compress_level=1)
            rendered[c["k"]] = name
        lines += [f"file '{name}'", f"duration {e - s:.6f}"]
        cursor = e
    tail = max(0.5, duration - cursor + 0.5)
    lines += [f"file '{blank}'", f"duration {tail:.6f}", f"file '{blank}'"]
    path = work / f"{tag}list.txt"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path, top


def render(job: Job, pid: str, p: dict, ratio: str, quality: str, with_captions: bool, lo: float, hi: float,
           audio_only: dict | None = None) -> dict:
    """Render one output file. Progress is reported between `lo` and `hi`."""
    d = compose.derive(p, quality, ratio)
    lay: compose.Layout = d["_layout"]
    fps = lay.fps
    f = float(fps)
    fps_s = f"{fps.numerator}/{fps.denominator}"
    w, h = d["frame"]["w"], d["frame"]["h"]
    total_f = lay.total_f
    if total_f <= 0:
        raise UserError("הטיימליין ריק. מוסיפים קליפ ואז מייצאים.")
    T = total_f / f
    pd = model.pdir(pid)
    work = pd / f"work-{job.id}-{ratio.replace(':', 'x')}"
    work.mkdir(parents=True, exist_ok=True)
    span = hi - lo

    def note(frac: float, msg: str) -> None:
        job.update(lo + span * frac, msg)

    try:
        g = Graph(work)
        items = {it["id"]: (t, it) for t, it in model.all_items(p)}
        note(0.01, "מכין את הטיימליין…")

        # ----- picture
        g.add(f"color=c=black:s={w}x{h}:r={fps_s}:d={T + 0.2:.3f},format=yuv420p,settb=AVTB[base]")
        cur = "base"
        acc, acc_f = None, 0
        for iid in lay.order:
            info = lay.items[iid]
            if not info["dur_f"]:
                continue
            _, it = items[iid]
            lab = _video_chain(g, pid, p["media"][it["media"]], it, info, w, h, fps, True)
            if acc is None:
                acc, acc_f = lab, info["dur_f"]
                continue
            nxt = g.label("m")
            if info["trans_f"]:
                td = info["trans_f"] / f
                kind = (it.get("transition") or {}).get("type", "fade")
                g.add(f"[{acc}][{lab}]xfade=transition={kind}:duration={td:.5f}:offset={(acc_f - info['trans_f']) / f:.5f}"
                      f",fps={fps_s},format=yuv420p,settb=AVTB[{nxt}]")
                acc_f += info["dur_f"] - info["trans_f"]
            else:
                g.add(f"[{acc}][{lab}]concat=n=2:v=1:a=0,fps={fps_s},settb=AVTB[{nxt}]")
                acc_f += info["dur_f"]
            acc = nxt
        if acc:
            nxt = g.label("c")
            g.add(f"[{cur}][{acc}]overlay=eof_action=pass[{nxt}]")
            cur = nxt

        for track in reversed(p["tracks"]):
            if track["kind"] != "video" or track.get("main") or track.get("hidden"):
                continue
            for it in track["items"]:
                info = lay.items[it["id"]]
                if not info["dur_f"]:
                    continue
                lab = _video_chain(g, pid, p["media"][it["media"]], it, info, w, h, fps, True)
                start = info["start_f"] / f
                nxt = g.label("c")
                op = float(it.get("opacity", 1))
                if it.get("blend") == "screen":
                    g.add(f"[{lab}]format=gbrp,tpad=start_duration={start:.5f}:stop_mode=add:stop_duration={T + 1:.3f}"
                          f"[{lab}p];[{cur}]format=gbrp[{lab}m];[{lab}m][{lab}p]blend=all_mode=screen:all_opacity={op:.3f}"
                          f":shortest=1,format=yuv420p[{nxt}]")
                else:
                    alpha = f"format=yuva420p,colorchannelmixer=aa={op:.3f}," if op < 0.999 else ""
                    g.add(f"[{lab}]{alpha}setpts=PTS+{start:.5f}/TB[{lab}p];[{cur}][{lab}p]overlay=eof_action=pass[{nxt}]")
                cur = nxt

        if with_captions:
            for cues, style, tag in ((d["cues"], d["_style"], "c"), (d["cues2"], d["_style2"], "d")):
                note(0.05, "מצייר כתוביות…")
                cap = _caption_list(cues, style, w, h, fps, work, tag, T)
                if cap:
                    idx = g.input("-f", "concat", "-safe", "0", "-i", str(cap[0]))
                    nxt = g.label("c")
                    g.add(f"[{cur}][{idx}:v]overlay=0:{cap[1]}:eof_action=pass:format=auto[{nxt}]")
                    cur = nxt

        for n, t in enumerate(d["titles"]):
            spec = compose.cue_spec(t["k"])
            if not spec:
                continue
            name = f"t{n:03d}.png"
            captions.render(spec[0], -1, spec[2], w, h).save(work / name, compress_level=1)
            dur = t["dur"]
            idx = g.input("-loop", "1", "-framerate", fps_s, "-t", f"{dur:.4f}", "-i", str(work / name))
            fade = min(t["fade"], dur / 2)
            fx = f"format=rgba,fade=t=in:st=0:d={fade:.3f}:alpha=1,fade=t=out:st={dur - fade:.3f}:d={fade:.3f}:alpha=1," \
                if fade > 0.01 else "format=rgba,"
            nxt = g.label("c")
            g.add(f"[{idx}:v]{fx}setpts=PTS+{t['start']:.5f}/TB[tt{n}];[{cur}][tt{n}]overlay=0:{t['top_px']}"
                  f":eof_action=pass:format=auto[{nxt}]")
            cur = nxt
        g.add(f"[{cur}]trim=end_frame={total_f},format=yuv420p[v]")

        # ----- sound
        note(0.08, "מכין אודיו…")
        voices: list[str] = []
        order = lay.order
        for track in p["tracks"]:
            if track["kind"] == "text" or track.get("muted"):
                continue
            for it in track["items"]:
                m = p["media"][it["media"]]
                info = lay.items[it["id"]]
                if it.get("mute") or not (m["has_audio"] or m["kind"] == "audio"):
                    continue
                fin, fout = float(it.get("fade_in", 0)), float(it.get("fade_out", 0))
                if track.get("main"):
                    # a transition also cross-fades the sound of the two clips
                    fin = max(fin, info["trans_f"] / f)
                    k = order.index(it["id"])
                    if k + 1 < len(order):
                        fout = max(fout, lay.items[order[k + 1]]["trans_f"] / f)
                lab = _audio_chain(g, pid, m, info, fps, float(it.get("volume", 1)), fin, fout, job)
                if lab:
                    voices.append(lab)
        if voices:
            mix = "".join(f"[{v}]" for v in voices)
            g.add(f"{mix}amix=inputs={len(voices)}:normalize=0:duration=longest,alimiter=limit=0.97:level=disabled,"
                  f"apad=whole_dur={T:.5f},atrim=0:{T:.5f}[a]")
        else:
            g.add(f"anullsrc=r={SR}:cl=stereo,atrim=0:{T:.5f}[a]")

        script = work / "graph.txt"
        script.write_text(";\n".join(g.chains), encoding="utf-8")
        args = g.inputs + (["-/filter_complex", "graph.txt"] if media.ffmpeg_major() >= 7
                           else ["-filter_complex_script", "graph.txt"])
        if audio_only is not None:
            args += ["-map", "[a]", "-c:a", "pcm_s16le", "-ar", str(SR), "-t", f"{T:.3f}", "out.wav"]
            media.run(args, lambda x: note(0.1 + 0.9 * x, "מייצא אודיו…"), T, job.cancel, cwd=work)
            return {"file": work / "out.wav", "duration": T, "work": work}
        args += ["-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "fast", "-crf", "19", "-r", fps_s,
                 "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-t", f"{T + 0.02:.3f}", "out.mp4"]
        label = "מייצא וידאו…" if ratio in ("source", p["canvas"]["ratio"]) else f"מייצא {ratio}…"
        media.run(args, lambda x: note(0.1 + 0.9 * x, label), T, job.cancel, cwd=work)

        stem = re.sub(r"[^\w֐-׿ -]+", "", p["name"]).strip().replace(" ", "-")[:40] or "video"
        tag = "" if ratio == "source" else "-" + ratio.replace(":", "x")
        name = f"{stem}{tag}-{time.strftime('%m%d-%H%M%S')}.mp4"
        (pd / "exports").mkdir(exist_ok=True)
        final = pd / "exports" / name
        (work / "out.mp4").replace(final)
        return {"file": name, "created": time.time(), "duration": round(T, 3), "width": w, "height": h,
                "size": final.stat().st_size, "captions": bool(with_captions and (d["cues"] or d["cues2"])),
                "ratio": ratio, "fps": round(f, 2)}
    finally:
        if audio_only is None:
            shutil.rmtree(work, ignore_errors=True)


def export_project(job: Job, pid: str, opts: dict) -> dict:
    """Export the project in one or more frame shapes."""
    with model.lock(pid):
        p = model.load(pid)
    if not p:
        raise UserError("הפרויקט לא נמצא.")
    ratios = opts.get("ratios") or [opts.get("ratio") or p["canvas"]["ratio"]]
    ratios = [r for r in dict.fromkeys(ratios) if r in model.RATIOS] or [p["canvas"]["ratio"]]
    quality = str(opts.get("quality")) if str(opts.get("quality")) in ("720", "1080", "source") else "1080"
    with_captions = bool(opts.get("captions", p["captions"]["enabled"]))
    if opts.get("fps") in model.FPS_CHOICES:
        p["canvas"]["fps"] = opts["fps"]
    entries = []
    for n, ratio in enumerate(ratios):
        entries.append(render(job, pid, p, ratio, quality, with_captions, n / len(ratios), (n + 1) / len(ratios)))
    with model.lock(pid):
        cur = model.load(pid)
        if cur:
            cur["exports"] = entries[::-1] + cur.get("exports", [])
            cur["rev"] = cur.get("rev", 0) + 1
            model.save(cur)
    return {"exports": entries}
