# Mechanisms

Nineteen families cover the 132 reference pieces. Each section says what the family is, the one trick that makes it hold, a sketch, and the traps. The sketches use the kit (`K.spring`, `K.map`, `K.gauss`, `K.drag`, `K.loop`) and are written here, not taken from any gallery piece. To see how others staged a family: `python3 scripts/gallery.py search --family <name>`, then `clip <slug>`.

| Family | In the gallery | One line |
|---|---|---|
| `world` | 14 | The control's state is a small scene; one number runs both |
| `story` | 9 | A sequence driven by progress or time: loaders, intros, button states |
| `ring` | 15 | Items on a circle, arc, wheel, helix or tunnel, placed by one rotation |
| `rail` | 18 | A strip where each item's look is a function of its distance from focus |
| `stack` | 3 | A pile you leaf through or throw from |
| `expand` | 10 | One opens and its neighbours make room |
| `morph` | 6 | One surface travelling between two measured layouts |
| `fold` | 10 | Paper: peel, fold, tear, crumple, turn, unroll |
| `fluid` | 5 | Levels that slosh, blobs that merge, ink that stretches |
| `lens` | 10 | Glass that bends what is behind it |
| `field` | 13 | The pointer is the input and position matters |
| `sdf` | 8 | A soft object or character drawn by raymarching in a shader |
| `physics` | 11 | Bodies: pendulums, cables, throws, detents |
| `glyph` | 7 | Text moving letter by letter or word by word |
| `mask` | 10 | A reveal through a moving shape |
| `scroll` | 5 | Driven by position on the page |
| `light` | 4 | Glows and gradients on registered CSS properties, no script per frame |
| `object` | 3 | One lit 3D object that answers the pointer |
| `camera` | 1 | A move between two scales of the same scene |

## world: the control is a scene

One number `p`. Every element of the scene reads `p` through its own window, so they do not all move at once.

```js
function render(p) {
  const dusk = K.map(p, 0.10, 0.60), night = K.map(p, 0.45, 1.00);    // overlapping windows of p
  sun.style.transform  = `translateY(${dusk * 130}%)`;
  moon.style.transform = `translateY(${(1 - night) * 130}%)`;
  scene.style.setProperty('--night', night.toFixed(3));              // CSS mixes the sky from it
  lamp.style.opacity = K.map(p, 0.70, 0.82);                          // comes on late, quickly
  knob.style.insetInlineStart = `calc(${p} * (100% - var(--knob)))`;
}
```

- Dragging the knob sets `p` directly; letting go settles on the nearer end, biased by release speed: `(p + vx / 900) > 0.5`.
- Let the windows overlap so every quarter of the range changes something. The probe fails a scrub with a dead quarter.
- Three to five moving things. A scene inside a 64 px control has to read at that size.
- The consequence outside the control is one custom property on a parent or one event, never a reach into the page's own DOM.
- **Trap:** tying any layer to the clock instead of `p`. Then half way is not a picture, it is a moment.

## story: driven by progress or time

Loaders, intros, multi-beat buttons. The settled picture is still a function of `p`; only how `p` advances differs.

- Write the beats as windows of `p`, each with a caption: `0–0.25 reading`, `0.25–0.3 the window fills (it hesitates)`, `0.3–1 the tape climbs`, `1 done`.
- Real progress stalls. Design the stall: whatever is on screen at any `p` must look intended for ten seconds.
- One honest beat (it waits at 99%, it hesitates when full) is charm. Faked progress is a lie: if there is no real signal, build an indeterminate story that loops through a still point.
- A loader must not outlast the wait. Give the exit a fixed, short duration and let it start from any `p`.
- An intro removes itself from the DOM when done and never traps focus.

`examples/spill.html` is this family: tokens are a pure function of `p`; the tape's scroll is the only spring.

## ring: one pivot

Every item turns about the same point. One angle per item gives both its position and its lean, so there is no per-item trigonometry.

```css
/* 2D arc or fan: the pivot is far below (an arch) or at the items' own edge (a fan, a deck, a spike) */
.item { position: absolute; transform-origin: 50% calc(50% + var(--radius)); }
```
```js
for (const it of items) it.el.style.transform = `rotate(${(it.i - focus.x) * step}deg)`;   // focus is the number
// drag: an arc length of dx turns the ring by dx / radius radians
K.drag(el, { move: ({ dx }) => { focus.to = start - (dx / radius) * (180 / Math.PI) / step; loop.wake(); } });
```

```css
/* 3D wheel or cylinder */
.ring { perspective: 1400px; }  .ring > .turn { transform-style: preserve-3d; }
.item { transform: rotateY(calc(var(--i) * var(--step))) translateZ(var(--radius)); }
```

- **Helix:** add `translateY(angle * pitch)`. **Tunnel:** place items on the walls and move them along Z, wrapping with a modulo.
- **Depth:** browsers sort heavily overlapping 3D planes badly. Compute each item's depth (`cos` of its angle) every frame and set `z-index`, or draw back to front yourself.
- **The far side:** leave it visible through the gaps, dimmed by depth. That is what makes a ring read as a cylinder and not a shallow fan. Mirrored text on back faces is correct; hiding it flattens the object.
- **Even gaps:** equal angles give unequal gaps on screen. Solve the angle from the screen position you want: `angle = asin(x / radius)`.
- **Momentum:** release velocity from the kit, then `rest = focus + v * 0.25`, round to a whole item, spring there.
- **Traps:** perspective stronger than about three times the ring's width distorts; too few items to wrap leaves a hole at the back; hit-testing tilted items needs generous targets.

`examples/spike.html` is the fan case: the pivot is a pin through the slips, and the fan is one spring per slip toward its own angle.

## rail and stack: a function of distance

`d = item index − focus`, as a fraction. Everything about an item is `f(d)`.

```js
for (const it of items) {
  const d = wrap(it.i - focus.x, n), a = Math.min(Math.abs(d), 3);              // wrap: -n/2 .. n/2, for an endless strip
  it.el.style.transform = `translateX(${d * gap}px) rotateY(${K.clamp(d, -1, 1) * -32}deg) scale(${1 - a * 0.1})`;
  it.el.style.zIndex = String(100 - Math.round(a * 10));
  it.el.style.opacity = String(1 - a * 0.22);
}
```

- **Lifted focus:** make the focused item leave the curve its neighbours sit on, with a step in scale or height. A continuous falloff reads as "nearest"; a step reads as "picked up".
- **Re-crop, do not scale:** to open an image, change the frame's aspect and keep `object-fit: cover`. The picture widens into the frame.
- **Stack:** the top card follows the drag with rotation proportional to offset; past a threshold or a fast release it flies off and the index advances, otherwise it springs back.
- **Traps:** live `blur()` on many large images is slow, so blur only the nearest three or use pre-blurred copies; only the focused video plays.

## expand and morph

**Expand.** The opening item grows, the others give way, and nothing inside re-wraps.

```css
.row  { display: flex; gap: 10px; }
.card { flex: var(--grow, 1) 1 0; min-inline-size: 0; overflow: hidden; }   /* spring --grow from 1 to 4 */
.card .inner { inline-size: var(--open-width); }                            /* laid out once, at the open size */
```

The inner box has the open width at all times; the card clips it. The text is already in its final lines when the card starts to open.

**Morph.** One surface moves between two measured layouts. Not a second element fading in behind the first.

```js
const a = from.getBoundingClientRect(), b = to.getBoundingClientRect();     // measure after document.fonts.ready
// animate the ONE surface: left, top, width, height and border-radius from a to b, through one spring
// content of the old state blurs out as content of the new state blurs in, both clipped by the surface
```

- A moving highlight under tabs is the same thing: one element, measured boxes.
- **Traps:** scaling the surface with `transform: scale` bends its corner radius and its text, so animate real size on small elements; measuring before fonts load; swapping to a different element at the end, which jumps.

## fold: paper

Paper reads as paper when it has a back, a crease, and a shadow along the crease.

**Peel or fold from a corner.** The crease is the perpendicular bisector of the line from the corner to the pointer.

```js
// corner c, pointer q (page coordinates)
const mx = (c.x + q.x) / 2, my = (c.y + q.y) / 2, ang = Math.atan2(q.y - c.y, q.x - c.x);
// page:  clip-path keeps the side of the crease away from the corner
// flap:  the same page reflected across the crease, showing its back, clipped to the folded region
flap.style.transform = `translate(${mx}px, ${my}px) rotate(${ang}rad) scaleX(-1) rotate(${-ang}rad) translate(${-mx}px, ${-my}px)`;
// shadow: a gradient band along the crease whose width grows with how far the fold has gone
```

- **Page or board turn:** `rotateY` about the spine with `transform-style: preserve-3d`, two faces with `backface-visibility: hidden`, a shadow that follows the sine of the angle.
- **Tear:** the perforation is a row of points. Each lets go when the pull passes its threshold, starting from the pulled end; the loose part turns about the last point still attached, then falls as a free body.
- **Crumple:** a true crumple is a displaced mesh in WebGL. Without one, do not fake it with a blur; choose fold or peel.
- **Unroll:** reveal by clip, and draw the roll at the leading edge as a narrow light-to-dark band.
- **Traps:** a flap with no back colour and no shadow is a sticker; `clip-path` in percent and transforms in pixels drift apart on resize.

## fluid and lens

**A level that sloshes.** The surface is a line with a tilt and a ripple, both springs kicked by the container's acceleration.

```js
tilt.to = 0; tilt.v += -accel * 0.004;                 // a shove tips the surface the other way
ripple.to = 0; ripple.v += Math.abs(accel) * 0.002;
const y = (x) => level + tilt.x * (x - cx) + ripple.x * 5 * Math.sin(x * 0.06 + t * 9);
```

Draw it as a filled path on a canvas or in SVG. It must come to rest; liquid that never settles is a screensaver.

**Blobs that merge and split** (ink strands, pours, droplets). In a fragment shader, combine circle distances with a smooth minimum and threshold the result:

```glsl
float smin(float a, float b, float k) { float h = clamp(0.5 + 0.5 * (b - a) / k, 0.0, 1.0); return mix(b, a, h) - k * h * (1.0 - h); }
```

For a handful of blobs in the DOM, an SVG "goo" filter (a blur followed by an alpha contrast in `feColorMatrix`) on a group of circles does it without WebGL. Keep text out of the filtered group.

**Glass that bends.**
- Over a picture you own: sample it in a shader with the lookup offset along the lens normal, strongest at the rim; shift the colour channels by a hair for the fringe.
- Over live page content: `backdrop-filter: blur()` gives frost everywhere. Bending needs `backdrop-filter: url(#displacement)`, which only Chromium supports, so design the frosted fallback first and treat the bend as an upgrade.
- **Fluted glass:** quantise the horizontal lookup into ribs and squeeze within each: `u = (floor(u * N) + 0.5 + (fract(u * N) - 0.5) * squeeze) / N`.
- **Traps:** `backdrop-filter` over a large area costs a full-area blur per frame; a lens with no highlight and no rim shadow looks like a hole.

## field: the pointer is the input

```js
// every cell is pushed by one Gaussian around the pointer
const k = K.gauss(Math.hypot(cell.x - px, cell.y - py), 90);          // 0..1
cell.dx = (cell.x - px) * k * 0.4; cell.dy = (cell.y - py) * k * 0.4;
```

- **Smooth the pointer, not the cells.** Put two springs on the pointer position and feed that to the field.
- **Ripple lattice:** each cell has a height and a velocity; `v += (average of neighbours − h) * c; v *= damping; h += v`. A swell spreads, overshoots and settles.
- **Trail:** emit by distance travelled, not per pointer event, so spacing is even at any speed: accumulate distance and spawn at interpolated points every `spacing` pixels.
- **Ordered dither:** `on = luminance > BAYER[y % 4][x % 4]` inside a ragged radius, drawn on a canvas laid over a real `<img>`, so the photograph stays a photograph everywhere else.
- **Particle text:** draw the word to an off-screen canvas, sample its alpha on a grid for home positions, spring each dot home, repel with the Gaussian.
- **Budget:** canvas 2D handles about ten thousand cells per frame. Past that, one shader pass.
- **Traps:** an overlay without `pointer-events: none` kills the section under it; touch has no hover, so follow the last touch and then relax; the loop must stop when the field is flat.

## sdf: raymarched objects and characters

For soft glossy things that turn, squash, merge or look at the pointer, with no model files. It costs a GPU, so it is for one hero object, never for a list.

- One full-screen triangle; a camera ray per pixel; up to 64 marching steps; the scene is a smooth minimum of a few primitives; the normal from central differences; lighting is diffuse plus rim plus a soft highlight.
- State drives shape: a shell's height, a blob's radius, a bend. Pass `p`, the smoothed pointer and time as uniforms.
- **Budget:** render at 1.5× device pixels at most; keep the canvas under about 512 px on its long side; pause off screen; handle `webglcontextlost`; ship a still image for when WebGL is missing.
- **Trap:** a mascot that never stops moving. Blinks and glances at irregular intervals, with rest between.

## physics: bodies

The kit's spring steps at a fixed 1/120 s. Do the same for everything else here; a variable step explodes on a slow frame.

```js
// throw, coast, land on a detent
const rest = x + v / friction;                         // where it would stop by itself
target.to = Math.round(rest / detent) * detent;        // the nearest station to that
```

```js
// a cable or rope: points that remember where they were (Verlet), then constraints
for (const p of pts) { const vx = (p.x - p.px) * 0.99, vy = (p.y - p.py) * 0.99; p.px = p.x; p.py = p.y; p.x += vx; p.y += vy + g * h * h; }
for (let k = 0; k < 6; k++) for (let i = 1; i < pts.length; i++) pull(pts[i - 1], pts[i], restLength);   // ends pinned
```

- **Pendulum** for anything that hangs: `angle'' = −(g / L)·sin(angle) − c·angle' − (lineAcceleration / L)·cos(angle)`. Speeding up or stopping the line makes everything on it swing and settle.
- **Traps:** micro-jitter that never sleeps (add a rest threshold); mass so heavy the piece fights the hand.

## glyph: text

Use `K.split(el)` (letters) or `K.split(el, 'word')`. It keeps a readable copy for assistive tech, keeps a word and its punctuation on one line, and keeps every word in its own direction.

```js
const glyphs = K.split(title).map((el, i, all) => ({ el, at: i / all.length, lean: rnd() * 2 - 1 }));
for (const g of glyphs) {
  const t = K.smooth(K.map(p, g.at * 0.6, g.at * 0.6 + 0.4));       // a wave of arrival across the line
  g.el.style.transform = `translateY(${(1 - t) * 0.6}em) rotate(${(1 - t) * g.lean * 12}deg)`;
  g.el.style.opacity = t;
}
```

- A focus frame or highlight that travels between words uses measured boxes: `getBoundingClientRect()` after `document.fonts.ready` and again on resize.
- Rolling digits: one column per digit, `translateY` by its value, `font-variant-numeric: tabular-nums`.
- **Traps:** Arabic and other joined scripts must be split by word; a web font arriving late changes every measurement.

`examples/fever.html` is this family driven by a `world` number.

## mask, light and scroll

**Mask.** Reveal through a shape driven by `p`: `clip-path: circle(calc(var(--p) * 150%) at var(--x) var(--y))`, or a `mask-image` gradient. Cut notches and holes with a mask so the fill can be any gradient or picture. A mask also clips `box-shadow`; put the shadow on a wrapper with `filter: drop-shadow()`.

**Light.** Register a custom property and CSS can animate a gradient by itself, with no script per frame:

```css
@property --turn { syntax: '<angle>'; inherits: false; initial-value: 0deg; }
.ring { background: conic-gradient(from var(--turn), #0000 0 70%, #7cf 86%, #f7c); transition: --turn .7s cubic-bezier(.2, .8, .2, 1); }
.button:hover .ring, .button:focus-visible .ring { --turn: 360deg; }
```

**Scroll.** `p` is how far the element has travelled through the viewport.

```js
const r = el.getBoundingClientRect(), vh = innerHeight;
const p = K.clamp((vh - r.top) / (vh + r.height));       // read once per frame, never per scroll event
```

Use `animation-timeline: view()` where it exists and keep the script as the fallback. For speed effects, spring the scroll velocity and feed that in. Never take over the page's scrolling.

## object and camera

**Object.** One lit thing in three.js or CSS 3D that tilts toward a smoothed pointer and has one action (it presses, it spins with momentum). Light it with a key and a coloured rim; sink labels into the surface. Give drag momentum and let it come to rest.

**Camera.** A move between two scales of one scene (a seat map and the view from the seat). Animate the camera with one spring on a 0..1 path, keep something shared on screen the whole way, and make the way back the same path reversed.
