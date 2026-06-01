# ADR-0002: Consolidate collection lanes into a deep unified adapter interface

Date: 2026-05-31

## Status
Proposed

## Context
The collection system uses four separate lanes to gather intelligence signals:
- Lane A: X Feed (`xcli_utils.py`, `phase1_collect.py`)
- Lane B: Corporate RSS (`corporate_rss_discovery.py`)
- Lane C: YouTube discovery (`orchestrate_videos.py`, `orchestrate_all_latest.py`, `yt_transcript_cli.py`)
- Lane D: Community discussion (`hn_scraper_standalone.py`, `reddit_mcp_buddy_collect.py`)

Currently, these lanes are implemented as shallow modules. Their programmatic interfaces match the high complexity of their underlying implementations. Rather than importing code, they leverage shell execution (spawning Python and Node subprocesses) and communicate via side-effect files written to the local filesystem. This design induces high subprocess execution overhead and fragments locality.

Furthermore, we identified two leaked seams in the YouTube discovery module:
1. A circular dependency loop: the `youtube_extractor.py` module imports `source_clis.py` to call `yt_transcript_command` (which spawns `yt_transcript_cli.py` as a subprocess), while `yt_transcript_cli.py` imports `youtube_extractor.py` as a module.
2. A path leakage: the default path for `yt_transcript_py_script` is configured to an absolute directory outside the active workspace.

## Decision
We will establish a deep unified collection adapter interface (a programmatic seam) that consolidates all collection lanes. 

1. **Unified Collection Adapter**: Define a single programmatic adapter interface:
   ```python
   class CollectionAdapter:
       def collect(self, source_config: dict) -> list[dict]:
           pass
   ```
   This adapter interface accepts programmatic configurations and yields normalized signal payloads in-memory, bypassing filesystem writes and subprocess overhead.

2. **In-Process Integration**: Implement concrete adapters for X, Corporate RSS, YouTube, and Community lanes inside the codebase. Banish `subprocess.run` calls for internal scripts, leveraging Python module imports instead.

3. **Resolve YouTube Leaks**:
   - Refactor `youtube_extractor.py` to remove its dependency on `source_clis.py`. Direct script execution of `youtube_extractor.py` must import and invoke the extractor functions directly rather than calling the global CLI subprocess.
   - Restrict runtime script configurations in `source_registry.json` to paths relative to the workspace root, preserving locality.

## Consequences
- Subprocess execution overhead is eliminated for internal module integration.
- The collection logic becomes deep, hiding network and parsing complexity behind a clean in-memory adapter interface.
- Collection logic, validation, and error-handling leverage in-process python structures, enhancing testability.
- Locality of configurations is restored by eradicating absolute host path leaks.
