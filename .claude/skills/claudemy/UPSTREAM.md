# Source

Vendored from https://github.com/assafkip/claudemy (MIT, commit 438a628, plugin version 0.3.2), `skills/claudemy/`.

Local changes:
- `references/workshop-mode.md` (new) and the matching lines in `SKILL.md`: workshop and lecture mode, Hebrew.
- `scripts/check_lessons.py`: accepts Hebrew cards and scripts (Hebrew headings, Hebrew pressure phrases, a Hebrew word band).
- `scripts/render_audio.py`: stamps the running time on a Hebrew card's `**האזנה:**` line; reads and writes UTF-8 explicitly.
- `tests/test_scripts.py`: points at this folder, drops the plugin-only tests (key hook, version strings), adds Hebrew tests.

The plugin's SessionStart hook is not installed: in the cloud, set `ELEVENLABS_API_KEY` as an environment secret instead.

Run the tests: `python3 -m unittest discover -s .claude/skills/claudemy/tests`
