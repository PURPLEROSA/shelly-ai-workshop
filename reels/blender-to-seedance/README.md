# Blender previz -> Seedance 2.5 one-take reel

A 30-second, 1080x1920 split-screen reel: a cast reference strip on top, the Seedance 2.5 render in the middle,
the Blender grey-box previz it was driven by underneath, and the tool marks bottom-right.

- `blender/onetake.py` builds the whole city blockout and the one-take camera path procedurally and renders it with
  Blender's Workbench engine (`pip install bpy`). `blender/onetake.blend` is the same scene with baked keyframes.
  - stills: `python blender/onetake.py -- --mode stills --times 0,4.9,11.9 --res 640x360 --out out/stills`
  - frames: `python blender/onetake.py -- --mode anim --start 0 --end 899 --out out/frames` (resumable)
  - `blender/make_tex.py <out_dir> <font.otf>` regenerates the fictional billboard art in `blender/tex/`.
- `previz.mp4` is the rendered previz (1280x720, 30 fps). It is the `reference_videos` input for Seedance 2.5.
- `seedance_prompt.txt` is the prompt; the six cast images go in as `reference_images`
  (16:9, 720p, 30 s, audio on).
- `layout/compose.sh <previz.mp4> <out.mp4> [seedance.mp4|-] [thumb1 ... thumb6]` assembles the final reel
  (needs `ffmpeg`, `node` + `playwright`, and the Inter font). With `-` the top panel is a placeholder.

## Roller one-take (Venice Beach / LA, morning to sunset)

Second scene, same pipeline: `blender/rollertake.py` (and `blender/rollertake.blend`) is a rollerblade one-take. It opens
on a top view of the boardwalk, corkscrews down and whips a full circle round the skater, slides under her kerb jump,
orbits a 360 spin, pushes in and out through a supermarket (orange avalanche, a can of zero-sugar cola dropping into her
hand), and ends at sunset in the SHOTCALLER garage yard, where she grabs a police cruiser and is towed away up the coast
road while the camera cranes up. `roller/previz.mp4` is the render and `roller/seedance_prompt.txt` the matching prompt.

An earlier ending, where a police helicopter lifts her off the road, is kept as `blender/rollertake_helicopter.py`,
`roller/previz_helicopter.mp4` and `roller/seedance_prompt_helicopter.txt`.

Light-pink layout with a name and logo tiles:
`OVERLAY=overlay_pink.html NAME="Shelly Or Gisser" layout/compose.sh roller/previz.mp4 out.mp4 [seedance.mp4|-] ref1 ref2 ref3 ref4`
