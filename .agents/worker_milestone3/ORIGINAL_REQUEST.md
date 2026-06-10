## 2026-06-10T20:16:08Z
Implement Milestone 3 (R2) - Robust XCLI and Video Discovery Error Recovery.

Objective:
Make the X watchlist collection and YouTube channel scanning resilient to timeouts, feed restrictions, and page failures.

Requirements:
1. X Watchlist Cache Fallback (`scripts/x_collection_coordinator.py`):
   - Refactor the collection logic so that when a live timeline scrape or home feed collection fails (due to XCLI/Playwright timeouts or wait failures), the coordinator switches to cached files (e.g. `cache/xcli_home.json` or channel timeline files).
   - Crucially, if the cache file is older than `WATCHLIST_CACHE_MAX_HOURS` (48 hours), use it anyway as a last resort instead of returning an empty list `[]` (which causes downstream pipeline starvation/failures).
   - When falling back to a stale cache, emit a detailed warning notification (`WARN stale_cache_fallback`) to `logs/x_collection_notifications.jsonl`.

2. Resilient Channel Scanning (`scripts/orchestrate_videos.py`):
   - Refactor `scan_channel` or the video discovery loop so that failures on specific channels (due to restricted feeds, network issues, or no recent uploads) do not crash the pipeline.
   - Implement a robust multi-stage fallback sequence:
     a. `yt-dlp` flat playlist scan (default).
     b. YouTube RSS feed parser (Option B) fetching `https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}`.
     c. Read from local cached channel history files (Option C) as a last resort.
   - Implement a `YouTubeNotifier` class (modeled after the `XNotifier` architecture in `scripts/xcli_utils.py` or `scripts/x_collection_coordinator.py`) that catches exceptions and logs warning notifications to `logs/youtube_channel_notifications.jsonl`.

3. Verify:
   - Run compile checks and execute the existing unit tests to confirm no regressions are introduced.
   - Write test scenarios or checks (simulating timeouts/failures) to verify that stale caches are loaded and warning notifications are emitted.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Handoff:
Write a handoff report documenting the changes made, the exact code blocks modified, and the outputs of the compile checks and test verification to `C:\Users\Manit\Desktop\x-distribution\.agents\worker_milestone3\handoff.md`.
