import json

try:
    from intelligence_queue import load_queue
    _, items = load_queue()
    
    print("### 🚀 Phase 1: Technical Alpha Dashboard (May 8, 2026)\n")
    print("| # | Priority | Source | Signal Type | Payload |")
    print("| :--- | :--- | :--- | :--- | :--- |")
    
    count = 1
    for item in items[:8]:  # Display top 8
        source = item.get('source_name', 'Unknown')
        headline = item.get('headline', 'No Title').replace('|', '-')
        category = item.get('category', 'General')
        url = item.get('source_url', '')
        
        # Simple heuristic for priority
        score = item.get('relevance_score', 0)
        priority = "HIGH" if score > 8 else ("MEDIUM" if score > 5 else "LOW")
        if 'openai' in url.lower() or 'anthropic' in url.lower():
             priority = "CRITICAL" if score > 8 else "HIGH"
        
        print(f"| **{count}** | **{priority}** | `{source}` | {category.title()} | **{headline}** |")
        count += 1
        
except Exception as e:
    print(f"Error reading news_queue: {e}")
