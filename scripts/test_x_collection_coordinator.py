"""Deterministic contract tests for shared read-only X collection."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from x_collection_coordinator import XCollectionCoordinator, dedupe_tweets


NOW = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)


def tweet(url: str, **extra) -> dict:
    return {"url": url, "text": url, **extra}


class XCollectionCoordinatorHappyPathTests(unittest.TestCase):
    def test_home_runs_before_three_reusable_watchlist_slots(self):
        events = []
        released = []

        def home_collector(count, output_path, *, slot):
            events.append(("home", slot))
            return [tweet("https://x.com/home/status/1")]

        def timeline_collector(handle, *, days, output_path, slot):
            events.append((handle, slot))
            return [tweet(f"https://x.com/{handle}/status/1")]

        with tempfile.TemporaryDirectory() as temp_dir:
            result = XCollectionCoordinator(
                home_collector=home_collector,
                timeline_collector=timeline_collector,
                slot_releaser=lambda: released.append(True),
                status_path=Path(temp_dir) / "status.json",
                cache_dir=Path(temp_dir) / "cache",
                now=lambda: NOW,
            ).collect(["a", "b", "c", "d", "e"], workers=3)

        self.assertEqual(("home", "home"), events[0])
        self.assertEqual({"watch-1", "watch-2", "watch-3"}, {slot for _, slot in events[1:]})
        self.assertEqual("LIVE_OK", result["status"])
        self.assertEqual(6, result["tweet_count"])
        self.assertEqual([True], released)

    def test_skip_home_is_intentional_and_status_is_written(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            status_path = Path(temp_dir) / "status.json"
            result = XCollectionCoordinator(
                home_collector=lambda *args, **kwargs: self.fail("home should be skipped"),
                timeline_collector=lambda handle, **kwargs: [tweet(f"https://x.com/{handle}/status/1")],
                slot_releaser=lambda: True,
                status_path=status_path,
                cache_dir=Path(temp_dir) / "cache",
                now=lambda: NOW,
            ).collect(["openai"], skip_home=True)
            status = json.loads(status_path.read_text(encoding="utf-8"))

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


if __name__ == "__main__":
    unittest.main()
