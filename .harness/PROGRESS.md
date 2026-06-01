# Project Progress

## Current State
- Architecture hardening pass completed on 2026-05-31.
- Current focus: bounded three-worker read-only X collection is implemented; live trial #6 and final gate #7 remain intentionally deferred.
- Verification status: deterministic implementation gates passed after shared X coordinator integration.

## Completed
- [x] Centralized X/YT route policy through `scripts/source_clis.py`.
- [x] Added GitHub and arXiv as first-class live sources in `config/source_registry.json`.
- [x] Documented data storage in `references/data-storage.md`.
- [x] Added master CLI in `scripts/x_distribution.py`.
- [x] Added schema validation in `scripts/validate_schemas.py`.
- [x] Added storage compatibility layout and manifest.
- [x] Added script inventory in `references/script-inventory.md`.
- [x] Integrated Reddit as a multi-route collector: reddit-mcp-buddy probe, RSS fallback, legacy JSON preservation fallback.
- [x] Ran targeted Reddit collection: MCP probe hit Reddit 403; RSS fallback collected 359 posts and 245 discoveries.
- [x] Added Finance/Macro Lane F with `config/finance_sources.json`, `scripts/finance_market_collector.py`, registry wiring, storage docs, schema validation, and Phase 1 ingestion.
- [x] Added Startup Funding Lane G with `config/startup_sources.json`, `scripts/startup_funding_collector.py`, registry wiring, storage docs, schema validation, and Phase 1 ingestion.
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


## In Progress
- [x] F01 full collection test
- [x] F02 data layout hardening
- [x] F03 master CLI
- [x] F04 schema validation
- [x] F05 legacy script classification
- [x] F06 end-to-end verification
- [x] F07 finance/macro intelligence lane verification
- [x] F08 startup funding/product hunt verification
- [x] F09 creator-fast-update and subreddit expansion
- [x] F10 YouTube all-in-window transcript policy and channel priority map
- [x] F11 YouTube priority escalation and source cleanup
- [x] F12 XCLI watchlist collection verification
- [x] F13 Regional AI/startup coverage expansion
- [x] F14 protected queue architecture, editorial safety, and documentation
- [x] F15 bounded three-worker read-only X watchlist collection
- [x] F15.1 Bounded Polymarket prediction market source lane integration (Issue #9, Issue #10)
    - [x] F16.1: Schema Registration & Validation (Issue #9)
    - [x] F16.2: Standalone Polymarket Collector (Issue #10)
    - [x] F16.3: Phase 1 pipeline ingestion and dynamic odds deduplication merging

## Known Issues
# Project Progress

## Current State
- Architecture hardening pass completed on 2026-05-31.
- Current focus: bounded three-worker read-only X collection is implemented; live trial #6 and final gate #7 remain intentionally deferred.
- Verification status: deterministic implementation gates passed after shared X coordinator integration.

## Completed
- [x] Centralized X/YT route policy through `scripts/source_clis.py`.
- [x] Added GitHub and arXiv as first-class live sources in `config/source_registry.json`.
- [x] Documented data storage in `references/data-storage.md`.
- [x] Added master CLI in `scripts/x_distribution.py`.
- [x] Added schema validation in `scripts/validate_schemas.py`.
- [x] Added storage compatibility layout and manifest.
- [x] Added script inventory in `references/script-inventory.md`.
- [x] Integrated Reddit as a multi-route collector: reddit-mcp-buddy probe, RSS fallback, legacy JSON preservation fallback.
- [x] Ran targeted Reddit collection: MCP probe hit Reddit 403; RSS fallback collected 359 posts and 245 discoveries.
- [x] Added Finance/Macro Lane F with `config/finance_sources.json`, `scripts/finance_market_collector.py`, registry wiring, storage docs, schema validation, and Phase 1 ingestion.
- [x] Added Startup Funding Lane G with `config/startup_sources.json`, `scripts/startup_funding_collector.py`, registry wiring, storage docs, schema validation, and Phase 1 ingestion.
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


## In Progress
- [x] F01 full collection test
- [x] F02 data layout hardening
- [x] F03 master CLI
- [x] F04 schema validation
- [x] F05 legacy script classification
- [x] F06 end-to-end verification
- [x] F07 finance/macro intelligence lane verification
- [x] F08 startup funding/product hunt verification
- [x] F09 creator-fast-update and subreddit expansion
- [x] F10 YouTube all-in-window transcript policy and channel priority map
- [x] F11 YouTube priority escalation and source cleanup
- [x] F12 XCLI watchlist collection verification
- [x] F13 Regional AI/startup coverage expansion
- [x] F14 protected queue architecture, editorial safety, and documentation
- [x] F15 bounded three-worker read-only X watchlist collection
- [x] F15.1 Bounded Polymarket prediction market source lane integration (Issue #9, Issue #10)
    - [x] F16.1: Schema Registration & Validation (Issue #9)
    - [x] F16.2: Standalone Polymarket Collector (Issue #10)
    - [x] F16.3: Phase 1 pipeline ingestion and dynamic odds deduplication merging

## Known Issues
- `graphify` is not available on PATH in this shell.
- `make` is not installed in this PowerShell shell; run the Python commands from `Makefile` directly.
- Full live collection can be slow because it touches X, YouTube, Reddit, HN, GitHub, arXiv, finance/RSS, SEC, startup funding/product feeds, and corporate sites.
- Direct Reddit JSON endpoints returned 403 from this environment for both `www.reddit.com` and `old.reddit.com`; RSS returned 200 and is now the practical fallback.
- The browser plugin blocks local `file://` navigation, so the interactive documentation was statically verified rather than visually inspected inside the in-app browser.

## Next Steps
- Continue the incremental storage migration toward `data/raw/`, `data/normalized/`, `data/verified/`, and `data/content/` with compatibility shims.
