#!/usr/bin/env python3
"""gallery.py: find a reference in the Prompt Motion gallery, then read its prompt from the source.

The index (../data/gallery-index.json) holds metadata only: title, creator, tags, stack, links and a few
flags worked out from each prompt. The prompts themselves belong to their creators, so they are not
copied here; `fetch` reads one live from prompt-motion.com when you want to study or adapt it.

  python3 gallery.py search --tag "kinetic type" --top 8
  python3 gallery.py search --family product-film --has banned,check
  python3 gallery.py search --stack remotion
  python3 gallery.py search --q recipe
  python3 gallery.py search --kind skill
  python3 gallery.py show twoclipping-5cba86
  python3 gallery.py fetch twoclipping-5cba86              the creator's prompt, with credit
  python3 gallery.py fetch twoclipping-5cba86 --improved   Prompt Motion's rewrite of it, where one exists
  python3 gallery.py fetch templates/showreel              the site's own templates (also templates/realtime)
  python3 gallery.py stats

families: showreel, product-film, explainer, narrated-explainer, character-short, realtime-3d,
          creator-structured (the creator wrote a full blocked prompt), other
--has:    banned (a banned list), beat (a beat grid), check (asks Claude to check its own frames), inputs
Results are ordered by the gallery's own popularity ranking.
"""
import argparse, html, json, os, re, sys, urllib.request
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(HERE, "..", "data", "gallery-index.json")
SITE = "https://prompt-motion.com"
FLAGS = {"banned": "has_banned_list", "beat": "has_beat_grid", "check": "has_self_check", "inputs": "has_inputs_block"}


def load():
    with open(INDEX, encoding="utf-8") as f:
        return json.load(f)


def line(e):
    marks = " ".join(k for k, f in FLAGS.items() if e.get(f))
    return (f"#{e['rank']:<3} {e['slug']:<28} {e['title'][:44]:<44} {e['creator'][:18]:<18} "
            f"{e['family'][:18]:<18} {e['words']:>5}w  {e['stack'][:18]:<18} {marks}")


def cmd_search(a):
    rows = load()
    if a.tag:
        rows = [e for e in rows if any(a.tag.lower() == t.lower() for t in e["tags"])]
    if a.family:
        rows = [e for e in rows if e["family"] == a.family]
    if a.kind:
        rows = [e for e in rows if a.kind in e["kind"]]
    if a.stack:
        rows = [e for e in rows if a.stack.lower() in e["stack"].lower()]
    if a.creator:
        rows = [e for e in rows if a.creator.lower().lstrip("@") in e["creator"].lower()]
    if a.q:
        rows = [e for e in rows if a.q.lower() in (e["title"] + " " + " ".join(e["tags"])).lower()]
    if a.min_words:
        rows = [e for e in rows if e["words"] >= a.min_words]
    for h in [x for x in (a.has or "").split(",") if x]:
        if h not in FLAGS:
            sys.exit(f"--has takes: {', '.join(FLAGS)}")
        rows = [e for e in rows if e[FLAGS[h]]]
    print(f"{len(rows)} entries" + (f", showing {a.top}" if len(rows) > a.top else ""))
    for e in rows[: a.top]:
        print(line(e))


def cmd_show(a):
    for e in load():
        if e["slug"] == a.slug:
            print(json.dumps(e, indent=2, ensure_ascii=False))
            return
    sys.exit(f"no entry with slug {a.slug}; try: gallery.py search --q <word>")


def cmd_stats(_):
    rows = load()
    print(f"{len(rows)} entries")
    for k in ("kind", "family", "stack", "improved"):
        print(f"\n{k}:")
        for v, n in Counter(e[k] or "(not stated)" for e in rows).most_common(12):
            print(f"  {n:>4}  {v}")
    print("\ntags:")
    for v, n in Counter(t for e in rows for t in e["tags"]).most_common():
        print(f"  {n:>4}  {v}")


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (motion-director skill; single page lookup on a person's request)"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return r.read().decode("utf-8", "replace")
    except Exception as e:  # blocked host, offline, 404
        sys.exit(f"could not read {url}: {e}\nIf this is a cloud session, prompt-motion.com may need adding to the environment's allowed hosts.\n"
                 f"Open the page in a browser instead: {url}")


def blocks(page):
    body = re.sub(r"<script\b.*?</script>", " ", page, flags=re.S)
    out = []
    for b in re.findall(r"<div[^>]*whitespace-pre-wrap[^>]*>(.*?)</div>", body, flags=re.S):
        out.append(html.unescape(re.sub(r"<[^>]+>", "", re.sub(r"<br\b[^>]*>", "\n", b))).strip())
    return out


def cmd_fetch(a):
    slug = a.slug.strip("/")
    if slug.startswith("templates/"):
        url = f"{SITE}/{slug}"
        got = blocks(get(url))
        if not got:
            sys.exit(f"no prompt found at {url}")
        print(f"# Prompt Motion template, written by Prompt Motion\n# source: {url}\n\n{got[0]}")
        return
    entry = next((e for e in load() if e["slug"] == slug), None)
    credit = f"{entry['title']}, by {entry['creator']}" if entry else slug
    if a.improved:
        url = f"{SITE}/customize/{slug}"
        got = blocks(get(url))
        if len(got) < 2:
            sys.exit(f"no improved version at {url}")
        print(f"# Prompt Motion's rewrite of: {credit}\n# source: {url}\n\n{got[-1]}")
    else:
        url = f"{SITE}/{slug}"
        got = blocks(get(url))
        if not got:
            hint = f"\ninstall: {'; '.join(entry['install'])}\nrepo: {' '.join(entry['repo'])}" if entry and entry["install"] else ""
            sys.exit(f"no prompt on {url} (a skill entry has an install command, not a prompt){hint}")
        post = f"\n# original post: {entry['post']}" if entry and entry["post"] else ""
        print(f"# {credit}\n# source: {url}{post}\n# The prompt belongs to its creator. Credit them if you share what you make from it.\n\n{got[0]}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search"); s.set_defaults(fn=cmd_search)
    s.add_argument("--tag"); s.add_argument("--family"); s.add_argument("--kind"); s.add_argument("--stack")
    s.add_argument("--creator"); s.add_argument("--q"); s.add_argument("--has"); s.add_argument("--min-words", type=int, default=0)
    s.add_argument("--top", type=int, default=15)
    s = sub.add_parser("show"); s.add_argument("slug"); s.set_defaults(fn=cmd_show)
    s = sub.add_parser("fetch"); s.add_argument("slug"); s.add_argument("--improved", action="store_true"); s.set_defaults(fn=cmd_fetch)
    s = sub.add_parser("stats"); s.set_defaults(fn=cmd_stats)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
