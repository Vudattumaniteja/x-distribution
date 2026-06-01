# Julian Goldie / Coverage / Storage Audit

Updated: 2026-05-29

## What Was Checked

- `@JulianGoldieSEO` is already configured in `config/youtube_channels.json`.
- YouTube RSS entries were checked from channel `UCc-FovAyBAQDw2Y7PQ_v0Zw`.
- The canonical `yt-transcript latest` route was also checked against `https://www.youtube.com/@JulianGoldieSEO`.
- Four recent transcripts were pulled through the pinned YT Transcript CLI route into `data/transcripts/julian_goldie_audit/`:
  - `89N7ylFVnUE` - Claude + Obsidian Just Got Smarter
  - `5BBuk78EgjM` - The New NotebookLM Update Is Wild
  - `89fSMlVP_8k` - AntiGravity 2.0 Update: The Game Just Got 10x Better
  - `0gQnOZA-7cg` - AI Studio Just Got Wild Updates
- Five newest videos from the canonical latest route were pulled into `data/transcripts/julian_goldie_latest/`:
  - `c0xu_8TdvU4` - OpenClaw 5.27 Update Just Dropped...
  - `_lV7CB4NVCU` - Claude Opus 4.8 Ultracode is INSANE!
  - `moQp7dXtVBQ` - This FREE Chinese AI Coding Agent is INSANE
  - `8pkLt1kn9RY` - NEW Claude Opus 4.8 is WILD!
  - `9TfvBH_efCU` - NEW Hermes Agent v0.15: Kanban Agent Swarms!

Important discovery: YouTube RSS and `yt-transcript latest` disagreed. RSS showed `Claude + Obsidian Just Got Smarter` as newest, while `yt-transcript latest` found a newer creator-video set around OpenClaw, Claude Opus/Ultracode, a Chinese coding agent, and Hermes. For this channel, the system should trust the canonical `yt-transcript latest` route over RSS-only recency.

Implemented policy: YouTube discovery now defaults to `yt-transcript latest` with a configurable day window in `config/source_registry.json -> youtube_discovery`. The default is a 2-day lookback, up to 500 playlist entries inspected as a safety guard, and no transcript count cap. Every video found inside the day window is eligible for transcript retrieval.

## Julian Goldie Pattern

Julian's speed appears to come from a narrow editorial lane:

- He watches fast-moving AI productivity tools and converts updates into tutorials quickly.
- His recent channel cadence is high: multiple uploads landed between 2026-05-24 and 2026-05-28.
- The transcript pattern is product-update heavy: AI Studio, NotebookLM, Claude, Obsidian, AntiGravity, Gemini, Google tooling.
- The newest transcript set is even more "fast update" oriented: OpenClaw 5.27, Claude Opus 4.8 / Ultracode, a Chinese coding agent, and Hermes v0.15.
- He packages news as "what changed + why it matters + workflow demo + CTA", not as a broad intelligence report.
- His visible sourcing pattern leans toward product surfaces, docs, community comments, and creator/product ecosystems rather than deep primary-source provenance.

The lesson for X Distribution: treat creators like Julian as a fast secondary radar, not as source-of-truth. Use them to trigger checks against official docs, changelogs, GitHub releases, product pages, and community discussion.

## Current Coverage Breadth

Current X Distribution lanes:

- Lane A: X home feed and followed-account timelines through pinned XCLI.
- Lane B: corporate RSS/blogs.
- Lane C: YouTube latest-video discovery and transcripts through pinned YT Transcript CLI.
- Lane D: Reddit and Hacker News community discussion.
- Lane E: GitHub and arXiv artifact/research discovery.
- Lane F: finance, macro, newsletter, and SEC market signals.
- Lane G: startup funding, Series A/B/C, investors, and product-launch signals.

This is broad for AI news discovery because it covers official announcements, social chatter, creator videos, communities, code artifacts, research, funding, and market context.

## Coverage Gaps

Important gaps if the goal is to catch Julian-style updates faster:

- Official changelog and docs diff monitoring for tools with weak RSS coverage.
- Creator-radar scoring for high-cadence AI/productivity channels.
- Newsletter inbox ingestion beyond public RSS mirrors.
- Discord, Slack, private community, and early-access forum monitoring.
- Product launch boards beyond Product Hunt: YC Launch, BetaList, Indie Hackers, GitHub trending, Chrome Web Store updates, Chinese product directories, and regional startup/product communities.
- Browser-visible product update probes for apps that announce changes only inside the UI.
- LinkedIn founder/operator posts, especially for startup and enterprise AI updates.
- Benchmark and leaderboard watches: model leaderboards, cloud pricing pages, eval dashboards, and model-card updates.

## Source Expansion Notes

- Newsletter inbox ingestion should be treated as a first-class source lane. Best architecture: dedicated monitored inbox, allowlisted senders, IMAP/Gmail API ingestion, message hashing, and extraction into `data/newsletter_raw.json` plus `data/newsletter_signals.json`.
- Discord and Slack are high-friction. Do not scrape private spaces blindly. Use official exports, bots/webhooks in communities where the user has permission, or public community mirrors. Store source permission and channel metadata with every item.
- UI-only changes are lower priority unless they imply product launch, pricing, capability, model, API, or workflow change.
- Subreddits are a strong discovery layer for missed products, especially Chinese tools, indie launches, model tooling, coding agents, and real developer complaints. Add subreddit-specific source groups rather than one generic Reddit bucket.
- For Chinese and non-US products, add sources that are not English-first: GitHub trending by language/topic, Hugging Face org/repo activity, Product Hunt alternatives, Chinese AI newsletters, official model/company blogs, and Reddit/Telegram/HN mentions that point back to primary pages.
- Reddit expansion added to `config/community_sources.json`: `AI_Agents`, `AutoGPT`, `SaaS`, `SideProject`, `startups`, `Entrepreneur`, `ArtificialInteligence`, `China`, `Sino`, `opensource`, and `github`. These should be treated as discovery surfaces, then verified against primary sources.
- Research archiving implication: arXiv and research collectors should not only write the latest `data/arxiv_raw_standalone.json`; they should also preserve per-run research snapshots under `data/runs/<run_id>/raw/research/` and promote durable papers into a paper ledger with title, authors, URL, first_seen_at, last_seen_at, categories, source_run, and verification status.

## Storage Heads-Up

Current storage is functional but not yet a clean event ledger.

What exists:

- `data/news_queue.json` is the active working queue.
- `scripts/phase1_collect.py` writes the queue from current collection results.
- `scripts/queue_maintenance.py` normalizes and deduplicates the queue by canonical URL.
- `config/source_registry.json` defines collector outputs and active source lanes.
- Raw collector outputs remain in `data/*.json`.
- Some collectors keep history files such as `data/github_history.json`, `data/release_history.json`, `data/hf_history.json`, and `data/sitemap_history.json`.
- Verification runs append to `.harness/verification_results.json`.
- Older agent outputs remain in `logs/agent_runs/`.
- Transcript files are preserved in `data/transcripts/` and `data/mass_transcript_pool.json`.

Why a six-day-old item can still appear:

- `phase1_collect.py` keeps items from the last seven days.
- Items without a valid `published_at` can survive the filter because the collector treats unknown dates as fresh enough to keep.
- `data/news_queue.json` is the active queue, not a strict per-run snapshot.

## Recommended Next Storage Upgrade

Add a real run ledger:

- `data/runs/<run_id>/raw/*.json` for raw outputs from that run.
- `data/runs/<run_id>/news_queue.json` for the exact queue produced by that run.
- `data/item_ledger.jsonl` or SQLite for item lifecycle:
  - `item_id`
  - `canonical_url`
  - `first_seen_at`
  - `last_seen_at`
  - `last_confirmed_at`
  - `source_runs`
  - `sources`
  - `status`: active, stale, verified, rejected, archived
  - `decay_reason`
- Keep `data/news_queue.json` as the active top-N view only.
- Add a stale policy: e.g. active for 7 days, keep if re-seen, demote if not re-seen, archive after 30 days unless verified.

This would make history explainable: an item from six days ago remains because it is inside the active window, was re-seen, or was preserved as verified evidence. Otherwise it should be stale/demoted rather than silently floating in the queue.
