"""Everything that shells out to ffmpeg: probing, preview files, waveform."""
from __future__ import annotations

import re
import subprocess
import threading
from functools import lru_cache
from pathlib import Path


class MediaError(Exception):
    pass


class Cancelled(Exception):
    pass


@lru_cache(maxsize=1)
def ffmpeg() -> str:
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


@lru_cache(maxsize=1)
def ffmpeg_major() -> int:
    out = subprocess.run([ffmpeg(), "-version"], capture_output=True, text=True, encoding="utf-8",
                         errors="replace", **_quiet()).stdout
    m = re.search(r"ffmpeg version n?(\d+)\.", out)
    return int(m.group(1)) if m else 99


def _quiet() -> dict:
    """Keep ffmpeg from flashing a console window on Windows."""
    import os
    if os.name == "nt":
        return {"creationflags": 0x08000000}
    return {}


def _time_to_s(text: str) -> float:
    h, m, s = text.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def probe(path: Path) -> dict:
    """Read duration, display size, frame rate and audio presence of a media file."""
    res = subprocess.run([ffmpeg(), "-hide_banner", "-i", str(path)], capture_output=True,
                         text=True, encoding="utf-8", errors="replace", **_quiet())
    err = res.stderr
    info = {"duration": 0.0, "width": 0, "height": 0, "fps": 30.0, "has_audio": False,
            "has_video": False, "rotation": 0}
    m = re.search(r"Duration:\s*(\d+:\d+:\d+(?:\.\d+)?)", err)
    if m:
        info["duration"] = _time_to_s(m.group(1))
    lines = err.splitlines()
    for i, line in enumerate(lines):
        if "Audio:" in line and "Stream #" in line:
            info["has_audio"] = True
        if "Video:" in line and "Stream #" in line and not info["has_video"]:
            if "attached pic" in line:
                continue
            m = re.search(r",\s*(\d{2,5})x(\d{2,5})(?=[\s,\[])", line)
            if not m:
                continue
            info["has_video"] = True
            info["width"], info["height"] = int(m.group(1)), int(m.group(2))
            f = re.search(r"([\d.]+)\s*fps", line) or re.search(r"([\d.]+)\s*tbr", line)
            if f:
                try:
                    info["fps"] = float(f.group(1))
                except ValueError:
                    pass
            for extra in lines[i + 1:i + 14]:
                if "Stream #" in extra:
                    break
                r = re.search(r"rotation of (-?[\d.]+) degrees", extra) or \
                    re.search(r"rotate\s*:\s*(-?[\d.]+)", extra)
                if r:
                    info["rotation"] = int(round(float(r.group(1)))) % 360
    if info["rotation"] in (90, 270):
        info["width"], info["height"] = info["height"], info["width"]
    return info


def run(args: list[str], on_progress=None, total: float | None = None, cancel=None, cwd: Path | None = None) -> None:
    """Run ffmpeg. Reports progress as 0..1 of `total` seconds and honours `cancel`."""
    cmd = [ffmpeg(), "-hide_banner", "-nostdin", "-y", "-loglevel", "error", "-progress", "pipe:1",
           "-nostats"] + args
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                            encoding="utf-8", errors="replace", cwd=str(cwd) if cwd else None, **_quiet())
    err_lines: list[str] = []

    def drain() -> None:
        for line in proc.stderr:
            err_lines.append(line.rstrip())
            del err_lines[:-40]

    t = threading.Thread(target=drain, daemon=True)
    t.start()
    try:
        for line in proc.stdout:
            if cancel is not None and cancel.is_set():
                proc.kill()
                raise Cancelled()
            if on_progress and total and line.startswith("out_time_us="):
                try:
                    on_progress(min(1.0, max(0.0, int(line.split("=")[1]) / 1e6 / total)))
                except ValueError:
                    pass
        code = proc.wait()
    finally:
        if proc.poll() is None:
            proc.kill()
        t.join(timeout=2)
    if cancel is not None and cancel.is_set():
        raise Cancelled()
    if code != 0:
        raise MediaError("\n".join(err_lines[-12:]) or f"ffmpeg exited with code {code}")


def make_thumb(src: Path, dst: Path, duration: float) -> None:
    at = min(1.0, max(0.0, duration / 2))
    try:
        run(["-ss", f"{at:.2f}", "-i", str(src), "-frames:v", "1", "-vf", "scale=-2:480",
             "-q:v", "5", str(dst)])
    except MediaError:
        pass


def make_proxy(src: Path, dst: Path, info: dict, on_progress=None, cancel=None) -> None:
    """A small, seek-friendly H.264 copy that every browser can play."""
    scale = "scale='if(gt(iw,ih),min(1280,iw),-2)':'if(gt(iw,ih),-2,min(1280,ih))'"
    args = ["-i", str(src), "-map", "0:v:0"]
    if info.get("has_audio"):
        args += ["-map", "0:a:0"]
    args += ["-vf", scale + ",setsar=1", "-c:v", "libx264", "-preset", "veryfast", "-crf", "25",
             "-g", "15", "-pix_fmt", "yuv420p"]
    if info.get("has_audio"):
        args += ["-c:a", "aac", "-b:a", "128k", "-ac", "2"]
    args += ["-movflags", "+faststart", str(dst)]
    run(args, on_progress, info.get("duration"), cancel)


def make_peaks(src: Path, duration: float) -> list[int]:
    """Waveform for the timeline: loudness 0..100 in evenly spaced buckets."""
    import numpy as np
    proc = subprocess.run([ffmpeg(), "-hide_banner", "-nostdin", "-loglevel", "error", "-i", str(src),
                           "-vn", "-map", "0:a:0", "-ac", "1", "-ar", "8000", "-f", "s16le", "pipe:1"],
                          capture_output=True, **_quiet())
    data = np.frombuffer(proc.stdout, dtype="<i2")
    if data.size < 800:
        return []
    buckets = int(min(4000, max(200, duration * 40)))
    step = max(1, data.size // buckets)
    usable = data[: (data.size // step) * step].reshape(-1, step)
    peaks = np.abs(usable.astype(np.int32)).max(axis=1).astype(np.float64)
    ref = max(float(np.percentile(peaks, 99.5)), 1.0)
    return [int(v) for v in np.clip(peaks / ref * 100, 0, 100).round()]


def extract_pcm(src: Path, dst: Path, cancel=None) -> None:
    """Full-quality audio as raw 48 kHz stereo, aligned to start at time zero."""
    run(["-i", str(src), "-vn", "-map", "0:a:0", "-af", "aresample=48000:async=1:first_pts=0",
         "-ac", "2", "-f", "s16le", str(dst)], cancel=cancel)


def audio_16k(src: Path):
    """The whole soundtrack as mono 16 kHz float samples, the format Whisper expects."""
    import numpy as np
    proc = subprocess.run([ffmpeg(), "-hide_banner", "-nostdin", "-loglevel", "error", "-i", str(src),
                           "-vn", "-map", "0:a:0", "-ac", "1", "-ar", "16000", "-f", "s16le", "pipe:1"],
                          capture_output=True, **_quiet())
    if proc.returncode != 0 or len(proc.stdout) < 3200:
        raise MediaError(proc.stderr.decode("utf-8", "replace")[-400:] or "could not read the audio track")
    return np.frombuffer(proc.stdout, dtype="<i2").astype(np.float32) / 32768.0


def make_strip(src: Path, dst: Path, duration: float) -> dict | None:
    """A row of small frames across the video, shown inside its clips on the timeline."""
    n = int(min(40, max(1, round(duration / 2.5))))
    try:
        run(["-i", str(src), "-vf", f"fps={n / max(duration, 0.1):.5f},scale=-2:64,tile={n}x1", "-frames:v", "1",
             "-q:v", "6", str(dst)])
    except MediaError:
        return None
    return {"n": n} if dst.exists() else None


def make_audio_proxy(src: Path, dst: Path) -> None:
    run(["-i", str(src), "-vn", "-map", "0:a:0", "-c:a", "aac", "-b:a", "128k", "-ac", "2", str(dst)])


def cut_wav(src: Path, dst: Path, start: float, end: float) -> None:
    """A mono WAV of one stretch of a file's sound."""
    run(["-ss", f"{max(0.0, start):.3f}", "-t", f"{max(0.1, end - start):.3f}", "-i", str(src), "-vn", "-map", "0:a:0",
         "-ac", "1", "-ar", "44100", "-c:a", "pcm_s16le", str(dst)])
