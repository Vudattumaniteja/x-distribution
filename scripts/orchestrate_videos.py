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


import xml.etree.ElementTree as ET
import urllib.request
import threading
import os
import shutil
from datetime import timedelta

class YouTubeNotifier:
    def __init__(
        self,
        run_id: str,
        *,
        path: str | Path = WORKSPACE_ROOT / "logs" / "youtube_channel_notifications.jsonl",
        now = lambda: datetime.now(timezone.utc),
        max_bytes: int = 5 * 1024 * 1024,
    ):
        self.run_id = run_id
        self.path = Path(path)
        self.previous_path = self.path.with_name("youtube_channel_notifications.previous.jsonl")
        self.now = now
        self.max_bytes = max_bytes
        self.records: list[dict] = []
        self._lock = threading.Lock()

    def _rotate(self) -> None:
        if not self.path.exists() or self.path.stat().st_size < self.max_bytes:
            return
        self.previous_path.parent.mkdir(parents=True, exist_ok=True)
        if self.previous_path.exists():
            self.previous_path.unlink()
        try:
            shutil.move(str(self.path), str(self.previous_path))
        except Exception:
            pass

    def notify(self, severity: str, notification_type: str, reason: str, **state) -> dict:
        record = {
            "timestamp": self.now().isoformat(),
            "run_id": self.run_id,
            "severity": severity,
            "type": notification_type,
            "reason": reason,
            **state,
        }
        print(f"[YT NOTIFY] {severity} {notification_type}: {reason}")
        with self._lock:
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                self._rotate()
                with self.path.open("a", encoding="utf-8") as file_handle:
                    file_handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            except Exception:
                pass
        self.records.append(record)
        return record


def parse_youtube_rss(xml_content: str) -> list[dict]:
    root = ET.fromstring(xml_content)
    
    def find_local(element, local_name):
        for child in element:
            if child.tag.split('}')[-1] == local_name:
                return child
        return None

    videos = []
    for child in root:
        tag_local = child.tag.split('}')[-1]
        if tag_local == "entry":
            video_id_el = find_local(child, "videoId")
            video_id = video_id_el.text if video_id_el is not None else ""
            
            title_el = find_local(child, "title")
            title = title_el.text if title_el is not None else "Unknown"
            
            published_el = find_local(child, "published")
            published_at = published_el.text if published_el is not None else None
            
            link_el = find_local(child, "link")
            link_url = ""
            if link_el is not None:
                link_url = link_el.attrib.get("href", "")
            if not link_url and video_id:
                link_url = f"https://www.youtube.com/watch?v={video_id}"
                
            videos.append({
                "id": video_id,
                "title": title,
                "url": link_url,
                "published_at": published_at,
                "duration": None
            })
    return videos


def parse_iso_datetime(dt_str: str) -> datetime | None:
    if not dt_str:
        return None
    try:
        clean_str = dt_str.replace("Z", "+00:00")
        return datetime.fromisoformat(clean_str)
    except Exception:
        return None


def filter_by_days(videos: list[dict], days: int | None) -> list[dict]:
    if not days or days <= 0:
        return videos
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    filtered = []
    for v in videos:
        pub_str = v.get("published_at")
        if not pub_str:
            continue
        dt = parse_iso_datetime(pub_str)
        if dt and dt >= cutoff:
            filtered.append(v)
    return filtered


def update_channel_cache(channel_id: str, new_videos: list[dict]):
    cache_file = WORKSPACE_ROOT / "cache" / f"youtube_channel_{channel_id}.json"
    existing = []
    if cache_file.exists():
        try:
            with cache_file.open("r", encoding="utf-8") as f:
                existing = json.load(f)
                if not isinstance(existing, list):
                    existing = []
        except Exception:
            existing = []
    
    seen_ids = set()
    merged = []
    
    def get_id(item):
        return item.get("video_id") or item.get("id") or video_id_from_url(item.get("url"))

    for v in new_videos:
        vid_id = get_id(v)
        if vid_id and vid_id not in seen_ids:
            seen_ids.add(vid_id)
            merged.append(v)
    for v in existing:
        vid_id = get_id(v)
        if vid_id and vid_id not in seen_ids:
            seen_ids.add(vid_id)
            merged.append(v)
            
    try:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with cache_file.open("w", encoding="utf-8") as f:
            json.dump(merged, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def scan_channel(yt_cli, name, config, profiles, days, max_scan_per_channel, notifier=None):
    channel_id = config.get("channel_id")
    url = f"https://www.youtube.com/channel/{channel_id}"
    priority = profiles.get(name, {}).get("priority", "unprofiled")
    
    videos = []
    errors = []
    status = "ERROR"
    fallback_used = None
    
    # Stage A: yt-dlp flat playlist scan (default)
    try:
        raw_videos = yt_cli.get_latest_videos(url, count=None, days=days, max_scan=max_scan_per_channel)
        if raw_videos:
            videos = [normalize_video(video, name) for video in raw_videos]
            status = "OK"
        else:
            errors.append("yt-dlp returned no videos")
    except Exception as exc:
        errors.append(f"yt-dlp error: {exc}")
        
    # Stage B: YouTube RSS feed parser
    if not videos:
        rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        try:
            req = urllib.request.Request(
                rss_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
            with urllib.request.urlopen(req, timeout=15) as response:
                xml_data = response.read().decode("utf-8", errors="replace")
            
            rss_raw = parse_youtube_rss(xml_data)
            rss_filtered = filter_by_days(rss_raw, days)
            if rss_filtered:
                videos = [normalize_video(v, name) for v in rss_filtered]
                status = "OK"
                fallback_used = "rss"
                if notifier:
                    notifier.notify(
                        "WARN",
                        "youtube_rss_fallback",
                        f"yt-dlp failed for channel {name}; fell back to RSS feed",
                        channel=name,
                        channel_id=channel_id,
                        errors=errors,
                    )
            else:
                errors.append("RSS feed returned no videos within lookback days")
        except Exception as exc:
            errors.append(f"RSS error: {exc}")
            
    # Stage C: local cached channel history files
    if not videos:
        cache_file = WORKSPACE_ROOT / "cache" / f"youtube_channel_{channel_id}.json"
        try:
            if cache_file.exists():
                with cache_file.open("r", encoding="utf-8") as f:
                    cached_raw = json.load(f)
                if isinstance(cached_raw, list) and cached_raw:
                    cached_filtered = filter_by_days(cached_raw, days)
                    is_stale_cache = False
                    if not cached_filtered:
                        cached_filtered = cached_raw[:10]
                        is_stale_cache = True
                    if cached_filtered:
                        videos = [normalize_video(v, name) for v in cached_filtered]
                        status = "DEGRADED"
                        fallback_used = "cache"
                        if notifier:
                            notifier.notify(
                                "WARN",
                                "youtube_cache_fallback",
                                f"yt-dlp and RSS failed for channel {name}; fell back to local cache (stale={is_stale_cache})",
                                channel=name,
                                channel_id=channel_id,
                                errors=errors,
                                stale=is_stale_cache,
                            )
                    else:
                        errors.append("Cached channel history had no videos")
            else:
                errors.append("Local channel cache file does not exist")
        except Exception as exc:
            errors.append(f"Cache read error: {exc}")

    # If all stages failed
    if not videos:
        status = "FAILED"
        if notifier:
            notifier.notify(
                "ERROR",
                "youtube_channel_failed",
                f"Failed to scan channel {name} via all stages",
                channel=name,
                channel_id=channel_id,
                errors=errors,
            )
            
    # Save successful results to cache
    if status == "OK" and videos:
        update_channel_cache(channel_id, videos)
        
    health = {
        "channel": name,
        "priority": priority,
        "channel_id": channel_id,
        "status": status,
        "items": len(videos),
    }
    if errors:
        health["errors"] = errors
    if fallback_used:
        health["fallback_used"] = fallback_used
        
    return videos, health


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

    import os
    now_dt = datetime.now(timezone.utc)
    run_id = f"yt-{now_dt.strftime('%Y%m%dT%H%M%S.%fZ')}-{os.getpid()}"
    notifier = YouTubeNotifier(run_id)

    with ThreadPoolExecutor(max_workers=min(workers, max(1, len(scan_targets)))) as executor:
        futures = {
            executor.submit(scan_channel, yt_cli, name, config, profiles, days, max_scan_per_channel, notifier): (name, config)
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
