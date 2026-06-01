# AGENTS.md

## Project Overview
X Distribution is a local AI/tech intelligence and X-content operations system. It collects source signals from X, YouTube, RSS/blogs, Reddit, Hacker News, GitHub, Hugging Face, arXiv, finance/macro feeds, startup funding/product feeds, and SEC filings, then ranks, verifies, and converts selected items into post/reply artifacts.

## Tech Stack
- Runtime: Python 3.11 on Windows PowerShell
- Data format: JSON and Markdown files
- External CLIs: XCLI and YT Transcript CLI via `scripts/source_clis.py`
- Main storage: `config/`, `data/`, `cache/`, `logs/`

## Quick Start
- Check routes and schemas: `make check`
- Run schema validation only: `make validate`
- Run compile check only: `make test`
- Run collection: `make collect`
- Normalize queue: `make normalize`
- Cleanup stale generated files: `make cleanup`

If `make` is not installed, run the Python commands shown in `Makefile` directly with:

```powershell
C:\Users\Manit\AppData\Local\Programs\Python\Python311\python.exe
```

## Hard Constraints
1. Use `scripts/source_clis.py` for all XCLI and YT Transcript CLI routing.
2. Do not scrape X or YouTube through browser tools when a pinned CLI route exists.
3. Keep source lists in `config/*.json`, not duplicated in scripts.
4. Treat `data/news_queue.json`, transcript files, and verification ledgers as protected state.
5. Archive stale generated files through `scripts/archive_stale_files.py`; do not hard-delete them manually.
6. Run schema validation before claiming the pipeline is healthy.
7. Run Python compile checks after script edits.
8. Preserve `system-snapshot/` as historical reference unless the user explicitly asks to remove it.
9. Avoid posting or replying to X automatically; this system prepares manual-copy artifacts.
10. Log significant architecture decisions in `.harness/DECISIONS.md`.

## Topic Docs
- `references/data-storage.md` - storage rules, protected data, and target layout.
- `references/system-optimization-report.md` - recent architecture cleanup and verification.
- `references/config-schemas.md` - JSON file shapes and source registry schema.
- `references/news-hunting-agents.md` - news discovery agent protocols.
- `references/reply-hunting-agents.md` - reply opportunity protocols.
- `references/fact-checking.md` - verification workflow.

## Session Workflow
- Clock in: read `.harness/PROGRESS.md`, `.harness/DECISIONS.md`, and `.harness/feature_list.json`.
- Work one active feature at a time unless subagents are doing read-only audits.
- Before handoff: run `make check` or document the exact failing command in `.harness/PROGRESS.md`.
- Clock out: update `.harness/PROGRESS.md`, `.harness/session_state.json`, and feature states.
