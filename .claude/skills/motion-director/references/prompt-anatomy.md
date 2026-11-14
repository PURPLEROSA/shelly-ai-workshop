# Prompt anatomy

The strongest prompts in the gallery, and every rewrite the site publishes, share one shape: up to six tagged blocks. Each block answers a question Claude would otherwise answer with a default. Length is a side effect; a block that decides nothing should be cut.

## Contents

- The six blocks
- Skeleton to fill
- The dials: creativity, pace, polish
- Format and length
- Upgrading a one-line prompt
- Writing habits that pay

## The six blocks

| Block | Question it answers | Must contain |
|---|---|---|
| `<inputs>` | What do you need from me? | What to ask for, each with a default if skipped. Makes the prompt reusable for any product. Leave out when the piece needs nothing. |
| `<direction>` | What is it and how should it look and move? | Length and format. The concept in one line. Typeface, palette, canvas. Motion rules. The banned list. |
| `<structure>` | What happens when? | Tempo and bar count. Hook, middle, payoff, or a shot list. For product films, the named moments in order. |
| `<build>` | How are the frames made? | Renderer and size. The pure-function-of-time rule. Easing and springs. Sound. Motion blur. The check before the full render. |
| `<gotchas>` | What goes wrong on this kind of piece? | Three to six specific traps, each with its consequence ("or the loop stutters"). Only ones that apply. |
| `<start>` | What happens first, and what do I get? | What to show before building (concept, storyboard, stills) and whether to wait. The deliverable. |

Creators who add voice or a real music track split out more blocks: `<script>`, `<voice>`, `<sound>`. Use them when those parts carry real instructions.

## Skeleton to fill

Replace everything in square brackets. Drop a block that has nothing to decide.

```
<inputs>
Ask me for anything below I haven't given you; if I skip one, use its default:
[asset or fact] (default: [fallback]), [asset or fact] (default: [fallback]).
</inputs>

<direction>
A [length]-second [kind of video] for [subject], [format and pixel size].
Concept: [the one idea every shot grows out of]. Name it in one line before you storyboard.
[How scenes connect: what the shared element is and what it becomes.]
Look: [canvas colour], [one typeface], [one accent colour and what it is reserved for].
Motion rules: [springs and overshoot limit]; [how things enter]; [what the camera does]; [what changes per beat].
Banned: [five to nine named effects], anything that looks like a template.
</direction>

<structure>
[BPM], [bars]. Write a timed storyboard first, beat by beat, then build exactly that.
Hook: [first bar]. Middle: [the moments, in order]. Payoff: [the strongest moment, then the end card].
</structure>

<build>
1. One HTML file at [W]x[H]. Every style is computed from time inside window.seek(t): no CSS animations, no timers, no state between frames.
2. Springs and easing written as functions of time. [Any technique this piece depends on.]
3. Sound: [a soundtrack written in code, or a real track analysed for its beat grid].
4. Render with Playwright at 60 fps, [3] subframes per frame blended for motion blur, then mux the audio.
5. Before the full render, make one still per beat on a contact sheet and fix anything cramped, empty, overlapping, off the beat or hard to read.
</build>

<gotchas>
[Trap, and what happens if ignored.] [Trap.] [Trap.]
</gotchas>

<start>
Show me [the concept / what you found / the storyboard / N stills], then [build without asking anything else | wait for my go]. Give me the final MP4.
</start>
```

Two `<start>` styles exist and they suit different people. "Show the storyboard, then build without asking" suits a one-shot run. "Ask for the inputs, show the beat map and four stills, wait for my go" suits a piece that matters; it costs a pause and saves a wasted render.

## The dials: creativity, pace, polish

The site's customise tool exposes three sliders. They translate into prompt lines:

| Dial | Low end | High end |
|---|---|---|
| Creativity (safe to wild) | Keep to the recipe's concept device. Conventional layouts. | Ask for three unrelated concepts first, one of them uncomfortable. Allow one rule to be broken on purpose and say which. |
| Pace (calm to frantic) | 90 to 100 BPM, one change per bar, holds allowed where there is something to read. | 128 BPM and up, changes on eighth or sixteenth notes in named runs, no hold over a quarter second. |
| Polish (quick to obsessive) | One still per beat, then render. | Contact sheet, strips on every transition, a low-quality preview, a pop scan, and a second pass on anything flagged. More subframes. |

Polish costs the most. Say which level is wanted before starting.

## Format and length

Name both. Most launch prompts in the gallery never state a format and get landscape by default.

| Use | Size |
|---|---|
| Landscape, sites and X | 1920x1080 |
| Vertical, Reels, TikTok, Shorts | 1080x1920 |
| Square, feeds | 1080x1080 or 1440x1440 |
| Portrait feed | 1080x1350 |

Length: 15 seconds suits a showreel or teaser, 20 to 30 a launch film, 30 to 60 an explainer at about five seconds per idea. At 120 BPM a bar is two seconds, so 15 seconds is seven and a half bars.

## Upgrading a one-line prompt

Given something like "make a dynamic 15-second motion graphics video for [product], go all out":

1. Find out what kind of video it is and pick the recipe in `archetypes.md`.
2. Replace "dynamic" with a tempo and "something changes on every beat".
3. Replace "go all out" with a concept device and a banned list.
4. Replace the product name alone with the promise in one line and three to five real moments to show, in order.
5. State the look: hex colours, one font, light or dark.
6. Add the build block and the still-per-beat check.
7. State the ending: logo, URL, or one line of copy.
8. If it should be reusable, turn the specifics into an `<inputs>` block with defaults.

Keep what the original author cared about. If their line said "avoid text in the corners", that goes into the banned list in their words.

## Writing habits that pay

- **Say what to do instead.** "No crossfades: every scene grows out of the one before" works where "no crossfades" alone does not.
- **Give numbers.** "Push from 1.0 to 1.04 across a scene" beats "subtle camera movement". "At least 0.3 s" beats "not too fast".
- **Name the thing that connects scenes** and trace its path in the structure block: where it starts, what it becomes in each scene, where it ends.
- **One line of structure per moment**, in order, with what happens on screen. A sequence with a visible start and end (empty glass to finished drink) gives the video its shape before any design.
- **End the banned list with the standard**, "anything that looks like a template", so effects you did not think to name get the same scrutiny.
- **Ask for evidence.** "Show me the frames" rather than "is it fixed?".
- **For anything factual**, add "research it first; never invent numbers, names or quotes", then check the result yourself.
- **Say who it is for.** One line about the audience sets vocabulary, pace and what needs explaining.
