import feedparser
import json
import os
from datetime import datetime, timezone, timedelta
import requests

def get_new_videos(handle, channel_id, last_id):
    feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    try:
        feed = feedparser.parse(feed_url)
        
        videos = []
        for entry in feed.entries:
            video_id = entry.yt_videoid
            if video_id == last_id:
                print(f"  - Hit last processed ID: {last_id}")
                break
                
            published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            videos.append({
                "video_id": video_id,
                "title": entry.title,
                "published_at": published.isoformat(),
                "url": entry.link,
                "channel": feed.feed.title
            })
        return videos
    except Exception as e:
        print(f"Feed error for {handle}: {e}")
        return []

if __name__ == "__main__":
    config_path = 'config/youtube_channels.json'
    with open(config_path, 'r') as f:
        channels = json.load(f)

    all_new = {}
    for handle, data in channels.items():
        print(f"Polling {handle}...")
        new_vids = get_new_videos(handle, data['channel_id'], data['last_processed_video_id'])
        if new_vids:
            all_new[handle] = new_vids
            channels[handle]['last_processed_video_id'] = new_vids[0]['video_id']
            print(f"  → Found {len(new_vids)} new videos.")

    with open(config_path, 'w') as f:
        json.dump(channels, f, indent=2)

    with open('data/new_videos_queue.json', 'w') as f:
        json.dump(all_new, f, indent=2)


    # Save updated config
    with open(config_path, 'w') as f:
        json.dump(channels, f, indent=2)

    # Output found videos for the next step
    with open('data/new_videos_queue.json', 'w') as f:
        json.dump(all_new, f, indent=2)
