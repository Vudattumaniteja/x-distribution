import json
import os
from datetime import datetime, timezone

from intelligence_queue import merge_queue

BREADTH_FILE = 'data/breadth_verified_items.json'

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

    new_breadth_items = []
    for item in breadth_data.get('verified_items', []):
        source_url = item.get('source_url')
        if not source_url:
            continue
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M')
        item['id'] = f"breadth_{timestamp}_{abs(hash(source_url)) % 10000}"
        item['category'] = item.get('agent', 'general').lower().split(' ')[0]
        item['combined_score'] = item.get('relevance_score', 0) + 5 # Timeliness bonus
        new_breadth_items.append(item)

    if new_breadth_items:
        _document, added_count, duplicate_count = merge_queue(new_breadth_items)
        print(
            f"Merged {added_count} breadth items into news_queue.json; "
            f"merged {duplicate_count} duplicate(s)"
        )
    else:
        print("No new breadth items to merge.")

if __name__ == "__main__":
    main()
