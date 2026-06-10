# Implementation Plan - X-Distribution Pipeline Audit, Robustification, and Optimization

## Milestone 1: Exploration and Codebase Audit
- **Goal**: Analyze the current implementation of YouTube transcript extraction, X watchlist/home collection lanes, channel scanning, and news synthesis.
- **Verification**: Explorer report detailing current code layout, functions, and files to be modified.

## Milestone 2: R1 - Multi-Layer YouTube Transcript Seam
- **Goal**: Implement a multi-layered fallback transcript extraction strategy in `scripts/yt_transcript_cli.py` (or the relevant script).
  1. `youtube-transcript-api`
  2. Parse `ytInitialPlayerResponse` from YouTube page player JSON.
  3. Run `yt-dlp --skip-download --write-auto-subs` and parse/clean VTT.
  4. NoteGPT Playwright fallback.
- **Verification**: Verified using a verify check command (e.g. `python scripts/yt_transcript_cli.py verify`) with unit tests for each layer. Videos with no captions are marked in `data/transcripts_unavailable.json`.

## Milestone 3: R2 - Robust XCLI and Video Discovery Error Recovery
- **Goal**: Make X watchlist/home collection and video discovery resilient to failures.
  1. Switch to cache files and emit detailed warnings on timeouts or page wait failures.
  2. Handle restricted feeds or no recent uploads during channel scanning.
- **Verification**: Test execution with simulated timeouts and restricted feeds, validating correct fallback and warning outputs.

## Milestone 4: R3 - Advanced News Synthesis and LLM Workload Reduction
- **Goal**: Implement synthesis algorithms:
  1. Semantic chunking & deduplication.
  2. Atomic claim extraction.
  3. Claim merging & story clustering.
  4. Hierarchical Map-Reduce summarization.
- **Verification**: Execution on mock high-density feeds showing >= 50% context reduction while preserving all atomic claims.

## Milestone 5: E2E Integration and Forensic Audit
- **Goal**: Integrate all features, verify that the pipeline runs successfully (`scripts/x_distribution.py collect` saves validated `data/news_queue.json`), and pass the Forensic Audit.
- **Verification**: Run `make check`, run E2E test cases, and verify clean audit trace.
