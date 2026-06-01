---
name: platinum-intel-factory
description: Zero-hand-holding technical intelligence factory. Automates the 6-stage technical discovery pipeline (X, RSS, Sitemaps, yt-transcript) and parallel fleet extraction to deliver "Platinum" (verified, 48h) AI news and viral X threads.
---

# Platinum Intelligence Factory — Orchestrator Guide

This skill implements the **Zero-Hand-Holding** technical intelligence pipeline. When triggered, you are mandated to execute the end-to-end "Intelligence Factory" without asking for permission at each stage.

## 🏭 The 6-Stage Execution Protocol

### Stage 1: Raw Discovery (Multi-Lane Scrape)
Execute these lanes in parallel to capture all technical signals from the last 48 hours:
1. **Lane A (X/Twitter):** `C:\Users\Manit\AppData\Local\Programs\Python\Python311\python.exe "C:\Users\Manit\Desktop\Twitter automation\cli.py" twitter_home --count 100`
2. **Lane B (Corporate):** `C:\Users\Manit\AppData\Local\Programs\Python\Python311\python.exe scripts/corporate_rss_discovery.py`
3. **Lane C (Stealth):** `C:\Users\Manit\AppData\Local\Programs\Python\Python311\python.exe scripts/sitemap_sentinel_standalone.py`
4. **Lane D (TLDR):** `C:\Users\Manit\AppData\Local\Programs\Python\Python311\python.exe scripts/tldr_direct_fetch.py` (Direct fetch to bypass RSS lag)

### Stage 2: Deep Signal (yt-transcript)
**Mandate:** Use the pinned YT Transcript CLI directly. Do not use secondary transcript sources.
1. Run `C:\Users\Manit\AppData\Local\Programs\Python\Python311\python.exe C:\Users\Manit\.gemini\x-distribution\scripts\yt_transcript_cli.py latest <url>` for each channel in `config/youtube_channels.json`.
2. Run `C:\Users\Manit\AppData\Local\Programs\Python\Python311\python.exe scripts/final_transcript_aggregator.py` to consolidate findings into `data/mass_transcript_pool.json`.

### Stage 3: Unified Aggregation
1. Run `C:\Users\Manit\AppData\Local\Programs\Python\Python311\python.exe scripts/phase1_collect.py` to merge all discoveries into `data/news_queue.json`.
2. Apply a strict **48-hour cutoff**. Purge any news older than today - 48h.

### Stage 4: Surgical Partitioning
1. Run `C:\Users\Manit\AppData\Local\Programs\Python\Python311\python.exe scripts/stage4_partition.py` to split the pooled news into 6 segments in `tmp_segments/`.

### Stage 5: Fleet Extraction (Map Phase)
Invoke these 6 sub-agents in parallel using `invoke_agent`. Task each with scanning their segment for:
1. **Drops** (New models/tools)
2. **Moves** (Deals/Pivots)
3. **Architecture** (Technical SOTA)
4. **Economics** (Funding/Pricing)

### Stage 6: Final Synthesis (The Platinum Report)
1. Read all `tmp_segments/gold_*.md` files.
2. Synthesize into `MASTER_EXTRACTION_REPORT.md`.
3. **Deliver the Daily Deep Dive** to the user in a clean, clinical table format.

## 🧵 The "Non-Pro" Viral Thread Blueprint
Once extraction is complete, you must offer a high-value viral thread based on the most "interesting" story found.

**The Dot-Connecting Rule:**
- Connect **Infrastructure** (e.g. SpaceX compute) ➡️ **Tooling** (e.g. /goal command) ➡️ **Value** (e.g. 10x productivity).
- **Template:** Use the "Scroll-Stopper Hook" + "The Big Shift" + "The Value Gift" structure.

## 🛠️ Error Handling & Uptime
- **ArXiv API:** If 429 occurs, use `web_fetch` on the abstract URL directly.
- **Tool Failures:** If a scraper fails, note it in the log and continue. Never stall the pipeline.
- **Cleanup:** Always delete `tmp_segments/` after synthesis.

## 📋 Hard Mandates (Absolute)
1. **Cold Verbs Only:** No "insane," "revolutionary," or "game-changing."
2. **Verification:** Every claim must have a source citation (file + snippet).
3. **One-Sentence Rule:** One question ➡️ One agent ➡️ One answer.
