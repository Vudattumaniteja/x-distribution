# X Distribution System Optimization Report

Updated: 2026-05-28

## 2026-05-31 Architecture Hardening

Protected queue persistence now has one authoritative module:

- `scripts/intelligence_queue.py` owns historical queue-shape reads, canonical URL identity, provenance merging, recency filtering, queue metadata, and atomic JSON replacement.
- Canonical and compatibility writers route through this seam.
- `scripts/test_intelligence_queue.py` verifies the queue interface.

Editorial drafting now fails safe:

- `scripts/generated_codegen.py` creates empty manual drafting packets only for `VERIFIED` or `LIKELY_TRUE` items.
- `scripts/process_news.py` is an explicit disabled compatibility guard because its historical implementation embedded prototype stories.
- `scripts/test_post_generation.py` verifies the editorial contract.

Documentation now has durable entry points:

- `README.md`
- `CONTEXT.md`
- `docs/ARCHITECTURE.md`
- `docs/x-distribution-architecture.html`
- `docs/adr/0001-protected-intelligence-queue-seam.md`

Post-change review evidence:

- 77 Python scripts compiled.
- 426 live JSON files parsed.
- 7 contract tests passed.
- Schema validation returned 0 errors and 0 warnings.
- XCLI and YT Transcript CLI route checks passed.
- The report builder regenerated categorized JSON, Markdown, and HTML outputs.
- An AST audit found 0 scripts opening `data/news_queue.json` in write mode.

## What Changed

The system now has a central source and queue registry:

- `config/source_registry.json` controls collector outputs, queue limits, dedupe URL fields, stale-file archive policy, external CLI paths, Hugging Face orgs, GitHub orgs, GitHub release repos, and live source lanes including finance and startup funding.
- `scripts/source_registry.py` exposes registry helpers for collectors.
- `config/source_tiers.json` controls trusted domains and quarantine entries.
- `scripts/tier_policy.py` exposes tier checks for aggregators.

The source collectors no longer keep separate hardcoded GitHub or Hugging Face watchlists:

- `scripts/hf_tracker_standalone.py` reads Hugging Face orgs from the registry.
- `scripts/github_monitor_standalone.py` reads GitHub orgs from the registry.
- `scripts/github_releases_discovery.py` reads release repos from the registry.
- `scripts/finance_market_collector.py` reads Bloomberg, CNBC, Economic Times, Times of India, TLDR, and SEC source definitions from `config/finance_sources.json`.
- `scripts/startup_funding_collector.py` reads startup funding, Series A/B/C, and product-launch sources from `config/startup_sources.json`.

The queue path is cleaner:

- `scripts/aggregate_deep_discovery.py` reads collector output files from the registry.
- `scripts/merge_breadth.py` and `scripts/aggregate_news.py` use the registry queue cap instead of hardcoded small limits.
- `scripts/queue_maintenance.py` normalizes and deduplicates `data/news_queue.json` by canonical URL.

The X and YouTube source routes are explicit:

- `scripts/source_clis.py` is the authority for local XCLI and YT Transcript CLI paths.
- `scripts/xcli_utils.py` wraps read-only XCLI calls with UTF-8 handling and author/timeline validation.
- `scripts/weekly_sweep_orchestrator.py` now uses validated X home collection and `scripts/orchestrate_videos.py` instead of the legacy RSS-only YouTube fetcher.

## Cleanup

Generated and stale files are archived, not deleted.

- Dry-run manifest: `cache/stale_file_audit.json`
- Applied archive manifest: `cache/stale_archive/20260528_055744/manifest.json`

Archived files include root `tmp_*.json`, `tmp_*.md`, old raw X output dumps, root scratch scan scripts, formatted transcript scratch output, and Python cache folders.

## Current Canonical Flow

1. Configure sources in `config/*.json`.
2. Run live collection:
   - X: `scripts/xcli_utils.py` through `scripts/source_clis.py`
   - YouTube: `scripts/orchestrate_videos.py` through the global YT Transcript implementation
   - Blogs/RSS: `scripts/corporate_rss_discovery.py`
   - Community: `scripts/hn_scraper_standalone.py` and `scripts/reddit_scraper_standalone.py`
   - Artifacts: Hugging Face and GitHub collectors
   - Finance/Macro: `scripts/finance_market_collector.py`
   - Startup Funding/Product: `scripts/startup_funding_collector.py`
3. Aggregate with `scripts/aggregate_deep_discovery.py`, `scripts/aggregate_news.py`, or the hybrid aggregator.
4. Normalize with `scripts/queue_maintenance.py`.
5. Verify claims before drafting or publishing.

## Verification Run

Commands run on 2026-05-28:

```powershell
C:\Users\Manit\AppData\Local\Programs\Python\Python311\python.exe -m py_compile <touched scripts>
C:\Users\Manit\AppData\Local\Programs\Python\Python311\python.exe scripts\source_clis.py
C:\Users\Manit\AppData\Local\Programs\Python\Python311\python.exe scripts\queue_maintenance.py
C:\Users\Manit\AppData\Local\Programs\Python\Python311\python.exe scripts\archive_stale_files.py
C:\Users\Manit\AppData\Local\Programs\Python\Python311\python.exe scripts\archive_stale_files.py --apply
```

Results:

- Compile check passed for touched Python scripts.
- `scripts/source_clis.py` reported `XCLI: ready` and `YT Transcript CLI: ready`.
- Queue normalized from 801 to 801 items with 0 duplicate URL merges.
- 23 stale candidates were archived with a manifest.

## Remaining Intentional Hardcoding

Only machine-specific executable paths remain in `config/source_registry.json`. This is intentional: they are now configuration data, not scattered script logic. Override them with environment variables when moving machines:

- `X_DISTRIBUTION_PYTHON`
- `XCLI_SCRIPT`
- `YT_TRANSCRIPT_CLI`
- `YT_TRANSCRIPT_PY_SCRIPT`
