from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from transcript_retrieval import retrieve_transcript


class TranscriptRetrievalTests(unittest.TestCase):
    def video(self, video_id: str = "abc123") -> dict:
        return {
            "video_id": video_id,
            "title": "Demo Video",
            "channel": "Demo Channel",
            "url": f"https://www.youtube.com/watch?v={video_id}",
        }

    def test_reuses_existing_default_transcript_without_cli(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            existing = output_dir / "abc123_Demo Video.txt"
            existing.write_text("already fetched", encoding="utf-8")

            def fail_command(*args: str) -> list[str]:
                raise AssertionError("CLI should not be called when transcript already exists")

            result = retrieve_transcript(
                self.video(),
                output_dir=output_dir,
                command_builder=fail_command,
            )

        self.assertEqual("SKIPPED_EXISTS", result["status"])
        self.assertEqual(str(existing), result["transcript_file"])
        self.assertEqual(str(existing), result["output_location"])
        self.assertIsNone(result.get("reason"))

    def test_no_caption_cli_failure_is_no_transcript_available(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "abc123_Demo Video.txt"

            def runner(*args, **kwargs) -> subprocess.CompletedProcess:
                return subprocess.CompletedProcess(args[0], 1, stdout="not found", stderr="no transcript")

            result = retrieve_transcript(
                self.video(),
                output_path=output_path,
                reuse_existing=False,
                command_builder=lambda *args: ["yt-transcript", *args],
                runner=runner,
                caption_probe=lambda url: (False, "no_manual_or_automatic_captions_detected"),
            )

        self.assertEqual("NO_TRANSCRIPT_AVAILABLE", result["status"])
        self.assertEqual("no_manual_or_automatic_captions_detected", result["reason"])
        self.assertEqual(str(output_path), result["output_location"])
        self.assertIn("no transcript", result["stderr_tail"])

    def test_cli_adapter_success_writes_requested_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "abc123_Demo Video.txt"

            def command_builder(*args: str) -> list[str]:
                return ["fake-yt", *args]

            def runner(cmd, **kwargs) -> subprocess.CompletedProcess:
                self.assertEqual(
                    [
                        "fake-yt",
                        "get",
                        "https://www.youtube.com/watch?v=abc123",
                        "-o",
                        str(output_path),
                    ],
                    cmd,
                )
                output_path.write_text("transcript text", encoding="utf-8")
                return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

            result = retrieve_transcript(
                self.video(),
                output_path=output_path,
                reuse_existing=False,
                command_builder=command_builder,
                runner=runner,
            )

        self.assertEqual("OK", result["status"])
        self.assertEqual(str(output_path), result["transcript_file"])
        self.assertEqual(len("transcript text"), result["bytes"])

    def test_failed_adapter_and_subprocess_are_failed_not_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "abc123_Demo Video.txt"

            adapter_result = retrieve_transcript(
                self.video(),
                output_path=output_path,
                reuse_existing=False,
                command_builder=lambda *args: (_ for _ in ()).throw(FileNotFoundError("missing cli")),
                caption_probe=lambda url: (False, "no captions"),
            )

            def timeout_runner(cmd, **kwargs) -> subprocess.CompletedProcess:
                raise subprocess.TimeoutExpired(cmd, timeout=1)

            subprocess_result = retrieve_transcript(
                self.video("def456"),
                output_path=Path(temp_dir) / "def456_Demo Video.txt",
                reuse_existing=False,
                command_builder=lambda *args: ["yt-transcript", *args],
                runner=timeout_runner,
                caption_probe=lambda url: (False, "no captions"),
            )

        self.assertEqual("FAILED", adapter_result["status"])
        self.assertTrue(adapter_result["reason"].startswith("adapter_error:"))
        self.assertEqual("FAILED", subprocess_result["status"])
        self.assertTrue(subprocess_result["reason"].startswith("subprocess_timeout:"))


if __name__ == "__main__":
    unittest.main()
