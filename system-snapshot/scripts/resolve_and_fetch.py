import requests
import re
import json
import feedparser
import sys

def resolve_handle(handle):
    if not handle.startswith('@'):
        handle = '@' + handle
    url = f"https://www.youtube.com/{handle}"
    try:
        response = requests.get(url, timeout=10)
        html = response.text
        # Primary: JSON match
        match = re.search(r'"channelId":"(UC[\w-]+)"', html)
        if match:
            return match.group(1)
        # Secondary: Canonical URL match
        match = re.search(r'href="https://www.youtube.com/channel/(UC[\w-]+)"', html)
        if match:
            return match.group(1)
        # Tertiary: Meta tag match
        match = re.search(r'content="https://www.youtube.com/channel/(UC[\w-]+)"', html)
        if match:
            return match.group(1)
    except Exception as e:
        pass
    return None

def get_latest_video_info(channel_id):
    feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    try:
        feed = feedparser.parse(feed_url)
        if feed.entries:
            latest = feed.entries[0]
            return {
                "last_processed_video_id": latest.yt_videoid,
                "latest_video_title": latest.title
            }
    except Exception as e:
        pass
    return {
        "last_processed_video_id": None,
        "latest_video_title": "Unknown"
    }

if __name__ == "__main__":
    handles = [
        "@AlexFinnOfficial",
        "@anthropic-ai",
        "@BuildersCentral",
        "@claude",
        "@IshanSharma7390",
        "@n8n-io",
        "@NetworkChuck",
        "@nicksaraev",
        "@VarunMayya",
        "@JulianGoldieSEO"
    ]
    
    results = {}
    for h in handles:
        cid = resolve_handle(h)
        if cid:
            info = get_latest_video_info(cid)
            results[h] = {
                "channel_id": cid,
                "last_processed_video_id": info["last_processed_video_id"],
                "rss_url": f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}",
                "latest_video_title": info["latest_video_title"]
            }
        else:
            results[h] = {"error": "Could not resolve channel ID"}

    print(json.dumps(results, indent=2))
