import json
import os
from datetime import datetime, timezone

# Files to aggregate
DISCOVERY_FILES = [
    'data/sitemap_discoveries.json',
    'data/hf_discoveries.json',
    'data/github_discoveries.json'
]

QUEUE_FILE = 'data/news_queue.json'

def load_json(path):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def main():
    new_items = []
    
    for file in DISCOVERY_FILES:
        data = load_json(file)
        if not data:
            continue
            
        discoveries = data.get('new_discoveries', [])
        for d in discoveries:
            # Standardize for news_queue.json
            timestamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M')
            source_url = d.get('url', '')
            item_id = f"deep_{timestamp}_{abs(hash(source_url)) % 10000}"
            
            headline = ""
            if 'model_id' in d:
                headline = f"New Model on HF: {d['model_id']}"
            elif 'repo_name' in d:
                headline = f"New GitHub Repo: {d['repo_name']}"
            else:
                headline = f"New Page Discovered: {source_url.split('/')[-1] or source_url}"

            new_items.append({
                "id": item_id,
                "headline": headline,
                "summary": d.get('description', f"Automatically discovered via {d['source'] if 'source' in d else 'Sitemap'} monitoring."),
                "source_url": source_url,
                "source_name": d.get('source', d.get('company', 'Deep Discovery')),
                "published_at": d.get('discovered_at'),
                "relevance_score": 9.0, 
                "combined_score": 15.0, # High priority for deep signals
                "category": "deep-discovery",
                "tags": ["deep-discovery", d.get('org', d.get('company', 'general')).lower()]
            })

    if not new_items:
        print("No new deep discoveries to aggregate.")
        return

    # Load existing queue
    queue_data = load_json(QUEUE_FILE)
    
    # Handle the case where news_queue.json is a list instead of a dict
    if isinstance(queue_data, list):
        items = queue_data
        metadata = {"description": "Legacy List Format", "max_items_kept": 100}
    elif isinstance(queue_data, dict):
        items = queue_data.get('items', [])
        metadata = queue_data.get('metadata', {"description": "Raw news items", "max_items_kept": 100})
    else:
        items = []
        metadata = {"description": "Raw news items", "max_items_kept": 100}

    # Deduplicate against existing items by URL
    existing_urls = {item.get('source_url') for item in items if isinstance(item, dict)}
    unique_new_items = [r for r in new_items if r['source_url'] not in existing_urls]

    if unique_new_items:
        final_items = unique_new_items + items
        final_items = final_items[:100]
        
        output_data = {
            "metadata": metadata,
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "items": final_items
        }
        
        with open(QUEUE_FILE, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2)
        print(f"Aggregated {len(unique_new_items)} new items into news_queue.json")
    else:
        print("All discoveries already exist in the queue.")

if __name__ == "__main__":
    main()
