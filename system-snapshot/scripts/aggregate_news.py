import json
import os
from datetime import datetime, timezone, timedelta

current_time = datetime(2026, 4, 17, 12, 0, 0, tzinfo=timezone.utc)

def parse_iso(s):
    try:
        if len(s) == 10:
            s += "T00:00:00Z"
        return datetime.fromisoformat(s.replace('Z', '+00:00'))
    except:
        return current_time # default to now if parsing fails

with open('tmp_agent_outputs.json', 'r') as f:
    all_agent_data = json.load(f)

# Flatten and assign metadata
master_list = []
for data in all_agent_data:
    agent_name = data['agent']
    for item in data.get('items', []):
        item['discovered_by'] = agent_name
        item['discovered_by_agents'] = [agent_name]
        master_list.append(item)

# Deduplication
deduped = {}
for item in master_list:
    key = item['headline'].lower()
    
    # Custom merge rules based on common themes in the output
    if 'opus 4.7' in key or 'claude 4.7' in key: key = 'claude-opus-4.7'
    if 'mythos' in key: key = 'openai-mythos'
    if 'claude code' in key: key = 'claude-code-leak'
    if 'firefly' in key: key = 'adobe-firefly'

    if key not in deduped:
        deduped[key] = item
    else:
        existing = deduped[key]
        if item['relevance_score'] > existing['relevance_score']:
            item['discovered_by_agents'] = list(set(existing['discovered_by_agents'] + item['discovered_by_agents']))
            deduped[key] = item
        else:
            existing['discovered_by_agents'] = list(set(existing['discovered_by_agents'] + item['discovered_by_agents']))

# Ranking Formula
tier_1_sources = ['OpenAI', 'Anthropic', 'Google', 'Meta', 'Microsoft', 'arxiv', 'Nature', 'Gartner', 'WEF', 'FT', 'Business Wire', 'Anthropic Blog', 'OpenAI Blog', 'Google DeepMind', 'Bloomberg', 'PwC']

final_items = []
for key, item in deduped.items():
    score = item.get('relevance_score', 0)
    
    pub_at = parse_iso(item.get('published_at', ''))
    if pub_at:
        diff = (current_time - pub_at).total_seconds() / 3600
        if diff < 6: score += 3
        elif diff < 24: score += 1
        elif diff < 72: score += 0
        else: score -= 2
    
    # Audience Match
    headline_lower = item.get('headline', '').lower()
    if any(k in headline_lower for k in ['code', 'coding', 'benchmark', 'agent', 'architecture', 'mcp', 'sota', 'fine-tuning', 'sdk', 'api', 'model', 'github', 'open-source', 'repository', 'developer']):
        score += 2
    else:
        score += 1
        
    # Cross-Agent Bonus
    agent_count = len(item.get('discovered_by_agents', []))
    if agent_count >= 3: score += 1
    elif agent_count == 2: score += 0
    else:
        source_name = item.get('source_name', '')
        if not any(t1 in source_name for t1 in tier_1_sources):
            score -= 1

    # Video Verification Bonus
    if 'Video Analyst' in item.get('discovered_by_agents', []) and agent_count > 1:
        score += 2

    item['combined_score'] = score
    
    if score >= 3:
        final_items.append(item)

final_items.sort(key=lambda x: x['combined_score'], reverse=True)
top_10 = final_items[:10]

# Print markdown table
print("| Rank | Grade | Agent | Headline | Source | Age |")
print("|---|---|---|---|---|---|")
for i, item in enumerate(top_10, 1):
    pub_at = parse_iso(item.get('published_at', ''))
    age_hours = int((current_time - pub_at).total_seconds() / 3600)
    print(f"| {i} | {item['combined_score']} | {item['discovered_by']} | {item['headline']} | {item.get('source_name', 'Unknown')} | {age_hours}h |")

# Load existing queue, append, archive old
queue_path = 'data/news_queue.json'
existing_queue = []
if os.path.exists(queue_path):
    with open(queue_path, 'r') as f:
        existing_queue = json.load(f)

cutoff_time = current_time - timedelta(days=14)
archived_count = 0
active_queue = []

for item in existing_queue:
    pub_at = parse_iso(item.get('published_at', ''))
    if pub_at < cutoff_time:
        item['archived'] = True
        archived_count += 1
    else:
        item['archived'] = False
    active_queue.append(item)

# Append new
active_queue.extend(final_items)

# Keep last 100
active_queue = active_queue[-100:]

with open(queue_path, 'w') as f:
    json.dump(active_queue, f, indent=2)

# Write log
log_path = f'logs/agent_runs/news_hunt_{current_time.strftime("%Y%m%d_%H%M%S")}.json'
run_log = {
    'timestamp': current_time.isoformat(),
    'agent_stats': {d['agent']: len(d.get('items', [])) for d in all_agent_data},
    'total_discovered': len(master_list),
    'after_dedup': len(deduped),
    'archived_old_items': archived_count,
    'queue_size': len(active_queue),
    'top_10': top_10
}

with open(log_path, 'w') as f:
    json.dump(run_log, f, indent=2)
