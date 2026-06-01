import json
import os
from datetime import datetime, timezone

from intelligence_queue import merge_queue
from source_registry import collector_outputs, queue_policy

def load_json(path):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def main():
    new_items = []
    
    for file in collector_outputs():
        data = load_json(file)
        if not data:
            continue

        if isinstance(data, list):
            discoveries = data
        else:
            discoveries = data.get('new_discoveries', [])

        # Older Reddit collector output used `posts` only. Keep this fallback so
        # community discussions are not silently dropped from the unified queue.
        if isinstance(data, dict) and not discoveries and 'posts' in data:
            discoveries.extend(data['posts'])
        
        # Handle corporate announcements which use a different key
        if 'announcements' in data:
            discoveries.extend(data['announcements'])
            
        for d in discoveries:
            # Standardize for news_queue.json
            timestamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M')
            source_url = d.get('url', '')
            item_id = f"deep_{timestamp}_{abs(hash(source_url)) % 10000}"
            
            headline = ""
            if 'title' in d:
                headline = d['title']
            elif 'model_id' in d:
                headline = f"New Model on HF: {d['model_id']}"
            elif 'repo_name' in d:
                headline = f"New GitHub Repo: {d['repo_name']}"
            elif 'subreddit' in d:
                headline = d.get('title', f"Reddit discussion in r/{d['subreddit']}")
            elif 'title' in d and 'url' in d:
                headline = d['title']
            else:
                headline = f"New Page Discovered: {source_url.split('/')[-1] or source_url}"

            new_items.append({
                "id": item_id,
                "headline": headline,
                "summary": d.get('summary', d.get('description', f"Automatically discovered via {d.get('source', 'Sitemap')} monitoring.")),
                "source_url": source_url,
                "source_name": d.get('source', d.get('source_account', d.get('company', 'Deep Discovery'))),
                "published_at": d.get('published_at', d.get('discovered_at')),
                "relevance_score": 9.0,
                "combined_score": 15.0, # High priority for deep signals
                "category": (
                    "community-discussion" if d.get('discussion_signal')
                    else "video-discovery" if file.endswith('new_videos_queue.json')
                    else "deep-discovery"
                ),
                "tags": [
                    (
                        "community-discussion" if d.get('discussion_signal')
                        else "video-discovery" if file.endswith('new_videos_queue.json')
                        else "deep-discovery"
                    ),
                    d.get('org', d.get('company', d.get('subreddit', 'general'))).lower()
                ],
                "discussion_signal": d.get('discussion_signal'),
                "top_comments": d.get('top_comments', [])
            })

    if not new_items:
        print("No new deep discoveries to aggregate.")
        return

    max_items = int(queue_policy().get("active_queue_max_items", 1000))
    _document, added_count, duplicate_count = merge_queue(new_items, max_items=max_items)
    if added_count:
        print(
            f"Aggregated {added_count} new items into news_queue.json; "
            f"merged {duplicate_count} duplicate(s)"
        )
    else:
        print("All discoveries already exist in the queue.")

if __name__ == "__main__":
    main()
