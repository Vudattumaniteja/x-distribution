"""Contract tests for verified-only editorial drafting packets."""

from __future__ import annotations

import unittest

from generated_codegen import build_draft_packets, eligible_items


class PostGenerationTests(unittest.TestCase):
    def test_only_fact_checked_items_are_eligible(self) -> None:
        items = [
            {"id": "verified", "fact_check_status": "verified"},
            {"id": "likely", "fact_check_data": {"verdict": "LIKELY_TRUE"}},
            {"id": "pending", "fact_check_status": "pending"},
            {"id": "missing"},
        ]
        self.assertEqual([item["id"] for item in eligible_items(items)], ["verified", "likely"])

    def test_packets_contain_empty_manual_drafts(self) -> None:
        packets = build_draft_packets(
            [{"id": "verified", "headline": "Source-backed", "verdict": "VERIFIED"}],
            [{"id": 1, "name": "Hook-Accuracy", "strategy": "Precise", "structure": ["Hook"]}],
        )
        self.assertEqual(packets[0]["status"], "needs_manual_draft")
        self.assertEqual(packets[0]["variants"][0]["text"], "")


if __name__ == "__main__":
    unittest.main()
