"""Contract tests for opt-in XCLI read-only automation slots."""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import xcli_utils


class XcliSlotRoutingTests(unittest.TestCase):
    @patch("xcli_utils.run_xcli_json", return_value=[])
    @patch("xcli_utils.xcli_command", side_effect=lambda *args: list(args))
    def test_home_slot_is_forwarded_only_when_requested(self, command, _run):
        xcli_utils.collect_home_tweets(7)
        self.assertEqual(("twitter_home", "--count", "7"), command.call_args.args)

        xcli_utils.collect_home_tweets(7, slot="home")
        self.assertEqual(
            ("twitter_home", "--count", "7", "--slot", "home"),
            command.call_args.args,
        )

    @patch("xcli_utils.run_xcli_json", return_value=[])
    @patch("xcli_utils.xcli_command", side_effect=lambda *args: list(args))
    def test_timeline_slot_is_forwarded_only_when_requested(self, command, _run):
        xcli_utils.collect_timeline_tweets("OpenAI", days=2)
        self.assertEqual(
            ("twitter_timeline", "--handle", "openai", "--days", "2"),
            command.call_args.args,
        )

        xcli_utils.collect_timeline_tweets("OpenAI", days=2, slot="watch-2")
        self.assertEqual(
            (
                "twitter_timeline",
                "--handle",
                "openai",
                "--days",
                "2",
                "--slot",
                "watch-2",
            ),
            command.call_args.args,
        )

    @patch("xcli_utils.subprocess.run")
    def test_strict_mode_rejects_failed_or_unrefreshed_live_output(self, run):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "timeline.json"
            output_path.write_text("[]", encoding="utf-8")

            run.return_value = subprocess.CompletedProcess(["xcli"], 1, "", "bridge down")
            self.assertEqual([], xcli_utils.run_xcli_json(["xcli"], output_path=output_path))
            with self.assertRaisesRegex(RuntimeError, "bridge down"):
                xcli_utils.run_xcli_json(
                    ["xcli"],
                    output_path=output_path,
                    allow_cache_fallback=False,
                    raise_on_error=True,
                )

            run.return_value = subprocess.CompletedProcess(["xcli"], 0, "", "")
            with self.assertRaisesRegex(RuntimeError, "did not refresh"):
                xcli_utils.run_xcli_json(
                    ["xcli"],
                    output_path=output_path,
                    allow_cache_fallback=False,
                    raise_on_error=True,
                )


if __name__ == "__main__":
    unittest.main()
