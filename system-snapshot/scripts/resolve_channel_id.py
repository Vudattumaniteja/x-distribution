import requests
import re
import sys
import json
import os

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
        print(f"Error resolving {handle}: {e}")
    return None

if __name__ == "__main__":
    handles = sys.argv[1:]
    results = {}
    
    # Load existing if exists
    config_path = 'config/youtube_channels.json'
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            results = json.load(f)

    for h in handles:
        cid = resolve_handle(h)
        if cid:
            results[h] = {
                "channel_id": cid,
                "last_processed_video_id": results.get(h, {}).get("last_processed_video_id", None),
                "rss_url": f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}"
            }
            print(f"RESOLVED: {h} -> {cid}")
        else:
            print(f"FAILED: {h}")

    with open(config_path, 'w') as f:
        json.dump(results, f, indent=2)
