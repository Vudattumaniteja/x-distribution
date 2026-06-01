import feedparser
import json
import os
from datetime import datetime, timezone, timedelta

def parse_corporate_feeds():
    config_path = 'config/corporate_blogs.json'
    output_path = 'data/corporate_announcements.json'
    
    if not os.path.exists(config_path):
        print(f"Config not found: {config_path}")
        return

    with open(config_path, 'r') as f:
        config = json.load(f)

    all_announcements = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=7) # Look back 7 days

    for blog in config['blogs']:
        print(f"Parsing {blog['name']}...")
        try:
            feed = feedparser.parse(blog['rss_url'])
            for entry in feed.entries:
                # Handle different date formats in RSS
                published_struct = entry.get('published_parsed') or entry.get('updated_parsed')
                if not published_struct:
                    continue
                
                published_dt = datetime(*published_struct[:6], tzinfo=timezone.utc)
                
                if published_dt >= cutoff:
                    all_announcements.append({
                        "title": entry.title,
                        "url": entry.link,
                        "published_at": published_dt.isoformat(),
                        "source": blog['name'],
                        "tier": blog['tier'],
                        "summary": entry.get('summary', '')[:300]
                    })
        except Exception as e:
            print(f"  → Error: {e}")

    # Deduplicate and sort
    all_announcements.sort(key=lambda x: x['published_at'], reverse=True)
    
    with open(output_path, 'w') as f:
        json.dump({
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "announcements": all_announcements
        }, f, indent=2)
    
    print(f"Done. Saved {len(all_announcements)} announcements to {output_path}")

if __name__ == "__main__":
    parse_corporate_feeds()
