# Recipes by kind of video

Each recipe gives the concept device, the direction lines that matter, the structure, what to ask the person for, the traps, and gallery entries to study. Read a reference with `python3 scripts/gallery.py fetch <slug>` (add `--improved` for the site's rewrite).

The build block is the same for most of them (one HTML file, `seek(t)`, Playwright, subframe blur, a still per beat); see `build-pipelines.md`. Only differences are noted here.

## Contents

1. Showreel
2. Product or launch film
3. UI morph loop
4. Explainer on one diagram
5. Narrated explainer
6. Character short
7. Real-time 3D
8. Page fly-over
9. Kinetic type bumper
10. Data story
11. Recipe or process film
12. Music-led edit and talking-head cut

## 1. Showreel

The gallery's most copied request: show off as a motion designer in 15 seconds. It needs nothing from the person, which is why it spread, and why its results scatter.

- **Device:** one named concept, with each shot made out of the previous one (shapes, type and colour transform; no cuts or fades).
- **Direction:** one typeface, at most three colours plus black and white, one camera language. Show range in equal shares: kinetic type, shape morphing, a 2D-to-3D moment, a data or UI moment, an end title.
- **Structure:** 120 BPM. First bar is the hook, then one technique per bar, each flowing out of the last. Last full bar is the strongest moment. Final half bar is the title, and the last frame matches the first so it loops.
- **Start:** state the concept and show a beat-by-beat storyboard, then build.
- **Traps:** a tour of unrelated effects; corner labels and timecodes; text that overlaps during handoffs.
- **Study:** `stephanlivera-df17a2` (the original line), `templates/showreel` (the site's tested rewrite), `ultimaxbt-bbebf5` (one orange dot connects every scene), `techhalla-90b8ec`.

## 2. Product or launch film

The largest category. The weak version asks Claude to show off and uses the product as a backdrop. The strong version says what is on screen.

- **Device:** a through-line object taken from the product itself (its cursor, a key button, the mark in the logo, one data point). It starts in the UI, changes shape or role in each scene, and becomes the logo on the end card. Name it before storyboarding.
- **Direction:** research the product first (what it does, who it is for, real interface, brand) and use only what is found. Rebuild the real UI as vector layers so its parts can move alone; never slide a flat screenshot in. A cursor drives every interaction with real clicks and drags. The camera zooms so each moment fills the frame. Brand colours and typeface; the accent appears only on the through-line object and the key word.
- **Motion rules:** small spring overshoot at most; nothing appears from nothing; the camera never sits still (a push of about 4% across a scene, each scene starting at the zoom the last ended on); something changes on every beat.
- **Structure:** hook in the first bar, the problem in three to five words of large type that the object interrupts. Middle, three or four moments of the product at its best, each starting with the object becoming the next UI element and landing one readable idea. Payoff, the strongest moment on the biggest beat, then the object becomes the logo with the name and one line of call to action.
- **Ask for:** three to six screenshots of the real interface, the logo, brand colours and font, a track with a clear beat. Give each a default (capture them, take from the site, its own, compose one in code).
- **Traps:** invented features and numbers; a long product name that no longer fits a lockup sized for a short one; hard-coded positions that break match cuts.
- **Study:** `twoclipping-221cab` (one continuous take, liquid glass, real photos), `twoclipping-6dd14e` (real footage, masked type, match cuts), `ultimaxbt-2ddf1e` (colour floods from one object into the next), `rossaxbt-3085b7` (voiceover, glass UI, cuts on sixteenth notes), `lexnlin-038035` (research first, then an art direction with its own rules), `steventey-0d20e4` (the short prompt version, for contrast).

## 3. UI morph loop

One shape that never cuts, becoming a button, a loader, a player, a slider, a toggle, tabs, a chart, a command palette, a toast, and the button again.

- **Device:** every state is the same element changing size, radius and colour while its content swaps with a short blur.
- **Direction:** Dribbble-level UI motion on a quiet canvas, black and white components, one UI font. A cursor causes every change. The camera zooms so each state fills the frame. Last frame equals first.
- **Structure:** a tempo, a bar count, and the chain of states written as an arrow list. Something happens on every beat.
- **Build extras:** springs as closed-form step responses; a value retargeted many times is the sum of one spring per change. Give the two edges of a sliding indicator different springs so the leading edge stretches ahead. While the cursor holds a drag, compute the value from the cursor position; on release, spring back from wherever it was.
- **Ask for:** eight to twelve UI states, black and white or one accent, a track around 120 BPM.
- **Traps:** text swapping inside a morphing container needs its own enter and exit timing; the loop stutters unless cursor position and speed match across the seam.
- **Study:** `twoclipping-5cba86`, `rossaxbt-94583b` (a ball travels through one continuous layout), `demonugc-4c5753`.

## 4. Explainer on one diagram

Explainers have the shortest prompts in the gallery and show it. The fix is structural.

- **Device:** the whole explanation is one diagram in one continuous space. The camera zooms into a part to explain it and pulls back to show where it fits, so the viewer always knows where they are.
- **Direction:** say who it is for. Every idea gets a picture before it gets words. Labels sit on the thing they name, never in a legend. One thing moves at a time. Arrows and flows animate in the direction things really move. No more than seven words on screen at once, each held about a third of a second per word.
- **Structure:** hook, a question the viewer already has, asked over the first picture. Middle, three to five steps, each zooming into one part, showing one concrete example, then pulling back as that part locks into place. Payoff, a pull back to the finished diagram and a one-line takeaway.
- **Banned here:** walls of text, bullet lists, stock-looking icons, generic gradients, glows, crossfades.
- **Traps:** unchecked facts (no gallery explainer asked Claude to check them; always ask); a layout that reshuffles when the camera moves.
- **Study:** `alex-prompter-1ea044` (five scenes named in one sentence), `emollick-8661a8` (a structural idea in place of a scene list), `linearuncle-5d2bae` (Manim for mathematics), `kloss-xyz-fe0c31` (a timeline).

## 5. Narrated explainer

As above, but the voice sets the timing.

- **Build order changes:** write the narration script first, line by line, marking what is on screen for each line. Generate each line with a synthesised voice and measure its real length. Time the animation to those lengths. Mux narration, quiet music under it, and subtitles synced line by line.
- **Voice:** `edge-tts` is free and needs no key (`en-US-AriaNeural`; Hebrew `he-IL-HilaNeural`, `he-IL-AvriNeural`). ElevenLabs gives better delivery and needs a key. For word-level captions see `build-pipelines.md`.
- **Check:** a key frame from each section before the full render.
- **Study:** `1stnoel-c20a89`, `rossaxbt-3085b7` for voice handling at a high level of polish.

## 6. Character short

- **Device:** write the story first. One character with one clear want, three attempts that fail in different and escalating ways, a turn, an ending that lands, and a last-second gag.
- **Acting:** every pose reads in silhouette. Anticipation before each action and follow-through after. Squash and stretch on anything soft. The eyes move first and the body follows. Hold key poses for at least six frames.
- **Staging:** one action per shot, framed to read instantly. Cut on action, matching movement across the cut. Colour shifts with mood. Sound tells half the story.
- **Structure:** a shot list, one action per shot, with timings. Shots join through motion and sound.
- **Traps:** feet and hands sliding where they touch things; proportions drifting between shots; a gag with no beat of stillness before it.
- **Study:** `abderrahmen-g-9e8ed0` (hand-drawn inputs), `axtonliu-0b861d`, `loicrambo-ad6830`.

## 7. Real-time 3D

- **Device:** design the signature shot first, the one frame someone would screenshot, and build every shot toward it.
- **Camera:** a film camera, not orbit controls. One named move per shot (dolly, crane, orbit, push-in, rack focus), eased in and out, never passing through geometry.
- **Light and materials:** key, fill and rim light with soft shadows, an environment map, fog for depth, physical materials with varied roughness, ACES tone mapping. Nothing should look like a default material.
- **Motion:** things react to each other (what is hit moves, what is near lights up), driven by springs or simple physics, never linear tweens.
- **Banned here:** default materials and lighting, floating text labels, glows on everything, a slowly spinning object as the whole idea, anything that looks like a tech demo.
- **Structure:** an establishing wide, three to five shots with one camera move and one event each, the signature shot, a final wide that shows it in a new light.
- **Build:** one HTML file, three.js from a CDN, everything modelled in code. A `?render` mode where every frame is computed from time with seeded randomness, so it can be captured. One captured frame per shot, checked for anything flat, aliased, clipping or unreadable.
- **Study:** `templates/realtime`, `nft-chen-5f8bb0`, `gorden-sun-041f56` (beat-synced), `sayan-shanky-f850d8`.

## 8. Page fly-over

A real landing page laid flat and filmed in one move.

- **Device:** one continuous camera that never cuts: low over the hero, gliding down the page at a steady speed, rising overhead to show the whole page, diving back to land the hero as a card under a title.
- **Build:** load the live page in headless Chromium, scroll once so lazy content settles, mark the pieces that lift (cards, mockups, chips, photos), screenshot the page without them and each piece alone on transparency with its position. Draw the page as a textured quad and each piece as its own quad at its height. Drive the camera from one speed curve integrated into position, not from position keys. Depth of field per pixel, thin in front of the subject.
- **Banned here:** cuts, stops or surges in the glide, the camera turning sideways, zooming in and back out, text laid over the page before the end card.
- **Traps:** far text shimmers without mipmaps and anisotropic filtering; any change in a section's height shifts everything after it, so lock the page before timing; measure a quick preview to confirm the speed never dips.
- **Study:** `twoclipping-d89be5`, `ercankeskinx-ec2568` (scroll-driven sections), `pankajstwt-49978ed`.

## 9. Kinetic type bumper

Text is the animation.

- **Device:** one sentence or word set, with each word's motion meaning what the word says. Letters are individual elements.
- **Direction:** one typeface in one or two weights, large enough to crop at the edges. Type rises from mask lines, splits, stretches along a variable axis, or hands off letter by letter into the next word. Outgoing and incoming text get separate timing.
- **Structure:** words land on beats; a count of bars; an end lockup.
- **Traps:** measuring text before fonts load; animating letters in a right-to-left script in the wrong order (see `gotchas.md`); squeezing a wordmark without scaling letter widths so gaps open.
- **Study:** `shneural-2abdfa`, `techhalla-90b8ec`, `zheke-38deff`, `gdgtify-287ddf` (a speech built as architecture).

## 10. Data story

- **Device:** one number or one chart that the whole piece builds to. The line, bar or dot that carries the data is the through-line object.
- **Direction:** the chart draws itself in the direction the data moves. Axis labels are large and few. A value counts up only while the mark it describes is moving. One accent colour for the series that matters, grey for context.
- **Rules:** every figure comes from a source the person supplied or one that is cited; never round into a nicer number; no chart with more than about seven marks on screen.
- **Structure:** the question, the build-up of context, the reveal on the biggest beat, the takeaway.
- **Study:** `dale-vaz-cc612a` (trading terminal), `aistocksavvy-3fb9f5`, search `--tag charts`.

## 11. Recipe or process film

- **Device:** a physical sequence with a visible start and end. "Empty glass to finished drink" gives the film its structure before a frame is designed.
- **Direction:** the subject stays in one place throughout. Each ingredient and its measure appears as it goes in, in clean type beside the action. The camera eases in for the finish.
- **Structure:** one step per bar.
- **Banned here:** stock clip art, measurements you would have to pause to read.
- **Study:** `ror-fly-9950f1`, `sarut0bisasuke-cefa43`. For a topic that is not physical, find the sequence inside it: a request moving through a system, a number changing as each input changes, a timeline with a fixed number of stops.

## 12. Music-led edit and talking-head cut

- **Music-led:** analyse the track first for tempo, beat grid, energy per bar and the drop, and calibrate the grid to the real kick hits. Every cut sits on a downbeat, every UI hit on a beat. The biggest visual lands on the drop. Place each sound effect by its measured peak, not its file start.
- **Talking-head cut:** transcribe with word timestamps and make the cut list from the transcript. Captions follow the word table. Find the beat grid of any music and nudge cuts to it where it helps.
- **Rights:** only use music and effects whose licence allows the intended use.
- **Study:** `sab8a-364a5a` (clip edit), `gorden-sun-041f56`, `samaote-5e2fc2` (sung words timed), search `--tag music`.
