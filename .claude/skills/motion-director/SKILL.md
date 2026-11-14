---
name: motion-director
description: Direct motion graphics made with code. Use when someone wants a motion graphics video, animation, launch or product film, explainer, showreel, kinetic typography, animated chart, UI motion loop or 3D piece built in HTML, canvas, three.js, Remotion or HyperFrames; wants a prompt for one written, upgraded or customised for their product; wants a rendered piece critiqued, checked or fixed; or mentions Prompt Motion or prompt-motion.com. Supplies the prompt architecture, recipes per kind of video, the list of effects that make a video look AI-made and what to do instead, a deterministic seek(t) render pipeline with scripts (frame capture with motion blur, contact sheets, pop scanning), the plan-check-fix loop, and a searchable index of 240 reference videos with their prompts.
metadata:
  source: Distilled from the public Prompt Motion gallery and guides (https://prompt-motion.com), curated by @p4nthera_. Prompts belong to their creators and are referenced, not copied.
---

# Motion director

A video made by Claude is code that draws frames. Whether it looks designed or looks AI-made is decided before any code is written, by the decisions the prompt makes and by whether anyone looks at frames before the final render. This skill holds those decisions and the tools to check them.

Reply in the language the person writes in. Write prompts for the build in English unless they ask otherwise. For Hebrew or other right-to-left text on screen, read the RTL section of `references/gotchas.md` first.

## What the person is asking for

| They want | Do this |
|---|---|
| A prompt written or improved | Build it from the six blocks in `references/prompt-anatomy.md`, using the recipe for that kind of video in `references/archetypes.md`. Give them the prompt, ready to paste. |
| The video itself, here | Run the loop below. Default stack is one HTML file drawn by `seek(t)`, rendered with `scripts/render.mjs`. |
| A reference ("show me how others did X") | `python3 scripts/gallery.py search ...`, then `fetch <slug>` to read that prompt from the source. |
| A fix to a piece that exists | `references/review-loop.md`: measure first (`scripts/popscan.py`, `scripts/stills.mjs --strip`), then change one thing. |
| A specialist job | Hand over to the sibling skill, see "When another skill fits better". |

## The five decisions

Short prompts leave these open and Claude fills them with defaults, which is why one viral 26-word prompt produced results from ignored to celebrated. Make each one on purpose:

1. **One concept.** A single idea every shot grows out of: one shape that never cuts, one object that travels through every scene, one diagram the camera explores. Without it you get a tour of effects.
2. **A banned list.** Name what Claude reaches for by default and say what to do instead. See `references/look-and-banned.md`.
3. **A beat grid.** A tempo and a bar count, and "something changes on every beat", instead of the word "dynamic".
4. **A build method.** How frames get made, not only what they show. Name the renderer, or Claude picks a different one each run.
5. **A review step.** Stills before the render, strips around transitions, a scan after it.

## The loop

1. **Plan, then wait.** Three different ideas with one still each when the concept is open. Then the asset list (every screen, logo and image, and where each comes from; a missing asset is a question, never something to invent) and a beat table: time, what is on screen, what moves, why the beat exists. A beat with no reason is cut. Save the plan to a file.
2. **Build** from the recipe. Start from `scripts/seek-starter.html`: it carries the springs, camera, seeded random and soundtrack helpers and a scene that follows the rules.
3. **Check stills.** `node scripts/stills.mjs film.html --out sheet.png` gives one still per beat on one sheet. Read the sheet and fix what it shows before rendering: one focal element per frame at half the frame width or more, text at 32 px or more at 1080p, nothing in the corners, a new layout on every still, no two texts overlapping.
4. **Check motion.** `--strip <time>` shows every frame around a transition. Then `node scripts/render.mjs film.html --preview` for a fast half-size render to watch at full speed.
5. **Render** with motion blur, then `python3 scripts/popscan.py film.mp4`. It reports single-frame pops, jumps, holds and empty frames with timestamps.
6. **Fix one thing at a time**, naming the second it happens, protecting what works, and proving the fix with frames. Start a fresh session for each round of fixes on a long job; the plan file is what lets it pick up.

Say plainly what cannot be judged from frames: sound, and whether motion feels right. Ask the person to watch at full speed with the sound on.

## Rules that hold on every stack

- Every frame is a pure function of time. No CSS transitions or animations, no timers, no state carried between frames, no unseeded random numbers.
- Nothing appears from nothing: it grows, slides from an edge, or is revealed by a mask. Exits finish before entries start.
- Scenes join through a shared element that changes role, not through cuts, crossfades or blur-ins.
- Springs settle; they do not bounce. Durations and delays vary between elements, never equal staggers.
- One typeface, one accent colour, a lot of empty space. The focal element is large; crop at the edge rather than shrink to fit.
- Use the real product: its real screens rebuilt as layers, its colours and type. Never invent features, numbers or quotes. For explainers, check every fact against a source.
- Measure positions at runtime after fonts load. Do not hard-code text widths.

## Scripts

All in `scripts/`, tested with Node 22, Playwright Chromium, ffmpeg 6 and numpy.

| Script | Use |
|---|---|
| `seek-starter.html` | Starting point: `window.FILM`, `window.seek(t)`, optional `window.renderAudio()`. Opens in a browser for live preview. |
| `render.mjs` | Frame-by-frame capture to MP4. `--subframes 3` blends subframes for motion blur, `--preview` for a quick look, `--loudnorm` for -14 LUFS, `--audio track.wav` for a real track. |
| `stills.mjs` | Contact sheet per beat, per time, or a frame-by-frame strip around one moment. |
| `popscan.py` | Scans a rendered MP4 for pops, jumps, holds and empty frames. `--allow 3.2-4.1` marks ranges where fast cuts are intended. |
| `gallery.py` | Searches the reference index and reads a prompt live from prompt-motion.com. |

## When another skill fits better

These are installed beside this one. Use this skill to shape the brief and review the result; let the specialist build.

| Job | Skill |
|---|---|
| A product film built in Remotion from a real React codebase and design system | `product-film` |
| A premium launch, update or feature film with a full production toolchain (Remotion or HyperFrames) | `cinetic` |
| An original film on any topic with frames drawn in Python and a synthesised score | `generative-film` |
| A film of a working session with the person, from local history (HyperFrames) | `session-story` |
| A live HTML product demo window for a web page, not a video file | `html-demo` |
| A website, landing page or dashboard, not motion | `design-taste-frontend` |

## References

- `references/prompt-anatomy.md`: the six blocks, the dials, a skeleton to fill, how to upgrade a one-line prompt.
- `references/archetypes.md`: recipes for showreel, product film, UI morph loop, explainer, narrated explainer, character short, 3D, page fly-over, kinetic type, data story, each with gallery references.
- `references/look-and-banned.md`: the tells, why each reads as AI-made, the replacement, default banned lists.
- `references/build-pipelines.md`: choosing a renderer, the seek(t) contract, springs, camera, motion blur, soundtrack, voice, footage.
- `references/review-loop.md`: how to ask for a fix, symptom to prompt line, cost and session hygiene, what Claude cannot judge.
- `references/gotchas.md`: traps by area, including right-to-left text.
- `references/sources.md`: where this comes from, the gallery in numbers, the six installed skills and their licences.
