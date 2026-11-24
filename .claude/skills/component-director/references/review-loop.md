# Checking and fixing a piece

Nothing is finished until it has been driven through its states and someone has looked at the result. The probe does the driving and takes the photographs. Reading them is still a person's or the model's job.

## Run it

```
node scripts/probe.mjs piece.html                          # one HTML file
node scripts/probe.mjs http://localhost:5173/pieces/fever  # a component on a dev-server route
node scripts/probe.mjs piece.html --variant he=?lang=he    # plus a pass in another language
node scripts/probe.mjs piece.html --rtl                    # plus a pass with dir="rtl" forced
node scripts/probe.mjs piece.html --steps steps.json       # your own gestures
```

It writes `sheet.png` (every still, labelled, with the findings at the top) and `report.json`, prints the findings, and exits 1 on any FAIL. A run takes under half a minute.

What it does, in order: rest; hover; a sweep across the control; press; hold; release; a drag that is then let go; the pointer leaving; Tab into the piece, three arrow keys, Enter, Space; `scrub` at 0, 0.25, 0.5, 0.75 and 1; the piece pushed off screen; a reload under reduced motion; a reload at 390 px with touch (tap, touch drag); then any RTL or variant passes.

Gestures are aimed at `[data-grab]`, or at a slider or switch inside the piece, or at the piece as a whole. If the stills show the pointer missing the control, add `data-grab` or pass `--target`.

## Read the sheet

The findings catch contract breaks. These are the things only looking catches, each of which turned up while building this skill's own examples:

| Look at | For |
|---|---|
| `rest` | Is it one clear picture? Is the piece large enough on the stage? Would a stranger know what to do? |
| `hover`, `press`, `drag` against `rest` | Did the right thing respond, in the right place? Is any text selected (a blue band)? |
| `0.16 s after letting go`, `settled` | Did it land on a state or stop between two? |
| `scrub 0.25 … 0.75` | Is each quarter a good still by itself? Any half-faded pair of texts, any element caught mid-swap? |
| `keyboard focus` | Can you see where focus is without hunting? |
| `reduced motion` | Is the still designed, or just frame zero? |
| `phone 390` | Line breaks, cramped captions, anything touching the edge |
| RTL or language variant | Reversed Latin words or numbers, a full stop alone on a line, an element at the wrong end, a gesture that points the wrong way |
| Any still | Something half-hidden peeking from under a neighbour; a shadow clipped by a mask; a caption that did not change with the state |

## From symptom to fix

| The probe says | Usual cause | Fix |
|---|---|---|
| `errors` | A script threw | Read the message; fix before anything else, the other findings are unreliable until then |
| `idle-loop`: frames requested while nothing changes | An unconditional `requestAnimationFrame` loop | Use `K.loop`; return `false` from `tick` when every spring is at rest |
| `settle`: still moving after the pointer left | Ambient motion tied to `:focus` after a mouse click, or a spring with no rest threshold | Tie it to hover, drag and `:focus-visible`; let springs snap at rest |
| `rest`: moves at rest | Intended ambient motion, or a loop that never ends | If intended, `data-ambient` on the root, and still earn it; otherwise as above |
| `offscreen`: frames while scrolled away | No visibility gate | `K.loop` gates on IntersectionObserver; check the root you passed is the piece |
| `response`: nothing responded | The gesture missed the control, or handlers are on the wrong element | `data-grab`; check with a `--steps` script |
| `touch`: mouse but not touch | `mousedown` and `mousemove` handlers, or no `touch-action` | Pointer events; `touch-action: pan-y` on the dragged element |
| `selection`: dragging selected text | No `user-select: none` | Add it to the dragged surface and anything decorative under it |
| `keys`: nothing takes focus | The control is a `div` with listeners | A real `button` or `input`, or a role with `tabindex="0"` and key handlers |
| `focus`: focus not visible | `outline: none` with no replacement | A `:focus-visible` ring |
| `scrub`: two pictures for one value | Time or unseeded random in `render` | Seed; freeze the clock in `scrub` |
| `scrub`: nothing changes between two quarters | A dead zone in the mapping | Widen or overlap the `K.map` windows |
| `reduced-motion` | Springs still animate, or ambient motion ignores the setting | `if (K.reduced()) spring.snap()` in the one place targets are set |
| `phone`: does not fit | Fixed pixel widths | Size in `em` from a root font-size that follows the viewport |
| `phone-text`, `phone-targets` | Scaling took text under 11 px, or a hit area is thin | A floor in the `clamp`; pad the hit area without changing how it looks |
| `frames`: slow | Layout read or written per frame; a large blur; a full-canvas redraw | Cache measurements; drop the blur; redraw only what changed |
| `self-contained`: other hosts | A CDN font or script | A system stack; inline what is needed |

## Your own gestures

When the default set does not exercise the idea (strike, peel, wind, throw), write the gesture:

```json
[
  { "move": [0.15, 0.5] }, { "shot": "about to strike" },
  { "drag": [[0.15, 0.5], [0.85, 0.35]], "ms": 180 }, { "shot": "struck, held" },
  { "wait": 700 }, { "shot": "caught" },
  { "key": "Escape" }, { "wait": 500 }, { "shot": "put out" }
]
```

Positions are fractions of the gesture target's box. `drag` records frame times. `set` and `scrub` call the handle.

## Asking for a fix

1. **Name the still.** "In `scrub 0.5` two wordings overlap" beats "the text looks off".
2. **One thing per round.** Two fixes at once and you cannot tell which one moved the result.
3. **Protect what works.** Say what must not change: "keep the slosh on release exactly as it is".
4. **Ask for the cause, then the fix.** A symptom patched at the surface comes back in another state.
5. **Prove it.** The next sheet, same gestures, the named still fixed and the rest unchanged.

On a long job, start a fresh session for each round and hand it the file, the sentence and the last sheet. The header comment in the piece is what lets a new session pick it up.

## What stills cannot tell you

Say this to the person every time, and ask them to try the piece:

- **Feel.** Whether the spring is too heavy, the throw too slippery, the response a beat late.
- **Real devices.** A phone's touch latency and GPU, a trackpad's inertia. The probe's frame times are from a headless browser drawing in software.
- **Assistive tech.** The probe checks that a control is reachable and labelled, not what a screen reader says in what order.
- **The tenth use.** Whether the idea is still welcome after a day of it.
