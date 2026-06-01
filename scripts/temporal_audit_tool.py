import json
from datetime import datetime, timezone, timedelta

def audit_temporal_accuracy():
    queue_path = 'data/news_queue.json'
    cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
    cutoff_str = cutoff.isoformat()
    
    print(f"--- Temporal Audit (Cutoff: {cutoff_str}) ---")
    
    from intelligence_queue import load_queue
    _, items = load_queue()
    stale_count = 0
    fresh_count = 0
    missing_date = 0
    
    print("\n[STALE ITEMS FOUND IN REPORTED LIST]")
    for item in items:
        pub_at = item.get('published_at', '')
        headline = item.get('headline', item.get('text', 'No Headline')[:50])
        
        if not pub_at:
            missing_date += 1
            continue
            
        if pub_at < cutoff_str:
            stale_count += 1
            # Check if this was one of my "Platinum" items
            target_keywords = ["Daybreak", "Instant", "SpaceX", "Subquadratic", "Agent View", "4.8"]
            if any(kw.lower() in headline.lower() for kw in target_keywords):
                print(f"⚠️ STALE: {pub_at} | {headline}")
        else:
            fresh_count += 1

    print(f"\nSummary:")
    print(f"Total Items: {len(items)}")
    print(f"Fresh (<=48h): {fresh_count}")
    print(f"Stale (>48h): {stale_count}")
    print(f"Missing Timestamp: {missing_date}")

if __name__ == "__main__":
    audit_temporal_accuracy()
