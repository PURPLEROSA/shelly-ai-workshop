# Installed skills

Installed on 14 November 2026 from the skills listed on [prompt-motion.com](https://prompt-motion.com). Each third-party folder is an unmodified copy of the upstream skill at the commit shown, with the upstream licence file beside it.

| Skill folder | Source | Path in repo | Commit | Licence | Size |
|---|---|---|---|---|---|
| `product-film` | [Rieranthony/product-film-skill](https://github.com/Rieranthony/product-film-skill) | `plugins/product-film/skills/product-film` | `fe11efc` | MIT | 148 KB |
| `generative-film` | [buildfastwithai/buildfast-skills](https://github.com/buildfastwithai/buildfast-skills) | `generative-film-skill` | `838b397` | MIT | 1.9 MB |
| `session-story` | [heygen-com/hyperframes-community-skills](https://github.com/heygen-com/hyperframes-community-skills) | `skills/session-story` | `ba7a0bb` | Apache 2.0 | 420 KB |
| `cinetic` | [Leonxlnx/cinetic](https://github.com/Leonxlnx/cinetic) | `skills/cinetic` | `f4bbfc8` | MIT | 19 MB |
| `html-demo` | [MengTo/Skills](https://github.com/MengTo/Skills) | `agent-skills/web-design/html-demo` | `07274a3` | MIT | 332 KB |
| `motion-director` | Written here, distilled from the Prompt Motion gallery and guides | | | yours | 280 KB |
| `component-director` | Written here on 24 November 2026, distilled from the Scrolltide component gallery's public previews | | | yours | 250 KB |

## The install commands the site lists

For installing on another machine, or user-wide instead of in this repo:

```
/plugin marketplace add Rieranthony/product-film-skill
/plugin install product-film@product-film-skill
npx skills@latest add https://github.com/buildfastwithai/buildfast-skills
npx skills add heygen-com/hyperframes-community-skills --skill session-story
npx skills add Leonxlnx/cinetic
npx skills add MengTo/Skills --skill html-demo
```

## Things to know

- **`session-story` reads local agent history** (`~/.claude/projects/...`) to build its film. It writes one output file and sends nothing anywhere.
- **`cinetic` expects a toolchain**: Node 22+, ffmpeg 6+, Python 3.11+ with numpy, scipy, soundfile, pyloudnorm, opencv-python and librosa. It sets projects up on first use.
- **`product-film` targets Remotion.** Check Remotion's licence terms before commercial use.
- `cinetic` is 19 MB of the 22 MB here. Delete its folder to remove it; nothing else depends on it.

## `component-director` and Scrolltide

`component-director` is for single interactive pieces (a switch, a loader, a card that opens), where `motion-director` is for video. It was written from the public side of [scrolltide.co/components](https://www.scrolltide.co/components): the listing page and its 132 preview clips.

- **Scrolltide's prompts are not in it.** They are the paid product (the page says Yearly and Lifetime plans). The skill's index holds names, tags and links to the public preview clips, plus labels worked out here. A purchased prompt can be pasted into a session and built and checked with this skill like any other.
- **Its examples are original:** `fever` (a model-temperature slider), `spill` (a context-window loader) and `spike` (a done-list on a desk spike), each one HTML file, each with `?lang=he`.
- **It needs** Node 22 with Playwright Chromium for `probe.mjs`, Python 3.11+ for `gallery.py`, and ffmpeg only for `gallery.py clip`.
- **The site refuses automated requests** after the first page load, so the index is a snapshot from 24 November 2026 and has no live refresh. To update it, save the gallery page from a browser and rebuild from that.

## Left out on purpose

The site lists a sixth skill, `design-taste-frontend` ([Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill), MIT, 40 MB). It is not installed here: it triggers on most landing-page work, including this repo's site, applies its own design rules, and registers a Stop hook that holds a turn open while one of its builds has open failures. To add it later:

```
npx skills add https://github.com/Leonxlnx/taste-skill --skill "design-taste-frontend"
```

## Updating

Re-copy the path above from a fresh clone of the source, or run the matching `npx skills add` command. Review what changed before committing: a skill is instructions that Claude will follow.
