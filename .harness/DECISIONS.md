# Design Decisions

## 2026-05-28: Initialize harness around existing script workspace
- Decision: Wrap the current X Distribution workspace with `AGENTS.md`, `Makefile`, and `.harness/` state files instead of reorganizing the project first.
- Reason: The project already has live scripts and data; the harness should improve continuity without breaking current paths.
- Rejected alternative: Move files into a package structure immediately.
- Constraint: Compatibility shims and documentation must come before physical data moves.

## 2026-05-28: Treat source registry as the source-of-truth for live source lanes
- Decision: GitHub and arXiv source enablement lives in `config/source_registry.json` and is read through `scripts/source_registry.py`.
- Reason: Avoid new hardcoded source lists and make source lanes editable without code changes.
- Rejected alternative: Add more fixed script lists to `phase1_collect.py`.
- Constraint: Collectors should ask the registry which live source scripts and outputs are enabled.

## 2026-05-31: Centralize protected intelligence queue persistence
- Decision: Route canonical collection, deep-discovery aggregation, and normalization through `scripts/intelligence_queue.py`.
- Reason: The active intelligence queue is protected state. URL identity, historical shape compatibility, duplicate provenance merging, recency filtering, metadata, and atomic replacement need one testable implementation.
- Rejected alternative: Continue maintaining independent direct JSON writes in each canonical script.
- Constraint: Legacy writers may remain for compatibility, but new queue writers must use the protected queue seam.

## 2026-05-31: Make editorial drafting verified-only and manual
- Decision: Replace hardcoded prototype post output with verified-only manual drafting packets.
- Reason: Editorial artifacts must never introduce unverified claims or imply automated publishing. The queue is an intelligence surface, not evidence that a claim is ready to publish.
- Rejected alternative: Keep demo claims reachable through the master CLI.
- Constraint: Post packets require `VERIFIED` or `LIKELY_TRUE` fact-check status and contain empty manual drafting fields.

## 2026-06-01: Bound read-only X collection to three owned browser slots
- Decision: Route read-only X collection through one coordinator: attempt the dedicated `home` tab first, collect watchlists through `watch-1` to `watch-3`, and degrade to a notified serialized retry path after three consecutive live failures.
- Reason: Independent browser-backed XCLI subprocesses must not navigate the same user tab or hide browser instability behind stale cached output.
- Rejected alternative: Parallelize existing timeline calls while letting each bridge subprocess navigate the first available Chrome page.
- Constraint: Posting, reply, follow, and older bridge workflows retain their default behavior; cache policy and the X-only PID lock apply inside the shared read-only coordinator boundary.
