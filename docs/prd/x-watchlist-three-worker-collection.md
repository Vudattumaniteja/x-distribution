# PRD: Bounded Three-Worker X Watchlist Collection

## Problem Statement

The X source lane is slow because authenticated browser-backed collection processes watched timelines serially. The operator wants the home feed collected first, followed by three parallel watchlist workers using dedicated Chrome tabs. The system must remain understandable when browser collection becomes unstable: it must notify the operator, preserve usable coverage through bounded retries and fresh cache fallback, and degrade to one worker after three consecutive live failures.

The current pinned external XCLI bridge cannot safely provide that behavior yet. Each subprocess connects to the same Chrome context and navigates the first available page, which means naive parallelism would cause workers to compete for one tab. The feature therefore requires a shared X collection coordinator and read-only tab-slot support in the pinned bridge.

## Solution

Introduce a shared X collection coordinator used by canonical Phase 1 collection and targeted X radar commands.

The coordinator performs two phases:

1. Attempt the home feed in a dedicated `home` automation tab.
2. After that attempt finishes, collect watchlist timelines through three reusable dedicated tabs: `watch-1`, `watch-2`, and `watch-3`.

If the initial home-feed attempt fails, the operator is notified immediately and watchlist collection continues. Home-feed collection is retried once after the watchlist phase. If it still fails, fresh cached home-feed data may be used.

During watchlist collection, any successful live account resets the consecutive-failure counter. After three consecutive live failures, new parallel scheduling stops, active workers drain, and the remaining work continues through a notified one-worker fallback. Failed parallel accounts are retried first. Fresh cached timelines may preserve coverage, but cache use still counts as a live failure and remains visible in final status.

## User Stories

1. As an operator, I want home-feed collection to run before watchlist collection, so that the two collection phases remain predictable.
2. As an operator, I want watchlist timelines collected with three workers, so that X collection finishes faster.
3. As an operator, I want each worker to own a dedicated Chrome tab, so that concurrent navigation does not collide.
4. As an operator, I want worker tabs reused across accounts, so that the system avoids unnecessary tab churn.
5. As an operator, I want automation tabs separated from my untagged browser tabs, so that collection does not disrupt my browsing session.
6. As an operator, I want a failed home-feed attempt to notify me immediately, so that I know watchlist collection is continuing with reduced coverage.
7. As an operator, I want home-feed scraping retried once after watchlist collection, so that transient failures can recover.
8. As an operator, I want a successful home-feed retry to notify me, so that I know coverage recovered.
9. As an operator, I want cached home-feed data used only when it is no older than 24 hours, so that fallback evidence is not silently stale.
10. As an operator, I want cached watchlist data used only when it is no older than 48 hours, so that degraded runs remain useful without hiding obsolete evidence.
11. As an operator, I want cached watchlist use to count as a live scrape failure, so that cache does not hide a broken browser session.
12. As an operator, I want watchlist collection to fall back to one worker after three consecutive live failures, so that unstable parallel collection can recover.
13. As an operator, I want any successful live account scrape to reset the consecutive-failure counter, so that isolated failures do not cause premature fallback.
14. As an operator, I want active parallel workers to drain before serialized recovery starts, so that browser-backed jobs are not force-cancelled.
15. As an operator, I want failed parallel accounts retried before unattempted accounts in serialized mode, so that missing coverage is repaired first.
16. As an operator, I want each account retried once in serialized mode, so that recovery is bounded.
17. As an operator, I want the system to continue after an unrecoverable account failure, so that one account does not block the full watchlist.
18. As an operator, I want output deduplicated by tweet URL, so that retries do not inflate results.
19. As an operator, I want live results preferred over cached results, so that output retains the freshest evidence.
20. As an operator, I want clear console notifications, so that I can see degradation while a run is active.
21. As an operator, I want durable JSONL notifications, so that I can inspect what happened after a long run.
22. As an operator, I want notification severity levels, so that recovery, degradation, and hard failures are distinguishable.
23. As an operator, I want notification logs rotated at 5 MB, so that the audit trail remains bounded.
24. As an operator, I want each run to have a run ID, so that outputs and notifications can be correlated.
25. As an operator, I want overlapping X runs blocked, so that two collections do not exceed the intended tab limit.
26. As an operator, I want stale locks replaced when their owning PID is gone, so that crashed runs do not block future collection.
27. As an operator, I want active locks respected regardless of age, so that slow legitimate runs are not duplicated.
28. As an operator, I want stale automation tabs reclaimed after crashes, so that a new run does not create duplicate slot tabs.
29. As an operator, I want duplicate automation tabs closed without touching untagged user tabs, so that cleanup is safe.
30. As an operator, I want a compact latest-status artifact, so that I can inspect the most recent X run without searching logs.
31. As an operator, I want X status included in Phase 1 lane health, so that broader pipeline health reflects degraded X coverage.
32. As an operator, I want `LIVE_OK`, `DEGRADED_OK`, `PARTIAL`, and `FAILED` statuses, so that coverage quality is explicit.
33. As an operator, I want `DEGRADED_OK` and `PARTIAL` to remain fail-soft for Phase 1, so that other source lanes continue.
34. As an operator, I want `FAILED` to exit non-zero, so that automation detects the absence of usable X data.
35. As an operator, I want a `--workers` override on targeted X radar commands, so that I can debug with one worker or validate with three.
36. As an operator, I want `--skip-home` retained for targeted watchlist-only trials, so that I can isolate watchlist behavior.
37. As an operator, I want posting, reply, and follow workflows unchanged, so that read-only performance work does not broaden risk.
38. As an operator, I want an X-only three-worker live trial after implementation, so that the real browser-backed behavior is tested directly.
39. As an operator, I want the live trial findings converted into additional test cases, so that observed failures become repeatable coverage.

## Implementation Decisions

- Add a shared X collection coordinator as the authoritative read-only X collection boundary.
- Use an explicit two-phase state flow: isolated home-feed attempt, then watchlist collection.
- Set configured watchlist concurrency to `3`; retain a targeted CLI override.
- Pass explicit slot IDs to the external XCLI bridge: `home`, `watch-1`, `watch-2`, and `watch-3`.
- Apply slot behavior only to read-only home-feed and timeline collection commands.
- Keep posting, reply, follow, and older standalone bridge workflows unchanged unless they explicitly request a slot.
- Tag automation tabs by slot ID, reclaim stale matching tabs, close duplicate slot tabs, and never close untagged user tabs.
- Reuse fixed watchlist tabs across accounts and release automation tabs after a normal run.
- Add a consecutive live-failure counter for watchlist collection. Reset it after any successful live account scrape.
- After three consecutive live failures, stop scheduling new parallel accounts, drain active jobs, notify the operator, and process recovery serially.
- Retry failed parallel accounts first in serialized mode, followed by unattempted accounts.
- Limit serialized retries to one per failed account.
- Distinguish live success, fresh-cache fallback, stale-cache rejection, and missing data.
- Accept home-feed cache up to 24 hours old and watchlist timeline cache up to 48 hours old.
- Deduplicate output by tweet URL and prefer live evidence over cached evidence.
- Emit console notifications prefixed with `[X NOTIFY]`.
- Append structured notifications to a rotating JSONL log with severity, run ID, type, reason, timestamp, and relevant state.
- Rotate the JSONL log at 5 MB while preserving one previous file.
- Generate a timestamp-based run ID for each X collection.
- Use an X-only lock containing run ID, PID, and creation timestamp.
- Reject overlapping active X runs; reclaim stale locks only when the owning PID is no longer running.
- Write disposable latest-state output for quick operator inspection.
- Include X run ID and X status in broader Phase 1 lane health.
- Keep `LIVE_OK`, `DEGRADED_OK`, and `PARTIAL` fail-soft for Phase 1; return non-zero only for `FAILED`.
- Route canonical Phase 1 collection, targeted X radar commands, and the independent master poller through the shared coordinator.
- Leave the weekly sweep structure unchanged because it delegates to canonical Phase 1 collection.

## Testing Decisions

Tests should assert observable behavior through the highest stable seam: the shared X collection coordinator. Avoid tests coupled to thread-pool internals or Playwright implementation details.

### Coordinator contract tests

- Verify home-feed collection is attempted before watchlist scheduling.
- Verify three worker slots are used for watchlist mode.
- Verify one success resets the consecutive-failure counter.
- Verify three consecutive live failures trigger serialized fallback.
- Verify new parallel scheduling stops after the threshold while active work drains.
- Verify failed parallel accounts retry before unattempted accounts.
- Verify serialized mode retries each failed account once.
- Verify fresh cache preserves coverage but still marks degradation.
- Verify stale cache is rejected at the 24-hour and 48-hour boundaries.
- Verify tweet URL deduplication prefers live results over cache.
- Verify final statuses: `LIVE_OK`, `DEGRADED_OK`, `PARTIAL`, and `FAILED`.
- Verify `--skip-home` records an intentional skip rather than a failure.

### Notification and lock tests

- Verify console and JSONL notifications for home failure, home recovery, serialized fallback, cache use, missing coverage, active-lock rejection, stale-lock replacement, and fatal no-data runs.
- Verify JSONL records include run ID, severity, timestamp, type, and reason.
- Verify log rotation at 5 MB.
- Verify an active PID blocks a second X run regardless of lock age.
- Verify a dead PID permits stale-lock replacement.

### External bridge integration tests

- Verify `home`, `watch-1`, `watch-2`, and `watch-3` resolve to separate dedicated automation tabs.
- Verify matching stale slot tabs are reclaimed.
- Verify duplicate tagged tabs are closed.
- Verify untagged user tabs are never navigated or closed.
- Verify read-only slot behavior does not alter posting, reply, or follow defaults.

### Pipeline integration tests

- Verify X status and run ID appear in Phase 1 lane health.
- Verify `DEGRADED_OK` and `PARTIAL` remain fail-soft.
- Verify `FAILED` propagates a non-zero result.

### Mandatory bounded live trial

After implementation:

1. Run X-only collection with the initial home-feed attempt enabled.
2. Scan 10 watchlist accounts with exactly three watchlist workers.
3. Inspect Chrome to confirm dedicated tab-slot behavior.
4. Inspect console notifications, durable JSONL notifications, latest status output, and X lane-health metadata.
5. Record timing and compare it with serialized watchlist collection.
6. Identify any browser, timing, throttling, authentication, stale-tab, or output-shape issues observed during the real run.
7. Convert each observed issue into a deterministic regression test where feasible.

Existing contract-test style in the repository should be followed for focused script-level behavioral verification.

## Out of Scope

- Automated posting or replying to X.
- Changes to editorial verification or manual drafting policy.
- Parallelizing non-X source lanes beyond their existing worker policies.
- Modifying the weekly sweep orchestration beyond inherited coordinator behavior.
- Allowing more than three production watchlist workers before repeated live trials justify a higher cap.
- Closing, navigating, or otherwise managing untagged user Chrome tabs.
- Replacing the pinned XCLI or authenticated Chrome profile.

## Further Notes

- The proposed ADR is `Bounded parallel X watchlist collection`.
- The active feature branch is `feat/x-watchlist-three-worker-collection`.
- Preliminary uncommitted implementation edits exist on the feature branch. They must be reconciled with this PRD before testing or committing.
- The live trial is a required discovery step, not merely a final smoke test. Any newly observed edge cases must be reviewed and added to the test suite before merge.
