import json
import subprocess
import os
import importlib.util
import re
from source_clis import yt_transcript_command, yt_transcript_python_script

DEFAULT_COUNT_PER_CHANNEL = 1
INVALID_TRANSCRIPT_MARKERS = (
    "Google Sorry",
    "We're sorry",
    "automated queries",
    "unusual traffic from your computer network",
    "To protect our users, we can't process your request right now",
    "<!doctype html",
    "<html",
)

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
    if not url.startswith("http"):
        url = f"https://www.youtube.com/watch?v={video_id or url}"
    return {
        "video_id": video_id,
        "title": video.get("title", "Unknown"),
        "published_at": video.get("published_at"),
        "url": url,
        "channel": source_name,
        "source_account": source_name,
        "discovered_by": "yt-transcript latest",
        "duration": video.get("duration"),
    }

def is_valid_transcript(content):
    if not content or len(content.strip()) < 200:
        return False
    lowered = content.lower()
    return not any(marker.lower() in lowered for marker in INVALID_TRANSCRIPT_MARKERS)

def discover_latest_videos(channels):
    yt_cli = load_global_yt_cli()
    videos = []
    for name, config in channels.items():
        channel_url = f"https://www.youtube.com/channel/{config['channel_id']}"
        print(f"  -> Discovering latest for {name} via yt-transcript source")
        try:
            discovered = yt_cli.get_latest_videos(channel_url, DEFAULT_COUNT_PER_CHANNEL)
        except Exception as exc:
            print(f"     Discovery failed for {name}: {exc}")
            continue
        videos.extend(normalize_video(video, name) for video in discovered)
    return videos

def mass_pool():
    with open('config/youtube_channels.json', 'r', encoding='utf-8') as f:
        channels = json.load(f)
    
    output_dir = "data/transcripts"
    os.makedirs(output_dir, exist_ok=True)
    
    pool_results = []
    
    # 1. Fetch latest URLs through the global yt-transcript implementation.
    print("--- Step 1: Fetching Latest URLs for 24 Channels ---")
    videos = discover_latest_videos(channels)
    os.makedirs("cache", exist_ok=True)
    with open("cache/mass_pool_urls.json", "w", encoding="utf-8") as f:
        json.dump(videos, f, indent=2, ensure_ascii=False)
        
    print(f"Found {len(videos)} recent videos. Starting Mass Transcript Extraction...")

    # 2. Extract Transcripts for EACH
    # We limit to the single newest video per channel for this specific "pool" request
    seen_channels = set()
    
    for v in videos:
        channel_name = v.get('channel', 'Unknown')
        if channel_name in seen_channels: continue
        seen_channels.add(channel_name)
        
        video_id = v['video_id']
        video_url = v['url']
        print(f"  -> Extracting: [{channel_name}] {v['title']}")
        
        transcript_file = f"transcript_{video_id}.txt"
        transcript_path = os.path.join(output_dir, transcript_file)
        
        # Transcript content must come through the canonical YT Transcript CLI.
        result = subprocess.run(
            yt_transcript_command("get", video_url, "-o", transcript_path),
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
        )
        
        if os.path.exists(transcript_path):
            with open(transcript_path, 'r', encoding='utf-8') as tf:
                content = tf.read()
            if not is_valid_transcript(content):
                os.remove(transcript_path)
                print(f"     Rejected invalid transcript content for {video_url}.")
                if result.stderr:
                    print(f"     CLI stderr: {result.stderr}")
                continue
            
            pool_results.append({
                "headline": v['title'],
                "source": channel_name,
                "url": video_url,
                "transcript": content[:5000], # Keep a large snippet for the pool
                "signal_type": "Deep Signal",
                "notes": "Full Transcript Pooled via yt-transcript CLI",
                "published_at": v.get('published_at')
            })
            
    # 3. Save Mass Pool
    with open('data/mass_transcript_pool.json', 'w', encoding='utf-8') as f:
        json.dump(pool_results, f, indent=2, ensure_ascii=False)
        
    print(f"\n--- SUCCESS ---")
    print(f"Mass pool complete. {len(pool_results)} transcripts ingested into data/mass_transcript_pool.json")

if __name__ == "__main__":
    mass_pool()
