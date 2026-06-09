import json
import os
import importlib.util
from source_clis import yt_transcript_python_script
from transcript_retrieval import (
    is_valid_transcript,
    normalize_video_url,
    retrieve_transcript,
    video_id_from_url,
)

DEFAULT_COUNT_PER_CHANNEL = 1
def load_global_yt_cli():
    global_yt_transcript = yt_transcript_python_script()
    spec = importlib.util.spec_from_file_location(
        "global_yt_transcript_cli",
        global_yt_transcript,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def normalize_video(video, source_name):
    url = normalize_video_url(video)
    video_id = video.get("id") or video_id_from_url(url)
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
        
        result = retrieve_transcript(
            v,
            output_path=transcript_path,
            reuse_existing=False,
            require_valid=True,
            accept_output_on_nonzero=True,
        )
        
        if result.get("status") == "OK" and os.path.exists(transcript_path):
            with open(transcript_path, 'r', encoding='utf-8') as tf:
                content = tf.read()
            if not is_valid_transcript(content):
                os.remove(transcript_path)
                print(f"     Rejected invalid transcript content for {video_url}.")
                if result.get("stderr_tail"):
                    print(f"     CLI stderr: {result.get('stderr_tail')}")
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
        else:
            print(f"     Transcript retrieval {result.get('status')} for {video_url}: {result.get('reason', '')}")
            
    # 3. Save Mass Pool
    with open('data/mass_transcript_pool.json', 'w', encoding='utf-8') as f:
        json.dump(pool_results, f, indent=2, ensure_ascii=False)
        
    print(f"\n--- SUCCESS ---")
    print(f"Mass pool complete. {len(pool_results)} transcripts ingested into data/mass_transcript_pool.json")

if __name__ == "__main__":
    mass_pool()
