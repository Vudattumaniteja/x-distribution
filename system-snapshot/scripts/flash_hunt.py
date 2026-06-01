import feedparser
import json
import os
import re
from datetime import datetime, timezone, timedelta

# High-Signal Technical Triggers from "The Staying Ahead Method"
TRIGGERS = [
    r"v5\.5", r"v6\.0", r"GPT-5", r"GPT-6", r"Claude 4", r"Claude 5",
    r"Humanity's Last Exam", r"HLE", r"SOTA", r"benchmark",
    r"300 specialists", r"4000 tool calls", r"100\+ agents",
    r"Kimi K2\.6", r"DeepSeek-V3", r"Hermes v0\.", r"model drop"
]

FEEDS = {
    "OpenAI": "https://openai.com/news/rss.xml",
    "Anthropic": "https://www.anthropic.com/index.xml",
    "Google DeepMind": "https://deepmind.google/blog/rss.xml",
    "Reddit Singularity": "https://www.reddit.com/r/singularity/.rss",
    "Reddit LocalLLaMA": "https://www.reddit.com/r/LocalLLaMA/.rss",
    "Hacker News AI": "https://hnrss.org/newest?q=AI"
}

def check_triggers(text):
    matched = []
    for pattern in TRIGGERS:
        if re.search(pattern, text, re.IGNORECASE):
            matched.append(pattern.replace("\\", ""))
    return matched

def flash_hunt():
    print(f"Starting Flash Hunt at {datetime.now(timezone.utc).isoformat()}")
    results = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=6) # Very fresh only
    
    for source, url in FEEDS.items():
        print(f"Polling {source}...")
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                # Handle different date formats in RSS
                published = None
                for date_key in ['published_parsed', 'updated_parsed', 'created_parsed']:
                    if hasattr(entry, date_key) and getattr(entry, date_key):
                        published = datetime(*getattr(entry, date_key)[:6], tzinfo=timezone.utc)
                        break
                
                if not published:
                    continue

                if published >= cutoff:
                    content = entry.title + " " + entry.get('summary', '')
                    matches = check_triggers(content)
                    
                    if matches:
                        print(f"  🔥 TRIGGER MATCH: {entry.title} ({source})")
                        results.append({
                            "id": f"flash_{published.strftime('%Y%m%d%H%M')}_{source[:3].lower()}",
                            "headline": entry.title[:100],
                            "summary": entry.get('summary', '')[:200],
                            "source_url": entry.link,
                            "source_name": source,
                            "published_at": published.isoformat(),
                            "discovered_by_agent": "Flash Hunt",
                            "relevance_score": 9.5, # Flash hunt items are high-signal by default
                            "combined_score": 20.0, # Pre-ranked for Headline Story
                            "breakthrough_flags": matches,
                            "tags": ["flash-hunt", "breaking-news"] + matches
                        })
        except Exception as e:
            print(f"Error polling {source}: {e}")

    # Load existing news queue
    queue_path = 'data/news_queue.json'
    if os.path.exists(queue_path):
        with open(queue_path, 'r') as f:
            queue = json.load(f)
    else:
        queue = {"metadata": {"description": "News from 7 agents", "max_items_kept": 100}, "items": []}

    # Deduplicate against existing items by URL
    existing_urls = {item['source_url'] for item in queue.get('items', [])}
    new_items = [r for r in results if r['source_url'] not in existing_urls]

    if new_items:
        queue['items'] = new_items + queue.get('items', [])
        queue['items'] = queue['items'][:100] # Keep last 100
        queue['last_updated'] = datetime.now(timezone.utc).isoformat()
        
        with open(queue_path, 'w') as f:
            json.dump(queue, f, indent=2)
        print(f"Added {len(new_items)} new flash updates.")
    else:
        print("No new flash updates found.")

if __name__ == "__main__":
    flash_hunt()
