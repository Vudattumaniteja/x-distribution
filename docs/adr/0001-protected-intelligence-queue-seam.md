# ADR-0001: Centralize protected intelligence queue persistence

Date: 2026-05-31

## Status
Accepted

## Context
The active intelligence queue is protected state used by reporting, verification, and editorial workflows. Multiple canonical scripts previously implemented their own queue parsing, URL identity, duplicate merging, and direct JSON writes. That made queue behavior difficult to verify and allowed interrupted writes to corrupt the shared artifact.

## Decision
Use `scripts/intelligence_queue.py` as the authoritative module for active intelligence queue persistence. Canonical collection, aggregation, and normalization scripts cross this seam for:

- historical list-shape compatibility
- canonical URL identity
- duplicate provenance merging
- recency filtering
- queue metadata
- atomic JSON replacement

Legacy scripts may remain for compatibility, but new queue writers must use this module.

## Consequences
- The protected queue has one testable interface.
- Interrupted canonical writes preserve the previous complete JSON file.
- Duplicate behavior and legacy compatibility have locality.
- Remaining legacy queue writers are visible migration work rather than hidden alternatives.
