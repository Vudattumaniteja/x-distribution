---
name: platinum-intel-factory
description: Maximum Recall technical intelligence factory. Automates the technical discovery pipeline (X, RSS, Sitemaps, Transcripts) and executes Fractal Extraction via micro-interrogations to capture every atomic claim, nuance, and opinion into a comprehensive Encyclopedia.
---

# Platinum Intelligence Factory — Orchestrator Guide

This skill implements the **Maximum Recall / Fractal Extraction** technical intelligence pipeline. When triggered, you are mandated to execute the end-to-end "Intelligence Factory" without asking for permission at each stage. 

**Core Mandate:** Do NOT summarize. Your goal is to capture *every single atomic update, nuance, and opinion* across the dataset.

## 🏭 The Execution Protocol

### Stage 1: Raw Discovery (Multi-Lane Scrape)
Execute these lanes in parallel:
1. **Lane A (X/Twitter):** `x-bridge twitter_scrape --handle home --count 100`
2. **Lane B (Corporate):** `python scripts/corporate_rss_discovery.py`
3. **Lane C (Stealth):** `python scripts/sitemap_sentinel_standalone.py`
4. **Lane D (TLDR):** `python scripts/tldr_direct_fetch.py` (Direct fetch to bypass RSS lag)

### Stage 2: Deep Signal (yt-transcript)
**Mandate:** Use the `yt-transcript` CLI directly.
1. Run `yt-transcript latest <url>` for each channel in `config/youtube_channels.json`.
2. Run `python scripts/final_transcript_aggregator.py` to consolidate into `data/mass_transcript_pool.json`.

### Stage 3: Unified Aggregation & High-Resolution Chunking
1. Run `python scripts/phase1_collect.py` to merge all discoveries into `data/news_queue.json`.
2. **Chunking for Context:** Ensure data is logically chunked (target ~50k tokens per chunk) to combat "Lost in the Middle" syndrome during agent processing. 

### Stage 4: Fractal Extraction (The Micro-Interrogation Phase)
Invoke specialized sub-agents in parallel using `invoke_agent`. **Do NOT ask them to summarize.** Provide them with highly specific, narrow prompts (Micro-Interrogations).

**Agent Prompts MUST follow this structure:**
*   "Extract every single numerical change related to latency, pricing, token limits, or context windows."
*   "Extract every direct quote from a user expressing dissatisfaction with a specific feature, tool, or update."
*   "List every URL, codename, or unannounced project mentioned in passing."

**Output Format Rule:** Agents must output raw, atomic claims mapped to exact source lines/timestamps. Each claim must be tagged with `[Entity]`, `[Category]`, `[Sentiment]`, `[Source Type]`, and an `[Obscurity Score 1-10]`.

### Stage 5: Append-Only Synthesis (The Encyclopedia)
1. Read all intermediate extraction files from the sub-agents.
2. **Rule:** Deduplicate exact string matches, but otherwise **Append Only**. Do not reduce or delete "low score" items.
3. Synthesize into `ATOMIC_CLAIM_BANK.md`. This is a massive, navigable Markdown database sorted by the tags generated in Stage 4.

## 🧵 The "Non-Pro" Viral Thread Blueprint
Once extraction is complete, offer a high-value viral thread based on the most actionable intelligence.
**The Dot-Connecting Rule:**
- Connect **Infrastructure** ➡️ **Tooling** ➡️ **Value**.
- **Template:** Use the "Scroll-Stopper Hook" + "The Big Shift" + "The Value Gift" structure.

## 🛠️ Error Handling & Uptime
- **ArXiv API:** If 429 occurs, use `web_fetch` on the abstract URL directly.
- **Tool Failures:** If a scraper fails, note it in the log and continue. Never stall the pipeline.

## 📋 Hard Mandates (Absolute)
1. **NO SUMMARIZATION:** Never collapse separate announcements into one vague bullet.
2. **Cold Verbs Only:** No "insane," "revolutionary," or "game-changing."
3. **Verification:** Every atomic claim must have a source citation (file + snippet/timestamp).
