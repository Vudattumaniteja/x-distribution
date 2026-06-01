# ADR-0004: Establish Secure Queue Seam and Verification Engine

Date: 2026-05-31

## Status
Proposed

## Context
The active intelligence queue (`data/news_queue.json`) is a protected shared state. An audit revealed multiple scripts bypassing the `intelligence_queue.py` seam to perform direct reads or writes, compromising state integrity. Additionally, the verification pipeline lacked decoupling; `TemporalSentinel` directly coordinated and parsed raw third-party dates retrieved via `TruthOracle`, merging decision-tree verification depth with raw adapter logic.

## Decision
1. Eliminate all direct queue reads and writes. Refactor the scripts `fresh_news_finder.py`, `build_intelligence_report.py`, `stage4_partition.py`, `summarize_sweep.py`, and `temporal_audit_tool.py` to route persistence operations through the `intelligence_queue` module seam. We leverage the `load_queue` and `load_queue_document` interfaces to maintain state locality.
2. Establish a deep `VerificationEngine` module as a seam between raw date parsing and decision-tree logic.
3. The new `VerificationEngine` class encapsulates `TruthOracle` as an adapter, parsing raw third-party formats into normalized UTC timestamp objects.
4. Refactor `TemporalSentinel` to invoke this shallow-to-deep date interface, focusing its implementation solely on the core decision-tree verification.

## Consequences
- Single-point write/read locality for `data/news_queue.json` ensures atomic persistence, protecting state integrity.
- Clear structural decoupling: `TemporalSentinel` is insulated from raw third-party date parsing changes.
- Test coverage for the verification engine seam ensures that the decision-tree rules are verified with stable inputs.
- The depth of raw third-party adapter changes remains isolated within the `VerificationEngine` implementation.
