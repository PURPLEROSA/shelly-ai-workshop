# What makes a component look AI-made

Each of these is a default a model reaches for when the prompt leaves a decision open. None is wrong in itself; together they are a signature. The fix is always the same shape: make the decision the default was standing in for.

## Idea

| Tell | Why it reads as generated | Instead |
|---|---|---|
| The component is a card with a headline, a line of copy and a button | That is a page section. A piece does one job | Name the job in one word and remove everything that is not it |
| The metaphor is paint: a "liquid" button that only has a wavy gradient | Take the liquid away and nothing about the behaviour changes | The thing must explain the behaviour (the removal test in `conceit.md`) |
| The idea is the effect: a tilt card, a cursor spotlight, a glow that follows the pointer | An effect with no job is a demo of a technique | Give the effect something to say about state: the tilt shows which card is picked, the light shows what is ready |
| Five ideas in one piece: it glows, tilts, sparkles, morphs and confettis | No single thing to remember | One sentence. Cut what the sentence does not mention |
| A dark stage, a purple-to-blue gradient, glass panels | The house style of generated UI | A material and a palette taken from the product; say the hexes |

## Behaviour

| Tell | Why | Instead |
|---|---|---|
| Hover scales the element by five percent and deepens the shadow | It tells the person nothing about the object | A response that reveals something: the picture re-crops, a tab slides to show what is under it, the light moves across the surface |
| Two states and a 300 ms ease between them | Nothing exists half way, so it cannot be dragged or stopped | One number, drawn through a spring, scrubbed by the drag |
| Everything bounces | Overshoot on every part reads as a toy | Damping near 1 by default; one overshoot on the one part with mass |
| Items arrive with equal delays, 50 ms apart | A metronome | Vary by mass or distance; give each part its own stiffness |
| It floats, pulses or shimmers forever | It spends battery and attention on nobody | Motion earned by hover, focus or touch, that then comes to rest |
| It works with a mouse and nothing else | Half of visitors are on a phone, and some use keys | Pointer events, a real control element, a focus ring |
| The reveal is hover-only | Dead on touch | Tap and focus reach the same state |
| Dragging selects the text underneath | Nobody tried dragging it | `user-select: none` on the dragged surface, `touch-action` set |
| Text re-wraps while a card opens; an image stretches as it grows | Layout is being animated | Lay out once at the final size and clip; re-crop pictures |
| It looks different on every load | Unseeded random numbers; nothing can be reviewed or reproduced | Seed them |
| It rests half way through a fade | A cross-fade tied to a value that happens to sit on the threshold | Discrete swaps with their own spring |
| Confetti on success | The reflex celebration | A consequence that belongs to the thing: the stamp lands, the slip goes on the spike |
| It plays a sound | Nobody asked | Silence unless requested; then behind a setting, never on load |

## Content and finish

| Tell | Why | Instead |
|---|---|---|
| "Card Title", "Lorem ipsum", "John Doe", "$99/mo" | Placeholder content makes any design look like a template | The person's real labels and numbers, or plausible ones in their voice and language |
| Emoji used as icons | A shortcut | Inline SVG drawn for the piece, or no icon |
| A font loaded from a CDN, falling back to Arial | A network dependency for a look that then fails | A system stack chosen on purpose, or the product's own font passed in |
| The piece fills the stage edge to edge | No air, no focus | 30 to 60 percent of the width on a quiet ground |
| Every state has the same caption | The copy was not designed | Microcopy that changes with state and says what happened |
| No focus ring, or the browser default on a custom shape | Keyboard users were not considered | A ring drawn for the material |
| English-only geometry on a right-to-left page | The mirror was never tried | Logical properties and a direction sign (`contract.md`) |

## A banned list to paste

Trim it to what the piece is at risk of. Each line names the default and the replacement, because "do not X" alone leaves a hole the model fills with the next default.

```
BANNED
- No hover that only scales and adds shadow. Hover reveals something about the object.
- No two-state CSS transition as the main motion. One value p, drawn through a spring, scrubbed by dragging.
- No bounce on everything. Damping ratio 0.8 to 1; at most one part overshoots once.
- No equal stagger delays. Parts differ in stiffness.
- No animation that runs at rest. Ambient motion only while hovered, focused or just touched, then it stops.
- No purple-blue gradient, glass panel or neon glow unless the brief names it. Use the stated material and hexes.
- No placeholder text, names or prices. Use the content given.
- No emoji icons, no icon font, no CDN fonts or scripts.
- No confetti, particles or sound unless the brief names them.
- No hover-only reveals, no mouse-only handlers. Pointer events, a real control element, a visible focus ring.
- No text that re-wraps or image that stretches during the motion. Lay out once at the final size.
- No unseeded randomness. The same value always draws the same picture.
- No second idea. If it is not in the sentence, it is not in the piece.
```
