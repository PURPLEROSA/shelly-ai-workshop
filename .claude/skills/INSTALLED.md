# Installed skills

Installed on 14 November 2026 from the skills listed on [prompt-motion.com](https://prompt-motion.com). Each folder is an unmodified copy of the upstream skill at the commit shown, with the upstream licence file beside it.

| Skill folder | Source | Path in repo | Commit | Licence | Size |
|---|---|---|---|---|---|
| `product-film` | [Rieranthony/product-film-skill](https://github.com/Rieranthony/product-film-skill) | `plugins/product-film/skills/product-film` | `fe11efc` | MIT | 148 KB |
| `generative-film` | [buildfastwithai/buildfast-skills](https://github.com/buildfastwithai/buildfast-skills) | `generative-film-skill` | `838b397` | MIT | 1.9 MB |
| `session-story` | [heygen-com/hyperframes-community-skills](https://github.com/heygen-com/hyperframes-community-skills) | `skills/session-story` | `ba7a0bb` | Apache 2.0 | 420 KB |
| `cinetic` | [Leonxlnx/cinetic](https://github.com/Leonxlnx/cinetic) | `skills/cinetic` | `f4bbfc8` | MIT | 19 MB |
| `design-taste-frontend` | [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) | `skills/taste-skill` | `f6b7657` | MIT | 40 MB |
| `html-demo` | [MengTo/Skills](https://github.com/MengTo/Skills) | `agent-skills/web-design/html-demo` | `07274a3` | MIT | 332 KB |
| `motion-director` | Written here, distilled from the Prompt Motion gallery and guides | | | yours | 280 KB |

## The install commands the site lists

For installing on another machine, or user-wide instead of in this repo:

```
/plugin marketplace add Rieranthony/product-film-skill
/plugin install product-film@product-film-skill
npx skills@latest add https://github.com/buildfastwithai/buildfast-skills
npx skills add heygen-com/hyperframes-community-skills --skill session-story
npx skills add Leonxlnx/cinetic
npx skills add https://github.com/Leonxlnx/taste-skill --skill "design-taste-frontend"
npx skills add MengTo/Skills --skill html-demo
```

## Things to know

- **`design-taste-frontend` registers a Stop hook.** While one of its builds is armed (a `.taste-skill/build.json` exists in the project), it runs its checker when Claude tries to finish and holds the turn open while fixable failures remain. With no armed build it exits at once. Its description triggers on most landing-page work, including this repo's site.
- **`session-story` reads local agent history** (`~/.claude/projects/...`) to build its film. It writes one output file and sends nothing anywhere.
- **`cinetic` expects a toolchain**: Node 22+, ffmpeg 6+, Python 3.11+ with numpy, scipy, soundfile, pyloudnorm, opencv-python and librosa. It sets projects up on first use.
- **`product-film` targets Remotion.** Check Remotion's licence terms before commercial use.
- `cinetic` and `design-taste-frontend` account for 59 MB of the 61 MB. Delete either folder to remove it; nothing else depends on them.

## Updating

Re-copy the path above from a fresh clone of the source, or run the matching `npx skills add` command. Review what changed before committing: a skill is instructions that Claude will follow.
