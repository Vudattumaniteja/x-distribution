"""Shared YouTube transcript retrieval adapter.

All transcript content must come through the pinned YT Transcript CLI route in
source_clis.py. This module owns reuse, output-path handling, and failure
classification so orchestration scripts do not fork those rules.
"""

from __future__ import annotations

import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping, Sequence

from source_clis import WORKSPACE_ROOT, yt_transcript_command


TRANSCRIPT_DIR = WORKSPACE_ROOT / "data" / "transcripts"
INVALID_TRANSCRIPT_MARKERS = (
    "Google Sorry",
    "We're sorry",
    "automated queries",
    "unusual traffic from your computer network",
    "To protect our users, we can't process your request right now",
    "<!doctype html",
    "<html",
)


def safe_filename_part(value: str, limit: int = 80) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value or "untitled")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:limit].rstrip(" .") or "untitled"


def video_id_from_url(url: str) -> str:
    if not url:
        return ""
    match = re.search(r"(?:v=|/shorts/|youtu\.be/)([A-Za-z0-9_-]{6,})", url)
    if match:
        return match.group(1)
    return url.rstrip("/").split("/")[-1]


def normalize_video_url(video: Mapping[str, object] | str) -> str:
    if isinstance(video, str):
        url = video
        video_id = video_id_from_url(url)
    else:
        url = str(video.get("url") or "")
        video_id = str(video.get("video_id") or video.get("id") or video_id_from_url(url))
    if not url.startswith("http"):
        url = f"https://www.youtube.com/watch?v={video_id or url}"
    return url


def video_identity(video: Mapping[str, object] | str) -> dict:
    url = normalize_video_url(video)
    if isinstance(video, str):
        video_id = video_id_from_url(url)
        return {"video_id": video_id, "title": None, "channel": None, "url": url}
    video_id = str(video.get("video_id") or video.get("id") or video_id_from_url(url))
    return {
        "video_id": video_id,
        "title": video.get("title"),
        "channel": video.get("channel") or video.get("source_account"),
        "url": url,
    }


def default_output_path(video: Mapping[str, object] | str, output_dir: Path = TRANSCRIPT_DIR) -> Path:
    identity = video_identity(video)
    video_id = identity["video_id"] or re.sub(r"[^\w-]", "_", identity["url"][-16:])
    title = safe_filename_part(str(identity.get("title") or video_id))
    return output_dir / f"{video_id}_{title}.txt"


def legacy_transcript_path(video: Mapping[str, object] | str, output_dir: Path = TRANSCRIPT_DIR) -> Path:
    identity = video_identity(video)
    return output_dir / f"transcript_{identity['video_id']}.txt"


def existing_transcript(video_id: str, output_dir: Path = TRANSCRIPT_DIR) -> Path | None:
    if not video_id:
        return None
    matches = list(output_dir.glob(f"{video_id}_*.txt"))
    return matches[0] if matches else None


def is_valid_transcript(content: str, min_chars: int = 200) -> bool:
    if not content or len(content.strip()) < min_chars:
        return False
    lowered = content.lower()
    return not any(marker.lower() in lowered for marker in INVALID_TRANSCRIPT_MARKERS)


def youtube_caption_state(url: str) -> tuple[bool, str]:
    try:
        import yt_dlp
    except Exception as exc:
        return False, f"yt_dlp_unavailable: {exc}"

    try:
        with yt_dlp.YoutubeDL({"quiet": True, "skip_download": True, "no_warnings": True}) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as exc:
        return False, f"metadata_unavailable: {exc}"

    subtitles = info.get("subtitles") or {}
    automatic = info.get("automatic_captions") or {}
    if subtitles or automatic:
        return True, "captions_present_but_yt_transcript_failed"
    return False, "no_manual_or_automatic_captions_detected"


def _result(identity: dict, status: str, output_path: Path | None, **extra: object) -> dict:
    payload = {
        "video_id": identity.get("video_id"),
        "title": identity.get("title"),
        "channel": identity.get("channel"),
        "url": identity.get("url"),
        "status": status,
        "output_location": str(output_path) if output_path else None,
    }
    if output_path:
        payload["transcript_file"] = str(output_path)
    payload.update({key: value for key, value in extra.items() if value is not None})
    return payload


def retrieve_transcript(
    video: Mapping[str, object] | str,
    *,
    output_path: str | Path | None = None,
    output_dir: str | Path = TRANSCRIPT_DIR,
    timeout_seconds: int | None = 360,
    reuse_existing: bool = True,
    require_valid: bool = False,
    min_chars: int = 200,
    accept_output_on_nonzero: bool = False,
    caption_probe: Callable[[str], tuple[bool, str]] = youtube_caption_state,
    command_builder: Callable[..., Sequence[str]] = yt_transcript_command,
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
    env: Mapping[str, str] | None = None,
) -> dict:
    """Retrieve a transcript through the canonical CLI and classify the result."""

    identity = video_identity(video)
    out_dir = Path(output_dir)
    out_file = Path(output_path) if output_path is not None else default_output_path(video, out_dir)

    if reuse_existing and output_path is None:
        existing = existing_transcript(str(identity.get("video_id") or ""), out_dir)
        if existing:
            return _result(identity, "SKIPPED_EXISTS", existing)

    out_file.parent.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc)
    try:
        cmd = list(command_builder("get", identity["url"], "-o", str(out_file)))
    except Exception as exc:
        return _result(identity, "FAILED", out_file, reason=f"adapter_error: {exc}")

    try:
        result = runner(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            env=dict(env) if env is not None else None,
        )
    except subprocess.TimeoutExpired as exc:
        return _result(identity, "FAILED", out_file, reason=f"subprocess_timeout: {exc}")
    except Exception as exc:
        return _result(identity, "FAILED", out_file, reason=f"subprocess_error: {exc}")

    duration = (datetime.now(timezone.utc) - started).total_seconds()
    if out_file.exists() and out_file.stat().st_size > 0 and (
        result.returncode == 0 or accept_output_on_nonzero
    ):
        if require_valid:
            content = out_file.read_text(encoding="utf-8", errors="replace")
            if not is_valid_transcript(content, min_chars=min_chars):
                out_file.unlink(missing_ok=True)
                return _result(
                    identity,
                    "FAILED",
                    out_file,
                    reason="invalid_transcript_content",
                    stdout_tail=(result.stdout or "")[-800:],
                    stderr_tail=(result.stderr or "")[-800:],
                    duration_seconds=duration,
                )
        return _result(
            identity,
            "OK",
            out_file,
            bytes=out_file.stat().st_size,
            duration_seconds=duration,
        )

    if out_file.exists() and out_file.stat().st_size == 0:
        out_file.unlink(missing_ok=True)

    has_captions, caption_reason = caption_probe(str(identity["url"]))
    if not has_captions:
        return _result(
            identity,
            "NO_TRANSCRIPT_AVAILABLE",
            out_file,
            reason=caption_reason,
            stdout_tail=(result.stdout or "")[-800:],
            stderr_tail=(result.stderr or "")[-800:],
            duration_seconds=duration,
        )

    return _result(
        identity,
        "FAILED",
        out_file,
        reason=caption_reason or "yt_transcript_cli_failed",
        stdout_tail=(result.stdout or "")[-800:],
        stderr_tail=(result.stderr or "")[-800:],
        duration_seconds=duration,
    )
