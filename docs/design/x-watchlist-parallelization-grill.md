# X Watchlist Parallelization Grill

Status: design interview complete

## Resolved Decisions

### Two-phase collection

X collection keeps an explicit sequence:

1. Collect the home feed as a single isolated phase.
2. After the home-feed attempt finishes, collect watchlist timelines concurrently.

### Watchlist worker policy

- Default watchlist concurrency: `3` workers.
- Operator override: allow a lower worker count for testing and fallback debugging.
- Initial production cap: `3` workers until repeated browser-backed XCLI tests justify a higher cap.

### Operator notifications

The operator must be notified when the requested `3`-worker watchlist mode degrades to the serialized `1`-worker fallback. Normal movement between the home-feed phase and watchlist phase is logged, but it is not an operator notification.

The notification must identify:

- requested mode: `3` watchlist workers
- fallback mode: `1` watchlist worker
- reason for fallback
- point in the run where the fallback occurred

### Fallback threshold

Do not degrade immediately after one worker failure. Fall back from `3` watchlist workers to the serialized `1`-worker mode after `3` repeated failures.

Failures are counted consecutively across the whole watchlist phase. Any successful account scrape resets the counter. After `3` consecutive failures, notify the operator and process the remaining watchlist work through the serialized `1`-worker fallback.

When fallback activates, the serialized worker retries accounts that failed during the parallel attempt first. It then continues with accounts that have not been attempted yet. Account-level cached-output fallback remains available when a specific live timeline stays unavailable.

### Home-feed recovery

If the isolated home-feed scrape fails:

1. Notify the operator that home-feed collection failed.
2. Continue into the `3`-worker watchlist phase.
3. After watchlist collection finishes, retry the home-feed scrape.

The notification must state that watchlist collection is continuing despite the home-feed failure.
The post-watchlist home-feed retry budget is `1` attempt.

If the post-watchlist retry also fails, the run may use a valid cached home-feed result. Notify the operator that live home-feed collection failed and cached data was used. Include the cache timestamp so stale data is visible.

### Notification delivery

Operator notifications are emitted through both channels:

- Print a clear `[X NOTIFY]` line to the console immediately.
- Append a structured JSON record to `logs/x_collection_notifications.jsonl`.

The durable record preserves notification type, timestamp, reason, and relevant run state.

Successful recovery also emits a notification:

- A home-feed retry succeeds after the initial failure.
- The serialized watchlist fallback completes.
- Cached home-feed data is used.

### Cached watchlist output

If a live watchlist timeline scrape fails but cached output exists, use the cached timeline for coverage. The live scrape still counts as a failure toward the `3`-consecutive-failure threshold. Cached data must not hide a degraded live browser-backed XCLI session.

### Fallback failure scope

Activate the `1`-worker fallback after any `3` consecutive live watchlist failures. The threshold is not limited to errors recognized as browser-concurrency conflicts. The fallback notification includes the observed failure reasons.

### Serialized retry budget

In `1`-worker fallback mode, retry each failed watchlist account once. If that retry also fails, use cached timeline data when available, notify the operator, and continue to the next account.

### Final run status

Report one of four X collection statuses:

- `LIVE_OK`: all requested live scrapes succeeded.
- `DEGRADED_OK`: collection finished, but serialized fallback or cached data was used.
- `PARTIAL`: one or more requested accounts had neither live nor cached data.
- `FAILED`: no usable X data was collected.

### Parallel drain before fallback

When the third consecutive parallel failure triggers fallback:

1. Stop scheduling new parallel accounts.
2. Allow already-running parallel workers to finish.
3. Start serialized recovery after the active workers drain.

Do not force-cancel browser-backed jobs because that can leave tabs or Playwright contexts in a broken state.

### Retry deduplication

Deduplicate X collector output by tweet URL before writing it. Prefer the freshest live result over cached data and preserve source-account metadata.

### Merge gate

Configure `3` workers on the feature branch, but do not merge until a bounded live trial passes:

- Attempt the isolated home-feed scrape.
- Scan `10` watchlist accounts with `3` workers.
- Run a deterministic fallback simulation.
- Verify durable notification records.
- Run schema validation and Python compile checks.

### Deterministic fallback testing

Inject a test-only timeline collector function that deliberately fails for `3` consecutive accounts. Verify that:

- New parallel scheduling stops.
- Active workers drain.
- A `[X NOTIFY]` fallback record is written.
- Failed accounts retry first with `1` worker.
- Remaining accounts continue serially.
- Final status is `DEGRADED_OK` or `PARTIAL`, as appropriate.

### Shared coordinator boundary

Centralize the two-phase X collection behavior in a shared XCLI collection coordinator. Canonical Phase 1 collection and standalone X radar commands must use the same fallback, notification, status, and deduplication rules.

### Compatibility scope

Migrate `master_poller.py` to the shared X coordinator because it independently scrapes the home feed and watchlist timelines. Leave the weekly sweep path unchanged because it stages home data and delegates to `phase1_collect.py`, which inherits the shared coordinator.

### Worker configuration

Keep `3` as the configured watchlist-worker default in `config/source_registry.json`. Targeted X radar commands expose a `--workers` override for debugging with `1` or validating with `3`. Full Phase 1 collection uses the registry value so scheduled runs remain consistent.

### Notification log rotation

Rotate `logs/x_collection_notifications.jsonl` when it exceeds `5 MB`. Preserve the prior file as `logs/x_collection_notifications.previous.jsonl` so the durable audit trail remains bounded.

### Run identity

Generate a timestamp-based `run_id` for each X collection run. Include it in every operator notification, collector output, and final status so scheduled or concurrent activity remains traceable.

### Single active run

Do not allow overlapping X collection runs. Use `cache/x_collection.lock`. If another run is active, notify the operator and stop the second run. This prevents multiple `3`-worker runs from exceeding the intended browser-tab limit and interfering with the authenticated browser session.

### Stale lock recovery

Store `run_id`, PID, and creation timestamp in `cache/x_collection.lock`. If the PID is no longer running, notify the operator, replace the stale lock, and start the new run.

An active lock does not expire based on age alone. If its PID is still running, keep the lock and notify that X collection is already active.

### Collector output metadata

Write the following runtime details into final X collector output:

- `run_id`
- final status
- requested and effective worker counts
- whether serialized fallback activated
- home-feed attempt and retry results
- live, cached, and missing watchlist account counts
- failed account handles
- notification count
- start and finish timestamps

### Notification severity

Operator notifications carry a severity:

- `INFO`: recovery succeeded or a stale lock was replaced.
- `WARN`: home feed failed but watchlist collection continued, serialized fallback activated, or cached output was used.
- `ERROR`: an account had neither live nor cached data, or a second run was blocked by an active lock.
- `FATAL`: no usable X data was collected.

### Decision record

Capture the bounded-parallelism policy in an ADR because it deliberately revises the earlier serialized-X assumption. The accepted direction is an isolated home-feed attempt, `3` concurrent watchlist workers, automatic `1`-worker fallback, operator notifications, and single-run locking.

### Latest status artifact

Write `data/x_collection_status.json` after each X collection run for quick operator inspection. Include the latest run ID, final status, worker mode, fallback usage, cache usage, failed accounts, timestamps, and notification count.

Treat `data/x_collection_status.json` as disposable latest-state output. Durable notification history remains in `logs/x_collection_notifications.jsonl`.

### Phase 1 lane health

Include X collection status and `run_id` in `data/phase1_lane_health.json`. This makes `LIVE_OK`, `DEGRADED_OK`, `PARTIAL`, or `FAILED` visible in the broader intelligence pipeline health report.

### Phase 1 exit behavior

- `LIVE_OK`: exit `0`.
- `DEGRADED_OK`: exit `0` with warnings.
- `PARTIAL`: exit `0`, emit `ERROR` notifications, and mark lane health degraded.
- `FAILED`: exit non-zero.

This keeps other source lanes running unless X produced no usable data.

### Watchlist-only debugging

Keep `--skip-home` on targeted X radar commands for watchlist-only debugging and bounded trials. Record `home_feed_skipped: true` in status metadata so an intentional skip is not confused with a failed home scrape.

### Lock boundary

Apply `cache/x_collection.lock` only around the shared X coordinator. Other Phase 1 source lanes continue concurrently because they do not use the authenticated X browser session.

### Cache freshness

- Home-feed cache is usable for at most `24 hours`.
- Watchlist timeline cache is usable for at most `48 hours`.
- Older cache is not used. Mark the result `PARTIAL` or `FAILED`, as appropriate, and notify the operator.

## Code Audit Finding

The pinned external XCLI currently connects each subprocess to the same authenticated Chrome context and navigates the first available page (`pages[0]`). It does not assign a dedicated tab to each concurrent watchlist worker. Parallelizing only inside this repository would cause workers to compete for one browser tab instead of creating the requested three-tab watchlist scraper.

The implementation may modify the pinned external bridge under `C:\Users\Manit\Desktop\Twitter automation\` so concurrent watchlist workers receive dedicated Chrome tabs.

### Watchlist tab ownership

Use three fixed reusable tab slots for the watchlist phase. Each worker owns one dedicated tab and reuses it across accounts. Close or release those automation tabs when the X run finishes. This avoids per-account tab churn and cross-worker navigation conflicts.

### Home tab ownership

Use a dedicated automation tab for home-feed scraping. Do not navigate the user's existing first Chrome tab. Close or release the home automation tab after the attempt, then open the three watchlist worker tabs.

### Explicit tab slots

Pass an explicit slot ID from the shared coordinator to the pinned external XCLI bridge: `home`, `watch-1`, `watch-2`, or `watch-3`. The bridge creates or reclaims the dedicated automation tab for that slot and never falls back to navigating the user's first Chrome tab.

Dedicated tab-slot behavior applies only to read-only collection commands: `twitter_home` and `twitter_timeline`. Posting, reply, follow, and existing standalone bridge workflows remain unchanged unless they explicitly request a slot.

### Stale automation tab recovery

Tag automation tabs with their slot ID. If a crashed run leaves stale automation tabs behind, reclaim the matching tab on the next run and close duplicate tabs for the same slot. Never close untagged user tabs.

## Open Questions

None. Design interview complete.
