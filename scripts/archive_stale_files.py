"""Archive generated/stale workspace files without deleting user data."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from source_registry import load_registry


ROOT = Path(__file__).resolve().parents[1]


def resolve_inside_workspace(path: Path) -> Path:
    resolved = path.resolve()
    root = ROOT.resolve()
    if resolved != root and root not in resolved.parents:
        raise ValueError(f"Refusing path outside workspace: {resolved}")
    return resolved


def candidate_paths() -> list[Path]:
    policy = load_registry().get("stale_file_policy", {})
    candidates: list[Path] = []
    for pattern in policy.get("archive_patterns", []):
        for path in ROOT.glob(pattern):
            if path.exists():
                candidates.append(path)
    return sorted(set(candidates), key=lambda item: str(item).lower())


def archive_path_for(path: Path, archive_root: Path) -> Path:
    relative = path.relative_to(ROOT)
    return archive_root / relative


def main() -> None:
    parser = argparse.ArgumentParser(description="Archive stale generated files safely.")
    parser.add_argument("--apply", action="store_true", help="Move candidates into cache/stale_archive.")
    args = parser.parse_args()

    policy = load_registry().get("stale_file_policy", {})
    archive_root = ROOT / policy.get("archive_root", "cache/stale_archive")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_archive_root = archive_root / timestamp

    candidates = [resolve_inside_workspace(path) for path in candidate_paths()]
    manifest = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": "apply" if args.apply else "dry_run",
        "archive_root": str(run_archive_root),
        "candidate_count": len(candidates),
        "candidates": [],
    }

    for path in candidates:
        destination = archive_path_for(path, run_archive_root)
        entry = {
            "source": str(path),
            "destination": str(destination),
            "kind": "directory" if path.is_dir() else "file",
            "status": "planned",
        }
        if args.apply:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(path), str(destination))
            entry["status"] = "archived"
        manifest["candidates"].append(entry)

    if args.apply:
        run_archive_root.mkdir(parents=True, exist_ok=True)
        manifest_path = run_archive_root / "manifest.json"
    else:
        (ROOT / "cache").mkdir(parents=True, exist_ok=True)
        manifest_path = ROOT / "cache" / "stale_file_audit.json"

    with manifest_path.open("w", encoding="utf-8") as file_handle:
        json.dump(manifest, file_handle, indent=2, ensure_ascii=False)

    action = "Archived" if args.apply else "Audited"
    print(f"{action} {len(candidates)} stale candidate(s). Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
