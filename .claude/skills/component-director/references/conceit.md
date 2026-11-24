# Finding the idea

A piece is remembered for one thing. The work here is to find that thing before any code, and to throw away the candidates that only look like ideas.

## The sentence

> A **[job]** that is a **[thing]**: **[gesture]** and **[what happens]**, while **[what else changes]**.

- **Job**: what the piece does on a page, in the plainest word. A switch, a file upload, a progress bar, a pricing table.
- **Thing**: a physical object or scene with a material. A match and striker, a thermal printer, a window with blinds.
- **Gesture**: what the hand does to that thing. It comes from the thing, not from the job.
- **What happens**: the physical result, which is also the job getting done.
- **What else changes**: one consequence outside the control. The room goes dark. The page floods. The wording changes.

Three of this skill's examples, as sentences:

- *A model-temperature slider that is a thermometer: push the mercury up and the sentence above it loses its composure, letter by letter, while its wording drifts from fact to rumour.*
- *A loader whose context window is a window: tokens print in, the tape climbs and the oldest lines leave over the sill, while three counters keep the honest numbers.*
- *A done-list that is a desk spike: reach for the pile and the slips fan open around the pin; pick one and it lifts off and lies flat, while the rest fold back.*

## What the strongest reference pieces share

Read off the 132 previews, not from anyone's prompt. The gallery splits in half by date, and the halves differ. The 66 pieces added before November 2026 are mostly layouts that move: strips, rings and pointer fields, 42 of them with no material beyond the photographs they carry. The 66 added in November are mostly controls that are objects: all 9 toggles, all 14 pieces where the control's state is a whole scene, all 10 paper folds, all 8 raymarched objects, and 52 of 66 name a material. The second half is the direction worth following.

1. **The job is ordinary.** A dark-mode switch, a cookie banner, a password field, a date picker. The more ordinary the job, the more room the idea has.
2. **The state of the control is the state of the scene.** The switch's progress is the hour of the day in the room behind it. Password strength is how armoured the tortoise is. The drink logged is the level in the glass. There is one number, and both the control and the picture read it.
3. **The gesture belongs to the thing.** Strike, peel, wind, tear, pluck, pour, crumple, fling. Each brings its own physics for free: a struck match catches, torn paper gives one perforation at a time, a flung dial coasts and lands on a station.
4. **You can stop half way.** The knob drags, and dragging scrubs the whole change. Nothing snaps between two pictures.
5. **Something outside the control answers.** The whole page floods dark; the sign changes to NO VACANCY; the sea behind the receipt printer changes hour.
6. **One honest or funny beat.** A sync bar that stalls like a real sync. A paint crew that stops at 99% to watch it dry. Never more than one.
7. **The content is real.** Plausible names, routes, prices and times in the product's own voice. The small caption under the control changes with the state.
8. **It sits alone on a quiet stage.** One piece, 30 to 60 percent of the width, a near-black or warm paper ground, one typeface, a lot of air.

## Materials, their verbs, and what they are good at showing

| Material | Verbs | Maps naturally to |
|---|---|---|
| Liquid | pour, fill, slosh, splash, drip, merge | amounts, levels, progress, anything that joins or splits |
| Glass | refract, magnify, frost, fog, clink | selection (a lens over the chosen thing), privacy, focus |
| Paper | fold, peel, tear, crumple, stack, stamp, unroll | documents, tickets, pricing, reveal and discard, lists |
| Fire | strike, catch, burn, char, smoulder | destructive or irreversible actions, timers, warmth |
| Light | switch, dim, flicker, sweep, cast a shadow | on and off, themes, attention, time of day |
| Ink | flood, bleed, drip, stretch, stain | emphasis, filters, hover fills, anything that spreads |
| Grain (sand, dust, dots, particles) | scatter, assemble, sift, erode | forming and dissolving, deletion, loading from nothing |
| Rope, cable, cloth | sag, swing, pluck, tangle, plug in | connections, wiring, galleries that hang, elastic edges |
| Pixel diorama | a tiny lit scene inside the control | toggles and progress that tell a small story |
| Creature | watches, leans, blinks, eats, grows, dozes | fields that feel judged or boring: passwords, consent, empty states |
| Machine (watch, lens, radio, printer, synth) | wind, tune, zoom, print, click into a detent | precise values, ranges, anything with a mechanism to learn |
| Plant | grow, branch, bud, wilt | trees and hierarchies, streaks, slow progress |
| Sky and weather | dawn to dusk, clouds, rain, tide | themes, time, long waits |

Pick the material for what the number means, not for how it looks. A level wants liquid; a hierarchy wants a plant; an irreversible action wants fire.

## Finding open ground

`python3 scripts/gallery.py gaps` prints job against material with a count where the gallery already has a piece and a dot where it has none. 181 of 208 pairs were empty when the index was built. A pair is a start, not an idea; it still needs the gesture and the consequence.

Better ground than the grid is the product itself. Take its own nouns and ask what each would be as an object:

- An agents workshop gave *temperature* (a thermometer), *context window* (a window), and *done while you slept* (slips on a spike).
- An invoicing tool has *due*, *paid*, *overdue*, *reminder*. Overdue is a stamp; paid is a hole punch through the slip.
- A booking tool has *slots*, *holds*, *waitlist*. A hold is a coat on a chair.

Write three sentences that differ in material and gesture, not three wordings of one. Sketch one still for each. Choose with the person.

## Five tests

Run them on the sentence, before building.

1. **Stranger.** Read only the sentence to someone. Can they picture it and say what the gesture is? If they need a second sentence, the idea is two ideas.
2. **Removal.** Take the thing away and keep the behaviour. Does anything still need explaining? If the behaviour is just "it toggles with a nice animation", the thing was decoration. In a real idea the thing explains the behaviour: it stalls *because* paint dries.
3. **Half way.** What does 50% look like? If there is no good answer, there is no number, and it will be a two-state jump.
4. **Tenth time.** The main response should be done in about 600 ms and never block the next action. Would this still be pleasant on the tenth use today? Long theatre belongs to loaders and one-off moments, not to a switch someone flips daily.
5. **Job.** With motion off and the picture frozen, does it still do the job and say what state it is in?

## Staying original

Ideas and mechanisms are free to learn from. A specific piece is not free to rebuild: if someone who knows the gallery would say "that is their match-strike switch", it is a copy whatever it is called. Take the family (control state is a scene; cards on one pivot), then bring a different job, a different thing and the person's own content. When a person asks for an exact gallery piece, tell them the prompt for it is part of Scrolltide's paid plans, and offer a piece of your own for the same job.
