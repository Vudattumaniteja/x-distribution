"""Deterministic contract tests for shared read-only X collection."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

from x_collection_coordinator import XCollectionCoordinator, XNotifier, dedupe_tweets


NOW = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)


def tweet(url: str, **extra) -> dict:
    return {"url": url, "text": url, **extra}


def write_cache(path: Path, tweets: list[dict], *, age_hours: float = 0) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(tweets), encoding="utf-8")
    timestamp = (NOW - timedelta(hours=age_hours)).timestamp()
    os.utime(path, (timestamp, timestamp))


class CoordinatorTestCase(unittest.TestCase):
    def coordinator(self, temp_dir: str, **kwargs) -> XCollectionCoordinator:
        root = Path(temp_dir)
        return XCollectionCoordinator(
            home_collector=kwargs.pop("home_collector", lambda *args, **opts: [tweet("https://x.com/home/status/1")]),
            timeline_collector=kwargs.pop(
                "timeline_collector",
                lambda handle, **opts: [tweet(f"https://x.com/{handle}/status/1")],
            ),
            slot_releaser=kwargs.pop("slot_releaser", lambda: True),
            status_path=root / "status.json",
            cache_dir=root / "cache",
            lock_path=root / "cache" / "x_collection.lock",
            notification_path=root / "notifications.jsonl",
            now=lambda: NOW,
            **kwargs,
        )

    def notification_types(self, temp_dir: str) -> list[str]:
        path = Path(temp_dir) / "notifications.jsonl"
        if not path.exists():
            return []
        return [json.loads(line)["type"] for line in path.read_text(encoding="utf-8").splitlines()]


class XCollectionCoordinatorHappyPathTests(CoordinatorTestCase):
    def test_home_runs_before_three_reusable_watchlist_slots(self):
        events = []
        released = []

        def home_collector(count, output_path, **opts):
            events.append(("home", opts["slot"]))
            return [tweet("https://x.com/home/status/1")]

        def timeline_collector(handle, **opts):
            events.append((handle, opts["slot"]))
            return [tweet(f"https://x.com/{handle}/status/1")]

        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.coordinator(
                temp_dir,
                home_collector=home_collector,
                timeline_collector=timeline_collector,
                slot_releaser=lambda: released.append(True) or True,
            ).collect(["a", "b", "c", "d", "e"], workers=3)

        self.assertEqual(("home", "home"), events[0])
        self.assertEqual({"watch-1", "watch-2", "watch-3"}, {slot for _, slot in events[1:]})
        self.assertEqual("LIVE_OK", result["status"])
        self.assertEqual(6, result["tweet_count"])
        self.assertEqual([True], released)

    def test_skip_home_is_intentional_and_status_is_written(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            coordinator = self.coordinator(
                temp_dir,
                home_collector=lambda *args, **kwargs: self.fail("home should be skipped"),
            )
            result = coordinator.collect(["openai"], skip_home=True)
            status = json.loads((Path(temp_dir) / "status.json").read_text(encoding="utf-8"))

        self.assertEqual("LIVE_OK", result["status"])
        self.assertTrue(status["home_feed_skipped"])
        self.assertEqual("SKIPPED", status["home_feed_status"])
        self.assertRegex(status["run_id"], r"^x-20260601T120000\.000000Z-\d+$")
        self.assertNotIn("tweets", status)

    def test_dedupe_prefers_live_evidence_over_cache(self):
        result = dedupe_tweets(
            [
                tweet("https://x.com/openai/status/1", text="cached", _x_collection_source="cache"),
                tweet("https://x.com/openai/status/1", text="live", _x_collection_source="live"),
            ]
        )
        self.assertEqual(1, len(result))
        self.assertEqual("live", result[0]["text"])


class XCollectionCoordinatorFallbackTests(CoordinatorTestCase):
    def test_home_failure_notifies_then_recovers_after_watchlist(self):
        home_calls = []

        def home_collector(*args, **opts):
            home_calls.append(opts["slot"])
            if len(home_calls) == 1:
                raise RuntimeError("transient home error")
            return [tweet("https://x.com/home/status/recovered")]

        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.coordinator(temp_dir, home_collector=home_collector).collect(["openai"])
            notification_types = self.notification_types(temp_dir)

        self.assertEqual(["home", "home"], home_calls)
        self.assertEqual("DEGRADED_OK", result["status"])
        self.assertEqual("LIVE_RECOVERED", result["home_feed_status"])
        self.assertEqual(["home_failed", "home_recovered"], notification_types)

    def test_cache_boundaries_accept_exact_limit_and_reject_older(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            coordinator = self.coordinator(temp_dir)
            path = Path(temp_dir) / "cache.json"
            write_cache(path, [tweet("https://x.com/a/status/1")], age_hours=24)
            home_cache, home_meta = coordinator._fresh_cache(path, 24)
            write_cache(path, [tweet("https://x.com/a/status/1")], age_hours=24 + (1 / 3600))
            stale_home, stale_home_meta = coordinator._fresh_cache(path, 24)
            write_cache(path, [tweet("https://x.com/a/status/1")], age_hours=48)
            timeline_cache, timeline_meta = coordinator._fresh_cache(path, 48)
            write_cache(path, [tweet("https://x.com/a/status/1")], age_hours=48 + (1 / 3600))
            stale_timeline, stale_timeline_meta = coordinator._fresh_cache(path, 48)

        self.assertTrue(home_cache)
        self.assertEqual("FRESH", home_meta["cache_status"])
        self.assertFalse(stale_home)
        self.assertEqual("STALE", stale_home_meta["cache_status"])
        self.assertTrue(timeline_cache)
        self.assertEqual("FRESH", timeline_meta["cache_status"])
        self.assertFalse(stale_timeline)
        self.assertEqual("STALE", stale_timeline_meta["cache_status"])

    def test_three_failures_drain_then_retry_failed_before_unattempted_once(self):
        calls = []
        counts = Counter()

        def timeline_collector(handle, **opts):
            calls.append((handle, opts["slot"]))
            counts[handle] += 1
            if handle in {"a", "b", "c"} and counts[handle] == 1:
                raise RuntimeError(f"{handle} failed")
            return [tweet(f"https://x.com/{handle}/status/{counts[handle]}")]

        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.coordinator(temp_dir, timeline_collector=timeline_collector).collect(
                ["a", "b", "c", "d", "e", "f", "g"],
                workers=3,
                skip_home=True,
            )
            notification_types = self.notification_types(temp_dir)

        self.assertTrue(result["serialized_fallback_activated"])
        self.assertEqual(["a", "b", "c", "f", "g"], [handle for handle, _ in calls[-5:]])
        self.assertEqual({"watch-1"}, {slot for _, slot in calls[-5:]})
        self.assertEqual(2, counts["a"])
        self.assertEqual(2, counts["b"])
        self.assertEqual(2, counts["c"])
        self.assertEqual(1, counts["f"])
        self.assertEqual(1, counts["g"])
        self.assertIn("serialized_fallback_activated", notification_types)
        self.assertIn("serialized_fallback_completed", notification_types)

    def test_live_success_resets_consecutive_failure_counter(self):
        failures = {"a", "b", "d", "e"}

        def timeline_collector(handle, **opts):
            if handle in failures:
                raise RuntimeError(f"{handle} failed")
            return [tweet(f"https://x.com/{handle}/status/1")]

        with tempfile.TemporaryDirectory() as temp_dir:
            coordinator = self.coordinator(temp_dir, timeline_collector=timeline_collector)
            for handle in failures:
                write_cache(coordinator._timeline_output_path(handle), [tweet(f"https://x.com/{handle}/status/cache")])
            result = coordinator.collect(["a", "b", "c", "d", "e", "f"], workers=1, skip_home=True)

        self.assertFalse(result["serialized_fallback_activated"])
        self.assertEqual("DEGRADED_OK", result["status"])
        self.assertEqual(sorted(failures), result["watchlist_cached_accounts"])

    def test_home_cache_is_used_only_after_retry_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            coordinator = self.coordinator(
                temp_dir,
                home_collector=lambda *args, **opts: (_ for _ in ()).throw(RuntimeError("home down")),
            )
            write_cache(coordinator._home_output_path(), [tweet("https://x.com/home/status/cache")], age_hours=24)
            result = coordinator.collect(["openai"])

        self.assertEqual("DEGRADED_OK", result["status"])
        self.assertEqual("CACHE", result["home_feed_status"])

    def test_partial_and_failed_statuses_are_explicit(self):
        def timeline_collector(*args, **kwargs):
            raise RuntimeError("timeline down")

        with tempfile.TemporaryDirectory() as temp_dir:
            partial = self.coordinator(temp_dir, timeline_collector=timeline_collector).collect(["openai"], skip_home=False)
        with tempfile.TemporaryDirectory() as temp_dir:
            failed = self.coordinator(temp_dir, timeline_collector=timeline_collector).collect(["openai"], skip_home=True)

        self.assertEqual("PARTIAL", partial["status"])
        self.assertEqual("FAILED", failed["status"])


class XCollectionCoordinatorNotificationAndLockTests(CoordinatorTestCase):
    def test_jsonl_notification_fields_and_rotation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "x_collection_notifications.jsonl"
            path.write_text("x" * 20, encoding="utf-8")
            notifier = XNotifier("run-1", path=path, now=lambda: NOW, max_bytes=10)
            notifier.notify("WARN", "cache_used", "cache fallback")
            record = json.loads(path.read_text(encoding="utf-8").strip())
            rotated = (Path(temp_dir) / "x_collection_notifications.previous.jsonl").exists()

        self.assertEqual("run-1", record["run_id"])
        self.assertEqual("WARN", record["severity"])
        self.assertEqual("cache_used", record["type"])
        self.assertEqual("cache fallback", record["reason"])
        self.assertEqual(NOW.isoformat(), record["timestamp"])
        self.assertTrue(rotated)

    def test_active_pid_blocks_second_run_regardless_of_lock_age(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            lock_path = Path(temp_dir) / "cache" / "x_collection.lock"
            lock_path.parent.mkdir(parents=True)
            lock_path.write_text(
                json.dumps({"run_id": "old", "pid": 123, "created_at": "2000-01-01T00:00:00+00:00"}),
                encoding="utf-8",
            )
            result = self.coordinator(temp_dir, pid_checker=lambda pid: pid == 123).collect(["openai"])
            notifications = self.notification_types(temp_dir)

        self.assertEqual("FAILED", result["status"])
        self.assertTrue(result["blocked_by_active_lock"])
        self.assertEqual(["active_lock_rejected"], notifications)

    def test_dead_pid_lock_is_replaced_and_removed_after_run(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            lock_path = Path(temp_dir) / "cache" / "x_collection.lock"
            lock_path.parent.mkdir(parents=True)
            lock_path.write_text(json.dumps({"run_id": "dead", "pid": 321}), encoding="utf-8")
            result = self.coordinator(temp_dir, pid_checker=lambda pid: False).collect(["openai"])
            notifications = self.notification_types(temp_dir)

            self.assertFalse(lock_path.exists())

        self.assertEqual("LIVE_OK", result["status"])
        self.assertIn("stale_lock_replaced", notifications)


if __name__ == "__main__":
    unittest.main()
