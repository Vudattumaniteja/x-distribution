import json
import os
import importlib.util
import re
import subprocess
from datetime import datetime, timezone
from source_clis import (
    python_script_command,
    yt_transcript_command,
    yt_transcript_python_script,
)
from source_registry import collection_runtime_policy
from x_collection_coordinator import collect_x_read_only

# File Paths
PROCESSED_URLS_PATH = 'data/processed_urls.log'
CONFIG_BLOGS = 'config/corporate_blogs.json'
CONFIG_YOUTUBE = 'config/youtube_channels.json'
CONFIG_X = 'config/followed_accounts.json'
OUTPUT_POOL = 'data/raw_context_pool.json'
DEFAULT_YOUTUBE_COUNT_PER_CHANNEL = 15
UTF8_ENV = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
INVALID_TRANSCRIPT_MARKERS = (
    "Google Sorry",
    "We're sorry",
    "automated queries",
    "unusual traffic from your computer network",
    "To protect our users, we can't process your request right now",
    "<!doctype html",
    "<html",
)
LAST_X_COLLECTION = None

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

def normalize_youtube_url(video):
    url = video.get("url") or ""
    video_id = video.get("id") or video_id_from_url(url)
    if not url.startswith("http"):
        url = f"https://www.youtube.com/watch?v={video_id or url}"
    return url

def is_valid_transcript(content):
    if not content or len(content.strip()) < 200:
        return False
    lowered = content.lower()
    return not any(marker.lower() in lowered for marker in INVALID_TRANSCRIPT_MARKERS)

def extract_json_array(text):
    if not text:
        return None
    match = re.search(r'\[\s*\{', text)
    if not match:
        return None
    try:
        parsed, _ = json.JSONDecoder().raw_decode(text[match.start():])
        return parsed
    except json.JSONDecodeError:
        return None

def x_content(item):
    return (
        item.get("content")
        or item.get("primary_text")
        or item.get("text")
        or item.get("quoted_text")
        or ""
    )

def load_processed_urls():
    if os.path.exists(PROCESSED_URLS_PATH):
        with open(PROCESSED_URLS_PATH, 'r', encoding='utf-8') as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_processed_url(url):
    with open(PROCESSED_URLS_PATH, 'a', encoding='utf-8') as f:
        f.write(url + '\n')

def poller_1_x():
    """
    Poller 1: Twitter / X through the pinned local XCLI.
    """
    print("Running Poller 1: X (Watchlist)...")
    global LAST_X_COLLECTION
    if not os.path.exists(CONFIG_X):
        LAST_X_COLLECTION = {"status": "FAILED", "run_id": None, "tweets": []}
        return []
    
    with open(CONFIG_X, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    handles = [acc['handle'] for acc in config['accounts'] if acc['tier'] == 'must_follow']
    workers = max(1, int(collection_runtime_policy().get("x_workers", 3)))
    LAST_X_COLLECTION = collect_x_read_only(handles, workers=workers, days=7, home_count=30)
    tweets = []
    per_account_counts = {}
    for tweet in LAST_X_COLLECTION["tweets"]:
        scope = tweet.get("_x_collection_scope", "")
        if scope == "home":
            tweet.setdefault("source", "home")
        else:
            handle = scope.partition(":")[2]
            count = per_account_counts.get(handle, 0)
            if count >= 5:
                continue
            per_account_counts[handle] = count + 1
            tweet.setdefault("source", f"@{handle}")
        tweets.append(tweet)
    return tweets

def poller_2_blogs():
    """
    Poller 2: Corporate announcements via repaired multi-source discovery.
    """
    print("Running Poller 2: Corporate Blogs...")
    if not os.path.exists(CONFIG_BLOGS):
        return []

    blog_content = []
    processed_urls = load_processed_urls()

    try:
        subprocess.run(
            python_script_command('corporate_rss_discovery.py'),
            check=False,
            env=UTF8_ENV,
        )
        with open('data/corporate_announcements.json', 'r', encoding='utf-8') as f:
            discovered = json.load(f)
    except Exception as e:
        print(f"    Error running corporate discovery: {e}")
        return []

    for item in discovered.get('announcements', []):
        url = item.get('url')
        if not url or url in processed_urls:
            continue
        blog_content.append({
            "title": item.get('title', ''),
            "content": item.get('summary', ''),
            "url": url,
            "source": item.get('source', 'Corporate Discovery'),
            "type": "blog",
            "published_at": item.get('published_at'),
            "url_verified": item.get('url_verified'),
            "discovery_method": item.get('discovery_method'),
        })
            
    return blog_content

def fetch_transcript_via_cli(video_url):
    """
    Uses the pinned YT Transcript CLI provided by the user.
    """
    try:
        # The CLI saves to file if -o is provided
        video_id = video_id_from_url(video_url)
        temp_path = f"cache/temp_trans_{video_id}.txt"
        os.makedirs("cache", exist_ok=True)

        result = subprocess.run(
            yt_transcript_command("get", video_url, "-o", temp_path),
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            env=UTF8_ENV,
        )
        
        if os.path.exists(temp_path):
            with open(temp_path, 'r', encoding='utf-8') as f:
                content = f.read()
            os.remove(temp_path)
            if is_valid_transcript(content):
                return content
            print(f"    Invalid transcript content rejected for {video_url}.")
            if result.stderr:
                print(f"    CLI stderr: {result.stderr}")
        else:
            print(f"    CLI failed for {video_url}: {result.stderr}")
        return None
    except Exception as e:
        print(f"    CLI Error: {e}")
        return None

def poller_3_youtube():
    """
    Poller 3: YouTube latest-video discovery + Transcripts
    """
    print("Running Poller 3: YouTube latest discovery + Transcripts...")
    if not os.path.exists(CONFIG_YOUTUBE): return []
    
    with open(CONFIG_YOUTUBE, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    video_content = []
    processed_urls = load_processed_urls()
    yt_cli = load_global_yt_cli()
    
    for name, channel in config.items():
        print(f"  Polling YouTube: {name}...")
        try:
            channel_url = f"https://www.youtube.com/channel/{channel['channel_id']}"
            videos = yt_cli.get_latest_videos(channel_url, DEFAULT_YOUTUBE_COUNT_PER_CHANNEL)
            for video in videos:
                url = normalize_youtube_url(video)
                if url in processed_urls: continue
                
                print(f"    Fetching transcript for {url} via CLI...")
                transcript = fetch_transcript_via_cli(url)
                
                video_content.append({
                    "title": video.get("title", "Unknown"),
                    "content": transcript or "Transcript not available.",
                    "url": url,
                    "source": name,
                    "type": "youtube",
                    "video_id": video.get("id") or video_id_from_url(url),
                    "published_at": video.get("published_at"),
                    "transcript_available": bool(transcript),
                })
        except Exception as e:
            print(f"    Error polling YouTube {name}: {e}")
            
    return video_content

def main():
    print(f"--- Master Poller Started at {datetime.now().isoformat()} ---")
    
    # 1. Collect
    x_items = poller_1_x()
    blog_items = poller_2_blogs()
    yt_items = poller_3_youtube()
    
    # 2. Combine into Pool
    all_new_items = x_items + blog_items + yt_items
    
    if not all_new_items:
        print("No new content discovered in this tick.")
        return 1 if LAST_X_COLLECTION and LAST_X_COLLECTION["status"] == "FAILED" else 0

    # 3. Format "The Big Block"
    pool_text = "### RAW DISCOVERY POOL ###\n\n"
    
    if x_items:
        pool_text += "## SECTION 1: TWEETS / X FEED ##\n"
        for item in x_items:
            pool_text += f"Source: {item.get('source')}\nURL: {item.get('url')}\nContent: {x_content(item)}\n---\n"
            save_processed_url(item['url'])
            
    if blog_items:
        pool_text += "\n## SECTION 2: CORPORATE BLOGS ##\n"
        for item in blog_items:
            pool_text += f"Source: {item['source']}\nTitle: {item['title']}\nURL: {item['url']}\nContent: {item['content'][:1000]}...\n---\n"
            save_processed_url(item['url'])
            
    if yt_items:
        pool_text += "\n## SECTION 3: YOUTUBE TRANSCRIPTS ##\n"
        for item in yt_items:
            pool_text += f"Channel: {item['source']}\nTitle: {item['title']}\nURL: {item['url']}\nTranscript: {item['content'][:2000]}...\n---\n"
            save_processed_url(item['url'])

    # 4. Save Pool
    output = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "item_count": len(all_new_items),
        "raw_pool_text": pool_text,
        "items": all_new_items
    }
    
    with open(OUTPUT_POOL, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
        
    print(f"Tick Complete. Pooled {len(all_new_items)} items into {OUTPUT_POOL}")
    return 1 if LAST_X_COLLECTION and LAST_X_COLLECTION["status"] == "FAILED" else 0

if __name__ == "__main__":
    raise SystemExit(main())
