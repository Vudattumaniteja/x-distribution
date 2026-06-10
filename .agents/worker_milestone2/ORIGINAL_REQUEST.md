## 2026-06-10T14:37:10Z
Implement Milestone 2 (R1) - Multi-Layer YouTube Transcript Seam.

Objective:
Replace the current NoteGPT-only Playwright scraper in `scripts/yt_transcript_cli.py` and `scripts/youtube_extractor.py` with a prioritized fallback transcript extraction sequence:
1. `youtube-transcript-api` (Option A).
2. Direct scrape of `ytInitialPlayerResponse` XML caption track (Option B).
3. Auto-subs via `yt-dlp --skip-download --write-auto-subs` (Option C).
4. NoteGPT Playwright scraping (Option D) as a final fallback.

Requirements:
- All layers (Options A, B, and C) must extract and format transcripts with [HH:MM:SS] timestamps (e.g. `[00:01:23] Text of video`) to match the expected format of the verify script and ensure downstream processing works seamlessly.
- Failsafe auto-detection: If a video has no captions at all (e.g., music-only, or failed extraction across all methods), do not hang or time out. Catch the error, log a warning, and add the video ID/URL to the list in `data/transcripts_unavailable.json` (as a JSON list or dictionary of unavailable video entries).
- Refactor `scripts/yt_transcript_cli.py` and `scripts/youtube_extractor.py` cleanly. Align with existing style and guidelines in AGENTS.md.
- Ensure the verification check command `python scripts/yt_transcript_cli.py verify` succeeds quickly without spawning Chrome (since it will hit the API layer first).
- Run compile checks and execute the existing python test suite to confirm no regressions are introduced.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Handoff:
Write a handoff report documenting the changes made, the exact code blocks modified, and the outputs of the compile checks, verify command, and unit tests to `C:\Users\Manit\Desktop\x-distribution\.agents\worker_milestone2\handoff.md`.
