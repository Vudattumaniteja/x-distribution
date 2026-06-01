import json
import os
from datetime import datetime, timezone

BREADTH_FILE = 'data/breadth_verified_items.json'
QUEUE_FILE = 'data/news_queue.json'

def load_json(path):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except:
                return None
    return None

def main():
    breadth_data = load_json(BREADTH_FILE)
    if not breadth_data:
        print("No breadth data found.")
        return

    queue_data = load_json(QUEUE_FILE)
    
    # Standardize metadata
    metadata = {"description": "Raw news items", "max_items_kept": 100}
    items = []

    # Handle different queue formats
    if isinstance(queue_data, list):
        items = queue_data
    elif isinstance(queue_data, dict):
        items = queue_data.get('items', [])
        metadata = queue_data.get('metadata', metadata)
    
    existing_urls = {item.get('source_url') for item in items if isinstance(item, dict)}
    
    new_breadth_items = []
    for item in breadth_data.get('verified_items', []):
        if item.get('source_url') not in existing_urls:
            # Standardize
            timestamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M')
            item['id'] = f"breadth_{timestamp}_{abs(hash(item['source_url'])) % 10000}"
            item['category'] = item.get('agent', 'general').lower().split(' ')[0]
            item['combined_score'] = item.get('relevance_score', 0) + 5 # Timeliness bonus
            new_breadth_items.append(item)

    if new_breadth_items:
        final_items = new_breadth_items + items
        final_items = final_items[:100]
        
        output_data = {
            "metadata": metadata,
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "items": final_items
        }
        
        with open(QUEUE_FILE, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2)
        print(f"Merged {len(new_breadth_items)} breadth items into news_queue.json")
    else:
        print("No new breadth items to merge.")

if __name__ == "__main__":
    main()
