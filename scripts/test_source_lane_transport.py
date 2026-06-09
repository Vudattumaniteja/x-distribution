"""Contract tests for shared source-lane transport helpers."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from source_lane_transport import (
    collect_rss_source,
    dedupe_by_source_identity,
    write_collector_outputs,
)


class FakeResponse:
    def __init__(self, content: bytes, status_code: int = 200) -> None:
        self.content = content
        self.status_code = status_code


class FakeSession:
    def __init__(self, response: FakeResponse | None = None, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.requests: list[dict[str, Any]] = []

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        self.requests.append({"url": url, **kwargs})
        if self.error:
            raise self.error
        if self.response is None:
            raise RuntimeError("missing fake response")
        return self.response


def rss_fixture() -> bytes:
    return b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <item>
      <title>AI startup raises Series A</title>
      <link>https://example.com/a</link>
      <description><![CDATA[<p>Company raised funding for AI agents.</p>]]></description>
      <pubDate>Mon, 08 Jun 2026 10:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Ignored old item</title>
      <link>https://example.com/old</link>
      <description>Old AI funding news.</description>
      <pubDate>Mon, 01 Jun 2026 10:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>"""


class SourceLaneTransportTests(unittest.TestCase):
    def test_collect_rss_source_success_normalizes_entries_and_diagnostics(self) -> None:
        session = FakeSession(FakeResponse(rss_fixture()))
        cutoff = datetime(2026, 6, 7, tzinfo=timezone.utc)

        items, diagnostics = collect_rss_source(
            session,  # type: ignore[arg-type]
            {"name": "Example", "rss_url": "https://example.com/rss"},
            {"request_timeout_seconds": 7, "max_items_per_source": 5},
            cutoff,
            headers={"User-Agent": "test-agent"},
            item_builder=lambda source, title, url, published_at, summary, discovery_source: {
                "source": source["name"],
                "title": title,
                "url": url,
                "published_at": published_at,
                "summary": summary,
                "discovery_source": discovery_source,
                "relevance_score": 4,
            },
        )

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["summary"], "Company raised funding for AI agents.")
        self.assertEqual(items[0]["discovery_source"], "https://example.com/rss")
        self.assertEqual(session.requests[0]["timeout"], 7)
        self.assertEqual(session.requests[0]["headers"], {"User-Agent": "test-agent"})
        self.assertEqual(diagnostics["status"], "OK")
        self.assertEqual(diagnostics["http_status"], 200)
        self.assertEqual(diagnostics["feed_entries"], 2)
        self.assertEqual(diagnostics["items_seen"], 2)
        self.assertEqual(diagnostics["items_added"], 1)
        self.assertFalse(diagnostics["parse_warning"])

    def test_collect_rss_source_failure_reports_source_health(self) -> None:
        session = FakeSession(error=TimeoutError("timed out"))

        items, diagnostics = collect_rss_source(
            session,  # type: ignore[arg-type]
            {"name": "Broken", "rss_url": "https://example.com/rss"},
            {},
            datetime(2026, 6, 7, tzinfo=timezone.utc),
            item_builder=lambda *_args: None,
        )

        self.assertEqual(items, [])
        self.assertEqual(diagnostics["status"], "ERROR")
        self.assertIn("timed out", diagnostics["error"])
        self.assertEqual(diagnostics["items_seen"], 0)
        self.assertEqual(diagnostics["items_added"], 0)

    def test_dedupe_by_source_identity_keeps_best_item_per_source_key(self) -> None:
        items = [
            {"source": "A", "url": "https://example.com/one", "relevance_score": 2, "published_at": "2026-06-08T00:00:00+00:00"},
            {"source": "A", "url": "https://example.com/one", "relevance_score": 8, "published_at": "2026-06-08T00:00:00+00:00"},
            {"source": "B", "url": "https://example.com/one", "relevance_score": 3, "published_at": "2026-06-09T00:00:00+00:00"},
        ]

        deduped = dedupe_by_source_identity(items)

        self.assertEqual(len(deduped), 2)
        self.assertEqual(deduped[0]["source"], "B")
        self.assertEqual(deduped[1]["relevance_score"], 8)

    def test_write_collector_outputs_preserves_raw_and_signals_shapes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            raw_path = Path(temp_dir) / "raw.json"
            signals_path = Path(temp_dir) / "signals.json"
            cutoff = datetime(2026, 6, 7, tzinfo=timezone.utc)
            item = {"title": "AI funding", "url": "https://example.com/a"}
            health = {"source": "Example", "status": "OK"}

            write_collector_outputs(
                raw_path=raw_path,
                signals_path=signals_path,
                items=[item],
                diagnostics=[health],
                cutoff=cutoff,
            )

            raw_payload = json.loads(raw_path.read_text(encoding="utf-8"))
            signals_payload = json.loads(signals_path.read_text(encoding="utf-8"))
            self.assertEqual(raw_payload["cutoff"], cutoff.isoformat())
            self.assertEqual(raw_payload["total_items"], 1)
            self.assertEqual(raw_payload["items"], [item])
            self.assertEqual(raw_payload["source_health"], [health])
            self.assertEqual(signals_payload["signals"], [item])
            self.assertEqual(signals_payload["source_health"], [health])


if __name__ == "__main__":
    unittest.main()
