"""Canonical local CLI routes for X and YouTube source collection."""

import os
import json
from pathlib import Path
import subprocess
import sys


WORKSPACE_ROOT = Path(
    os.environ.get("X_DISTRIBUTION_ROOT", Path(__file__).resolve().parents[1])
)
SOURCE_REGISTRY_PATH = WORKSPACE_ROOT / "config" / "source_registry.json"


from source_registry import load_registry

RUNTIME_PATHS = load_registry().get("runtime_paths", {})
PYTHON_EXE = Path(os.environ.get("X_DISTRIBUTION_PYTHON", sys.executable))

def _resolve_config_path(configured_path: str) -> Path:
    if not configured_path or configured_path.startswith("__missing_"):
        return Path(configured_path)
    p = Path(configured_path)
    if not p.is_absolute():
        return WORKSPACE_ROOT / p
    return p

XCLI_SCRIPT = _resolve_config_path(
    os.environ.get(
        "XCLI_SCRIPT",
        RUNTIME_PATHS.get("default_xcli_script", "__missing_xcli_script__"),
    )
)
YT_TRANSCRIPT_CLI = _resolve_config_path(
    os.environ.get(
        "YT_TRANSCRIPT_CLI",
        RUNTIME_PATHS.get("default_yt_transcript_cli", "__missing_yt_transcript_cli__"),
    )
)
YT_TRANSCRIPT_PY_SCRIPT = _resolve_config_path(
    os.environ.get(
        "YT_TRANSCRIPT_PY_SCRIPT",
        RUNTIME_PATHS.get("default_yt_transcript_py_script", "__missing_yt_transcript_py_script__"),
    )
)


def _require_file(path: Path, label: str) -> None:
    if str(path).startswith("__missing_"):
        raise FileNotFoundError(
            f"{label} is not configured. Set the matching environment variable "
            "or config/source_registry.json runtime_paths entry."
        )
    if not path.is_file():
        raise FileNotFoundError(f"{label} is not available at the pinned path: {path}")


def xcli_command(*args: str) -> list[str]:
    """Return a command routed through the pinned X/Twitter CLI."""
    _require_file(PYTHON_EXE, "Python interpreter")
    _require_file(XCLI_SCRIPT, "XCLI")
    return [str(PYTHON_EXE), str(XCLI_SCRIPT), *map(str, args)]


def yt_transcript_command(*args: str) -> list[str]:
    """Return a command routed through the pinned global YouTube Transcript CLI."""
    _require_file(YT_TRANSCRIPT_CLI, "YT Transcript CLI")
    return [str(YT_TRANSCRIPT_CLI), *map(str, args)]


def yt_transcript_python_script() -> Path:
    """Return the importable Python implementation behind the global transcript CLI."""
    _require_file(YT_TRANSCRIPT_PY_SCRIPT, "YT Transcript Python script")
    return YT_TRANSCRIPT_PY_SCRIPT


def python_script_command(script_name: str, *args: str) -> list[str]:
    """Run another workspace script through the pinned Python interpreter."""
    script_path = WORKSPACE_ROOT / "scripts" / script_name
    _require_file(PYTHON_EXE, "Python interpreter")
    _require_file(script_path, f"workspace script {script_name}")
    return [str(PYTHON_EXE), str(script_path), *map(str, args)]


def check_routes() -> None:
    """Check CLI entrypoints without scraping or fetching live content."""
    for label, command in (
        ("XCLI", xcli_command("--help")),
        ("YT Transcript CLI", yt_transcript_command("--help")),
    ):
        subprocess.run(command, cwd=WORKSPACE_ROOT, check=True, capture_output=True, text=True)
        print(f"{label}: ready")


if __name__ == "__main__":
    check_routes()
