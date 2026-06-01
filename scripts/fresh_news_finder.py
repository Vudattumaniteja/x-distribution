from datetime import datetime, timezone, timedelta
from intelligence_queue import load_queue

def find_fresh_gems():
    cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
    cutoff_str = cutoff.isoformat()
    
    print(f"--- Searching for 48h 'Platinum' Gems (Cutoff: {cutoff_str}) ---")
    
    # 1. Search X Radar (Home feed is usually freshest)
    import json
    with open('data/x_radar_standalone.json', 'r', encoding='utf-8') as f:
        x_data = json.load(f)
    
    print("\n[FRESH X RADAR SIGNALS]")
    for item in x_data.get('new_discoveries', []):
        author = item.get('author', '')
        text = item.get('text', '')
        
        # Look for time markers in author string (e.g., "12h", "8h", "1h")
        is_fresh = False
        if any(h in author for h in ["h", "m", "s"]):
             # "May 8" or "May 10" would be stale, "12h" is fresh
             if "May" not in author:
                 is_fresh = True
        
        if is_fresh:
            print(f"💎 FRESH ({author}): {text[:150]}...")

    # 2. Search News Queue for strictly fresh items
    _, items = load_queue()
    
    print("\n[STRICTLY FRESH NEWS QUEUE ITEMS]")
    for item in items:
        pub_at = item.get('published_at', '')
        headline = item.get('headline', item.get('text', 'No Headline')[:100])
        
        if pub_at and pub_at >= cutoff_str:
            print(f"🚀 VERIFIED FRESH ({pub_at}): {headline}")

if __name__ == "__main__":
    find_fresh_gems()

