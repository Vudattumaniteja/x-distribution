import argparse
import json
import os
import requests
import feedparser
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup
import subprocess
from concurrent.futures import ThreadPoolExecutor

def get_channel_id(url):
    """Extract channel ID from a handle URL if not already an ID."""
    if "/channel/" in url:
        return url.split("/channel/")[1].split("/")[0]
    
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        # Look for canonical link or meta tags
        canonical = soup.find("link", rel="canonical")
        if canonical and "/channel/" in canonical['href']:
            return canonical['href'].split("/channel/")[1]
        
        # Fallback to meta tags
        meta_id = soup.find("meta", itemprop="channelId")
        if meta_id:
            return meta_id['content']
            
        # Try finding it in the page source if soup fails
        if "channelId\":\"" in response.text:
            return response.text.split("channelId\":\"")[1].split("\"")[0]
            
    except Exception as e:
        print(f"Error resolving channel ID for {url}: {e}")
    return None

def fetch_recent_rss(channel_id, days=4):
    """Fast RSS fetching for recent videos."""
    feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(feed_url, headers=headers, timeout=20)
        feed = feedparser.parse(response.content)
        if response.status_code >= 400 and not feed.entries:
            print(f"RSS HTTP {response.status_code} with no entries for {channel_id}")
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        
        videos = []
        for entry in feed.entries:
            published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            if published >= cutoff:
                videos.append({
                    "video_id": entry.yt_videoid,
                    "title": entry.title,
                    "published_at": published.isoformat(),
                    "url": entry.link,
                    "channel": feed.feed.title if 'title' in feed.feed else "Unknown"
                })
        return videos
    except Exception as e:
        print(f"RSS Error for {channel_id}: {e}")
        return []

def fetch_all_ytdlp(channel_url):
    """Comprehensive fetching using yt-dlp flat extraction."""
    try:
        cmd = [
            "yt-dlp",
            "--flat-playlist",
            "--print", "%(id)s|%(title)s|%(upload_date)s|%(webpage_url)s",
            channel_url + "/videos"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        videos = []
        for line in result.stdout.strip().split('\n'):
            if not line: continue
            parts = line.split('|')
            if len(parts) >= 4:
                # yt-dlp upload_date is YYYYMMDD
                raw_date = parts[2]
                dt = datetime.strptime(raw_date, "%Y%m%d").replace(tzinfo=timezone.utc)
                videos.append({
                    "video_id": parts[0],
                    "title": parts[1],
                    "published_at": dt.isoformat(),
                    "url": parts[3]
                })
        return videos
    except Exception as e:
        print(f"yt-dlp Error for {channel_url}: {e}")
        return []

def process_channel(url, mode, days):
    """Worker function for multithreading."""
    print(f"Processing: {url}...")
    if mode == "recent":
        channel_id = get_channel_id(url)
        if channel_id:
            return fetch_recent_rss(channel_id, days)
        else:
            print(f"Could not resolve channel ID for {url}.")
            return []
    else:
        return fetch_all_ytdlp(url)

def main():
    parser = argparse.ArgumentParser(description="High-performance YouTube discovery tool.")
    parser.add_argument("urls", nargs="+", help="YouTube channel URLs")
    parser.add_argument("--mode", choices=["recent", "all"], default="recent", help="Discovery mode")
    parser.add_argument("--days", type=int, default=4, help="Days to look back (for 'recent' mode)")
    parser.add_argument("--output", help="Optional JSON output file")
    
    args = parser.parse_args()
    
    print(f"Mode: {args.mode.upper()} | Targets: {len(args.urls)}")
    
    all_results = []
    with ThreadPoolExecutor(max_workers=min(len(args.urls), 10)) as executor:
        futures = [executor.submit(process_channel, url, args.mode, args.days) for url in args.urls]
        for future in futures:
            all_results.extend(future.result())
            
    # Deduplicate by video_id
    unique_results = {v['video_id']: v for v in all_results}.values()
    # Sort by date descending
    sorted_results = sorted(unique_results, key=lambda x: x['published_at'], reverse=True)
    
    print(f"Discovered {len(sorted_results)} unique videos across all targets.")
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(list(sorted_results), f, indent=2)
        print(f"Saved to {args.output}")
    else:
        # Print summary
        for v in list(sorted_results)[:15]:
            channel_tag = f"[{v.get('channel', 'Unknown')}] " if 'channel' in v else ""
            print(f"[{v['published_at'][:10]}] {channel_tag}{v['title']} ({v['video_id']})")
        if len(sorted_results) > 15:
            print(f"... and {len(sorted_results)-15} more.")

if __name__ == "__main__":
    main()

