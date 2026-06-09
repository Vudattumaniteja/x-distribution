import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from source_clis import WORKSPACE_ROOT
from source_registry import youtube_discovery_policy
from transcript_retrieval import (
    TRANSCRIPT_DIR,
    default_output_path,
    existing_transcript,
    retrieve_transcript,
    safe_filename_part,
    youtube_caption_state,
)


sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CHANNEL_PROFILE_CONFIG = WORKSPACE_ROOT / "config" / "youtube_channel_profiles.json"
VIDEO_QUEUE_PATH = WORKSPACE_ROOT / "data" / "new_videos_queue.json"
REPORT_PATH = WORKSPACE_ROOT / "data" / "transcript_pull_report.json"
UNAVAILABLE_PATH = WORKSPACE_ROOT / "data" / "transcripts_unavailable.json"
PRIORITY_RANK = {"P-2": -2, "P-1": -1, "P0": 0, "P1": 1, "P2": 2, "P3": 3}


def load_channel_profiles():
    if not CHANNEL_PROFILE_CONFIG.exists():
        return {}
    with CHANNEL_PROFILE_CONFIG.open("r", encoding="utf-8") as file_handle:
        return json.load(file_handle).get("channels", {})


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
    return default_output_path(video, TRANSCRIPT_DIR)


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


def pull_transcript(video: dict, timeout_seconds: int) -> dict:
    result = retrieve_transcript(video, timeout_seconds=timeout_seconds)
    result.pop("output_location", None)
    if result.get("status") not in {"OK", "SKIPPED_EXISTS"}:
        result.pop("transcript_file", None)
    return result


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
