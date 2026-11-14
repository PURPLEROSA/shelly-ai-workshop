# The plan, check, fix loop

A strong prompt is not enough. The first render is rarely the finished one, and a review that only asks Claude to "look at its frames" still misses empty frames, tiny text and long holds. What works is a loop in which each step catches problems while they are cheap: plan before anything is built, check the plan as stills, check the motion, then fix one thing at a time.

## Contents

- Before anything is built
- Stills before the render
- Motion
- Asking for a fix
- Symptom to prompt line
- Cost and session hygiene
- What cannot be judged from frames
- Lines to add to any prompt

## Before anything is built

Ask for the plan and wait for it.

- **Three different ideas, one still each.** It costs a fraction of a build, and the idea is what separates a good video from a great one. Three versions of one idea are not three ideas.
- **The asset list.** Every screen, logo and image the video needs and where each comes from. Anything missing is a question for the person.
- **A beat table.** One row per beat: time, what is on screen, what moves, and why the beat is there. The last column does the most work. If there is no reason for a beat, it does not belong in the video.

| Time | On screen | What moves | Why it is there |
|---|---|---|---|
| 0 to 2 s | The problem, in five words | Words land one by one on the beat | Names the pain |
| 2 to 4 s | The product panel, full frame | The last word becomes the panel's title | The answer is made out of the problem |
| 4 to 6 s | One action, very large | The camera pushes into a single control as it changes | The one feature people remember |

Save the chosen idea, the asset list and the beat table to files.

## Stills before the render

One still from the middle of each beat, all on one contact sheet (`scripts/stills.mjs`). A problem found on the sheet costs one edit; found after the render it costs a render as well. Look for:

- one focal element per frame, at least half the frame's width
- words readable on a phone: 32 px or more at 1080p
- nothing in the corners
- even spacing in anything laid out as a group
- a new layout on every still, never the same one twice in a row
- no two pieces of text overlapping, no element leaving a sliver at an edge
- no frame that is empty or holds one small thing

## Motion

Stills cannot show whether a transition is smooth or lands on the beat. One frame a second shows before and after, never how.

- For each transition, render every frame from 0.3 s before to 0.3 s after as one strip (`stills.mjs --strip <time>`).
- Scan the render for single-frame pops, where one frame jumps out of place (`popscan.py`). Only intended runs of fast cuts may jump; pass them with `--allow`.
- Watch a quick low-quality preview at full speed before the final render (`render.mjs --preview`).
- If the piece loops, compare the first and last frame.

## Asking for a fix

Name the second it happens and say what should happen instead. How the fix is asked decides how many rounds it takes.

| Weak | Strong |
|---|---|
| "The transitions feel off." | "At 18.3 s it cuts from the Copied button straight to an empty chat box. Nothing connects them." |
| "Make it smoother." | "The text above the button lifts off, arcs into the chat box and grows to the box's text size as it lands." |
| "Is it fixed?" | "Show me every frame from 18.0 to 19.0 s." |

Three habits save the most rounds:

- **Change one thing at a time.** With several fixes in one request you cannot tell which change did what, and a fix in one place can break another.
- **Protect what works.** "Do not change anything from 2.9 s on."
- **Ask for evidence.** A claim that it is fixed can be wrong. Frames and measurements cannot.

When acting on a fix request as Claude: change only what was named, re-shoot the strip or still that proves it, and report what the frames show, including anything still wrong.

## Symptom to prompt line

| You see | Say |
|---|---|
| Small things floating in big empty frames | The focal element spans at least 60% of the frame's width. Crop at the edges rather than shrink to fit. |
| Two pieces of text overlap for a few frames | Exits before entries: the old text is gone before the new text appears. |
| Scenes cut or fade into each other | At [time], [element] leaves [scene A], travels into [scene B] and becomes [its role there]. |
| Everything moves in lockstep | Durations, delays and speeds vary from element to element. Never equal staggers. |
| Bounce on everything | Smooth settles, no bounce or overshoot. |
| Things appear from nowhere | Nothing simply appears: it grows, slides in from an edge or is revealed by a mask. |
| Stutter, or a render that differs from the last | Compute every frame from time. No CSS animations, timers or unseeded random numbers. |
| Cuts that miss the beat | Map the track's beats from its audio first, and put every cut on a beat or half-beat. |
| The zoom snaps between scenes | Start each scene at the zoom the previous one ended on. |
| Text goes soft while the camera moves | Remove will-change from anything the camera scales. |
| Ghost copies on fast moves | Render eight subframes and slow the move down. |
| A colour flood flashes | The flood reaches the farthest corner and takes about 0.3 s. |
| The loop stutters | First and last frame match, including cursor position, speed and direction. |

## Cost and session hygiene

Prompt Motion's own test runs with Claude Opus in Claude Code, at API prices: a full 30-second video took about $14 to $15 and 1.5 to 2 hours. Three ideas with a still each cost about $3. Most of the rest goes on fixes, and long sessions make fixes dearer because the whole conversation is re-read with every message: three polish rounds in one session cost $5.83, then $9.69, then $13.48.

So:

- Keep the plan, the beat table and decisions in files.
- Start a fresh session for each round of fixes and point it at those files.
- Review on one contact sheet rather than dozens of separate images.
- Preview at half size without motion blur; pay for the full render once.

Figures are theirs and will vary with length and rounds; treat them as an order of magnitude.

## What cannot be judged from frames

- **Sound.** Loudness and beat positions can be measured. Whether the music fits or an effect is harsh cannot. The person should listen, ideally with eyes closed.
- **How motion feels.** Frames show that something moves smoothly, not whether it feels right. When Claude and a motion designer ranked the same thirteen videos they agreed only moderately, and Claude could not tell competent from great.

Say this when delivering, and ask the person to watch every render at full speed and describe what they feel in terms that can be acted on (a time, an element, what it should do).

## Lines to add to any prompt

- **Plan first.** Before building: three different ideas with one still each, the asset list, and a beat table with a reason for every beat. Wait for my go.
- **Check before the render.** A contact sheet with one still per beat and a strip around each transition. Fix anything cramped, empty, overlapping, too small or hard to read, show me both, and wait for my go.
- **Keep decisions in files** so a fresh session can pick up.
- **Fix one thing at a time.** Change only what I named and show me the frames that prove it.
