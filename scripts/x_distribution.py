"""Master CLI for X Distribution operations."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from source_clis import WORKSPACE_ROOT, python_script_command
from source_registry import collector_outputs, enabled_live_source_scripts, live_source_outputs


PYTHON = sys.executable
ROOT = WORKSPACE_ROOT
HARNESS_RESULTS = ROOT / ".harness" / "verification_results.json"


TARGET_STORAGE_DIRS = [
    "data/raw/youtube",
    "data/raw/x",
    "data/raw/reddit",
    "data/raw/hacker_news",
    "data/raw/rss",
    "data/raw/github",
    "data/raw/huggingface",
    "data/raw/arxiv",
    "data/raw/finance",
    "data/raw/startups",
    "data/raw/model_market",
    "data/raw/science",
    "data/raw/status",
    "data/normalized",
    "data/verified",
    "data/content",
    "data/state",
    "data/exports/reports",
]


def run_command(command: list[str], *, check: bool = False) -> subprocess.CompletedProcess:
    print("$ " + " ".join(command))
    return subprocess.run(command, cwd=ROOT, text=True, check=check)


def run_script(script_name: str, *args: str, check: bool = False) -> subprocess.CompletedProcess:
    return run_command(python_script_command(script_name, *args), check=check)


def write_verification_result(name: str, result: dict) -> None:
    HARNESS_RESULTS.parent.mkdir(parents=True, exist_ok=True)
    if HARNESS_RESULTS.exists():
        with HARNESS_RESULTS.open("r", encoding="utf-8") as file_handle:
            payload = json.load(file_handle)
    else:
        payload = {"runs": []}
    payload["runs"].append(
        {
            "name": name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **result,
        }
    )
    with HARNESS_RESULTS.open("w", encoding="utf-8") as file_handle:
        json.dump(payload, file_handle, indent=2, ensure_ascii=False)


def ensure_storage_layout() -> dict:
    created = []
    existing = []
    for rel_path in TARGET_STORAGE_DIRS:
        path = ROOT / rel_path
        if path.exists():
            existing.append(rel_path)
        else:
            path.mkdir(parents=True, exist_ok=True)
            created.append(rel_path)
        marker = path / ".gitkeep"
        if not marker.exists():
            marker.write_text("", encoding="utf-8")
    manifest = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "created": created,
        "existing": existing,
        "legacy_paths_preserved": [
            "data/news_queue.json",
            "data/new_videos_queue.json",
            "data/mass_transcript_pool.json",
            "data/transcripts",
        ],
    }
    manifest_path = ROOT / "data" / "storage_layout_manifest.json"
    with manifest_path.open("w", encoding="utf-8") as file_handle:
        json.dump(manifest, file_handle, indent=2, ensure_ascii=False)
    print(f"Storage layout ready. Manifest: {manifest_path}")
    return manifest


def validate() -> int:
    return run_script("validate_schemas.py").returncode


def check_routes() -> int:
    return run_script("source_clis.py").returncode


def normalize() -> int:
    return run_script("queue_maintenance.py").returncode


def collect(args: argparse.Namespace) -> int:
    if args.verify_only:
        print("Configured live source scripts:")
        for script in enabled_live_source_scripts():
            print(f"  - {script}")
        print("Configured live source outputs:")
        for output in live_source_outputs():
            print(f"  - {output}")
        print("Configured aggregate collector outputs:")
        for output in collector_outputs():
            print(f"  - {output}")
        write_verification_result(
            "collect-verify-only",
            {
                "status": "passed",
                "live_source_scripts": enabled_live_source_scripts(),
                "live_source_outputs": live_source_outputs(),
                "collector_outputs": collector_outputs(),
            },
        )
        return 0
    collect_args = ["--skip-x"] if args.skip_x else []
    return run_script("phase1_collect.py", *collect_args).returncode


def cleanup(args: argparse.Namespace) -> int:
    command_args = ["--apply"] if args.apply else []
    return run_script("archive_stale_files.py", *command_args).returncode


def generate_posts() -> int:
    return run_script("generated_codegen.py").returncode


def verify() -> int:
    checks = {
        "routes": check_routes(),
        "schemas": validate(),
    }
    status = "passed" if all(code == 0 for code in checks.values()) else "failed"
    write_verification_result("verify", {"status": status, "checks": checks})
    return 0 if status == "passed" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="X Distribution master CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    collect_parser = subparsers.add_parser("collect", help="Run Phase 1 collection")
    collect_parser.add_argument("--verify-only", action="store_true", help="Only print configured collectors and outputs")
    collect_parser.add_argument("--skip-x", action="store_true", help="Skip X (Twitter) feed collection")

    subparsers.add_parser("validate", help="Validate critical schemas")
    subparsers.add_parser("routes", help="Check XCLI and YT Transcript CLI routes")
    subparsers.add_parser("normalize", help="Normalize and dedupe news queue")
    subparsers.add_parser("storage-check", help="Ensure target storage layout exists")
    subparsers.add_parser("verify", help="Run route and schema checks")
    subparsers.add_parser("generate-posts", help="Prepare verified-only manual post drafting packets")

    cleanup_parser = subparsers.add_parser("cleanup", help="Archive stale generated files")
    cleanup_parser.add_argument("--apply", action="store_true", help="Move stale candidates into cache/stale_archive")

    args = parser.parse_args()
    if args.command == "collect":
        return collect(args)
    if args.command == "validate":
        return validate()
    if args.command == "routes":
        return check_routes()
    if args.command == "normalize":
        return normalize()
    if args.command == "storage-check":
        ensure_storage_layout()
        return 0
    if args.command == "verify":
        return verify()
    if args.command == "generate-posts":
        return generate_posts()
    if args.command == "cleanup":
        return cleanup(args)
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
