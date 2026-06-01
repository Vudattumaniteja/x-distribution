# Data Storage Guide

Updated: 2026-05-28

This document explains where X Distribution stores transcripts, news, social-source captures, verification state, generated posts, and cleanup artifacts.

## Storage Rules

The system separates files into four practical classes:

| Class | Meaning | Delete? |
|---|---|---|
| Canonical data | Current source-of-truth data used by the pipeline | No |
| Raw collector output | Latest output from source collectors | No, unless archived after replacement |
| Cache / ledger | Verification or dedupe memory | No, unless intentionally resetting state |
| Generated scratch | Temporary diagnostics, old run outputs, Python cache | Archive first, then optionally delete archive later |

Do not delete canonical data because it breaks repeatability. Temporary files should be moved into `cache/stale_archive/<timestamp>/` with a manifest.

## Canonical Data

### `data/news_queue.json`

Main active intelligence queue.

Used for:

- news ranking
- fact checking
- post generation
- downstream reporting

Current format:

```json
{
  "metadata": {
    "description": "Active intelligence queue aggregated from configured source registry outputs",
    "max_items_kept": 1000,
    "dedupe": "canonical_url"
  },
  "last_updated": "ISO timestamp",
  "total_items": 0,
  "items": []
}
```

Maintenance:

```powershell
C:\Users\Manit\AppData\Local\Programs\Python\Python311\python.exe scripts\queue_maintenance.py
```

### `data/transcripts/`

Canonical folder for YouTube transcript text files created by the YT Transcript route.

Keep these files. They are expensive to recollect and are used for long-form video analysis.

### `data/transcript_*.txt`

Older transcript files stored directly under `data/`.

These should be treated as protected until migrated into `data/transcripts/` or included in `data/mass_transcript_pool.json`.

### `data/mass_transcript_pool.json`

Aggregated transcript pool used for bulk analysis.

Keep this file. It is a normalized working corpus built from many transcript pulls.

## Raw Collector Outputs

These files are collector outputs. They can be regenerated, but they are still useful evidence for what the last collection found.

| File | Source |
|---|---|
| `data/corporate_announcements.json` | corporate RSS/blog discovery |
| `data/hn_raw_standalone.json` | Hacker News collector |
| `data/reddit_raw_standalone.json` | Reddit collector via reddit-mcp-buddy probe, RSS fallback, and legacy JSON preservation fallback |
| `data/arxiv_raw_standalone.json` | arXiv / research collector |
| `data/finance_raw_standalone.json` | AI-linked finance, market, macro, newsletter, and SEC collector |
| `data/finance_signals.json` | Filtered AI market intelligence signals promoted from finance sources |
| `data/startup_funding_raw.json` | AI startup fundraising and product-launch collector |
| `data/startup_funding_signals.json` | Filtered Series A/B/C, funding, investor, and product signals |
| `data/new_videos_queue.json` | latest YouTube video discovery |
| `data/x_radar_standalone.json` | X radar collector |
| `data/x_raw_standalone.json` | X timeline collector |
| `data/hf_discoveries.json` | Hugging Face discoveries |
| `data/github_discoveries.json` | GitHub repo discoveries |
| `data/release_discoveries.json` | GitHub release discoveries |
| `data/sitemap_discoveries.json` | sitemap discovery |

History files preserve dedupe state:

| File | Purpose |
|---|---|
| `data/hf_history.json` | seen Hugging Face artifacts |
| `data/github_history.json` | seen GitHub repos |
| `data/release_history.json` | seen GitHub releases |
| `data/sitemap_history.json` | seen sitemap URLs |

Do not delete history files unless you want the next collector run to rediscover old items.

## Post And Reply Outputs

| File | Purpose |
|---|---|
| `data/approved_posts.json` | generated post variants and grades |
| `data/reply_opportunities.json` | reply targets and drafted replies |
| `data/sent_posts.json` | manually tracked sent posts |
| `data/performance_history.json` | performance reports |
| `data/credibility_scores.json` | source/account credibility scores |

These files are part of the content loop, not scratch output.

## Evolution State

| File | Purpose |
|---|---|
| `data/evolution_state.json` | current self-evolution status |
| `data/evolution_backlog.json` | ranked improvement backlog |

Keep these if you want the system to remember what it has already planned or implemented.

## Cache And Ledgers

| File or folder | Purpose | Keep? |
|---|---|---|
| `cache/claim_ledger.json` | claim verification memory | yes |
| `cache/timestamp_oracle.json` | timestamp/source verification cache | yes |
| `cache/search_results.json` | cached verification search results | yes |
| `cache/invalid_transcripts/` | rejected transcript copies for debugging | archive after review |
| `cache/yt_transcript_cli_probe_*` | transcript CLI probe outputs | archive after review |
| `cache/stale_archive/` | archived stale files with manifests | yes until no longer needed |
| `cache/stale_file_audit.json` | dry-run stale cleanup manifest | yes |

The cache is not all disposable. Ledger files carry memory that prevents repeated bad verification or repeated duplicate work.

## Logs

| Folder | Purpose |
|---|---|
| `logs/agent_runs/` | run summaries from news/reply/evolution agents |
| `logs/fact_checks/` | fact-check logs |
| `logs/evolution/` | evolution logs |
| `logs/performance/` | performance logs |
| `logs/replies/` | reply logs |
| `logs/news/` | news logs |

Debug screenshots and old run logs may be archived, but logs are useful when explaining how a source entered the queue.

## Source Configuration

Source lists should live in config files, not scripts.

| File | Controls |
|---|---|
| `config/source_registry.json` | queue policy, collector outputs, YouTube discovery method/window, external CLI paths, GitHub/arXiv/Hugging Face source lists, stale archive policy |
| `config/source_tiers.json` | T1/T2/T3/T4 source domains and quarantine list |
| `config/community_sources.json` | Reddit and Hacker News sources, Reddit MCP/RSS fallback settings, and keywords |
| `config/finance_sources.json` | Bloomberg/CNBC/India business/TLDR/SEC finance sources and AI-market relevance filters |
| `config/startup_sources.json` | TechCrunch/Crunchbase/VentureBeat/Product Hunt startup funding and product sources |
| `config/corporate_blogs.json` | official company blogs/RSS |
| `config/youtube_channels.json` | YouTube channel IDs |
| `config/followed_accounts.json` | X/Twitter watchlist |

## Cleanup Policy

Use the archive script:

```powershell
C:\Users\Manit\AppData\Local\Programs\Python\Python311\python.exe scripts\archive_stale_files.py
C:\Users\Manit\AppData\Local\Programs\Python\Python311\python.exe scripts\archive_stale_files.py --apply
```

The first command writes a dry-run manifest to `cache/stale_file_audit.json`.

The second command moves configured stale files into `cache/stale_archive/<timestamp>/` and writes `manifest.json`.

The archive policy is controlled by:

```text
config/source_registry.json -> stale_file_policy
```

## Current Storage Problems

The current `data/` folder still mixes three layers:

- raw collector outputs
- normalized queue data
- generated content artifacts

This works, but it makes debugging slower because raw, normalized, and final outputs sit side by side.

## Recommended Next Layout

Target layout:

```text
data/
  raw/
    youtube/
    x/
    reddit/
    hacker_news/
    rss/
    github/
    huggingface/
    arxiv/
    finance/
    startups/

  normalized/
    news_queue.json
    videos_queue.json
    transcript_pool.json

  verified/
    claims.json
    announcements.json

  content/
    approved_posts.json
    reply_opportunities.json
    sent_posts.json
    performance_history.json

  state/
    credibility_scores.json
    evolution_state.json
    evolution_backlog.json

  exports/
    reports/
```

Migration should be done with compatibility shims. Existing scripts should keep working while new paths are introduced through `config/source_registry.json`.

## Safe Migration Order

1. Add new path settings to `config/source_registry.json`.
2. Update writers to write both old and new paths for one run.
3. Update readers to prefer new paths and fallback to old paths.
4. Run collection and verify item counts match.
5. Move old files into `cache/stale_archive/`.
6. Remove fallback reads only after multiple clean runs.

Do not move transcript or queue files in one step without fallback readers. These are the highest-value stored artifacts.
