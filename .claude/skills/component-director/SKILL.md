---
name: component-director
description: Direct single interactive UI pieces made with code, and explainer pages built from them. Use when someone wants one animated or interactive component built (a button, toggle, slider, input, loader, card, carousel, nav, text effect, background or 3D object) in HTML, React, canvas, WebGL or three.js; wants an interactive explainer site, guide or teaching page where each idea is something the reader can move; wants a prompt for a component written, upgraded or customised for their product; wants a component critiqued, checked or fixed; wants something "like the Scrolltide components"; or mentions Scrolltide or scrolltide.co. Supplies a method for finding the idea, the prompt architecture for a one-piece prompt, mechanism recipes by family, the habits that make a component look AI-made and what to do instead, a starter with a small dependency-free kit, a browser probe that drives a piece through hover, press, drag, keys, touch, reduced motion and right-to-left and photographs every state on one sheet, a composer that sets pieces into one page, six worked examples with a full explainer page built from them, and a searchable index of 132 reference previews.
metadata:
  source: Distilled from the public Scrolltide component gallery (https://www.scrolltide.co/components) by watching its 132 preview clips. Scrolltide's prompts and source code are its paid product; they are not copied, summarised or reconstructed here.
---

# Component director

A piece is one element that does one job and carries one idea: a switch, a loader, a card that opens. Whether it reads as designed or as generated is settled by the idea, and by whether anyone drove it through every state before calling it finished. This skill holds the way to find the idea and the tools to do the driving.

Reply in the language the person writes in. Write build prompts in English unless they ask otherwise. For Hebrew or any right-to-left page, read the RTL section of `references/contract.md` before laying anything out.

## What the person is asking for

| They want | Do this |
|---|---|
| A prompt written or improved | Find the sentence with `references/conceit.md`, then fill the eight blocks in `references/prompt-anatomy.md`. Give them the prompt, ready to paste. |
| The piece itself, here | Run the loop below. Default is one self-contained HTML file from `scripts/piece-starter.html`; for a React codebase, the same structure as one component (see `references/contract.md`). |
| A reference ("how did others do a paper tear?") | `python3 scripts/gallery.py search ...`, then `clip <slug>` to study the public preview. |
| An idea nobody has done | `python3 scripts/gallery.py gaps`, then the candidates step in `references/conceit.md`. |
| A fix to a piece that exists | `node scripts/probe.mjs <file or url>` first. Read the sheet, then `references/review-loop.md`. Change one thing. |
| An explainer site: a page that teaches something by letting the reader move it | `references/explainer.md`. Decide the question, the through-line and the stations; build each station as a piece; set them into a shell with `scripts/compose.mjs`. |
| A video, or a product demo window | Another skill, see the end of this file. |

## The five decisions

A short prompt leaves these open and they get filled with defaults: a rounded card, a 300 ms ease, a hover that scales by five percent. Make each one on purpose.

1. **One sentence.** *A [job] that is a [thing]: [gesture] and [what happens], while [what else changes].* The job is ordinary; the thing is physical. If the sentence will not write, there is no idea yet.
2. **One number.** The piece has a value `p` from 0 to 1 and everything drawn is a function of it. Then it can be dragged, stopped half way, reversed, photographed and reduced to a still. Two states joined by a transition cannot.
3. **A gesture that belongs to the thing.** A match is struck, paper is peeled, a crown is wound, a dial is flung and coasts. The thing decides the gesture and the physics. A click is the fallback every piece keeps, never the idea.
4. **The cheapest renderer that can do it.** CSS, then CSS with registered properties, then DOM with springs, then SVG, then canvas 2D, then a fragment shader, then three.js. Stop at the first that works. `references/contract.md` has the ladder.
5. **A probe run.** Stills of every state on one sheet, read before anyone says "done".

## The loop

1. **Find the sentence.** When the idea is open, write three different sentences from the product's own nouns and pick with the person. `references/conceit.md` has the tests that kill weak ones early.
2. **Name the number and the states.** What `p` means, what 0, 0.5 and 1 look like, which states are discrete on top of it (picked, focused, disabled, empty, error). Write them at the top of the file.
3. **Build from the starter.** `scripts/piece-starter.html` already has the spring, the sleeping loop, the unified drag, reduced motion and the `PIECE` handle. Take the mechanism from `references/mechanisms.md`. Use the person's real content: their labels, their numbers, their language.
4. **Probe.** `node scripts/probe.mjs piece.html` (add `--variant he=?lang=he` or `--rtl` when the page is right to left). It exits 1 on a failure.
5. **Read the sheet.** Open `sheet.png`. The warnings find contract breaks; your eyes find the rest: a resting state caught mid-fade, a lone full stop on its own line, a detail peeking from under a neighbour, a piece too small for its stage.
6. **Fix one thing, probe again.** Name the still that shows the fault, protect what works, and prove the fix with the next sheet.

Say plainly what stills cannot judge: how the motion feels, how it sounds, how it behaves on a real phone and with a real screen reader. Ask the person to try it.

## Rules that hold on every stack

- The settled picture depends on the value alone. Springs carry it between values; the clock and unseeded random numbers stay out of it.
- The loop sleeps at rest, off screen and in a hidden tab. Motion that runs with nobody attending is earned by hover, focus or a recent touch, and then comes to rest.
- Mouse, touch and pen go through pointer events, and every action has a keyboard path through a real `button`, `input` or ARIA role.
- Under `prefers-reduced-motion` the piece jumps to the settled state. That is the same code path as `scrub`.
- Lay text out once, at its final size. Reveal it by clipping or fading, never by letting it re-wrap. Widen a picture by re-cropping, never by stretching.
- Springs settle. A damping ratio of 0.7 to 1 is the default; one thing with mass may overshoot once.
- One material, one accent, real content. No lorem ipsum, no "Card Title", no invented numbers.
- One file or one component, nothing fetched from other hosts unless the person asked for it.
- A piece takes its colours and typeface from custom properties with defaults, and keeps page-level rules out of its own styles, so a page can theme it and `compose.mjs` can lift it.
- Take the mechanism from a reference, bring your own job, thing and content. Do not rebuild a named gallery piece under another name.

## Scripts

All in `scripts/`, tested with Node 22, Playwright Chromium, Python 3.11+ and ffmpeg 6.

| Script | Use |
|---|---|
| `piece-starter.html` | Starting point: a working switch that follows every rule above. Opens in a browser. |
| `kit.js` | The helpers pieces carry: fixed-step `spring`, sleeping `loop`, unified `drag` with release velocity, `fit` for a sharp canvas, seeded `rand`, `gauss`, `map`, and `split` for per-letter text that survives right-to-left and line wrapping. |
| `kit-sync.mjs` | Writes the current kit between the `kit:start` and `kit:end` markers of a piece, or checks that a copy is current. |
| `probe.mjs` | Drives a piece in a real browser and photographs each state: pointer, keys, scrub, reduced motion, a 390 px phone with touch, and optional RTL or query-string variants. Works on a piece alone or in place on a page (`--root`). Writes `sheet.png` and `report.json`. |
| `compose.mjs` | Sets pieces into a page shell and writes one file; `--artifact` also writes a variant for a Claude artifact. Refuses a piece that would arrive half styled or clash with the page's class names. |
| `gallery.py` | Searches the reference index by job, material, family, tech or gesture; `clip` fetches a public preview and cuts a strip; `gaps` shows the job and material pairs nobody has built. |

## Examples

Six original pieces built with this method, each one file, each passing the probe clean in English and Hebrew. Open them in a browser; add `?lang=he` for right to left.

| File | Sentence | Family |
|---|---|---|
| `examples/tokens.html` | A how-closely-are-you-looking slider over a sentence on a paper strip: slide it and the sentence is cut into slips, each slip gets a number, and the words fade while the numbers stay. | world |
| `examples/fever.html` | A model-temperature slider that is a thermometer: push the mercury up and the sentence above it loses its composure, letter by letter, while its wording drifts from fact to rumour. | world, glyph |
| `examples/spill.html` | A loader whose context window is a window: tokens print in, the tape climbs, and what no longer fits leaves over the sill and thins to an outline, while the counters stay honest. | story |
| `examples/keys.html` | A tool-permission panel that is a key rack: hand the agent a key and it swings across to the agent's rail, while the answer to the same request changes from words to deeds. | physics |
| `examples/loop.html` | An agent's work as a wheel you turn by hand: each lap it thinks, acts and checks, and the log beside it writes one line per lap. `loop.steps.json` is its turning gesture for the probe. | ring, story |
| `examples/spike.html` | A done-list that is a desk spike: reach for the pile and the slips fan open around the pin; pick one and it lifts off and lies flat to be read. | ring |

And one page built from all six: `examples/explainer/agent.shell.html`, an explainer in Hebrew that follows one request through an AI agent in six stations. Compose it with `node scripts/compose.mjs examples/explainer/agent.shell.html --out agent-explainer.html`.

## When another skill fits better

| Job | Skill |
|---|---|
| A video file: launch film, explainer, kinetic type, showreel | `motion-director`, or the specialist it points to |
| A product demo window that plays the app step by step on a web page | `html-demo` |
| A marketing or product site that is not an explainer | the project's own design system first; this skill supplies the pieces that sit in it |

## References

- `references/conceit.md`: the sentence, what the strongest gallery pieces share, materials and their verbs, finding open ground, the five tests, the three worked examples.
- `references/prompt-anatomy.md`: the eight blocks of a one-piece prompt, a skeleton, a full worked prompt, how to upgrade a one-liner.
- `references/mechanisms.md`: recipes by family with the trick that makes each one hold, code sketches and traps.
- `references/contract.md`: what every piece must do, the renderer ladder, performance budget, accessibility by job, right-to-left, packaging as a React component.
- `references/tells.md`: the habits that read as AI-made, why, the replacement, and a banned list to paste.
- `references/review-loop.md`: reading the probe sheet, symptom to fix, custom gesture scripts, what a person still has to judge.
- `references/explainer.md`: the question, the through-line, stations as claims, the four lines of copy, the page shell, composing, and the faults that only appear once pieces share a page.
- `references/sources.md`: where this comes from, what is stored and what is not, the gallery in numbers.
