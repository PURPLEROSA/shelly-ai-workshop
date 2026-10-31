# Agreement map · Grok Bot edition (search-excerpt mode)

**Scope change (31.10):** the workshop teaches **Grok Bot** agents, not Custom Agents in Grok chat. The earlier chat-feature map is in git history (commit d41c536).

**Read this first.** The session's network policy blocks docs.x.ai, cursor.com and almost every other host, so this map is built from web-search excerpts. Many excerpts quote xAI's and Cursor's official Grok Bot docs directly, which makes them stronger than the first round. On disk in `raw/web/`: only Anthropic's "Building effective agents" and a GitHub guide (now mostly superseded). **[verify]** = confirm in the live app before 2.11.

## Setup and money

## TH01 Grok Bot starts at the $30 Premium plan, on a weekly usage pool shared with Grok chat
- Sources: https://www.ai-toolbox.co/grok-models/grok-pricing-plans-api-2026, https://www.aipricing.guru/xai-subscription-pricing/, https://www.ai-toolbox.co/grok-management-and-productivity/grok-usage-limits-2026, https://christopheralarcon.com/blog/grok-usage-limits-explained
- Facts: "The X Subscription" launched October 12 2026: Plus $8, Premium $30, Super $100, Ultra $200. Premium is the first plan with Grok Bot. One weekly pool shared across Grok Chat, Imagine, Voice, Grok Bot and Cursor; Premium = 4x Plus. xAI publishes no absolute numbers, only a percentage bar.
- Corroborated by the YUV.AI course page the user pasted ("30$ a month in normal use, 100$ in heavy use"; "the usage screen shows only percentages").
- Disagree: older listings call the $30 plan "SuperGrok". The August launch coverage said SuperGrok Heavy only, $120 to $300. **[verify]** on x.ai/pricing.

## TH02 Install the app and sign in with a Cursor account before the workshop
- Sources: https://docs.x.ai/grok-bot/get-started, https://cursor.com/docs/grok-bot/get-started, https://docs.x.ai/grok-bot/mobile
- Facts: desktop app for macOS, Windows, Linux; phone app on App Store and Google Play, same Bots and cloud computer. "There is no separate Grok Bot login": sign in through the browser with a Cursor account; if access comes from a Grok plan, link that Grok account during sign-in. Accounts on Privacy Mode (Legacy) are asked to switch, since Grok Bot needs cloud storage. A first Bot named "Grok Bot" is created automatically.
- Disagree: download location (Cursor dashboard vs x.ai/bot vs cursor.com/download/bot). **[verify]**

## Building Bots

## TH03 One Bot, one stable job; add a Bot only for a stable specialist role
- Sources: https://docs.x.ai/grok-bot/bots (official), https://dev.to/joey_zou_63aa6b1f1cbaa2bb/giving-grok-bot-its-first-job-one-role-one-brief-approvals-before-autonomy-1mp6, https://www.datacamp.com/tutorial/grok-bot-tutorial
- Facts: New chat, then "Create new agent", opens a Bot named "New Agent". Bot actions, then Edit Profile: name, title, description. Official: "Give one Bot ownership of an end-to-end outcome. Add another Bot only when the work has a stable specialist role."

## TH04 Set a Bot up in its first message: job, sources, approval limits, "remember this", then a real task with a finish line
- Sources: https://cursor.com/docs/grok-bot/work, https://docs.x.ai/grok-bot/bots
- Quote: "In your first message, give the Bot its job, sources, and approval boundaries, and ask it to remember them. Send a real first task with a clear finish line."

## TH05 Memory is per Bot, self-managed, and not a source of truth
- Sources: https://www.learncursor.dev/learn/cursor-agents/grok-bot-memory, https://docs.x.ai/grok-bot/bots
- Facts: remembers preferences, rules ("Always ask before you send an email"), facts (name, time zone) and a dated work log. It decides what to save without asking. "There is no memory screen for a personal Bot. Ask in chat instead." "Memory is not a substitute for an authoritative source."

## TH06 Do it once in chat, then save it as a skill
- Sources: https://www.datacamp.com/tutorial/grok-bot-tutorial, https://docs.x.ai/grok-bot/skills-routines-and-automations
- Facts: a skill holds steps, decision rules, output format and safety boundaries. Example prompt: "Save the process we just used as a skill called 'Weekly account health.' Include the source systems, risk definitions, output format, and the rule that customer contact always requires approval."

## TH07 Voice comes from your own writing fed to the Bot
- Sources: https://readmultiplex.com/grokbot-rocks/, https://www.aibuilderclub.com/blog/grok-bot-guide, plus the general voice sources from round 1 (https://www.eesel.ai/blog/how-to-train-ai-to-match-your-writing-style, https://easycontent.io/resources/train-ai-in-your-brand-style/)
- Facts: "Users who got good drafts fed their bots transcripts, past posts, and reference formats first."

## Acting on its own

## TH08 Routines run in the cloud on a schedule or an event; test first, schedule last
- Sources: https://docs.x.ai/grok-bot/skills-routines-and-automations, https://cursor.com/help/grok-bot/routines.md, https://www.datacamp.com/tutorial/grok-bot-tutorial
- Facts: routines run "while your laptop is closed". Create by asking the Bot that owns the job, in chat; on mobile, "Add routine" in the Bot's profile. "Schedule a routine last, and only after a test run."

## TH09 Approvals: "Ask first" rules beat everything; routine emails wait as drafts
- Sources: https://docs.x.ai/grok-bot/approvals-security-and-privacy.md, https://www.datacamp.com/tutorial/grok-bot-tutorial, https://www.therundown.ai/tools/grok-bot
- Facts: Auto Review checks actions before a Bot takes them. Custom rules: Settings, then General, then Bot. "Ask first" rules always produce an approval card and win any clash. Emails from routines wait as drafts until you press Send. Auto Review is model-based, available in some rollouts, and no replacement for least privilege or human review.
- Agrees with the general HITL sources from round 1 (TH09 in the chat edition).

## TH10 Connectors: Gmail and Calendar connect separately; sending is its own permission
- Sources: https://docs.x.ai/grok/connectors/gmail-google-calendar (official), https://composio.dev/toolkits/gmail/framework/grok-bot
- Facts: separate OAuth sign-ins for Gmail and Calendar. Drafts "so you can review before sending". gmail.send applies only when send tools are on. Plugins are bundles of connectors and skills from a marketplace (Settings, then Plugins, then Marketplace, per third-party sources) **[verify]**.

## TH11 Notifications are per Bot
- Source: https://docs.x.ai/grok-bot/settings-and-notifications.md
- Facts: turn on Notifications in a Bot's settings to get an OS or mobile notification when it finishes or needs input; muted while the app is in focus.

## TH12 Routines eat the weekly pool; when it runs out, everything stops
- Sources: https://cursor.com/help/grok-bot/faqs, https://youmind.com/landing/x-viral-articles/grok-bot-quota-hacks, https://forum.cursor.com/t/why-does-grok-bot-chat-use-so-many-sand-tokens/169581.md, YUV.AI page (pasted)
- Facts: a stopped Bot usually means the weekly allowance is used; it resets weekly. On-demand usage continues at token cost up to a monthly cap; the cap doesn't stop a run mid-task. A routine every 30 minutes uses the allowance around the clock. Metered by work, not messages. Check Settings, then Usage & Billing.
- Saving tips (third-party): event triggers over frequent schedules, one job per Bot, stopping rules ("stop after two failed sources and report back"), long material in files.

## Security

## TH13 All Bots share one cloud computer: separate Bots are not a security boundary
- Sources: https://docs.x.ai/grok-bot/vault.md, https://docs.x.ai/grok-bot/approvals-security-and-privacy.md, https://agent-finder.co/reviews/grok-bot, https://kingy.ai/blog/grok-bot-ai-teammate-price-security/
- Facts: files, browser sessions and command-line credentials are shared across all your Bots; deleting a Bot doesn't remove them. Vault: "A Bot never sees a saved password, card number, or security code", but Vault covers the whole account. You can take over the computer for passwords, 2FA and CAPTCHAs, then hand back. Practical: keep banking and high-stakes logins off the Bot's computer.

## Channels and teams

## TH14 There's no official Telegram or WhatsApp channel; the workarounds carry risk
- Sources: https://x.com/itsolelehmann/status/2110401303910203768, https://x.com/byalexai/status/2111081404939288825, https://composio.dev/toolkits/telegram/framework/grok-bot.md, https://blueticks.co/blog/grok-whatsapp, YUV.AI page (pasted)
- Facts: community prompts have the Bot open WhatsApp Web or Telegram Web on its computer and link by code or QR. Composio plugins exist. Blueticks: "no official xAI Grok WhatsApp bot". YUV.AI: the unofficial WhatsApp link "may get the account blocked"; the official Meta route is "frustrating".
- Teaching call: Telegram is the low-risk channel to demo; WhatsApp gets a risk talk, not a hands-on.

## TH15 A team = a coordinating Bot plus specialists, trusted in stages
- Sources: https://www.theaiimpact.co/guides/grok-bot-beginners-guide, https://refoundai.com/blog/how-to-run-your-business-with-grok-bot/, https://www.anthropic.com/engineering/building-effective-agents (on disk)
- Facts: a "primary"/"chief of staff" Bot with a team register (name, responsibility, output location, routines, approval rules). This is a usage pattern from guides, not a documented feature. Anthropic: simple composable patterns; evaluator-optimizer for the review step.

## TH16 Use cases that work: prepare and park for approval, not auto-send
- Sources: https://squad.so/resources/grok-bot-use-cases, https://readmultiplex.com/grokbot-rocks/, https://www.aibuilderclub.com/blog/grok-bot-guide, https://stealwhatworks.com/blogs/news/grok-bot-best-use-cases
- Facts: Newsletter Writer drafts "parked for one editorial pass"; Social Media Manager studies posting history and keeps a queue; on X, preparing replies is good, auto-sending unsolicited AI replies is "not a good use today".

## TH17 Reliability: stuck computers, failed responses, fast quota burn
- Source: https://cellcog.ai/blog/grok-bot-problems/ (single third-party blog, anecdotal), plus the critics from round 1 (https://www.abqjournal.com/opinion/opinion-counterpoint-meet-the-ai-agents-of-2026-ambitious-overhyped-and-still-in-training/2947407)

## The big splits
1. **Autonomy vs approval:** "works 24/7" marketing (including YUV.AI's) vs official docs that default to drafts, Ask first and test-before-schedule. Room resolution: it prepares at night, you approve in the morning.
2. **Unofficial channels:** WhatsApp Web convenience vs account-ban risk.
3. **Cost:** "$30 a month" vs a weekly pool that routines can burn in a day.

## Coverage gaps
- No opened official page; every menu label needs a live check.
- Hebrew quality of Grok Bot output: no source.
- Whether a Bot can message you first without a routine: no official statement found.
- Plugin marketplace path: third-party only.
