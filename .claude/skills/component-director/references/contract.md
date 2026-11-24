# The contract

What every piece does, whatever it looks like. `scripts/probe.mjs` checks most of it; the rest is on the builder.

## Shape

| | |
|---|---|
| **One file or one component** | A single HTML file, or one React component file. Styles and helpers travel inside it. |
| **Root** | `data-piece="<name>"` on the outermost element. Add `data-ambient` if it moves at rest on purpose, `aria-hidden="true"` if it is decoration. |
| **Grab** | `data-grab` on the element people press and drag, when that is not obvious from a slider or switch role. |
| **Handle** | `window.PIECE = { name, value, scrub(p), set(p) }`. `scrub` draws the settled state for `p` at once. `set` travels there as a person would see it. |
| **Header comment** | The sentence, then `job · material · gesture · family`, then the trick in one line. |
| **Nothing fetched** | No fonts, scripts or images from other hosts unless the person asked. System font stacks; inline SVG; pictures come in as props. |

## One number, and how it moves

- Everything drawn is `render(p)`. Discrete states (picked, focused, open) are further numbers with their own springs, never booleans that swap classes with a transition.
- The settled picture depends on the numbers alone. Seed every random value (`K.rand(seed)`); keep the clock out, except for attention-earned shimmer that is frozen in `scrub`.
- Rest states must be clean. If two things cross-fade around a threshold, a value sitting on the threshold would rest half-faded: make the swap discrete and animate it with its own spring.
- A value follows its target through `K.spring`. Damping ratio 1 arrives without overshoot; 0.7 to 0.8 overshoots once; use below 0.6 only for something meant to ring.
- Give different parts different stiffness (heavier is slower). Equal delays read as a machine.

## The loop

- One `requestAnimationFrame` loop per piece, through `K.loop`. `tick` returns whether anything is still moving; when nothing is, the loop stops. Every input calls `wake()`.
- It stops off screen (IntersectionObserver) and in a hidden tab, and resumes where it was.
- Ambient motion is earned: it runs while the piece is hovered, dragged or keyboard-focused (`:focus-visible`, not `:focus`, or a mouse click leaves it running), then eases out and the loop sleeps.

## Input

- Pointer events only, through `K.drag`: mouse, touch and pen take one path, with pointer capture and a release velocity.
- `touch-action` on the dragged element: `pan-y` for a horizontal drag, `pan-x` for a vertical one, `none` only for a small free-drag surface. Without it a phone scrolls the page.
- `user-select: none` on any surface people drag across.
- Hover is a bonus. Anything hover reveals must also be reachable by tap and by focus. On touch, a first tap may open and a second act.
- A press that barely moves is a click; a drag that ends must not also fire the click.

## Keyboard and assistive tech

| Job | Element or role | Keys |
|---|---|---|
| Button, hold-to-confirm | `<button>` | Enter, Space (hold: keydown to keyup) |
| Toggle | `<button role="switch" aria-checked>` | Space, Enter |
| Slider, dial, zoom | `role="slider"` with `aria-valuemin/max/now` and `aria-valuetext` | arrows, Page Up/Down, Home, End |
| Tabs | `role="tablist"`, `tab`, `tabpanel` | arrows move, Enter or Space selects |
| Carousel, deck, fan | a list of `<button>`s or links; next and previous buttons | arrows, Tab |
| Disclosure, expanding card | `<button aria-expanded>` | Enter, Space, Escape to close |
| Loader | `role="progressbar"` with `aria-valuenow`, or `aria-busy` on what is loading | none |
| Background, mascot, trail | `aria-hidden="true"` | none |

- A visible `:focus-visible` ring on every focusable part, drawn to suit the material.
- Text that is split, masked or drawn on a canvas keeps a readable copy in the DOM (`K.split` does this). State changes that matter go to one polite live region; the animation itself is `aria-hidden`.
- Colour is never the only signal. The caption says the state.

## Reduced motion

`prefers-reduced-motion: reduce` means the piece changes state without travel: it is the `scrub` path. Hold a designed still at rest; no ambient motion; a short cross-fade is acceptable where a jump would confuse. A loader still shows progress, in steps. Listen for the setting changing (`K.onReduced`).

## Size and fit

- Size the whole piece in `em` from one `font-size` on the root, and let that font-size follow the container: `font-size: clamp(12.5px, (100vw - 32px) / 28.6, 19px)`. The piece then scales as one object and keeps its proportions.
- On a 390 px phone: no sideways scroll, text at 11 px or more, touch targets at 44 px (36 is the floor the probe warns under).
- Reserve space for the tallest state so opening something does not push the page.
- A canvas is sized by `K.fit`: backing store at CSS size times device pixel ratio, capped at 2.

## The renderer ladder

Stop at the first rung that can draw the still you sketched. Of the 113 gallery pieces whose stack is stated, 64 use WebGL and 36 are CSS; the CSS ones are not the lesser ones.

| Rung | Good for | Cost |
|---|---|---|
| CSS (transforms, clip-path, masks, `:has`, container queries) | folders, bookmarks, fills, most hover responses | none |
| CSS with `@property` | moving gradients, glows, lights with no script per frame | none |
| DOM with springs (the kit) | anything dragged or thrown; rings, rails, fans, expanding cards; per-letter text | a few dozen elements per frame |
| CSS 3D | wheels, cylinders, page turns, tunnels | watch depth sorting |
| SVG | paths that draw, cables, charts, goo for a few blobs | slow past a few hundred nodes |
| Canvas 2D | fields of thousands of cells, particles, dither, liquid surfaces | redraw area matters |
| Fragment shader | refraction, raymarched objects, simulations, anything per pixel | GPU; needs a fallback still |
| three.js | a real scene: camera moves, meshes, lights | a dependency and its weight |

## Performance budget

- Animate `transform`, `opacity` and custom properties. Changing layout properties every frame is acceptable on one small element, never on a list.
- Read layout once (on resize, after fonts load), not per frame. `getComputedStyle` and `getBoundingClientRect` inside the loop are the usual hidden cost.
- `filter: blur()` and `backdrop-filter` on large or many elements are the first thing to remove when frames drop.
- Shaders: cap resolution, cap march steps, pause off screen.
- The probe's frame times come from a headless browser. Use them to compare two versions, and trust a real device over them.

## Right to left

A piece that will sit on a Hebrew or Arabic page is built for it from the start.

- **Layout:** logical properties throughout: `inline-size`, `inset-inline-start`, `padding-inline`, `text-align: start`. They flip by themselves.
- **What does not flip by itself:** `transform-origin`, `translateX`, rotation direction, `clip-path` and gradient or mask positions. Read the direction once and carry a sign: `const side = getComputedStyle(root).direction === 'rtl' ? -1 : 1;` and add `[dir="rtl"]` rules for origins and mask positions.
- **Gestures:** a drag toward the inline end increases the value in both directions, so mirror the mapping. For a horizontal slider in RTL the left arrow increases.
- **Per-letter text:** always `K.split`. Each word carries its own direction, so "vibe" or "16:30" inside a Hebrew sentence is not reversed, and a full stop after a Latin word lands on the left where the sentence puts it. Hebrew splits by letter safely. Arabic does not: pass `'word'`.
- **Numbers and file names** inside RTL text: wrap in `<bdi>` or let `K.split` isolate them.
- **A trap found building the examples:** setting `direction: ltr` on an absolutely positioned child (to keep a time stamp left-to-right) makes its own `inset-inline-*` resolve the other way and the element jumps to the wrong end. Leave the direction alone; digits with a colon render correctly without it.
- **Mirror or not:** things that follow reading order mirror (a fan that opens away from its pin, a tape that prints from the start edge). Things that depict the world do not (a clock, a map, a photograph, a logo).
- Probe with `--rtl`, or `--variant he=?lang=he` when the piece has its own language switch, and read the stills for reversed words and stray punctuation.

## As a React component

The same structure in one file.

```tsx
export function Fever({ value, onChange, labels }: Props) {
  const root = useRef<HTMLElement>(null);
  useEffect(() => {
    const el = root.current!;                 // create springs, the loop and listeners here
    // ... render(p) writes styles straight to refs; it does not call setState per frame
    return () => { loop.stop(); off(); };     // stop the loop, remove listeners, disconnect observers
  }, []);
  useEffect(() => { go(value); }, [value]);   // a new prop is a new target, not a re-mount
  return <section ref={root} data-piece="fever">…</section>;
}
```

- Per-frame work writes to the DOM or canvas through refs. React state holds only what changes the markup: the committed value, which item is picked.
- Clean up everything in the effect's return: the loop, pointer listeners, observers, the WebGL context.
- Guard browser-only code for server rendering (`useEffect`, or a dynamic import for three.js). The first paint is the settled state for the initial value.
- Styles live in the file (a CSS module beside it, or a `<style>` in the component) and are scoped by the root's class, so the piece cannot leak into the page.
- To probe it, render the component alone on a route and run `node scripts/probe.mjs http://localhost:5173/that-route`. Expose the handle in development: `window.PIECE = { scrub, set }`.
