# Bounded parallel X watchlist collection

Status: accepted

X collection previously treated the authenticated browser-backed XCLI route as strictly serialized because parallel sessions could fail. The revised policy isolates the home-feed attempt, collects watchlist timelines with a bounded default of `3` workers, and degrades to a notified `1`-worker fallback after `3` consecutive live failures. A single-run lock prevents overlapping collectors from exceeding the intended browser-tab limit. This preserves the speed benefit when the browser route is healthy while keeping degraded behavior explicit and recoverable.

Dedicated slot behavior is opt-in and read-only. The external bridge owns `home`, `watch-1`, `watch-2`, and `watch-3` tagged tabs, reclaims stale matches, closes duplicate tagged tabs, and leaves untagged user tabs untouched. Posting, reply, follow, and legacy workflows keep their previous first-page defaults.

The coordinator owns fallback policy. Home cache is usable for at most `24` hours and watchlist cache for at most `48` hours. Cache use remains visible as degradation and still counts as a live watchlist failure. After three consecutive live failures, active workers drain before failed accounts and then unattempted accounts run through bounded serialized recovery.

Notifications are printed with `[X NOTIFY]`, appended to a rotating JSONL audit log, and correlated by run ID. `cache/x_collection.lock` blocks overlapping active PIDs but is reclaimed when the recorded PID is no longer running.
