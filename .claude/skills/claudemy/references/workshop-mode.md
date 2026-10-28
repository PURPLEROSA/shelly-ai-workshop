# Workshop and lecture mode

Use this when the class is for a room, not one learner: "a workshop on X", "סדנה על", "הרצאה על", "for my workshop", "for my participants", or a course the user will teach. The research, agreement map, lesson plan and honesty rules stay exactly the same. What changes is the language, who is addressed, and the extra files the facilitator gets.

## Ask once, before Step 1
If the request doesn't say, ask in one message (don't guess, and don't ask again later):
- Who's in the room: role and level (e.g. marketers new to AI, designers who already prompt daily).
- Format and length: a 90-minute workshop, a full day, a 40-minute keynote, a recurring course.
- Group size and setup: laptops or not, in person or online.
- Language: Hebrew or English. When the request is in Hebrew, default to Hebrew.

Write the answers into `sources.json` as `"audience"`, `"format"` and `"language"` so every reader and writer agent sees them.

## Hebrew
- Write spoken Israeli Hebrew, not translated English. Short sentences, natural reactions ("רגע, מה?", "בדיוק", "וואו"), numbers the way they're said.
- Keep tool and product names and established terms in English: Claude Code, prompt, agent, workflow, MCP. Don't make up Hebrew coinages for them.
- Address a room in the plural (אתם). Address one listener in the plural too, unless the user says otherwise; it avoids guessing gender.
- The script format doesn't change: one turn per line, `A: ...` / `B: ...`.
- Length: 210 to 280 Hebrew words for about 2 minutes. This band is a starting estimate. After the first render, compare word count to the stamped running time and tell the user if the band needs moving (the constants live in `scripts/check_lessons.py`).
- Offer, don't order applies in Hebrew too. The checker refuses אתם חייבים, אתה צריך, חובה ל, תקפידו, אל תשכחו and similar. Describing a situation is fine ("שני הצדדים צריכים להסכים").
- Hebrew cards use these headings, in this order (the checker looks for them):
  `# שיעור N. <שם>` · `**האזנה:**` · `**הרעיון בשלוש שורות**` · `**השפעה:**` · `**מי אומר את זה:**` · `**נסו את זה** · <Energy> · <דקות>` · `**כלל לשמור**` · `**דילוג**` · `**להעמקה (רשות)**`
- Audio: ElevenLabs `eleven_v3` reads Hebrew. Default voices are fine for a test. For a real class, pick two voices that sound native in Hebrew and set `CLAUDEMY_VOICE_A` / `CLAUDEMY_VOICE_B`. Where a word is ambiguous without vowels and the meaning matters, rephrase rather than add nikud.

## What the facilitator gets, on top of the normal class

### Workshop (`format` is a workshop)
Per lesson, next to `script.txt` and `card.md`, write `facilitator.md`:
- **Timing block** that adds up, e.g. `2' audio · 3' demo · 10' hands-on · 5' debrief = 20'`.
- **Live demo:** the exact steps the facilitator does on screen, including the exact prompt to type.
- **Hands-on:** the lesson's Try it, rewritten for this room (pairs or solo, what each person ends up with).
- **Debrief question:** one, taken from a Split in the lesson plan where one exists. Disagreement makes the best discussion.
- **Where people get stuck:** two or three likely failure points and the one-line fix for each.

Then `class/workshop-run.md`: the full agenda by the clock (opening, arcs as blocks, breaks, close), totalling the session length the user gave, plus a materials checklist (accounts, files, links to send beforehand). The audio lessons and cards become pre-work and a take-home kit; say so in the agenda.

### Lecture (`format` is a talk or keynote)
Write `class/lecture-spine.md` instead of per-lesson facilitator notes:
- **Opening hook** (one story or number from a real page) and the one-sentence promise of the talk.
- **Acts:** one per arc. For each: the claim, how widely the sources agree (N of M), the story that carries it, and a slide headline of 7 words or fewer.
- **Audience moments:** each Split becomes a live question to the room ("hands up if...").
- **Close:** the 3 to 5 rules from the playbook as the takeaway.
- Timing per act, totalling the talk length.

The spine is the content, not the slides. If the user wants a deck, hand the spine to whichever slide or presentation skill they use.

## Checks
`check_lessons.py` checks scripts and cards in either language. It doesn't read `facilitator.md`, `workshop-run.md` or `lecture-spine.md`, so apply the same rules to them by hand: every story and number traces to a page in `raw/`, and nothing is phrased as an order to the audience.
