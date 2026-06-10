# Original User Request

## Initial Request — 2026-06-10T20:01:58Z

Audit, robustify, and optimize the X-Distribution pipeline. Focus on making the YouTube transcript pulling and X collection source lanes resilient to failures, and implement advanced news synthesis algorithms to compress information, reduce LLM prompt tokens, and enhance intelligence reports.

Working directory: ~/teamwork_projects/x_distribution_optimization
Integrity mode: development

## Requirements

### R1. Multi-Layer YouTube Transcript Seam
Replace the current fragile NoteGPT Playwright scraper with a multi-layered fallback transcript extraction strategy:
1. Attempt to fetch transcripts directly via `youtube-transcript-api` (API-based, fast, no browser).
2. If that fails, attempt to scrape the direct YouTube page player JSON data (`ytInitialPlayerResponse`) and parse the XML caption tracks.
3. If that fails, attempt to download auto-subtitles using `yt-dlp` (`--skip-download --write-auto-subs`), parsing and cleaning the VTT format.
4. Fall back to NoteGPT Playwright scraping only if all other methods fail.

### R2. Robust XCLI and Video Discovery Error Recovery
Handle Playwright/XCLI timeouts and page wait failures gracefully:
1. Ensure the X watchlist and home collection source lanes robustly switch to cache files and emit detailed health warnings instead of causing pipeline failures.
2. Implement robust channel scanning in video discovery, avoiding failures when specific channels have restricted feeds or no recent uploads.

### R3. Advanced News Synthesis and LLM Workload Reduction
Implement algorithms to compress incoming raw information before LLM generation:
1. **Semantic Chunking & Deduplication**: Filter out repetitive text chunks within long transcripts and sitemaps.
2. **Atomic Claim Extraction**: Parse raw feeds into key factual claims with citations.
3. **Claim Merging & Story Clustering**: Group related items from multiple source lanes (e.g., a YouTube video drop + a Hacker News thread + an official blog post about the same release) to synthesize them.
4. **Hierarchical Summarization**: Implement a Map-Reduce workflow to summarize large inputs incrementally, minimizing the prompt window size for the final LLM intelligence report.

## Acceptance Criteria

### Execution & Integration
- [ ] Running `make check` (compilation, schema validation, and route checks) passes with 0 errors.
- [ ] The core pipeline `scripts/x_distribution.py collect` runs to completion without errors and saves a validated `data/news_queue.json`.

### YouTube Transcript Reliability
- [ ] A verify check command (e.g. `python scripts/yt_transcript_cli.py verify`) succeeds, extracting transcripts rapidly without spawning a Chrome browser.
- [ ] Failsafe auto-detection: videos without any captions are marked as unavailable in `data/transcripts_unavailable.json` without timing out the runner.

### Workload Reduction & Synthesis
- [ ] The new synthesis module deduplicates and clusters news queue items referencing the same URL or title.
- [ ] A verification run on mock high-density feeds (long transcripts and community discussions) shows a reduction in final generation context size by >= 50% while retaining all essential **Atomic claims**.
