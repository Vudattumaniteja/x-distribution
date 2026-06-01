"""Shared helpers for safe, read-only XCLI collection."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Iterable

from source_clis import xcli_command


UTF8_ENV = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}


def normalize_handle(handle: str) -> str:
    return (handle or "").strip().lstrip("@").lower()


def extract_json_array(text: str | None) -> list[dict] | None:
    if not text:
        return None
    match = re.search(r"\[\s*\{", text)
    if not match:
        return None
    try:
        parsed, _ = json.JSONDecoder().raw_decode(text[match.start() :])
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, list) else None


def read_json_list(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as file_handle:
        parsed = json.load(file_handle)
    return parsed if isinstance(parsed, list) else []


def run_xcli_json(command: list[str], *, timeout: int = 180, output_path: Path | None = None) -> list[dict]:
    """Run XCLI and return a JSON array from output file or stdout/stderr."""
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=UTF8_ENV,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        if output_path and output_path.exists():
            print(f"  XCLI timed out; using cached output at {output_path}.")
            return read_json_list(output_path)
        print("  XCLI timed out and no cached output is available.")
        return []
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        concise = ""
        for line in reversed(detail.splitlines()):
            if line.strip():
                concise = line.strip()
                break
        if output_path and output_path.exists():
            print(f"  XCLI failed ({concise[:180]}); using cached output at {output_path}.")
            return read_json_list(output_path)
        print(f"  XCLI failed ({concise[:180]}); no cached output available.")
        return []

    if output_path:
        return read_json_list(output_path)

    parsed = extract_json_array(result.stdout) or extract_json_array(result.stderr)
    return parsed or []


def tweet_url_handle(tweet: dict) -> str:
    url = tweet.get("url") or ""
    match = re.search(r"https?://(?:www\.)?(?:x|twitter)\.com/([^/?#]+)/", url, re.I)
    return normalize_handle(match.group(1)) if match else ""


def tweet_author_handles(tweet: dict) -> set[str]:
    author = tweet.get("author") or ""
    return {normalize_handle(match) for match in re.findall(r"@([A-Za-z0-9_]{1,15})", author)}


def tweet_matches_handle(tweet: dict, handle: str) -> bool:
    expected = normalize_handle(handle)
    if not expected:
        return False
    return tweet_url_handle(tweet) == expected or expected in tweet_author_handles(tweet)


def filter_tweets_for_handle(tweets: Iterable[dict], handle: str) -> list[dict]:
    source_tweets = list(tweets)
    filtered = [tweet for tweet in source_tweets if tweet_matches_handle(tweet, handle)]
    dropped = len(source_tweets) - len(filtered)
    if dropped:
        print(f"  Dropped {dropped} XCLI item(s) that did not match @{normalize_handle(handle)}.")
    return filtered


def collect_home_tweets(count: int = 30, output_path: str | Path | None = None) -> list[dict]:
    path = Path(output_path) if output_path else None
    return run_xcli_json(
        xcli_command("twitter_home", "--count", str(count), *(("--output", str(path)) if path else ())),
        timeout=240,
        output_path=path,
    )


def collect_timeline_tweets(
    handle: str,
    *,
    days: float = 7.0,
    output_path: str | Path | None = None,
) -> list[dict]:
    path = Path(output_path) if output_path else None
    tweets = run_xcli_json(
        xcli_command(
            "twitter_timeline",
            "--handle",
            normalize_handle(handle),
            "--days",
            str(days),
            *(("--output", str(path)) if path else ()),
        ),
        timeout=240,
        output_path=path,
    )
    return filter_tweets_for_handle(tweets, handle)
