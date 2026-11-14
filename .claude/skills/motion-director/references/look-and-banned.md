# Why a video looks AI-made, and what to do instead

Prompts with a banned list are rare in the gallery (about one in fourteen) and are over-represented among the most liked entries. Every such list removes the same thing: the look of motion nobody designed. A list works best when each ban comes with its replacement.

## The tells

| Tell | Why it gives the video away | Do this instead |
|---|---|---|
| Glows, neon, lens flares | The quickest way to make a frame look rich, so they appear when nothing calls for them. | Contrast from scale and empty space. Light only where the scene has a light source. |
| Particle bursts, shockwave rings | Motion that comes from nothing and goes nowhere is filler. | Every moving thing comes from an element already on screen and arrives somewhere. |
| Crossfades and blur-ins | What you get when nobody designed the transition. | A shared element changes role: a button expands into the page, a dot becomes the tittle of a letter, a shape floods the frame and contracts into the next scene. |
| Bouncy easing on everything | Reads as cartoonish. | Springs that settle, with a small overshoot at most, and none on text. |
| Text and brackets in the corners | Labels, timecodes and frame markers suggest detail and carry none. | Remove them. Put words only where they name something. |
| Long holds, frozen frames | A stretch where nothing happens makes fifteen seconds feel slow. | Hold only when there is something to read, about a third of a second per word. Keep the camera drifting. |
| Generic gradients, mesh backgrounds | Default decoration. | A flat canvas in a chosen colour. A gradient only when the brand has one. |
| Camera shake, RGB split, flashing backgrounds | Energy added on top instead of designed in. | Speed from the edit: cuts on the beat, moves that overshoot the frame. |
| 3D flips and extrusions in a flat piece | Borrowed depth with no reason. | Stay 2D unless the idea is spatial. One 2D-to-3D moment at most, and it must be the idea. |
| Stock footage, stock icons, placeholder cards | Nothing here belongs to the product. | Real screens, real photos, real numbers. Rebuild the UI as layers. |
| Everything moving in lockstep | Equal staggers and equal durations look generated. | Vary duration, delay and speed per element. One thing leads. |
| Things popping in | A 0.05 s fade is a pop. | Grow, slide from an edge, or reveal by a mask, over at least 0.3 s. |
| A highlight box behind a word | Looks like a text selection. | Colour the word, or underline it with a stroke that draws on. |
| Small things in big empty frames | Shrinking to fit instead of composing. | The focal element spans at least 60% of the frame width. Crop at the edges. |
| The same layout twice in a row | A slideshow. | A new composition on every beat. |
| A tour of effects | No concept, so each shot shows a different trick. | One concept, named first. |
| Walls of text, bullet lists (explainers) | A document, not a film. | A picture before the words, at most seven words on screen. |
| Default materials and lighting (3D) | Looks like a tech demo. | Three-point light, environment map, varied roughness, tone mapping. |
| A spinning object as the whole idea (3D) | The default of every 3D demo. | A shot list with named camera moves and events. |

Two bans concern the build, not the look: unseeded random numbers (a fixed frame changes on the next render) and CSS transitions or timers (frames drift from the clock).

## Writing a banned list

1. Start with the common tells for the kind of video.
2. Run the prompt once and add anything in the result that was not asked for. That is the real list.
3. Pair each ban with its replacement, in the direction or motion rules.
4. End with the standard: anything that looks like a template.
5. Keep it to one line of five to nine items. A list of thirty is ignored.

## Default lists

Use as a starting line, then edit for the piece.

- **Flat motion design, showreel, product film:** particle bursts, glows, lens flares, camera shake, RGB split, crossfades, generic gradients, bouncy easing, holds longer than half a second, anything that looks like a template.
- **One-take product film:** crossfades, blur-ins, 3D flips, particles, glows, camera moves that reverse direction, holds longer than one second, anything that looks like a template.
- **Explainer:** walls of text, bullet lists, generic gradients, stock-looking icons, glows, crossfades, anything that looks like a template.
- **Character short:** glows, lens flares, generic gradients, anything that looks like stock clip art, everything moving at once.
- **3D:** default materials and lighting, floating text labels, glows on everything, a slowly spinning object as the whole idea, anything that looks like a tech demo.
- **UI motion:** bouncy easing, particle bursts, glows, gradients on UI chrome, mismatched icon strokes, dead time, anything that looks like a template.

## Positive rules worth stating every time

- One typeface. One accent colour, reserved for the through-line object and the key word.
- Nothing appears from nothing.
- The camera never sits still and never reverses inside a scene.
- Exits before entries.
- No full stops in on-screen text unless the full stop is the idea.
- The last frame matches the first if it will loop.
