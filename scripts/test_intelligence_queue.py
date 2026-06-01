"""Contract tests for the protected intelligence queue seam."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from intelligence_queue import (
    canonical_url,
    filter_recent_items,
    load_queue,
    merge_queue,
    replace_queue,
)


class IntelligenceQueueTests(unittest.TestCase):
    def test_canonical_url_removes_fragment_and_trailing_slash(self) -> None:
        self.assertEqual(
            canonical_url("HTTPS://Example.COM/path/?q=1#section"),
            "https://example.com/path?q=1",
        )

    def test_replace_queue_merges_duplicate_provenance_and_writes_document(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "news_queue.json"
            document, duplicates = replace_queue(
                [
                    {"headline": "One", "url": "https://example.com/item/", "source": "RSS"},
                    {
                        "headline": "Duplicate",
                        "url": "https://example.com/item#fragment",
                        "source": "Reddit",
                        "top_comments": ["useful"],
                    },
                ],
                path=path,
            )
            self.assertEqual(duplicates, 1)
            self.assertEqual(document["total_items"], 1)
            self.assertEqual(document["items"][0]["provenance_sources"], ["RSS", "Reddit"])
            self.assertEqual(document["items"][0]["top_comments"], ["useful"])
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["total_items"], 1)

    def test_load_queue_supports_legacy_list_shape(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "news_queue.json"
            path.write_text('[{"headline": "Legacy"}]', encoding="utf-8")
            metadata, items = load_queue(path)
            self.assertEqual(metadata, {})
            self.assertEqual(items, [{"headline": "Legacy"}])

    def test_merge_queue_preserves_existing_items(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "news_queue.json"
            replace_queue([{"headline": "Existing", "url": "https://example.com/old"}], path=path)
            document, added, duplicates = merge_queue(
                [
                    {"headline": "Repeated", "url": "https://example.com/old/"},
                    {"headline": "New", "url": "https://example.com/new"},
                ],
                path=path,
            )
            self.assertEqual(added, 1)
            self.assertEqual(duplicates, 0)
            self.assertEqual(document["total_items"], 2)

    def test_filter_recent_items_keeps_fresh_and_undated_items(self) -> None:
        now = datetime.now(timezone.utc)
        items = [
            {"headline": "fresh", "published_at": now.isoformat()},
            {"headline": "old", "published_at": (now - timedelta(days=9)).isoformat()},
            {"headline": "undated"},
        ]
        self.assertEqual(
            [item["headline"] for item in filter_recent_items(items, days=7)],
            ["fresh", "undated"],
        )


if __name__ == "__main__":
    unittest.main()

