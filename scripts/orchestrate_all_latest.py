import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from source_clis import WORKSPACE_ROOT, yt_transcript_command
from source_registry import youtube_discovery_policy


sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CHANNEL_PROFILE_CONFIG = WORKSPACE_ROOT / "config" / "youtube_channel_profiles.json"
VIDEO_QUEUE_PATH = WORKSPACE_ROOT / "data" / "new_videos_queue.json"
TRANSCRIPT_DIR = WORKSPACE_ROOT / "data" / "transcripts"
REPORT_PATH = WORKSPACE_ROOT / "data" / "transcript_pull_report.json"
UNAVAILABLE_PATH = WORKSPACE_ROOT / "data" / "transcripts_unavailable.json"
PRIORITY_RANK = {"P-2": -2, "P-1": -1, "P0": 0, "P1": 1, "P2": 2, "P3": 3}


def load_channel_profiles():
    if not CHANNEL_PROFILE_CONFIG.exists():
        return {}
    with CHANNEL_PROFILE_CONFIG.open("r", encoding="utf-8") as file_handle:
        return json.load(file_handle).get("channels", {})


def safe_filename_part(value: str, limit: int = 80) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value or "untitled")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:limit].rstrip(" .") or "untitled"


def existing_transcript(video_id: str) -> Path | None:
    if not video_id:
        return None
    matches = list(TRANSCRIPT_DIR.glob(f"{video_id}_*.txt"))
    return matches[0] if matches else None


def load_unavailable_registry() -> dict:
    if not UNAVAILABLE_PATH.exists():
        return {}
    try:
        with UNAVAILABLE_PATH.open("r", encoding="utf-8") as file_handle:
            payload = json.load(file_handle)
    except (OSError, json.JSONDecodeError):
        return {}
    return payload.get("videos", {}) if isinstance(payload, dict) else {}


def save_unavailable_registry(videos: dict) -> None:
    UNAVAILABLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with UNAVAILABLE_PATH.open("w", encoding="utf-8") as file_handle:
        json.dump({
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "videos": videos,
        }, file_handle, indent=2, ensure_ascii=False)


def output_path_for_video(video: dict) -> Path:
    video_id = video.get("video_id") or re.sub(r"[^\w-]", "_", (video.get("url") or "")[-16:])
    title = safe_filename_part(video.get("title") or video_id)
    return TRANSCRIPT_DIR / f"{video_id}_{title}.txt"


def video_priority(video: dict, profiles: dict) -> tuple[int, str]:
    channel = video.get("channel") or video.get("source_account") or ""
    priority = profiles.get(channel, {}).get("priority", "P3")
    return (PRIORITY_RANK.get(priority, 99), str(video.get("published_at") or ""))


def video_enabled(video: dict, profiles: dict, policy: dict) -> tuple[bool, str]:
    channel = video.get("channel") or video.get("source_account") or ""
    disabled = {str(item).lower() for item in policy.get("disabled_channels", [])}
    profile = profiles.get(channel, {})
    if channel.lower() in disabled:
        return False, "policy_disabled_channel"
    if profile.get("enabled") is False:
        return False, "profile_disabled_channel"
    if str(profile.get("transcript_policy", "")).lower() == "disabled":
        return False, "profile_disabled_transcripts"
    return True, ""


def load_video_queue(profiles: dict, policy: dict, unavailable: dict) -> tuple[list[dict], list[dict]]:
    if not VIDEO_QUEUE_PATH.exists():
        return [], []
    with VIDEO_QUEUE_PATH.open("r", encoding="utf-8") as file_handle:
        raw_videos = json.load(file_handle)
    if not isinstance(raw_videos, list):
        return [], []

    selected = []
    skipped = []
    seen = set()
    for video in raw_videos:
        key = video.get("video_id") or video.get("url")
        if not key or key in seen:
            continue
        seen.add(key)
        if video.get("video_id") in unavailable:
            skipped.append({
                "video_id": video.get("video_id"),
                "title": video.get("title"),
                "channel": video.get("channel") or video.get("source_account"),
                "status": "SKIPPED_UNAVAILABLE",
                "reason": unavailable[video.get("video_id")].get("reason", "cached transcript unavailable"),
            })
            continue
        enabled, reason = video_enabled(video, profiles, policy)
        if not enabled:
            skipped.append({
                "video_id": video.get("video_id"),
                "title": video.get("title"),
                "channel": video.get("channel") or video.get("source_account"),
                "status": "SKIPPED",
                "reason": reason,
            })
            continue
        selected.append(video)

    selected.sort(key=lambda item: video_priority(item, profiles))
    return selected, skipped


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


def pull_transcript(video: dict, timeout_seconds: int) -> dict:
    video_id = video.get("video_id")
    channel = video.get("channel") or video.get("source_account")
    url = video.get("url")
    existing = existing_transcript(video_id)
    if existing:
        return {
            "video_id": video_id,
            "title": video.get("title"),
            "channel": channel,
            "url": url,
            "status": "SKIPPED_EXISTS",
            "transcript_file": str(existing),
        }

    out_file = output_path_for_video(video)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    cmd = yt_transcript_command("get", url, "-o", str(out_file))
    started = datetime.now(timezone.utc)
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_seconds,
    )
    if result.returncode == 0 and out_file.exists() and out_file.stat().st_size > 0:
        return {
            "video_id": video_id,
            "title": video.get("title"),
            "channel": channel,
            "url": url,
            "status": "OK",
            "transcript_file": str(out_file),
            "bytes": out_file.stat().st_size,
            "duration_seconds": (datetime.now(timezone.utc) - started).total_seconds(),
        }
    if out_file.exists() and out_file.stat().st_size == 0:
        out_file.unlink(missing_ok=True)
    has_captions, caption_reason = youtube_caption_state(url)
    if not has_captions:
        return {
            "video_id": video_id,
            "title": video.get("title"),
            "channel": channel,
            "url": url,
            "status": "NO_TRANSCRIPT_AVAILABLE",
            "reason": caption_reason,
            "stdout_tail": (result.stdout or "")[-800:],
            "stderr_tail": (result.stderr or "")[-800:],
            "duration_seconds": (datetime.now(timezone.utc) - started).total_seconds(),
        }
    return {
        "video_id": video_id,
        "title": video.get("title"),
        "channel": channel,
        "url": url,
        "status": "FAILED",
        "stdout_tail": (result.stdout or "")[-800:],
        "stderr_tail": (result.stderr or "")[-800:],
        "duration_seconds": (datetime.now(timezone.utc) - started).total_seconds(),
    }


def pull_all_transcripts():
    policy = youtube_discovery_policy()
    profiles = load_channel_profiles()
    workers = max(1, int(policy.get("transcript_workers", 2)))
    timeout_seconds = int(policy.get("transcript_per_video_timeout_seconds", 360))
    unavailable = load_unavailable_registry()
    videos, skipped = load_video_queue(profiles, policy, unavailable)

    print(f"--- Pulling transcripts for {len(videos)} discovered YouTube video(s) ---")
    if skipped:
        print(f"  Skipped {len(skipped)} video(s) via channel/transcript policy.")

    results = list(skipped)
    if not videos:
        report = {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "workers": workers,
            "timeout_seconds": timeout_seconds,
            "results": results,
            "summary": {"ok": 0, "failed": 0, "skipped": len(skipped)},
        }
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with REPORT_PATH.open("w", encoding="utf-8") as file_handle:
            json.dump(report, file_handle, indent=2, ensure_ascii=False)
        print("Done. No transcript targets after policy filtering.")
        return

    started_at = datetime.now(timezone.utc)
    with ThreadPoolExecutor(max_workers=min(workers, len(videos))) as executor:
        futures = {executor.submit(pull_transcript, video, timeout_seconds): video for video in videos}
        for future in as_completed(futures):
            video = futures[future]
            try:
                result = future.result()
            except Exception as exc:
                result = {
                    "video_id": video.get("video_id"),
                    "title": video.get("title"),
                    "channel": video.get("channel") or video.get("source_account"),
                    "url": video.get("url"),
                    "status": "ERROR",
                    "error": str(exc),
                }
            results.append(result)
            print(f"  -> {result['status']}: {result.get('channel')} / {result.get('title')}")

    ok = sum(1 for item in results if item.get("status") == "OK")
    failed = sum(1 for item in results if item.get("status") in {"FAILED", "ERROR"})
    unavailable_count = sum(1 for item in results if item.get("status") == "NO_TRANSCRIPT_AVAILABLE")
    skipped_count = sum(1 for item in results if str(item.get("status", "")).startswith("SKIPPED"))
    for item in results:
        if item.get("status") == "NO_TRANSCRIPT_AVAILABLE" and item.get("video_id"):
            unavailable[item["video_id"]] = {
                "title": item.get("title"),
                "channel": item.get("channel"),
                "url": item.get("url"),
                "reason": item.get("reason"),
                "last_checked": datetime.now(timezone.utc).isoformat(),
            }
    save_unavailable_registry(unavailable)
    report = {
        "started_at": started_at.isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "workers": workers,
        "timeout_seconds": timeout_seconds,
        "results": results,
        "summary": {"ok": ok, "failed": failed, "unavailable": unavailable_count, "skipped": skipped_count},
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with REPORT_PATH.open("w", encoding="utf-8") as file_handle:
        json.dump(report, file_handle, indent=2, ensure_ascii=False)
    print(f"Done. Transcript pull summary: {ok} OK, {failed} failed, {unavailable_count} unavailable, {skipped_count} skipped.")


if __name__ == "__main__":
    pull_all_transcripts()
