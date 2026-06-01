import hashlib
import json
import os
from datetime import datetime, timezone, timedelta

HASH_FILE = 'data/seen_hashes.json'
RETENTION_DAYS = 14

def load_hashes():
    if os.path.exists(HASH_FILE):
        with open(HASH_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_hashes(hashes):
    # Cleanup old hashes
    cutoff = (datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)).isoformat()
    filtered = {h: ts for h, ts in hashes.items() if ts > cutoff}
    with open(HASH_FILE, 'w') as f:
        json.dump(filtered, f, indent=2)

def get_item_hash(item):
    # Hash by normalized headline and source URL
    content = f"{item.get('headline', '').lower().strip()}|{item.get('source_url', '')}"
    return hashlib.md5(content.encode()).hexdigest()

def filter_stale_items(items):
    hashes = load_hashes()
    new_items = []
    current_ts = datetime.now(timezone.utc).isoformat()
    
    for item in items:
        h = get_item_hash(item)
        if h not in hashes:
            hashes[h] = current_ts
            new_items.append(item)
            
    save_hashes(hashes)
    return new_items
