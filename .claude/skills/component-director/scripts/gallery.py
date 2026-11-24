#!/usr/bin/env python3
"""gallery.py: find a reference among Scrolltide's component previews, and find what nobody has built yet.

The index (../data/gallery-index.json) holds metadata only: name, category, the site's own public tags,
the date added, a link to the public preview clip, and four labels worked out here from watching every
clip: job, material, family and gestures. It holds no prompts and no source code. Those are Scrolltide's
paid product (https://www.scrolltide.co/components) and are not copied, summarised or reconstructed.

  python3 gallery.py search --family ring --top 8          cards on a circle, arc, wheel or helix
  python3 gallery.py search --job toggle                   every on/off control
  python3 gallery.py search --material paper --gesture drag
  python3 gallery.py search --tech css-3d                  what was done without a canvas
  python3 gallery.py search --category Input --q liquid
  python3 gallery.py show tear-ticket                      one entry, with its clip link
  python3 gallery.py clip tear-ticket [--out dir]          download the public clip and cut a 6-frame strip (needs ffmpeg)
  python3 gallery.py gaps [--jobs toggle,button,slider]    job x material pairs the gallery has not touched
  python3 gallery.py stats

job       what the piece does on a page: toggle, button, slider, picker, upload, password, consent, filter, tabs,
          nav, footer, tree, loader, timer, intro, pricing, chart, dashboard, product, chat, testimonial, steps,
          accordion, list, carousel, deck, gallery, slideshow, card, ticket, text, background, trail, frame, object
material  what it pretends to be made of: liquid, glass, paper, fire, light, ink, grain, rope, pixel, creature,
          machine, plant, sky, photo, none
family    the mechanism (references/mechanisms.md): world, story, ring, rail, stack, expand, morph, fold, fluid,
          lens, field, sdf, physics, glyph, mask, scroll, object, light, camera
gesture   drag, fling, hover, move, click, hold, scroll, type, keys, auto
tech      as tagged by the site: css, css-3d, svg, canvas-2d, webgl, three, waapi, audio
"""
import argparse, json, os, shutil, subprocess, sys, urllib.request
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(HERE, "..", "data", "gallery-index.json")
SITE = "https://www.scrolltide.co/components"
MATERIALS = ["liquid", "glass", "paper", "fire", "light", "ink", "grain", "rope", "pixel", "creature", "machine", "plant", "sky"]
CONTROLS = ["toggle", "button", "slider", "picker", "upload", "password", "consent", "filter", "tabs", "nav", "loader", "timer", "pricing", "chart", "chat", "text"]


def load():
    with open(INDEX, encoding="utf-8") as f:
        return json.load(f)


def line(e):
    return (f"#{e['n']:<3} {e['slug']:<22} {e['category']:<10} {e['job']:<11} {e['material']:<9} "
            f"{'+'.join(e['family']):<15} {','.join(e['tech']) or '-':<16} {','.join(e['gestures'])}")


def find(rows, slug):
    hit = [e for e in rows if e["slug"] == slug] or [e for e in rows if slug.lower() in e["slug"] or slug.lower() in e["name"].lower()]
    if not hit:
        sys.exit(f"no entry matches '{slug}'. Try: python3 gallery.py search --q {slug}")
    return hit[0]


def cmd_search(a):
    rows = load()
    if a.category: rows = [e for e in rows if e["category"].lower() == a.category.lower()]
    if a.job: rows = [e for e in rows if e["job"] == a.job]
    if a.material: rows = [e for e in rows if e["material"] == a.material]
    if a.family: rows = [e for e in rows if a.family in e["family"]]
    if a.tech: rows = [e for e in rows if a.tech in e["tech"]]
    if a.gesture: rows = [e for e in rows if a.gesture in e["gestures"]]
    if a.q:
        q = a.q.lower()
        rows = [e for e in rows if q in (e["name"] + " " + e["slug"] + " " + " ".join(e["site_tags"])).lower()]
    if a.newest: rows = sorted(rows, key=lambda e: e["added"], reverse=True)
    print(f"{len(rows)} of {len(load())}   (# is the position on the site when the index was built)")
    for e in rows[: a.top]:
        print(line(e))
    if len(rows) > a.top:
        print(f"... {len(rows) - a.top} more, raise --top")


def cmd_show(a):
    e = find(load(), a.slug)
    print(f"{e['name']}  ({e['slug']})  ·  {e['category']}  ·  added {e['added']}  ·  #{e['n']} on the site")
    print(f"job {e['job']}  ·  material {e['material']}  ·  family {' + '.join(e['family'])}  ·  gestures {', '.join(e['gestures']) or '-'}")
    print(f"tech (site tags): {', '.join(e['tech']) or 'not stated'}")
    print(f"site tags: {', '.join(e['site_tags'])}")
    print(f"preview clip ({e['seconds']} s): {e['clip']}")
    print(f"poster: {e['poster']}")
    print(f"The description, and the prompt for subscribers, are on {SITE} (open it in a browser).")
    print("Study the clip for the idea and the motion. Build your own piece; do not rebuild this one under another name.")


def cmd_clip(a):
    e = find(load(), a.slug)
    out = os.path.abspath(a.out or f"clip-{e['slug']}")
    os.makedirs(out, exist_ok=True)
    mp4 = os.path.join(out, e["slug"] + ".mp4")
    try:
        req = urllib.request.Request(e["clip"], headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as r, open(mp4, "wb") as f:
            shutil.copyfileobj(r, f)
    except Exception as ex:
        sys.exit(f"could not download the clip ({ex}). Open it in a browser instead: {e['clip']}")
    print(mp4)
    if not shutil.which("ffmpeg"):
        print("ffmpeg not found: clip saved, no strip made")
        return
    d = float(e["seconds"] or 10)
    strip = os.path.join(out, e["slug"] + "-strip.png")
    ins, parts = [], []
    for k in range(6):
        ins += ["-ss", f"{d * (0.08 + 0.168 * k):.2f}", "-i", mp4]
        parts.append(f"[{k}:v]scale=480:-2[v{k}]")
    fc = ";".join(parts) + ";" + "".join(f"[v{k}]" for k in range(6)) + "xstack=inputs=6:layout=0_0|w0_0|w0+w1_0|0_h0|w0_h0|w0+w1_h0[o]"
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", fc, "-map", "[o]", "-frames:v", "1", strip], capture_output=True, text=True)
    print(strip if r.returncode == 0 else f"ffmpeg failed: {r.stderr.strip()[:300]}")


def cmd_gaps(a):
    rows = load()
    jobs = a.jobs.split(",") if a.jobs else CONTROLS
    have = Counter((e["job"], e["material"]) for e in rows)
    print("Job x material. A number is how many gallery pieces already sit there; a dot is open ground.\n")
    print(" " * 10 + "".join(f"{m[:7]:>8}" for m in MATERIALS))
    for j in jobs:
        print(f"{j:<10}" + "".join(f"{(str(have[(j, m)]) if have[(j, m)] else '·'):>8}" for m in MATERIALS))
    empty = [(j, m) for j in jobs for m in MATERIALS if not have[(j, m)]]
    print(f"\n{len(empty)} of {len(jobs) * len(MATERIALS)} pairs are untouched. A pair is only a start: it still needs")
    print("a gesture that belongs to the material and a consequence beyond the control (references/conceit.md).")


def cmd_stats(_):
    rows = load()
    print(f"{len(rows)} entries, added {min(e['added'] for e in rows)} to {max(e['added'] for e in rows)}")
    for key in ("category", "job", "material"):
        print(f"{key}: " + ", ".join(f"{k} {v}" for k, v in Counter(e[key] for e in rows).most_common()))
    for key in ("family", "tech", "gestures"):
        print(f"{key}: " + ", ".join(f"{k} {v}" for k, v in Counter(x for e in rows for x in e[key]).most_common()))
    print(f"no tech stated: {sum(1 for e in rows if not e['tech'])}")
    print("by month: " + ", ".join(f"{k} {v}" for k, v in sorted(Counter(e['added'][:7] for e in rows).items())))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search")
    for flag in ("category", "job", "material", "family", "tech", "gesture", "q"):
        s.add_argument("--" + flag)
    s.add_argument("--top", type=int, default=20)
    s.add_argument("--newest", action="store_true")
    s.set_defaults(fn=cmd_search)
    s = sub.add_parser("show"); s.add_argument("slug"); s.set_defaults(fn=cmd_show)
    s = sub.add_parser("clip"); s.add_argument("slug"); s.add_argument("--out"); s.set_defaults(fn=cmd_clip)
    s = sub.add_parser("gaps"); s.add_argument("--jobs"); s.set_defaults(fn=cmd_gaps)
    s = sub.add_parser("stats"); s.set_defaults(fn=cmd_stats)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
