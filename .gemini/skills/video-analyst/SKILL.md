---
name: video-analyst
description: Automates AI-focused YouTube intelligence. Use when Gemini CLI needs to find the latest videos from a curated list of AI builders, extract transcripts via proxy-scrapers, and distill technical workflows for the news queue and X-Distribution engine.
---

# Video Analyst

This skill automates the "Intelligence Factory" for YouTube-sourced AI news. It handles channel monitoring, transcript extraction (bypassing 429 blocks), and technical distillation.

## Core Workflows

### 1. Discovery (RSS Scouting)
Monitor the curated list of 13+ AI channels for new technical tutorials or breaking news.
- **Reference:** See `references/channel-mappings.md` for IDs.
- **Action:** Run `scripts/rss_discovery.py` to poll feeds.
- **Rule:** Differentiate between "Full Videos" (technical value) and "Shorts" (viral hook potential).

### 2. Extraction (The NoteGPT Exploit)
Bypass direct YouTube 429 blocks by using the NoteGPT proxy-scraper.
- **Script:** `scripts/notegpt_scraper.py`
- **Mechanism:** Launches a headless browser (Playwright), navigates to `notegpt.io/detail?id={ID}`, waits for AI rendering, and extracts clean text.
- **Usage:** `python scripts/notegpt_scraper.py {VIDEO_ID}`

### 3. Technical Distillation
Analyze extracted transcripts for "Actionable, Concrete, and Timely" (AC&T) signals.
- **Focus:** Model IDs, HLE benchmarks, specific n8n/Claude Code prompts, and architectural shifts.
- **Output:** Populate `data/news_queue.json` and trigger `x-original-post-factory`.

## Technical Reference

### Bypassing 429 Blocks
If direct extraction fails:
1. Construct proxy URL: `https://notegpt.io/detail?id={ID}&type=1&utm_source=youtube-transcript-generator`
2. Use Playwright to wait for `.transcript-item` rendering.
3. Fallback to broad `inner_text("body")` if specific selectors fail.

### Categorization Logic
- **Shorts:** < 60s. Focus on "Viral Hook" in X posts.
- **Reels:** 60s - 120s. Focus on "Problem/Solution" narrative.
- **Full Videos:** > 120s. Focus on "Technical Breakdown" and code-level insights.
