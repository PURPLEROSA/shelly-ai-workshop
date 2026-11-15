# Build pipelines

Claude does not produce pixels. It writes code that draws each frame, and a renderer turns that into an MP4. Every approach that works does the same thing underneath: a headless browser loads the animation, moves it to an exact time, takes a screenshot, repeats for every frame, and ffmpeg encodes the result. Because frames are computed from time rather than played live, a slow machine cannot drop frames or drift off the beat.

## Contents

- Choosing a renderer
- The seek(t) contract
- Springs and easing
- Camera
- Shared-element handoffs
- Motion blur
- Sound written in code
- A real music track
- Voice and captions
- Footage and images
- Fonts
- Using the scripts
- Without a machine to run code on

## Choosing a renderer

| Situation | Use | Notes |
|---|---|---|
| Simplest setup, any web technique | One HTML file plus Playwright and ffmpeg | The most common approach in the gallery and behind most of its best-liked entries. The prompt must state the build method. This skill's scripts implement it. |
| The product is built in React | Remotion | Reuses real components and styles. Each scene is a component reading the frame number. Check Remotion's licence terms before commercial use; some companies need a paid licence. Skill: `product-film` or `cinetic`. |
| A ready renderer without React | HyperFrames | Open source (Apache 2.0), from HeyGen. The video is HTML with data attributes; works with GSAP. Skills: `cinetic`, `session-story`. |
| Real 3D with light and a moving camera | three.js, captured the same way | Add a `?render` mode computed from time. Adds complexity that flat motion does not need. |
| Mathematics | Manim | A Python library made for it. |
| Frames drawn in Python | Pillow and numpy, ffmpeg | Every frame a function of time. Skill: `generative-film`. |

Name the choice in the prompt. Left open, Claude picks a different method each run and results are hard to repeat.

## The seek(t) contract

```
window.FILM = { width, height, fps, duration, bpm }
window.seek(t)           // set every style for time t in seconds; may be async
window.renderAudio()     // optional: return the soundtrack as a base64 WAV
window.ready             // optional: a promise that resolves when fonts and assets are loaded
```

Rules that make it deterministic:

- `seek(t)` reads nothing but `t` and constants. No CSS transitions or animations, no `setTimeout` or `requestAnimationFrame` inside the film logic, no variable that remembers the previous frame.
- Any frame can be drawn on its own. Typed text is "the part typed by time t", not an accumulating string.
- Randomness is seeded. Never `Math.random()`.
- Declare every variable before the first `seek()` call. Measure text and element positions once, after `document.fonts.ready`.
- If `seek` loads images or video frames, it awaits their decode before returning.
- The live preview loop runs only when the page is not in render mode (`?render`).

`scripts/seek-starter.html` implements all of this and is the place to start.

## Springs and easing

Write motion as functions of time.

- **Spring as a step response.** A damped spring going from 0 to 1 has a closed form in `t`, so it needs no simulation. The starter's `spring(t, { f, z })` takes a natural frequency in Hz and a damping ratio. `z` of 0.8 to 1 settles cleanly; below 0.6 is bouncy.
- **Many targets.** A value that changes target several times is the start value plus one spring per change, each scaled by the size of that change. `track(t, start, [[time, target], ...])` does this and stays a pure function.
- **Stretch.** Give the two edges of a moving shape different springs so the leading edge runs ahead and the shape stretches in flight. Works for tab indicators, toggle knobs and pills.
- **Direct manipulation.** While a cursor holds a drag, the value comes from the cursor position. On release it springs back from wherever it was.
- **Exits** use an ease-in (the thing accelerates away). **Entrances** use a spring or an ease-out.
- **Blur follows speed** and direction on fast moves, if blur is drawn in the page rather than by subframes.

## Camera

- One transform on a container that holds the whole world. Lay all components out in one space and make each close-up a move through it.
- Key it as `[time, zoom, x, y]` with eased segments. Interpolate zoom in log space, or pushes feel uneven.
- Keep it drifting: about 1.0 to 1.04 across a scene. Start each scene at the zoom the last one ended on, or the zoom snaps at the handoff.
- One eased move per scene. Never zoom in and straight back out.
- For a continuous glide, drive the camera from one speed curve and integrate it into position. Position keys every half second produce surges.
- Scale the cursor with the camera.

## Shared-element handoffs

The transition is part of the idea, not a gap between ideas.

- The outgoing scene and the incoming scene share one element: the button carries its label into the page it opens, a flood of colour carries a copy of the words it grew from.
- A flood must overscale past the farthest corner and take about 0.3 s. Shorter reads as a flash; too small leaves a corner uncovered for a frame.
- Text inside a morphing shape needs its own mask and its own exit and entry timing.
- Never let the through-line object teleport. Show the path of every handoff.

## Motion blur

Render several subframes per output frame at slightly different times and blend them.

- Three subframes suit most pieces. Fast camera moves need eight; four can leave ghost copies, in which case use eight and slow the move.
- `scripts/render.mjs --subframes N --shutter 0.5` spreads the subframes across half a frame, centred on the frame time, and blends with ffmpeg `tmix`.
- Motion blur multiplies render time by the subframe count. Preview without it.

## Sound written in code

Good when no track is supplied. Render offline with the Web Audio API (`OfflineAudioContext`), so no audio device is needed and the sound is locked to the same clock as the picture.

- A kick on every beat, a riser into the last full bar, a hit on each scene change.
- For explainers, a soft pulse under each step and a hit as each idea lands.
- Keep note and hit times in the same table the animation reads.
- The starter's `renderAudio()` shows the pattern and returns a WAV that `render.mjs` muxes in.

Claude cannot hear the result. It can measure loudness and timing only.

## A real music track

- Analyse the file first (numpy is enough): tempo, beat grid, energy per bar, where the drop is. Calibrate the grid to the real kick hits rather than assuming a constant tempo from the first beat.
- Start on a downbeat. Put every cut on a beat or half-beat and the strongest visual on the drop.
- One sound effect per event (click, key, whoosh, landing, impact). Place each so its measured peak, not the start of its file, lands on the event. Trim around the peak; many risers are seconds long.
- Under a voice, duck the music. Aim for the voice to sit clearly above the music in the speech band.
- Normalise the final mix to -14 LUFS (`render.mjs --loudnorm`).
- Use only music and effects licensed for the intended use.

## Voice and captions

- Write the script first and adapt every line to the product. Mark what is on screen for each line.
- `edge-tts` is free and keyless. ElevenLabs gives more control over delivery; generate several takes of the full script, let the person choose, and regenerate single lines that miss rather than the whole read. Emotion tags are easy to overuse.
- Tighten long pauses and even out phrase levels before timing anything to the read.
- For word-level captions, transcribe with word timestamps. A single pass over a long read can place words late; splitting at pauses and transcribing each segment keeps them aligned. Captions typed word by word must follow that table.
- Time the picture to the real audio length of each line, never to an estimate.

## Footage and images

- For video inside a film, extract it to an image sequence at the film's frame rate and swap the image source per frame, awaiting decode. Seeking a `<video>` element frame by frame is unreliable; if it must be used, re-encode all-intra and wait for the `seeked` event.
- Screenshots of a real page: capture at device scale 2 after scrolling once so lazy content loads.
- Use real photos the person owns or licensed ones. Never placeholder cards.

## Fonts

- Load the font in the page and await `document.fonts.ready` before measuring or rendering. A fallback font changes every measured width.
- One typeface. A variable font lets a wordmark squeeze or stretch along its width axis.
- Offline or sandboxed renders cannot reach font CDNs. Ship the font file beside the HTML and reference it with `@font-face`.

## Using the scripts

```
node scripts/stills.mjs film.html --out sheet.png             # one still per beat
node scripts/stills.mjs film.html --out strip.png --strip 4.3 # every frame around 4.3 s
node scripts/render.mjs film.html --out preview.mp4 --preview # half size, 30 fps, no blur
node scripts/render.mjs film.html --out film.mp4 --loudnorm   # 60 fps, 3 subframes, audio
python3 scripts/popscan.py film.mp4                           # pops, jumps, holds, empty frames
```

A six-second 1080p60 film with three subframes renders in under a minute on a small cloud machine; scale that by length and subframes. In a Claude cloud session Chromium and Playwright are already installed. If a project pins another Playwright, set `CHROMIUM_PATH` to the browser binary.

Read the contact sheet as an image and act on it. Then pull strips around each transition and anything `popscan.py` flags.

## Without a machine to run code on

In a chat with no code execution, only a live preview is possible. Say so at once: the page can play in a browser, and the MP4 needs a session that can run Playwright and ffmpeg, such as Claude Code.
