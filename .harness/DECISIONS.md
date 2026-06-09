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

## 2026-06-02: Implement Polymarket claim verification and confidence scoring
- Decision: Add `fetch_polymarket_corroboration` to `TruthOracle` and hook it into `VerificationEngine` (Check 2: Claim Verification) to query active prediction markets. Update the confidence score calculator to apply a `+10` bonus for YES odds > 70% and a `-15` penalty for YES odds < 15%.
- Reason: Prediction markets are a strong signal of claim likelihood; incorporating YES odds from active markets provides dynamic, market-backed verification metrics.
- Rejected alternative: Hardcode odds values in independent collectors or manual overrides.
- Constraint: Ensure keyword queries return binary active markets and handle non-binary or inactive markets gracefully by returning `None` without crashing.

## 2026-06-02: Separate code from the xdist-brain data repository
- Decision: Remove all code, scripts, configuration, and documentation files from the `xdist-brain` repository (remote `brain`) while keeping the code safe and fully active in the main `x-distribution` repository (remote `origin`).
- Reason: Separate concerns and make `xdist-brain` a dedicated, data-only repository storing transcripts, runs, and collection outputs.
- Rejected alternative: Keep both code and data in the same repository for both remotes.
- Constraint: Local workspace tracks `x-distribution` and keeps all code active; remote updates on `brain` are performed via temporary clean branches.

## 2026-06-09: Verify atomic claims through a claim-shaped interface
- Decision: Add `AtomicClaim`, `SourceEvidence`, and `VerificationResult` to `scripts/verification_engine.py`, with GitHub, Hugging Face, Wayback, and Polymarket fetches kept as adapter wrappers behind the claim interface.
- Reason: Atomic claims need source evidence, timestamps, corroboration hints, optional market context, and a reasoned verdict/confidence/rationale object before editorial workflows can safely consume them.
- Rejected alternative: Continue passing raw keyword strings and adapter-specific dictionaries directly through the confidence calculator.
- Constraint: Polymarket YES odds keep the existing >70 bonus and <15 penalty, and unsupported or disputed claims remain non-publishable so editorial generation fails closed.

## 2026-06-09: Route Phase 1 through lane adapters
- Decision: Add a Phase 1 lane adapter contract that returns normalized queue records and lane health, with artifact/research as the first subprocess/output-file tracer bullet.
- Reason: The runner should coordinate lanes without knowing each lane's command shape or output-file schema.
- Rejected alternative: Keep expanding `phase1_collect.py` with per-lane subprocess and JSON normalization logic.
- Constraint: X read-only coordination, fail-soft status propagation, and protected queue replacement stay unchanged.

## 2026-06-09: Share RSS transport without sharing lane scoring
- Decision: Extract `scripts/source_lane_transport.py` for session setup, request timeout handling, RSS parsing, source-health diagnostics, source-identity dedupe, and collector raw/signals persistence.
- Reason: Finance and startup lanes had duplicated transport code, but their scoring vocabulary and signal classification need to remain lane-owned.
- Rejected alternative: Move finance/startup keyword scoring into a generic collector abstraction.
- Constraint: Preserve existing raw/signals JSON shapes and keep protected queue state untouched.

## 2026-06-09: Centralize transcript retrieval behind the pinned CLI route
- Decision: Add `scripts/transcript_retrieval.py` as the programmatic transcript retrieval interface around `source_clis.yt_transcript_command`.
- Reason: Transcript reuse, output-path handling, subprocess status interpretation, empty-file cleanup, and no-caption classification should live in one module.
- Rejected alternative: Let each orchestrator construct CLI commands and classify failures independently.
- Constraint: Preserve transcript filenames, `data/transcript_pull_report.json`, `data/transcripts_unavailable.json`, and the distinction between `NO_TRANSCRIPT_AVAILABLE` and `FAILED`.
