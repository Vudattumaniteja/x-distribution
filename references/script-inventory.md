# Script Inventory

Updated: 2026-05-29

This inventory classifies `scripts/*.py` by operating role so agents know what is safe to run, what mutates important data, and what is legacy.

## Active Core

These scripts define the live control plane and queue path.

| Script | Role |
|---|---|
| `source_clis.py` | Canonical route authority for XCLI, YT Transcript CLI, and workspace Python scripts |
| `xcli_utils.py` | Safe read-only XCLI helpers with UTF-8 handling and timeline validation |
| `source_registry.py` | Source registry loader and helper API |
| `tier_policy.py` | Source tier and quarantine helper API |
| `x_distribution.py` | Master CLI for collect, validate, normalize, verify, cleanup, and storage checks |
| `validate_schemas.py` | Practical schema validator for critical config and data files |
| `phase1_collect.py` | Full Phase 1 collection across X, RSS, YouTube, Reddit, HN, GitHub, arXiv, finance, and startup funding |
| `master_poller.py` | Three-poller collection workflow into `data/raw_context_pool.json` |
| `queue_maintenance.py` | Canonical URL dedupe and queue normalization |
| `intelligence_queue.py` | Authoritative protected-queue seam: legacy shape reads, canonical URL identity, provenance merging, recency filtering, and atomic writes |
| `aggregate_deep_discovery.py` | Merge configured collector outputs into the news queue |
| `aggregate_news.py` | Legacy-compatible agent-output aggregation |
| `final_hybrid_aggregator.py` | Hybrid queue/ranking aggregator |
| `merge_breadth.py` | Merge breadth-verified items into queue |
| `weekly_sweep_orchestrator.py` | Weekly sweep wrapper using canonical X/YT routes |

## Active Collectors

These scripts collect or refresh source-specific data.

| Script | Output |
|---|---|
| `corporate_rss_discovery.py` | `data/corporate_announcements.json` |
| `reddit_mcp_buddy_collect.py` | `data/reddit_raw_standalone.json`; preferred Reddit collector using reddit-mcp-buddy first, RSS second, legacy preservation third |
| `reddit_mcp_buddy_bridge.mjs` | Node bridge that calls reddit-mcp-buddy package handlers directly when transport use is unreliable |
| `reddit_scraper_standalone.py` | Legacy Reddit JSON collector and preservation fallback for `data/reddit_raw_standalone.json` |
| `hn_scraper_standalone.py` | `data/hn_raw_standalone.json` |
| `hf_tracker_standalone.py` | `data/hf_discoveries.json`, `data/hf_history.json` |
| `github_monitor_standalone.py` | `data/github_discoveries.json`, `data/github_history.json` |
| `github_releases_discovery.py` | `data/release_discoveries.json`, `data/release_history.json` |
| `arxiv_sentinel_standalone.py` | `data/arxiv_raw_standalone.json` |
| `finance_market_collector.py` | `data/finance_raw_standalone.json`, `data/finance_signals.json`; AI-linked finance, macro, newsletter, and SEC signals |
| `startup_funding_collector.py` | `data/startup_funding_raw.json`, `data/startup_funding_signals.json`; AI startup funding, Series A/B/C, investor, and product-launch signals |
| `semantic_scholar_fetch.py` | arXiv/Semantic Scholar enrichment |
| `sitemap_sentinel_standalone.py` | `data/sitemap_discoveries.json`, `data/sitemap_history.json` |
| `tldr_direct_fetch.py` | Direct TLDR/company fetch enrichment |
| `x_radar_standalone.py` | `data/x_radar_standalone.json` |
| `x_timeline_scraper_standalone.py` | `data/x_raw_standalone.json` |
| `orchestrate_videos.py` | `data/new_videos_queue.json` |
| `orchestrate_all_latest.py` | `data/transcripts/*.txt` |
| `orchestrate_mass_pool.py` | `data/mass_transcript_pool.json` |
| `final_transcript_aggregator.py` | transcript pool aggregation |
| `flash_hunt.py` | fast high-impact news queue additions |

## Verification And Ranking

| Script | Role |
|---|---|
| `truth_oracle.py` | GitHub/HF/Wayback/SEC timestamp evidence fetches |
| `temporal_sentinel.py` | Temporal novelty and stale-claim checks |
| `temporal_sentinel_test.py` | Temporal sentinel regression tests |
| `temporal_regression_test.py` | Temporal regression harness |
| `temporal_audit_tool.py` | Queue temporal audit |
| `seo_refresh_test.py` | SEO/recycled-content checks |
| `reverify_news.py` | Reverification helper |
| `rolling_baseline.py` | Seen-hash stale filter |
| `rank_replies.py` | Reply opportunity ranking |
| `summarize_sweep.py` | Queue summary helper |
| `test_transcript.py` | Transcript route smoke test |

## Diagnostic And Operations

| Script | Role |
|---|---|
| `archive_stale_files.py` | Safe archive of generated/stale files |
| `chunk_data.py` | Split large data files into chunks |
| `hyper_chunker.py` | Chunk data for Hyper scan workflows |
| `hyper_distributor.py` | Assign Hyper chunks to workers; run after chunking |
| `hyper_scan_worker.py` | Process a Hyper scan queue |
| `hybrid_sweep.py` | Manual discovery sweep wrapper |
| `orchestrate_reply_hunt.py` | Reply hunt orchestration |
| `x_diagnostic.py` | Playwright/X diagnostic screenshot |

## Legacy Or Archive Candidates

Keep these only for compatibility, recovery, or explicit legacy-mode runs.

| Script | Reason |
|---|---|
| `yt_transcript_cli.py` | Superseded by global YT Transcript route through `source_clis.py` |
| `youtube_channel_fetcher.py` | RSS-only YouTube discovery; legacy unless explicitly requested |
| `youtube_extractor.py` | Local extractor fallback; prefer pinned YT Transcript CLI |
| `rss_discovery.py` | Older YouTube RSS flow |
| `notegpt_scraper.py` | Legacy transcript path; current docs forbid NoteGPT as primary |
| `check_descriptions.py` | One-off YouTube description probe |
| `fresh_news_finder.py` | One-off news helper |
| `generated_codegen.py` | Verified-only manual drafting packet preparation; intentionally does not invent post copy |
| `process_news.py` | Disabled compatibility guard; historical implementation embedded prototype stories and must not write protected queue state |
| `one_off_resolve.py` | One-off resolver |
| `resolve_any.py` | One-off YouTube handle resolver |
| `resolve_and_fetch.py` | One-off resolve/fetch helper |
| `resolve_channel_id.py` | One-off channel config helper |
| `audit_transcript.py` | Transcript diagnostic |
| `audit_transcript_v2.py` | Transcript diagnostic |

## Risk Notes

- `phase1_collect.py`, `master_poller.py`, `aggregate_news.py`, `final_hybrid_aggregator.py`, `process_news.py`, `queue_maintenance.py`, `flash_hunt.py`, `merge_breadth.py`, and `aggregate_deep_discovery.py` can mutate `data/news_queue.json`.
- `archive_stale_files.py --apply` moves files into `cache/stale_archive`; review dry-run output first.
- X and YouTube collectors depend on local authenticated CLIs and can fail for reasons outside this repo.
- Reddit first probes reddit-mcp-buddy, then falls back to subreddit RSS because direct `reddit.com/*.json` and `old.reddit.com/*.json` can return 403 from automation.
- Finance sources include public RSS and SEC EDGAR surfaces; paywalled sources such as Bloomberg may expose only feed summaries or may intermittently reject requests.
- Startup funding sources use public RSS surfaces from TechCrunch, Crunchbase News, VentureBeat, SiliconANGLE, EU-Startups, and Product Hunt; they are evidence sources, not complete private-market databases.
- GitHub, arXiv, finance, startup funding, and corporate collectors depend on public network availability and rate limits.
