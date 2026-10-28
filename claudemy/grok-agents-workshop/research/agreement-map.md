# Agreement map (search-excerpt mode)

**Read this first.** The session's network policy blocked 40 of 42 pages, so this map is built from web-search result excerpts. Each excerpt quotes a real page, but the full page was not opened. Only two pages are on disk in `raw/web/`: the GitHub custom-agents guide and Anthropic's "Building effective agents". Claims marked **[verify]** are product details (dates, limits, tiers, menu paths) to confirm on grok.com before 2.11.

N of M counts search excerpts, not opened pages.

## Grok's building blocks (T02 to T09)

## TH01 Custom Agents are the "agent" a beginner builds first: name, personality, instructions
- Agree: 5 of 5. https://github.com/RoryVining/grok-custom-agents-setup-guide (on disk), https://www.uniflow.kr/en/grok-custom-agents-setup-guide-slot-strategy/, https://www.blutrumpet.com/post/grok-custom-agents, https://aitoolsrecap.com/Blog/how-to-create-custom-grok-agents-2026, https://x.com/cb_doge/status/2038000263110525132
- Facts: launched March 4 2026. Path: profile icon, then Settings, then Customize, then Create Agent. Up to 4 agents. Instructions about 4,000 characters. Edits apply only to new chats. **[verify]** tiers: one source says SuperGrok and X Premium+; the GitHub guide says Expert mode is needed for reliable activation.
- Disagree: none on the basics. The 4,000 vs 12,000 character limit for global custom instructions changed during 2026 (uniflow says it was cut to 4,000 in March and restored to 12,000 in April; blutrumpet mentions only the cut).

## TH02 Projects/Workspaces hold the files and instructions that make it "know your business"
- Agree: 3 of 3. https://www.goodday.work/blog/how-to-use-grok-for-project-management/, https://www.uniflow.kr/en/grok-custom-instructions-setup-guide-workspaces-agents/, https://www.maginative.com/article/xai-upgrades-grok-with-personalized-memory-and-custom-workspaces/
- Facts: files uploaded to a project are referenced by every chat inside it; each project has its own instructions; workspaces keep contexts separate (work vs learning).

## TH03 Memory helps but isn't a filing system: see it, edit it, don't rely on it
- Agree: 4 of 5. https://blog.memoryplugin.com/how-grok-memory-works/, https://www.bluehost.com/blog/?p=280653, https://www.thestatesman.com/technology/grok-just-got-a-memory-upgrade-heres-how-it-works-1503421334.html, https://www.maginative.com/article/xai-upgrades-grok-with-personalized-memory-and-custom-workspaces/
- Facts: launched April 2025; memories can be viewed, edited, deleted, toggled; a book icon shows which past chats were used. **[verify]** EU/UK were excluded at launch.
- Disagree: https://www.memorylake.ai/en/blogs/grok-forgets-personal-preferences says saved info doesn't surface reliably and memory is account-wide, not project-aware (vendor with a competing product).

## TH04 Skills turn a good prompt into a reusable tool
- Agree: 4 of 4. https://infoq.com/news/2026/05/xai-grok-skills/, https://alternativeto.net/news/2026/5/grok-can-now-learn-and-remember-ai-skills-across-every-conversation-on-all-major-platforms/, https://www.testingcatalog.com/xai-prepares-skills-support-for-grok-to-rival-claude-and-chatgpt/, https://www.basenor.com/blogs/news/grok-skills-automate-workflows-with-prebuilt-and-custom-ai-skills
- Facts: shipped mid-May 2026 (one source: May 13). Created by describing in natural language or uploading .md/.zip/.skill. Built-in skills exist; custom ones take priority. Automations can call skills.

## TH05 Connectors let it read (and, if allowed, write) Gmail, Calendar, Drive
- Agree: 6 of 6. https://x.ai/news/grok-connectors (official), https://porteden.com/blog/grok-connectors/, https://www.creativeainews.com/articles/grok-connectors-gmail-notion-drive-setup-2026/, https://fast.io/resources/grok-connectors/, https://www.basenor.com/blogs/news/grok-now-connects-to-gmail-calendar-drive-github-notion, https://aiinsightsnews.net/what-are-connectors-in-grok-xai/
- Facts: live on web, iOS, Android. Web: the + button, then Connectors. Mobile: Settings, then Connectors. Launched around May 6 or 7 2026. Also GitHub, Microsoft 365, Notion, Linear, custom MCP.
- Permission tiers (porteden): read-only by default; drafts add modify; sending adds send. This is the safety lever for the workshop.

## TH06 Automations make it act without being asked: schedule or email trigger
- Agree: 7 of 7. https://x.ai/news/grok-automations (official), https://www.mindstudio.ai/blog/grok-automations-scheduled-tasks-email-triggers, https://beginnersinai.org/grok-automation/, https://flowith.io/blog/grok-automations-scheduled-email-trigger-guide/, https://testingcatalog.com/xai-is-working-on-automations-feature-for-grok/, https://www.eonmsk.com/2025/06/22/how-to-create-xai-grok-tasks/, https://grokaimodel.com/tasks/
- Facts (official): announced July 16 2026, replaces Tasks. Schedules once, daily, weekdays, weekly, monthly, yearly in your timezone. Each automation saves instructions, optional files, connectors, skills and a mode; every run is fresh with current data. Run now for testing; pause, resume, edit, delete. Email triggers match sender, recipient or subject.
- Disagree **[verify]**: tiers. One source says schedules are for everyone and email triggers need SuperGrok; old Tasks allowed free users 1 (or 2) daily tasks and 10 for paid.

## TH07 Grok Bot is the "agent with its own computer", but it's an expensive beta
- Agree: 4 of 4. https://interestingengineering.com/ai-robotics/xai-grok-bot-computer-agent, https://www.igeeksblog.com/grok-bot-macos-ios-launch/, https://www.unite.ai/?p=451040, https://pasqualepillitteri.it/en/news/10621/grok-bot-xai-autonomous-agents
- Facts: early beta August 11 2026; runs in its own cloud computer, signs into your tools, asks for approval; teach-by-showing routines. Paid top tiers only (SuperGrok Heavy, Cursor tiers); prices reported $120 to $300. Reliability on complex workflows not yet proven. **Teaching use: a demo of where this is going, not something participants build.**

## Writing and use cases (T10 to T16)

## TH08 Your voice comes from samples and do/don't lists, not adjectives
- Agree: 5 of 5. https://www.eesel.ai/blog/how-to-train-ai-to-match-your-writing-style, https://easycontent.io/resources/train-ai-in-your-brand-style/, https://www.jeffbullas.com/thread/how-to-use-ai-to-create-a-brand-voice-and-style-guide-a-beginners-guide/, https://www.prdaily.com/?p=344758, https://webgrowthweekly.beehiiv.com/p/train-ai-on-your-brand-voice-without-overcomplicating-it
- Technique: 3 to 5 of your best pieces (about 1,000 words) → ask the AI to analyze vocabulary, sentence length, tone → condense to one paragraph of instructions → add "do this, not that" examples → iterate with specific feedback.

## TH09 Drafts first, approval always, autonomy earned
- Agree: 6 of 6. https://blog.agent.ai/human-in-the-loop-hitl-the-smb-guide-to-safe-effective-ai, https://www.stackai.com/insights/human-in-the-loop-ai-agents-how-to-design-approval-workflows-for-safe-and-scalable-automation, https://viewmedia.com/insights/how-small-businesses-use-ai-agents-first-steps, https://dev.to/sphillips1337/stop-letting-ai-agents-click-the-expensive-buttons-247f, https://fourweekmba.com/ai-trend-2026-the-agent-reliability-gap-keeps-humans-in-the-loop/, https://www.anthropic.com/engineering/building-effective-agents (on disk)
- Rules: anything that sends externally or changes a record waits for a person; too many approvals make people rubber-stamp; when a category is approved unchanged over and over, it can be loosened.

## TH10 Start simple; chain steps only when one prompt isn't enough
- Agree: on disk, https://www.anthropic.com/engineering/building-effective-agents ("finding the simplest solution possible... This might mean not building agentic systems at all"). Patterns for the newsroom module: prompt chaining, routing, orchestrator-workers, evaluator-optimizer.
- Thin evidence for Grok specifically: no source shows Grok agents handing work to each other natively. The newsroom is taught as a chain the person runs (or as separate automations feeding each other through email/Drive). **[verify]** whether Automations can pass output to another automation.

## TH11 Trends: Grok's edge is live X data, via DeepSearch
- Agree: 3 of 4. https://flowith.io/blog/how-to-use-grok-monitor-market-trends-real-time, https://catalog.bensbites.com/tutorial/use-grok-3-deepsearch-to-do-product-research-on-x, https://thegtmdirectory.com/tools/grok
- Disagree: https://www.techloy.com/chatgpt-helped-me-run-a-viral-newsletter-these-5-prompts-changed-everything/ uses Grok only for "angles and reader-provoking questions", other tools for drafting and facts. Several trend guides look templated.

## TH12 Newsletter: AI drafts, you add the personal touch; check every link
- Agree: 3 of 3. https://tools-34m.pages.dev/en/how-to-create-weekly-newsletter-with-ai-chatgpt-claude-guide-en/ (60 to 90 min per issue after 2 to 3 h setup, their claim), https://aiblewmymind.substack.com/p/automate-newsletter-with-ai (fabricated links are the main failure), https://www.pulse.bot/ai/blogs/how-to-automate-a-newsletter-with-ai-anyone-can-do-it-651ed0bc-5640-4183-b7ed-a0c8655a325a/

## TH13 Payment reminders: AI drafts by days overdue; default tone is too soft
- Agree: 3 of 4. https://www.lilachbullock.com/ai-payment-reminders-late-paying-clients/, https://ruul.io/blog/ai-get-paid-faster-freelancers, https://www.producthunt.com/products/chasa-ai-invoice-follow-ups/makers (drafts at 1 week, 30 days, 60+; user sends)
- Disagree: a UK consultant (in lilachbullock excerpt) says AI reminders are too soft and teach late payers you're not a priority: firmer wording, real deadline, a phone call.

## TH14 Family ops: one evening message beats ten apps; keep identifying details out
- Agree: 3 of 4. https://www.mother.ly/news/viral-trending/ai-mental-load-moms-tips/ (don't include names, schools, addresses, medical info), https://www.ohai.ai/blog/chatgpt-co-parent-vs-ai-household-manager, https://dwealth.news/2025/10/ai-for-everyday-life-how-ai-helps-busy-families-stay-organized/
- Note: most family pages are from vendors selling household apps.

## Risks (T18)

## TH15 Know what Grok does with your data before connecting your inbox
- Agree: 4 of 4. https://www.strac.io/blog/is-grok-safe, https://anonyome.com/knowledge-center/ai-privacy/grok-privacy/, https://secureprivacy.ai/blog/grok-privacy-guide, https://sonomos.ai/blog/is-grok-gdpr-compliant-2026/
- Facts: a training setting on X was on by default; Ireland's DPC took X to court in 2024 over EU posts; investigations ongoing per one source. Practical: check Settings for data-sharing/training, connect read-only first, keep client IDs, health and financial details out.

## TH16 Agents are fast juniors, not autonomous employees
- Agree: 3 of 3. https://www.abqjournal.com/opinion/opinion-counterpoint-meet-the-ai-agents-of-2026-ambitious-overhyped-and-still-in-training/2947407 ("closer to junior staffers who work quickly, confidently and often incorrectly"), https://fourweekmba.com/ai-trend-2026-the-agent-reliability-gap-keeps-humans-in-the-loop/, https://dev.to/agentq/ai-agents-in-2026-the-hype-vs-the-reality-1pb
- Narrow, repeatable jobs hold up; open-ended multi-step ones don't yet.

## The big splits
1. **How much autonomy now?** Landing-page promise ("answers leads while you sleep") vs reliability critics (TH16) and HITL guides (TH09). Resolution for the room: the agent prepares everything while you sleep; you approve in the morning.
2. **Grok as the drafting tool, or only for trends/angles?** TH11 vs techloy. Resolution: Grok wins on live X data and automations; for long polished copy, test against what you already use.
3. **Soft vs firm payment reminders** (TH13).
4. **Plan tiers and limits** keep changing (TH01, TH06). Resolution: a pre-workshop "what plan do you need" email.

## Coverage gaps
- No opened official xAI help pages; every menu path needs a live check.
- Hebrew quality of Grok output: no source. Test live before 2.11.
- Agent-to-agent handoff inside Grok: no source (TH10).
- WhatsApp: no Grok connector found in sources; the family module routes through Calendar/Gmail.
