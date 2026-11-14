# Gotchas by area

Put the three to six that apply into the prompt's `<gotchas>` block, each with its consequence. A trap stated with what goes wrong is followed; a bare rule is skimmed.

## Contents

- Text
- Camera
- Shapes, floods and morphs
- Loops
- CSS and DOM traps
- Glass and blur
- 3D
- Footage and images
- Sound and voice
- Render and determinism
- Diagrams and explainers
- Characters
- Right-to-left text (Hebrew, Arabic)

## Text

- Give outgoing and incoming text separate timing, or letters overlap for a few frames.
- Text that swaps inside a morphing container needs its own mask and its own enter and exit.
- Measure text only after fonts load. A fallback font changes every width.
- A long name will not fit where a five-letter name did: scale the whole lockup together rather than letting one part fall off the frame.
- Keep typed text on fixed lines so the camera never has to chase a wrapping cursor.
- Typed text is "the portion typed by time t", so any frame renders alone.
- When squeezing a wordmark, move every letter toward the anchor by the same factor and scale drawn width with it, or gaps open.
- No more than seven words on screen at once in an explainer.

## Camera

- Never put `will-change` on anything the camera scales, or text renders blurry.
- If the camera resets to 1.0 at a handoff, the zoom snaps. Carry the zoom across.
- Interpolate zoom in log space.
- Never zoom in and out consecutively; no move that reverses direction within a scene.
- Drive a long glide from a speed curve, not position keys, or it surges.
- Leave room around notifications and small UI so they stay readable during moves.
- Scale the cursor with the camera.

## Shapes, floods and morphs

- When a shape fills the frame, scale it past all four corners.
- A flood should take about 0.3 to 0.35 s. Faster looks like a flash; half the screen changing in one frame is a pop.
- Set z-index on every layer, or cards float above the flood.
- Make shapes that transform into each other states of one element, preserving position and velocity through the change.
- A graph drawn beside a moving dot must use the same function that moves the dot, or the spring looks fake.
- Heavy blur can erase a shape completely. If a frame looks empty, lower the blur until the shape still reads.
- A white element on a white page needs a hairline edge and a faint shadow.

## Loops

- Make the last frame identical to the first, including cursor position, speed and direction.
- Springs must have settled by the end; check the numbers, not the look.
- Compare frame 0 and the final frame as images.

## CSS and DOM traps

- Never set `opacity` or `filter` on a `preserve-3d` element: it flattens and both faces show. Fade a wrapper instead.
- A child with `visibility: visible` shows through a hidden parent. Use `inherit`.
- `backdrop-filter: url()` misreads displacement maps in Chromium. Clone the scene behind the glass instead.
- Things that fade out with transparency reveal whatever is behind them. Fade into the background colour first and cut to transparent at the very end.
- Measure element positions at runtime for match cuts; hard-coded positions break when copy changes.
- Lock the layout before timing anything. A change in one section's height shifts everything after it.

## Glass and blur

- Glass disappears on plain white. Put a slow pastel wash or a blurred copy of the photo behind it.
- For a glass panel: capture the scene behind the shape, blur it for the body, draw a slightly magnified, lightly blurred copy in a narrow band along the edge, then add sheen, rim and a soft shadow.
- Use a goo effect (blur plus alpha threshold) under a sharp copy of the source, so the inside stays crisp.

## 3D

- Set shadow bias, or surfaces get striped acne.
- Keep near and far planes tight, or distant surfaces flicker.
- Seed every random number, or the render will not match the preview.
- Use mipmaps and anisotropic filtering on flat textured surfaces seen at an angle, or far text shimmers.
- The camera never passes through geometry.
- Rendering on a real GPU may need explicit browser flags; a software renderer changes the look.

## Footage and images

- Re-encode video all-intra and wait for `seeked`, or use image sequences.
- A simple static file server may not support range requests, which breaks video seeking. Use a blob URL or sequences.
- Do not put images that contain their own text inside cards that have a title, or the title doubles up.
- Capture real pages at device scale 2 after one full scroll.

## Sound and voice

- Place each effect by its measured peak, not its file start.
- Trim risers around their peak; many are several seconds long.
- An opener tagged warm can sound whispered; an excited tag can sound fake. Use emotion tags sparingly.
- A single transcription pass over a long read can place words late. Split at pauses.
- Keep effects quiet under music and normalise the mix.
- Check the licence of every track and effect.

## Render and determinism

- Declare every variable before the first `seek()` call.
- No timers, no CSS transitions, no state between frames, no unseeded randomness.
- Four subframes can leave ghost copies on fast moves. Use eight and slow the move.
- A 0.05 s fade is an instant pop-in.
- If code cannot be run where you are, say at once that only a live preview is possible and the MP4 needs a session that can run a browser and ffmpeg.

## Diagrams and explainers

- Check every number and name against a source.
- Keep the diagram's layout fixed so zooming in and out never reshuffles it.
- Arrows and flows animate in the direction things really move.

## Characters

- Lock feet and hands where they touch things, so contacts never slide.
- Keep proportions the same in every shot.
- Give each gag a beat of stillness before it lands.

## Right-to-left text (Hebrew, Arabic)

These are not from the gallery, which is almost entirely Latin and CJK. They are what breaks when the same techniques meet a right-to-left script.

- Set `dir="rtl"` and `lang` on text containers. Wrap embedded Latin, numbers and product names in `<bdi>` or `unicode-bidi: isolate`, or punctuation jumps to the wrong end. A line ending in a number or Latin word may need a right-to-left mark (U+200F) after it.
- Entrances mirror: text enters from the right, wipes and underlines draw right to left, progress fills right to left. A typewriter reveal starts at the right, with the caret on the left of the typed text.
- Stagger letters in reading order. In the DOM that is still first to last; on screen it runs right to left. Do not sort spans by x position.
- Split Hebrew by grapheme, not by code unit (`Intl.Segmenter` with `granularity: 'grapheme'`), so vowel points stay with their letter. Hebrew letters do not join, so per-letter animation is safe.
- Arabic letters join and change shape by position. Do not split an Arabic word into per-letter spans; animate by word, or use a mask over the whole line.
- On canvas set `ctx.direction = 'rtl'` and `textAlign = 'right'`.
- Tracking: Hebrew has no capitals and reads tighter than Latin at the same size. Keep letter-spacing near zero; the negative tracking common in Latin display type crowds it. Allow more line height when vowel points are shown.
- Fonts with good Hebrew: Heebo, Assistant, Rubik, Noto Sans Hebrew, Secular One for display, Frank Ruhl Libre for serif. Pair with a Latin face of matching weight when both appear, and check that numerals match.
- Charts usually keep a left-to-right time axis even in a right-to-left layout; numbers always read left to right. Decide once and keep it.
- UI mockups mirror: navigation on the right, back arrows point right, the cursor's natural rest is top right. Media controls and code do not mirror.
- For narration, `edge-tts` has `he-IL-HilaNeural` and `he-IL-AvriNeural`. Check word timings against the audio before syncing captions.
