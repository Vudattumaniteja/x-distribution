import importlib.util
import json
import re
import sys
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from source_clis import WORKSPACE_ROOT, yt_transcript_python_script
from source_registry import youtube_discovery_policy

CHANNEL_CONFIG = WORKSPACE_ROOT / "config" / "youtube_channels.json"
CHANNEL_PROFILE_CONFIG = WORKSPACE_ROOT / "config" / "youtube_channel_profiles.json"
OUTPUT_PATH = WORKSPACE_ROOT / "data" / "new_videos_queue.json"
REPORT_PATH = WORKSPACE_ROOT / "data" / "youtube_discovery_report.json"
DEFAULT_MAX_SCAN_PER_CHANNEL = 500
PRIORITY_RANK = {"P-2": -2, "P-1": -1, "P0": 0, "P1": 1, "P2": 2, "P3": 3}


def load_global_yt_cli():
    global_yt_transcript = yt_transcript_python_script()
    spec = importlib.util.spec_from_file_location(
        "global_yt_transcript_cli",
        global_yt_transcript,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def video_id_from_url(url):
    if not url:
        return ""
    match = re.search(r"(?:v=|/shorts/|youtu\.be/)([A-Za-z0-9_-]{6,})", url)
    if match:
        return match.group(1)
    return url.rstrip("/").split("/")[-1]


def normalize_video(video, source_name):
    url = video.get("url") or ""
    video_id = video.get("id") or video_id_from_url(url)
    return {
        "video_id": video_id,
        "title": video.get("title", "Unknown"),
        "published_at": video.get("published_at"),
        "url": url or f"https://www.youtube.com/watch?v={video_id}",
        "channel": source_name,
        "source_account": source_name,
        "discovered_by": "yt-transcript latest",
        "duration": video.get("duration"),
    }


def load_channel_profiles():
    if not CHANNEL_PROFILE_CONFIG.exists():
        return {}
    with CHANNEL_PROFILE_CONFIG.open("r", encoding="utf-8") as file_handle:
        return json.load(file_handle).get("channels", {})


def prioritized_channels(channels, profiles):
    def sort_key(entry):
        name, _config = entry
        priority = profiles.get(name, {}).get("priority", "P3")
        return (PRIORITY_RANK.get(priority, 99), name.lower())

    return sorted(channels.items(), key=sort_key)


def channel_enabled(name, profiles, policy):
    disabled = {str(item).lower() for item in policy.get("disabled_channels", [])}
    profile = profiles.get(name, {})
    if name.lower() in disabled:
        return False
    if profile.get("enabled") is False:
        return False
    if str(profile.get("transcript_policy", "")).lower() == "disabled":
        return False
    return True


def scan_channel(yt_cli, name, config, profiles, days, max_scan_per_channel):
    url = f"https://www.youtube.com/channel/{config['channel_id']}"
    priority = profiles.get(name, {}).get("priority", "unprofiled")
    try:
        videos = yt_cli.get_latest_videos(url, count=None, days=days, max_scan=max_scan_per_channel)
    except Exception as exc:
        return [], {
            "channel": name,
            "priority": priority,
            "channel_id": config.get("channel_id"),
            "status": "ERROR",
            "error": str(exc),
            "items": 0,
        }

    return [normalize_video(video, name) for video in videos], {
        "channel": name,
        "priority": priority,
        "channel_id": config.get("channel_id"),
        "status": "OK",
        "items": len(videos),
    }


def orchestrate(days=None, max_scan_per_channel=None):
    with CHANNEL_CONFIG.open("r", encoding="utf-8") as file_handle:
        channels = json.load(file_handle)

    profiles = load_channel_profiles()
    policy = youtube_discovery_policy()
    days = int(days if days is not None else policy.get("lookback_days", 2))
    max_scan_per_channel = int(max_scan_per_channel or policy.get("max_scan_per_channel", DEFAULT_MAX_SCAN_PER_CHANNEL))
    workers = max(1, int(policy.get("discovery_workers", 4)))
    yt_cli = load_global_yt_cli()
    all_discovered = []
    report = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "lookback_days": days,
        "max_scan_per_channel": max_scan_per_channel,
        "workers": workers,
        "channels": [],
    }

    scan_targets = []
    for name, config in prioritized_channels(channels, profiles):
        priority = profiles.get(name, {}).get("priority", "unprofiled")
        if not channel_enabled(name, profiles, policy):
            print(f"Skipping {name} [{priority}] via policy-disabled channel.")
            report["channels"].append({
                "channel": name,
                "priority": priority,
                "channel_id": config.get("channel_id"),
                "status": "SKIPPED_DISABLED",
                "items": 0,
            })
            continue
        scan_targets.append((name, config))

    with ThreadPoolExecutor(max_workers=min(workers, max(1, len(scan_targets)))) as executor:
        futures = {
            executor.submit(scan_channel, yt_cli, name, config, profiles, days, max_scan_per_channel): (name, config)
            for name, config in scan_targets
        }
        for future in as_completed(futures):
            name, _config = futures[future]
            priority = profiles.get(name, {}).get("priority", "unprofiled")
            print(f"Scanning {name} [{priority}] via yt-transcript latest source ({days} day window)...")
            videos, health = future.result()
            all_discovered.extend(videos)
            report["channels"].append(health)
            print(f"  -> {health['status']}; {health.get('items', 0)} items")

    seen = {}
    for video in all_discovered:
        key = video.get("video_id") or video.get("url")
        if key and key not in seen:
            seen[key] = video

    output = list(seen.values())
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as file_handle:
        json.dump(output, file_handle, indent=2, ensure_ascii=False)
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    report["total_videos"] = len(output)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with REPORT_PATH.open("w", encoding="utf-8") as file_handle:
        json.dump(report, file_handle, indent=2, ensure_ascii=False)

    print(
        f"Done. Discovered {len(output)} total videos from the last {days} day(s) at "
        f"{datetime.now(timezone.utc).isoformat()}."
    )


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Discover latest YouTube videos via yt-transcript latest.")
    parser.add_argument("--days", type=int, help="Only keep videos published in the last N days")
    parser.add_argument("--max-scan-per-channel", type=int, help="Safety cap for playlist items inspected per channel")
    args = parser.parse_args()
    orchestrate(days=args.days, max_scan_per_channel=args.max_scan_per_channel)
