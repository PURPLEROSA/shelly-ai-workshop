#!/usr/bin/env python3
"""popscan.py: measure a rendered film instead of trusting that it is fixed.

Decodes the video small and grey, then reports:
  pops    single frames that jump away and come straight back (the classic one-frame glitch)
  jumps   frame-to-frame changes far above their neighbours (hard cuts, snaps, a zoom that resets)
  holds   stretches where nothing moves for longer than --hold seconds (dead time)
  flat    stretches where the frame is almost one flat colour (an empty frame)

  python3 popscan.py film.mp4 [--spike 3.0] [--hold 0.5] [--flat 2.5] [--allow 3.2-4.1,9.0-9.5]

--allow names time ranges where fast jumps are intended (a run of cuts on 16th notes, say).
Needs ffmpeg and numpy. Exit code is 0 either way; read the report.
"""
import argparse, json, subprocess, sys

import numpy as np

W, H = 160, 90


def probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate,nb_frames",
         "-of", "json", path], capture_output=True, text=True, check=True).stdout
    s = json.loads(out)["streams"][0]
    num, den = s["r_frame_rate"].split("/")
    return float(num) / float(den)


def frames(path):
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-vf", f"scale={W}:{H}:flags=area,format=gray", "-f", "rawvideo", "-"],
        capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.uint8).reshape(-1, H, W).astype(np.float32)


def runs(mask):
    """(start, end) index pairs of consecutive True values, end exclusive."""
    out, start = [], None
    for i, m in enumerate(mask):
        if m and start is None:
            start = i
        if not m and start is not None:
            out.append((start, i)); start = None
    if start is not None:
        out.append((start, len(mask)))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--spike", type=float, default=3.0, help="a change this many times its neighbours counts as a jump")
    ap.add_argument("--hold", type=float, default=0.5, help="seconds of stillness that count as dead time")
    ap.add_argument("--flat", type=float, default=2.5, help="luminance spread below this counts as an empty frame")
    ap.add_argument("--allow", default="", help="time ranges where jumps are intended, e.g. 3.2-4.1,9-9.5")
    a = ap.parse_args()

    fps = probe(a.video)
    f = frames(a.video)
    n = len(f)
    if n < 4:
        sys.exit("too few frames to analyse")
    allowed = [tuple(map(float, r.split("-"))) for r in a.allow.split(",") if r]
    ok = lambda t: any(lo <= t <= hi for lo, hi in allowed)
    ts = lambda i: f"{i / fps:6.2f}s (frame {i})"

    d = np.abs(f[1:] - f[:-1]).mean(axis=(1, 2))            # d[i] = change from frame i to i+1
    floor = max(0.35, float(np.median(d)) * 0.5)

    pops, jumps = [], []
    for i in range(1, n - 1):
        # frame i differs from both neighbours, while the neighbours agree with each other
        around = float(np.abs(f[i + 1] - f[i - 1]).mean())
        if d[i - 1] > floor * 2 and d[i] > floor * 2 and around < 0.4 * min(d[i - 1], d[i]) and not ok(i / fps):
            pops.append(i)
    for i in range(len(d)):
        lo, hi = max(0, i - 4), min(len(d), i + 5)
        neigh = np.concatenate([d[lo:i], d[i + 1:hi]])
        if len(neigh) and d[i] > max(floor * 4, a.spike * float(np.median(neigh)) + 1.0) and (i + 1) not in pops and i not in pops:
            if not ok((i + 1) / fps):
                jumps.append(i + 1)

    still = d < 0.12
    holds = [(s, e) for s, e in runs(still) if (e - s) / fps >= a.hold]
    spread = f.reshape(n, -1).std(axis=1)
    flats = [(s, e) for s, e in runs(spread < a.flat) if (e - s) / fps >= 0.15]   # shorter than this reads as motion, not emptiness

    print(f"{a.video}: {n} frames at {fps:.2f} fps, {n / fps:.2f}s")
    print(f"  typical change per frame {float(np.median(d)):.2f}, largest {float(d.max()):.2f} at {ts(int(d.argmax()) + 1)}")
    print(f"\nsingle-frame pops: {len(pops)}")
    for i in pops[:40]:
        print(f"  {ts(i)}")
    print(f"\njumps (change over {a.spike}x its neighbours): {len(jumps)}")
    for i in jumps[:40]:
        print(f"  {ts(i)}  change {d[i - 1]:.1f}")
    print(f"\nholds of {a.hold}s or more: {len(holds)}")
    for s, e in holds[:40]:
        print(f"  {s / fps:6.2f}s to {(e + 1) / fps:6.2f}s  ({(e - s + 1) / fps:.2f}s still)")
    print(f"\nnear-empty stretches of 0.15s or more: {len(flats)}")
    for s, e in flats[:40]:
        print(f"  {s / fps:6.2f}s to {e / fps:6.2f}s")
    if not (pops or jumps or holds or flats):
        print("\nnothing flagged. This checks the picture only: still watch it at full speed, with the sound on.")
    else:
        print("\nA jump or a hold can be intended (a cut on the beat, a title held to be read). Pull a strip around each one"
              " with stills.mjs --strip <time> and decide. A pop is never intended.")


if __name__ == "__main__":
    main()
