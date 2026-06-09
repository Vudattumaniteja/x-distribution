"""Pipeline-level contracts for shared X coordinator entry points."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import master_poller
import phase1_collect
import x_radar_standalone
import x_timeline_scraper_standalone
from collection_adapter import ArtifactResearchLaneAdapter, LaneRunResult


def x_result(status: str = "LIVE_OK", *, run_id: str = "run-123", tweets=None) -> dict:
    return {
        "run_id": run_id,
        "status": status,
        "tweets": list(tweets or []),
    }


def watch_tweet(handle: str = "openai") -> dict:
    return {
        "url": f"https://x.com/{handle}/status/1",
        "text": "signal",
        "_x_collection_scope": f"watchlist:{handle}",
        "_x_collection_source": "live",
    }


class XCollectionEntryPointTests(unittest.TestCase):
    @patch("phase1_collect.collect_x_read_only")
    def test_canonical_x_lane_uses_shared_coordinator(self, collect):
        collect.return_value = x_result("DEGRADED_OK", tweets=[watch_tweet()])

        items, metadata = phase1_collect.collect_x_data()

        self.assertEqual("DEGRADED_OK", metadata["status"])
        self.assertEqual(1, len(items))
        self.assertEqual("Verified", items[0]["signal_type"])
        self.assertEqual(3, collect.call_args.kwargs["workers"])

    @patch("x_radar_standalone.collect_x_read_only")
    def test_targeted_radar_propagates_status_run_id_and_overrides(self, collect):
        collect.return_value = x_result("PARTIAL", tweets=[watch_tweet()])
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "accounts.json"
            output_path = Path(temp_dir) / "radar.json"
            config_path.write_text(
                json.dumps({"accounts": [{"handle": "@openai", "tier": "must_follow", "category": "corporate"}]}),
                encoding="utf-8",
            )
            with (
                patch.object(x_radar_standalone, "CONFIG_PATH", config_path),
                patch.object(x_radar_standalone, "OUTPUT_PATH", output_path),
                patch.object(sys, "argv", ["x_radar_standalone.py", "--workers", "1", "--skip-home"]),
            ):
                code = x_radar_standalone.main()
            output = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(0, code)
        self.assertEqual("PARTIAL", output["status"])
        self.assertEqual("run-123", output["run_id"])
        self.assertEqual(1, collect.call_args.kwargs["workers"])
        self.assertTrue(collect.call_args.kwargs["skip_home"])

    @patch("x_timeline_scraper_standalone.collect_x_read_only")
    def test_compatibility_timeline_uses_coordinator_and_failed_is_nonzero(self, collect):
        collect.return_value = x_result("FAILED")
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "accounts.json"
            output_path = Path(temp_dir) / "timeline.json"
            config_path.write_text(
                json.dumps({"accounts": [{"handle": "@openai", "tier": "must_follow"}]}),
                encoding="utf-8",
            )
            with (
                patch.object(x_timeline_scraper_standalone, "CONFIG_PATH", str(config_path)),
                patch.object(x_timeline_scraper_standalone, "OUTPUT_PATH", str(output_path)),
            ):
                code = x_timeline_scraper_standalone.main()
            output = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(1, code)
        self.assertEqual("FAILED", output["status"])
        self.assertTrue(collect.call_args.kwargs["skip_home"])

    @patch("master_poller.collect_x_read_only")
    def test_master_poller_x_lane_uses_coordinator(self, collect):
        collect.return_value = x_result(
            "LIVE_OK",
            tweets=[
                {**watch_tweet(), "url": f"https://x.com/openai/status/{index}"}
                for index in range(6)
            ],
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "accounts.json"
            config_path.write_text(
                json.dumps({"accounts": [{"handle": "@openai", "tier": "must_follow"}]}),
                encoding="utf-8",
            )
            with patch.object(master_poller, "CONFIG_X", str(config_path)):
                tweets = master_poller.poller_1_x()

        self.assertEqual(5, len(tweets))
        self.assertEqual("@openai", tweets[0]["source"])
        self.assertEqual("LIVE_OK", master_poller.LAST_X_COLLECTION["status"])
        collect.assert_called_once()

    def test_master_poller_failed_x_lane_returns_nonzero(self):
        with (
            patch.object(master_poller, "poller_1_x", return_value=[]),
            patch.object(master_poller, "poller_2_blogs", return_value=[]),
            patch.object(master_poller, "poller_3_youtube", return_value=[]),
        ):
            master_poller.LAST_X_COLLECTION = x_result("FAILED")
            code = master_poller.main()

        self.assertEqual(1, code)

    def test_weekly_sweep_remains_delegated_through_phase1(self):
        source = (Path(__file__).with_name("weekly_sweep_orchestrator.py")).read_text(encoding="utf-8")
        self.assertIn("python_script_command('phase1_collect.py')", source)
        self.assertNotIn("x_collection_coordinator", source)


class Phase1StatusPropagationTests(unittest.TestCase):
    def run_phase1(self, status: str) -> tuple[int, dict]:
        metadata = x_result(status, run_id=f"run-{status.lower()}")
        lane_names = [
            "collect_rss_data",
            "collect_youtube_data",
            "collect_community_data",
            "collect_finance_data",
            "collect_startup_funding_data",
            "collect_model_market_data",
            "collect_startup_collection_data",
            "collect_science_breakthrough_data",
            "collect_developer_sentiment_data",
            "collect_prediction_market_data",
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            lane_health_path = Path(temp_dir) / "lane_health.json"
            patches = [patch.object(phase1_collect, name, return_value=[]) for name in lane_names]
            for active_patch in patches:
                active_patch.start()
            try:
                with (
                    patch.object(phase1_collect, "collect_x_data", return_value=([], metadata)),
                    patch.object(
                        phase1_collect.ArtifactResearchLaneAdapter,
                        "run",
                        return_value=LaneRunResult("artifact_research", []),
                    ),
                    patch.object(phase1_collect, "replace_queue", return_value=({"total_items": 0}, 0)),
                    patch.object(phase1_collect, "filter_recent_items", return_value=[]),
                    patch.object(phase1_collect, "PHASE1_LANE_HEALTH_PATH", str(lane_health_path)),
                    patch.object(phase1_collect.os.path, "exists", return_value=False),
                ):
                    code = phase1_collect.main()
                lane_health = json.loads(lane_health_path.read_text(encoding="utf-8"))
            finally:
                for active_patch in reversed(patches):
                    active_patch.stop()
        return code, lane_health

    def test_live_degraded_and_partial_are_fail_soft_with_lane_metadata(self):
        for status in ("LIVE_OK", "DEGRADED_OK", "PARTIAL"):
            with self.subTest(status=status):
                code, lane_health = self.run_phase1(status)
                x_lane = next(lane for lane in lane_health["lanes"] if lane["lane"] == "x")
                self.assertEqual(0, code)
                self.assertEqual(status, x_lane["x_status"])
                self.assertEqual(f"run-{status.lower()}", x_lane["x_run_id"])

    def test_failed_x_lane_is_nonzero(self):
        code, lane_health = self.run_phase1("FAILED")
        x_lane = next(lane for lane in lane_health["lanes"] if lane["lane"] == "x")
        self.assertEqual(1, code)
        self.assertEqual("FAILED", x_lane["x_status"])


class Phase1LaneAdapterTests(unittest.TestCase):
    def test_artifact_research_adapter_hides_output_schema_from_runner(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "github_discoveries.json"
            output_path.write_text(
                json.dumps(
                    {
                        "new_discoveries": [
                            {
                                "repo_name": "openai-python",
                                "description": "SDK release",
                                "source": "GitHub",
                                "html_url": "https://github.com/openai/openai-python",
                                "updated_at": "2026-06-01T00:00:00Z",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            with (
                patch("collection_adapter.WORKSPACE_ROOT", Path(temp_dir)),
                patch("source_registry.enabled_live_source_scripts", return_value=["github_monitor_standalone.py"]),
                patch("source_registry.live_source_outputs", return_value=["github_discoveries.json"]),
                patch("source_clis.python_script_command", return_value=["py", "scripts/github_monitor_standalone.py"]),
                patch("collection_adapter.subprocess.run") as run,
            ):
                run.return_value.returncode = 0
                result = ArtifactResearchLaneAdapter().run()

        self.assertEqual("artifact_research", result.lane)
        self.assertEqual("OK", result.status)
        self.assertEqual(1, len(result.records))
        self.assertEqual("openai-python", result.records[0]["headline"])
        self.assertEqual("Artifact/Research Source", result.records[0]["signal_type"])
        self.assertEqual({"lane": "artifact_research", "status": "OK", "items": 1}, result.health_entry())


if __name__ == "__main__":
    unittest.main()
