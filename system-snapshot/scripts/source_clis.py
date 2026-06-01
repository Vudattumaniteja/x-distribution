"""Canonical local CLI routes shared by snapshot compatibility scripts."""

from pathlib import Path


PYTHON_EXE = Path(r"C:\Users\Manit\AppData\Local\Programs\Python\Python311\python.exe")
XCLI_SCRIPT = Path(r"C:\Users\Manit\Desktop\Twitter automation\cli.py")
YT_TRANSCRIPT_CLI_SCRIPT = Path(r"C:\Users\Manit\.gemini\x-distribution\scripts\yt_transcript_cli.py")


def _require_file(path: Path, label: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"{label} is not available at the pinned path: {path}")


def xcli_command(*args: str) -> list[str]:
    _require_file(PYTHON_EXE, "Python interpreter")
    _require_file(XCLI_SCRIPT, "XCLI")
    return [str(PYTHON_EXE), str(XCLI_SCRIPT), *map(str, args)]


def yt_transcript_command(*args: str) -> list[str]:
    _require_file(PYTHON_EXE, "Python interpreter")
    _require_file(YT_TRANSCRIPT_CLI_SCRIPT, "YT Transcript CLI")
    return [str(PYTHON_EXE), str(YT_TRANSCRIPT_CLI_SCRIPT), *map(str, args)]
