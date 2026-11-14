# Sources

## Where this comes from

Everything here was learned from [Prompt Motion](https://prompt-motion.com), a free gallery of motion graphics videos made with Claude, each shown beside the prompt or skill that made it. It is curated by [@p4nthera_](https://x.com/p4nthera_) and started in October 2026. Every entry credits its creator and links to their post on X.

What is stored in this skill and what is not:

- **Stored:** the method, written fresh (the references in this folder); working scripts; and `data/gallery-index.json`, which holds metadata only (title, creator, tags, stack, links, word count, and flags worked out from each prompt).
- **Not stored:** the prompts. They belong to their creators, and the site asks AI systems to treat its content as reference rather than reproduce it. `scripts/gallery.py fetch <slug>` reads one prompt from its page when it is wanted, with the credit attached.
- **When sharing** something made from a creator's prompt, credit them and link the entry.

Index built on 14 November 2026 from the site's sitemap and its `llms.txt`. Ranks follow the gallery's own popularity order on that day.

## The gallery in numbers

Counted from the index on the day it was built.

| | |
|---|---|
| Entries | 240, all made with Claude Opus |
| With a prompt | 235 (one of them also ships a skill) |
| Skill only | 5 |
| Median prompt length | 26 words; 161 prompts are 30 words or fewer, 6 are over 1,000 |
| Prompts with a banned list | 17 |
| Prompts with a beat grid | 16 |
| Prompts that ask Claude to check its own frames | 13 |
| Prompts with an inputs block | 12 |
| Entries that name a rendering stack | 61 of 240 |

Tags: Product UI 107, Kinetic type 100, Music 51, Shapes 43, Particles 43, Charts 34, Diagrams 31, Characters 27, Phone 23, Photos 23, Code 21.

Families, by which of the site's rewrite templates fits: product film 82, showreel 73, character short 12, explainer 8, narrated explainer 8, real-time 3D 5, creator-structured (the creator wrote a full blocked prompt) 13, other 39.

Stacks named by creators: Remotion 13, plain HTML, canvas or JavaScript with or without Playwright about 25, HyperFrames 11, three.js 5, and one each of Manim, Blender, Python with ffmpeg and others.

## The site's own guides

Worth reading in full when a job leans on one topic:

- [How to get Claude to fix its motion graphics: plan, check, fix](https://prompt-motion.com/blog/fix-ai-motion-graphics-with-claude)
- [AI motion graphics prompts: what 230 real examples show](https://prompt-motion.com/blog/ai-motion-graphics-prompts)
- [Why AI motion graphics look AI-made, and the prompt lines that fix it](https://prompt-motion.com/blog/make-ai-motion-graphics-look-less-ai)
- [How to prompt an AI launch video: lessons from 92 real prompts](https://prompt-motion.com/blog/ai-launch-video-prompts)
- [AI explainer video prompts: what 27 examples get right and wrong](https://prompt-motion.com/blog/ai-explainer-video-prompts)
- [Remotion vs HyperFrames vs plain HTML for AI motion graphics](https://prompt-motion.com/blog/remotion-vs-hyperframes)

Templates written by the site, free to copy: [the showreel prompt](https://prompt-motion.com/templates/showreel) and [the 3D template](https://prompt-motion.com/templates/realtime). Any entry can be rewritten for a product at `https://prompt-motion.com/customize/<slug>`.

## Skills the gallery links to

The six skills the gallery lists are installed beside this one. Sources, pinned commits and licences are in `../../INSTALLED.md`.

| Skill | From | Licence |
|---|---|---|
| `product-film` | github.com/Rieranthony/product-film-skill | MIT |
| `cinetic` | github.com/Leonxlnx/cinetic | MIT |
| `design-taste-frontend` | github.com/Leonxlnx/taste-skill | MIT |
| `generative-film` | github.com/buildfastwithai/buildfast-skills | MIT |
| `session-story` | github.com/heygen-com/hyperframes-community-skills | Apache 2.0 |
| `html-demo` | github.com/MengTo/Skills | MIT |
