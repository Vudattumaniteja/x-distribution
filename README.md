# X Distribution

X Distribution is a local AI and technology intelligence desk for Windows. It collects public signals from independent source lanes, preserves source-specific evidence, builds a protected active intelligence queue, generates categorized reports, and prepares verified-only manual editorial drafting packets.

It does **not** publish or reply to X automatically.

## Start Here

```powershell
$py = "C:\Users\Manit\AppData\Local\Programs\Python\Python311\python.exe"

& $py scripts\x_distribution.py routes
& $py scripts\x_distribution.py validate
& $py scripts\x_distribution.py collect --verify-only
& $py scripts\x_distribution.py collect
& $py scripts\x_distribution.py normalize
& $py scripts\build_intelligence_report.py
```

Open the interactive documentation:

- [Interactive architecture guide](docs/x-distribution-architecture.html)
- [Dense Markdown architecture guide](docs/ARCHITECTURE.md)
- [Data storage rules](references/data-storage.md)
- [Script inventory](references/script-inventory.md)

## Architecture In One Screen

```text
config/*.json
    |
    v
scripts/source_registry.py + scripts/source_clis.py
    |
    v
scripts/phase1_collect.py
    |
    +--> X watchlist and home feed
    +--> official and regional RSS
    +--> YouTube discovery and transcript queue
    +--> Reddit and Hacker News
    +--> GitHub, Hugging Face, and arXiv
    +--> finance, startup, model-market, science, and developer-sentiment lanes
    |
    v
source-specific JSON evidence under data/
    |
    v
scripts/intelligence_queue.py
    |
    v
data/news_queue.json
    |
    +--> scripts/build_intelligence_report.py
    +--> verification workflows
    +--> verified-only manual drafting packets
```

## Core Modules

| Module | Purpose |
|---|---|
| `scripts/x_distribution.py` | Operator CLI for collection, validation, routes, normalization, cleanup, reports, and drafting packets |
| `scripts/source_registry.py` | Reads source-lane configuration and queue policy |
| `scripts/source_clis.py` | Enforces pinned XCLI and YouTube transcript routes |
| `scripts/phase1_collect.py` | Runs source lanes concurrently and replaces the weekly active queue |
| `scripts/intelligence_queue.py` | Authoritative protected-queue seam: legacy reads, URL identity, dedupe, recency filtering, metadata, and atomic writes |
| `scripts/queue_maintenance.py` | Re-normalizes and ranks the active queue through the protected seam |
| `scripts/build_intelligence_report.py` | Produces categorized JSON, Markdown, and HTML intelligence views |
| `scripts/generated_codegen.py` | Produces verified-only manual drafting packets; it never invents publishable claims |

## Source Lanes

| Lane | Sources | Primary outputs |
|---|---|---|
| X | Pinned local XCLI, watched accounts, home feed | `data/x_raw_standalone.json`, `data/x_radar_standalone.json` |
| Official and regional news | Company blogs, RSS, sitemaps, regional media | `data/corporate_announcements.json` |
| YouTube | Pinned transcript CLI, prioritized channels | `data/new_videos_queue.json`, `data/transcripts/` |
| Community | Reddit MCP probe with RSS fallback, Hacker News | `data/reddit_raw_standalone.json`, `data/hn_raw_standalone.json` |
| Artifacts and research | GitHub, Hugging Face, arXiv | `data/github_discoveries.json`, `data/hf_discoveries.json`, `data/arxiv_raw_standalone.json` |
| Finance | Public market, macro, newsletter, SEC surfaces | `data/finance_raw_standalone.json`, `data/finance_signals.json` |
| Startups | Funding feeds, product launches, directory-style discovery | `data/startup_funding_signals.json`, `data/startup_collections_signals.json` |
| Model market | OpenRouter radar | `data/model_market_signals.json` |
| Science | Bio, science, and deep-tech feeds | `data/science_breakthrough_signals.json` |
| Developer sentiment | Provider status, outages, latency, pricing, adoption pain | `data/developer_sentiment_signals.json` |

## Protected State

Treat these as durable evidence:

- `data/news_queue.json`
- `data/transcripts/`
- `data/mass_transcript_pool.json`
- collector history files such as `data/github_history.json`
- `cache/claim_ledger.json`
- `cache/timestamp_oracle.json`
- verification and editorial state under `data/`

Queue writers must use `scripts/intelligence_queue.py`. Stale files must be archived with `scripts/archive_stale_files.py`; do not hard-delete them manually.

## Verification

```powershell
$py = "C:\Users\Manit\AppData\Local\Programs\Python\Python311\python.exe"

& $py -m py_compile scripts\*.py
& $py scripts\test_intelligence_queue.py
& $py scripts\test_post_generation.py
& $py scripts\validate_schemas.py
& $py scripts\source_clis.py
& $py scripts\x_distribution.py collect --verify-only
```

`make check` runs the core compile, contract, schema, and route checks when `make` is available.

## Editorial Safety

`scripts\x_distribution.py generate-posts` prepares empty manual drafting packets only for queue items carrying a `VERIFIED` or `LIKELY_TRUE` fact-check verdict. It does not generate factual copy, and the system never publishes automatically.

## Current Limitations

- Full live collection is network-dependent and can take time.
- XCLI uses a local authenticated browser-backed route and is intentionally serialized internally.
- Reddit can return `403`; the collector falls back to RSS and preserved legacy output.
- Public finance and startup feeds are useful evidence surfaces, not complete paid databases.
- Raw, normalized, and generated artifacts still coexist under `data/`; migration to the target storage layout remains incremental.
- Historical scripts remain for compatibility, but the canonical queue seam is `scripts/intelligence_queue.py`.

## Design Records

- [ADR-0001: Centralize protected intelligence queue persistence](docs/adr/0001-protected-intelligence-queue-seam.md)
- [.harness/DECISIONS.md](.harness/DECISIONS.md)
- [Domain context](CONTEXT.md)

