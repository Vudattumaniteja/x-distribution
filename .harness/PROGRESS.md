# Project Progress

## Current State
- Completed the full Phase 1 Discovery (News Collection) run on 2026-06-10.
- Current focus: Post-collection normalization, pipeline schema checks, and market intelligence generation.
- Verification status: Python compile checks, target tests, and schema validation pass; route checks are currently blocked by the missing pinned external XCLI file.

## Completed
- [x] Executed Phase 1 collection (task-193) on 2026-06-10, pooling 2,088 raw items and merging 77 duplicates into 1,000 active queue entries.
- [x] Saved premium HTML market report dashboard on the Desktop.
- [x] Generated detailed market intelligence digest markdown report.
- [x] Centralized X/YT route policy through `scripts/source_clis.py`.
- [x] Added GitHub and arXiv as first-class live sources in `config/source_registry.json`.
- [x] Documented data storage in `references/data-storage.md`.
- [x] Added master CLI in `scripts/x_distribution.py`.
- [x] Added schema validation in `scripts/validate_schemas.py`.
- [x] Added storage compatibility layout and manifest.
- [x] Added script inventory in `references/script-inventory.md`.
- [x] Integrated Reddit as a multi-route collector: reddit-mcp-buddy probe, RSS fallback, legacy JSON preservation fallback.
- [x] Ran targeted Reddit collection: MCP probe hit Reddit 403; RSS fallback collected 359 posts and 245 discoveries.
- [x] Added Finance/Macro Lane F with `config/finance_sources.json`, `scripts/finance_market_collector.py`, registry wiring, storage docs, schema validation, and Phase 1 Ingestion.
- [x] Added Startup Funding Lane G with `config/startup_sources.json`, `scripts/startup_funding_collector.py`, registry wiring, storage docs, schema validation, and Phase 1 Ingestion.
- [x] Made `yt-transcript latest` the default YouTube discovery method with a configurable 2-day lookback window and no transcript count cap inside the window.
- [x] Expanded subreddit coverage for AI agents, startups, indie launches, Chinese AI/tooling context, and open-source product discovery.
- [x] Promoted critical YouTube creators into P-2/P-1/P0 priority bands, added WorldofAI, removed NetworkChuck, and made transcript orchestrators process channels by priority order.
- [x] Verified XCLI timeline collection and refreshed X radar output with 19 validated watchlist tweets.
- [x] Added regional China, India, Southeast Asia, Europe, and emerging-market source coverage across RSS, startup/product feeds, Reddit, GitHub, and Hugging Face.
- [x] Added `scripts/intelligence_queue.py` as the authoritative protected-queue seam with atomic persistence and contract tests.
- [x] Routed canonical and compatibility queue writers through the protected queue seam.
- [x] Replaced reachable hardcoded editorial prototypes with verified-only manual drafting packets.
- [x] Disabled the historical `process_news.py` prototype so it fails closed instead of writing fabricated example stories.
- [x] Added root README, dense Markdown architecture documentation, an ADR, domain context, and interactive HTML documentation.
- [x] Completed post-improvement review: 77 Python scripts compile, 426 live JSON files parse, schema validation passes with 0 errors and 0 warnings, route checks pass, 7 contract tests pass, report regeneration succeeds, and direct queue-write audit finds 0 bypass writers.
- [x] Added opt-in external XCLI read-only tab slots, shared three-worker X coordination, notified serialized fallback, 24h/48h cache policy, rotating JSONL notifications, PID-aware locking, latest-state output, and canonical entry-point integration.
- [x] Executed Phase 1 collection and compiled an interactive Light-Themed Intelligence Dashboard (Sandoz color palette, custom bento grid, instant filter/search, and fully responsive layout).
- [x] Add prediction market source lane (F16, Issue #9, Issue #10)
  - [x] F16.1: Schema Registration & Validation (Issue #9)
  - [x] F16.2: Standalone Polymarket Collector (Issue #10)
  - [x] F16.3: Phase 1 pipeline ingestion and dynamic odds deduplication merging
- [x] Claim Verification and Corroboration via Polymarket (F16.5, Issue #14)
  - [x] F16.5.1: Implement fetch_polymarket_corroboration in TruthOracle and VerificationEngine
  - [x] F16.5.2: Integrate Polymarket YES odds into confidence score calculation (+10 bonus for >70% YES, -15 penalty for <15% YES)
  - [x] F16.5.3: Document prediction market corroboration rules in references/fact-checking.md
- [x] Added support for `--skip-x` option in master CLI and Phase 1 collector to allow skipping X (Twitter) collection.
- [x] Launched and completed parallel subagent analysis (China Tech, India Tech, Startup VC) and copied the compiled reports to the main artifacts folder.
- [x] Fixed `C:\Users\Manit\bin\yt-transcript.cmd` to point to the active workspace instead of the old desktop folder.

## Known Issues
- `graphify` is not available on PATH in this shell.
- `make` is not installed in this PowerShell shell; run the Python commands from `Makefile` directly.
- Route check currently fails at `C:\Users\Manit\AppData\Local\Programs\Python\Python311\python.exe scripts/x_distribution.py routes` because the pinned XCLI path is missing: `C:\Users\Manit\Desktop\Twitter automation\cli.py`.
- Full live collection can be slow because it touches X, YouTube, Reddit, HN, GitHub, arXiv, finance/RSS, SEC, startup funding/product feeds, and corporate sites.
- Direct Reddit JSON endpoints returned 403 from this environment for both `www.reddit.com` and `old.reddit.com`; RSS returned 200 and is now the practical fallback.
- The browser plugin blocks local `file://` navigation, so the interactive documentation was statically verified rather than visually inspected inside the in-app browser.

## Next Steps
- Continue the incremental storage migration toward `data/raw/`, `data/normalized/`, `data/verified/`, and `data/content/` with compatibility shims.

