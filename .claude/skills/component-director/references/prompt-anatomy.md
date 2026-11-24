# The one-piece prompt

A prompt for a single component, written so the model has nothing left to guess. This architecture is this skill's own, built from what the reference previews show and from what goes wrong when a block is missing. Scrolltide's prompts are its paid product and were not read.

## The eight blocks

| # | Block | Decides | Leave it out and you get |
|---|---|---|---|
| 1 | **Sentence** | the idea, in the form from `conceit.md` | a generic control with a transition |
| 2 | **Job and states** | what it controls, the range of the value, the discrete states on top, the default | two states and a jump between them |
| 3 | **The thing** | material, light, palette, typeface, the stage it sits on | a rounded card with a purple gradient |
| 4 | **Behaviour** | each gesture and its response, what the one number is, how it settles, the consequence outside the control | hover: scale 1.05 |
| 5 | **Build** | renderer, one file or one component, props, dependencies, sizes | a different stack every run, three files, a CDN font |
| 6 | **Contract** | keys, touch, reduced motion, right-to-left, sleeping at rest, the scrub handle | mouse only, a loop that never stops |
| 7 | **Banned** | the defaults to refuse, each with its replacement | exactly those defaults |
| 8 | **Check** | how the result is verified before it is called done | an untested first draft |

Blocks 1 to 4 change with every piece. Blocks 5 to 8 are nearly the same every time; keep a house version and paste it.

## Skeleton

```
ONE PIECE: <name>

1. SENTENCE
A <job> that is a <thing>: <gesture> and <what happens>, while <what else changes>.

2. JOB AND STATES
It controls <what>. Its value p runs from 0 (<meaning>) to 1 (<meaning>); default <value>.
At 0 it looks like <...>. At 0.5: <...>. At 1: <...>.
Discrete states on top of p: <focused, picked, disabled, loading, error, empty>.
Text that changes with state: <caption at each state, in the product's voice>.

3. THE THING
Material: <one>. Light: <where it comes from, what it does on the material>.
Palette: ground <hex>, ink <hex>, one accent <hex>. Typeface: <one family, plus mono for numbers>.
Stage: the piece alone on <ground>, about <40-60>% of the width, nothing else on screen.
Content: <the real labels, names, numbers; never placeholders>.

4. BEHAVIOUR
<gesture 1>: <response>, <how long>, <how it settles>.
<gesture 2>: ...
Dragging scrubs p continuously; letting go settles on <nearest state / stays / coasts and snaps>.
p is drawn through a spring: <arrives without overshoot | one small overshoot on the <part with mass>>.
Outside the control: <the consequence>.
At rest it is still. <Any ambient motion> runs only while hovered, focused or just touched.

5. BUILD
<One self-contained HTML file | one React component file, default export, no other files>.
Renderer: <CSS | CSS + registered properties | DOM + springs | SVG | canvas 2D | fragment shader | three.js> and nothing heavier.
No dependencies<, except ...>. Nothing loaded from other hosts. System font stack.
Props / options: <value, onChange, labels, colours, size>.
Root element carries data-piece="<name>". Everything is sized in em from one font-size so it scales as a unit.

6. CONTRACT
- Everything drawn is a function of p. Settled states depend on p alone: seeded random, no clock.
- One requestAnimationFrame loop that stops at rest, off screen (IntersectionObserver) and when the tab is hidden.
- Pointer events for mouse, touch and pen, with touch-action set on what is dragged. user-select: none on dragged surfaces.
- A real <button>/<input>/ARIA role for the job, a visible :focus-visible ring, arrows / Space / Enter / Escape as fits.
- prefers-reduced-motion: jump to the settled state, no travel, no ambient motion.
- Works in dir="rtl": logical properties, mirrored gesture and arrow keys, text split by word and grapheme without reversing.
- Fits a 390 px phone with no sideways scroll, text at 11 px or more, targets at 44 px.
- Expose window.PIECE = { scrub(p), set(p) }: scrub draws the settled state at once, set travels there.

7. BANNED
<paste from references/tells.md, trimmed to what this piece is at risk of>

8. CHECK
Before finishing, drive it: rest, hover, press, drag half way, release, keyboard only, reduced motion, 390 px wide, rtl.
For each, say what you saw. Fix what is wrong before you answer. Name anything you could not check.
```

## A worked prompt

The prompt that would produce `examples/fever.html`.

```
ONE PIECE: Fever

1. SENTENCE
A model-temperature slider that is a thermometer: push the mercury up and the sentence above it loses
its composure, letter by letter, while its wording drifts from fact to rumour.

2. JOB AND STATES
It sets the sampling temperature of a language model, 0.0 to 2.0, default 0.4. p = temperature / 2.
At 0 the sentence is set straight, tight and dark: "Two plus two is four."
At 0.5 the letters lean and drop off the baseline a little: "Two plus two is a small crowd."
At 1 they are loose, large and small, in vermilion: "Two is a feeling. Four is a rumour."
Four wordings in all, swapping at p = 1/6, 1/2 and 5/6. Exactly one shows at rest.
Read-out under the tube: the number to one decimal and one word: steady, loose, inventive, unhinged.

3. THE THING
A horizontal glass thermometer: a bulb at the start, a tube, mercury that fills to p.
Mercury runs from slate blue (#49627a) cold to vermilion (#e2452b) hot; the bulb gains a soft glow with heat.
Ground: warm paper #efeae1. Ink #1d1b1a. One serif for the sentence, one mono for numbers and labels.
The piece alone on the paper, about 60% of the width.

4. BEHAVIOUR
Drag anywhere on the tube: the mercury follows through a spring with one small slosh past the target.
Arrow keys step 0.1; Page Up and Page Down 0.5; Home and End go to the ends.
Each letter has its own fixed lean, drop and size, chosen once from a seeded generator. p only scales them,
so the same temperature always sets the same sentence.
A wording swap is a short blur from one line to the next, about a quarter of a second.
Above 1.1, and only while the tube is hovered, dragged or keyboard-focused, the letters shimmer slowly in
the heat. When attention leaves they come to rest.

5. BUILD
One self-contained HTML file. DOM and CSS, transforms on per-letter inline-blocks, one rAF loop. No canvas.
No dependencies, nothing from other hosts. Root: <section data-piece="fever">. ?lang=he switches to Hebrew.

6. CONTRACT
(house contract, plus:) The tube is role="slider" with aria-valuenow and aria-valuetext "1.2, inventive".
The moving letters are aria-hidden; one polite live region carries the current wording.
In rtl the bulb is on the right, the mercury grows leftward and the left arrow raises the value.
Split the sentence so a Latin word inside the Hebrew line is not reversed and punctuation stays with its word.

7. BANNED
No bounce on the letters: they lean, they do not jiggle, except the earned shimmer.
No colour change on the page ground. No emoji thermometer. No tooltip. No particles.
No continuous animation at rest.

8. CHECK
Run the probe with a Hebrew variant. On the sheet, look for: one wording per still, no selected text after
the drag, no punctuation alone on a line, focus ring visible, the phone still readable.
```

## Dials

Words that move the result, and what each one buys.

| Dial | Low | High |
|---|---|---|
| Literalness | "suggests a thermometer": a line and a dot | "is a thermometer": glass, bulb, highlight, ticks |
| Mass | "arrives without overshoot" | "one small slosh past the target" |
| Theatre | response done in 300 ms | a three-beat sequence of two seconds (loaders, one-off moments only) |
| Reach | the control changes | the control and one thing outside it change |
| Density of content | a label and a value | a full plausible card: route, times, price, seat |
| Renderer | CSS only | a shader. Raise this last, and only when a still shows CSS cannot do it |

## Upgrading a one-line prompt

Given "make me a cool animated toggle":

1. Ask what it switches. The job supplies the idea: notifications, dark mode, public or private, autopilot.
2. Write the sentence. *A do-not-disturb switch that is a door sign: flip it and the card turns over on its string to the other face, while the notification dots on the page behind it go quiet one by one.*
3. Name the number and what half way looks like: the card edge-on, both faces foreshortened.
4. Choose the renderer from the still: one element, one rotation about a hung pivot, so CSS 3D with a pendulum spring for the settle.
5. Paste the house blocks 5, 6 and 8. Trim block 7 to the risks: no bounce beyond the pendulum, no confetti, no loop at rest.

The person gets back a prompt of thirty or forty lines. That is the right length: under twenty leaves decisions open, and past eighty the model starts trading one instruction against another.
