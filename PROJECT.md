# Project: X-Distribution Pipeline Optimization

## Architecture
- **YouTube Transcript Subsystem**: Handles video transcription using multiple fallback layers: `youtube-transcript-api` -> watch page player JSON parsing -> `yt-dlp` auto-subs -> NoteGPT Playwright scraper.
- **X Watchlist & Discovery Subsystem**: Collects posts from X (with robust cache recovery) and scans YouTube channels (with multi-stage fallbacks: playlist scan -> RSS XML feed parsing -> cached discoveries).
- **News Synthesis Subsystem**: Groups raw news items into story clusters using TF-IDF and cosine similarity, extracts atomic claims, and uses Map-Reduce summarization.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|---|---|---|---|
| 1 | Exploration & Audit | Investigate current YouTube transcript pulling, X collection, and news synthesis | None | DONE |
| 2 | YouTube Transcript (R1) | Fallback sequence: API -> Player JSON -> yt-dlp -> Playwright | M1 | DONE |
| 3 | XCLI & Discovery Recovery (R2)| Cache fallback, resilient channel scanning | M1 | IN_PROGRESS |
| 4 | News Synthesis & Compression (R3) | Chunking, claim extraction, story clustering, Map-Reduce | M1 | PLANNED |
| 5 | E2E Integration & Verification | E2E tests, make check, Forensic Audit verification | M2, M3, M4 | PLANNED |

## Interface Contracts
1. **R1 Transcript CLI Contract (`scripts/yt_transcript_cli.py`)**:
   ```python
   def fetch_transcript(youtube_url: str, output_file: str | None = None, quiet: bool = False) -> str | None:
       """Runs prioritized fallback sequence:
          youtube-transcript-api -> player JSON -> yt-dlp auto-subs -> NoteGPT (Playwright).
          Saves to output_file if provided; returns formatted string or None on failure."""
   ```

2. **R2 Channel Discovery Contract (`scripts/orchestrate_videos.py`)**:
   ```python
   def scan_channel(yt_cli: object, name: str, config: dict, days: int, max_scan: int, target_file: Path, status_ledger: list) -> list[dict]:
       """Checks yt-dlp flat playlist -> YouTube RSS feed fallback -> cached channel files.
          Dispatches warnings to logs/youtube_channel_notifications.jsonl using YouTubeNotifier."""
   ```

3. **R2 X Watchlist Cache Fallback (`scripts/x_collection_coordinator.py`)**:
   ```python
   # Fall back to cache files older than 48 hours as a last resort instead of returning empty list.
   # Emit 'WARN stale_cache_fallback' notification to logs/x_collection_notifications.jsonl.
   ```

4. **R3 Synthesis Module Contract (`scripts/news_synthesis.py`)**:
   ```python
   def synthesize_news_queue(queue_path: Path, output_path: Path) -> dict:
       """Performs:
          1. Sentence-boundary chunking and deduplication.
          2. TF-IDF + Cosine Similarity clustering of news items.
          3. Atomic claim extraction.
          4. Map-Reduce hierarchical summarization.
          Saves results to output_path."""
   ```

## Code Layout
- `scripts/yt_transcript_cli.py` - Core transcript command routing and fallback manager.
- `scripts/youtube_extractor.py` - Concrete scraper/extractor implementations (API, JSON Parser, yt-dlp).
- `scripts/x_collection_coordinator.py` - Core X timeline collector with resilient stale cache recovery.
- `scripts/orchestrate_videos.py` - YouTube channel scan orchestrator with RSS/cache fallbacks and notifier.
- `scripts/news_synthesis.py` - Advanced news synthesis and deduplication/clustering algorithms.
- `data/news_queue.json` - Normalized input queue.
- `data/synthesized_queue.json` - Clustered and summarized output queue.
- `data/transcripts_unavailable.json` - Ledger of videos without captions.
