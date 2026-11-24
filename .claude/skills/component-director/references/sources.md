# Sources

## Where this comes from

Everything here was learned from [Scrolltide's component gallery](https://www.scrolltide.co/components): 132 single UI pieces, each shown as a short preview clip with a name, a category and a one-paragraph description. Scrolltide sells the prompt behind each piece. The gallery page says the components are included with its Yearly and Lifetime plans, and that each is a single prompt to paste into Claude, Cursor or v0.

How the study was done, on 24 November 2026:

- The public gallery page was loaded once. It lists every piece with its name, category, tags, description and a link to a public preview clip. The page data marks every piece as a paid-tier item and carries no prompt text and no source code for a visitor who is not signed in.
- All 132 preview clips were downloaded from the public links and watched as contact sheets, three frames each.
- After that first page load the site's firewall refused further automated requests from this environment. Nothing else was fetched and no way around the block was tried. The pricing, terms and other sections of the site were therefore not read.

## What is stored here and what is not

- **Stored:** the method and recipes in this folder, written fresh; the scripts and the kit; three original example pieces; and `data/gallery-index.json`.
- **In the index:** per piece, its name, slug, category, date added, the site's own public tags, the length and link of its public preview clip and poster, and four labels worked out here from watching the clip: `job`, `material`, `family`, `gestures`. `tech` is derived from the site's tags.
- **Not stored:** Scrolltide's descriptions, its prompts, or any of its code. The descriptions are the site's copy and are one click away. The prompts and code are the paid product and were never seen.
- **Not done:** no gallery piece is rebuilt here. The three examples have their own jobs, things and content; they share families with gallery pieces, as any two carousels share a ring.
- **If someone wants an exact gallery piece:** it is Scrolltide's to sell. Point them to the gallery. Their prompt, pasted into a session with this skill loaded, can then be built and probed like any other.

## The gallery in numbers

Counted from the index. Labels marked * were assigned here by watching the clips, so they are a reading, not the site's own classification.

| | |
|---|---|
| Pieces | 132, added between 31 August and 20 November 2026 |
| By month | August 4, September 22, October 40, November 66 |
| Site categories | Card 57, 3D 23, Button 18, Background 10, Input 9, Navigation 6, Text 5, Loader 4 |
| Stack, from site tags | WebGL 64 (10 of them three.js), CSS 36, canvas 2D 10, SVG 7, CSS 3D named on 6; not stated for 19 |
| Gestures* | drag 65, click 46, hover 27, pointer position 24, plays by itself 21, scroll 16, fling 13, hold 6, type 4 |
| Preview length | 5.7 to 29.1 seconds, median 11.7 |

**Jobs*:** carousel 24, card 16, gallery 12, button 10, background 10, toggle 9, text 5, then one to three each of dashboard, slider, testimonial, object, ticket, picker, loader, nav, deck, tabs, intro, slideshow, list, steps, accordion, upload, chart, timer, footer, product, chat, filter, pricing, tree, consent, password, trail and frame.

**Materials*:** none 28, photographs only 28, paper 14, glass 10, light 9, grain 8, liquid 7, fire 5, creature 5, rope 4, machine 3, ink 3, plant 3, pixel diorama 3, sky 2. So 76 of 132 pieces are built on a named material.

**Families*:** rail 18, ring 15, world 14, field 13, physics 11, expand 10, fold 10, mask 10, lens 10, story 9, sdf 8, glyph 7, morph 6, fluid 5, scroll 5, light 4, stack 3, object 3, camera 1. Thirty pieces carry two.

## The shift inside it

The gallery divides evenly at the start of November, and the two halves are different kinds of work.

| | Before November (66) | November (66) |
|---|---|---|
| Most common families* | rail 13, ring 11, field 9, expand 7, mask 7 | world 14, fold 10, sdf 8, story 7, physics 6, lens 6 |
| Most common jobs* | carousel 17, card 9, gallery 9, background 9 | toggle 9, carousel 7, card 7, button 6 |
| A named material* | 24 of 66 | 52 of 66 |
| WebGL | 21 | 43 |
| CSS, with no canvas or WebGL | 25 | 8 |

The earlier half arranges things and moves them: strips, wheels, pointer fields. The later half turns a plain control into an object with a state: every toggle, every piece whose control is a scene, every paper fold and every raymarched object is from November. This skill follows the later half, and `references/conceit.md` is built on it.

## Skills beside this one

- `motion-director` covers video. A piece built here can be filmed there: its `scrub(p)` is the same idea as a film's `seek(t)`.
- `html-demo` builds a product demo window that plays an app step by step. Its pointer script could drive a piece built here.
