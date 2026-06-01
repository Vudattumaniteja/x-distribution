import json
import os
from datetime import datetime, timezone, timedelta

from intelligence_queue import load_queue, replace_queue
from source_registry import queue_policy
from tier_policy import is_tier_source

# Config
CURRENT_TIME = datetime.now(timezone.utc)
NEWS_CUTOFF = CURRENT_TIME - timedelta(hours=48)
RESEARCH_CUTOFF = CURRENT_TIME - timedelta(days=7)

AGENT_FILES = [
    'tmp_automation_scout.json',
    'tmp_corporate_watcher.json',
    'tmp_leak_hunter.json',
    'tmp_research_tracker.json',
    'tmp_economics_analyst.json',
    'tmp_founder_insights.json',
    'tmp_tool_spotlight.json',
    'tmp_video_analyst.json'
]

def parse_iso(s):
    try:
        if not s or s == 'unknown': return None
        if len(s) == 10: s += "T00:00:00Z"
        return datetime.fromisoformat(s.replace('Z', '+00:00'))
    except:
        return None

def main():
    all_raw_items = []
    
    # 1. Load Subagent Data
    for filename in AGENT_FILES:
        if not os.path.exists(filename):
            print(f"Skipping missing file: {filename}")
            continue
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
                
                # Derive agent name from filename
                base_name = os.path.basename(filename).replace('tmp_', '').replace('.json', '')
                agent_name = ' '.join(word.capitalize() for word in base_name.split('_'))
                
                items = []
                if isinstance(data, dict):
                    agent_name = data.get('agent', agent_name)
                    items = data.get('items', [])
                elif isinstance(data, list):
                    items = data
                
                for item in items:
                    # Map different schema keys to standardized ones
                    if 'headline' not in item and 'claim' in item:
                        item['headline'] = item['claim']
                    if 'source_name' not in item and 'source_type' in item:
                        item['source_name'] = item['source_type']
                    if 'source_url' not in item and 'url' in item:
                        item['source_url'] = item['url']
                        
                    item['discovered_by'] = agent_name
                    all_raw_items.append(item)
        except Exception as e:
            print(f"Error loading {filename}: {e}")

    # 2. Load Phase 1 Data (Deep Discovery)
    queue_metadata, queue_items = load_queue()
    for item in queue_items:
        if 'discovered_by' not in item:
            item['discovered_by'] = 'Deep Discovery'
        all_raw_items.append(item)

    # 3. Truth Sentinel (Agent 09) - Verification & Filtering
    verified_items = []
    for item in all_raw_items:
        pub_at = parse_iso(item.get('published_at', ''))
        
        # Temporal Gate
        cutoff = RESEARCH_CUTOFF if item.get('discovered_by') in ['Research Tracker', 'Economics Analyst'] else NEWS_CUTOFF
        if pub_at and pub_at < cutoff:
            continue # Stale
        
        # Source Audit
        source_name = item.get('source_name', 'Unknown')
        is_t1 = is_tier_source(source_name, "T1")
        item['source_tier'] = "T1" if is_t1 else item.get('source_tier', 'unclassified')
        
        # Negative Alpha / Nuance
        # (Usually added by subagents or sentinel search, we preserve what's there)
        
        verified_items.append(item)

    # 4. Strategic Aggregator (Agent 10) - Dedup & Ranking
    deduped = {}
    for item in verified_items:
        # Key on headline (fuzzy match) or id
        key = item.get('id', item.get('headline', '')).lower().strip()
        if key not in deduped:
            deduped[key] = item
            deduped[key]['discovered_by_agents'] = [item['discovered_by']]
        else:
            existing = deduped[key]
            # Keep highest relevance
            if item.get('relevance_score', 0) > existing.get('relevance_score', 0):
                item['discovered_by_agents'] = list(set(existing.get('discovered_by_agents', []) + [item['discovered_by']]))
                deduped[key] = item
            else:
                existing['discovered_by_agents'] = list(set(existing.get('discovered_by_agents', []) + [item['discovered_by']]))

    # Ranking Formula
    ranked_items = []
    for item in deduped.values():
        score = float(item.get('relevance_score', 0))
        
        # Timeliness Bonus
        pub_at = parse_iso(item.get('published_at', ''))
        if pub_at:
            diff_hours = (CURRENT_TIME - pub_at).total_seconds() / 3600
            if diff_hours < 2: score += 5
            elif diff_hours < 6: score += 3
            elif diff_hours < 24: score += 1
        
        # Impact Bonus (Breakthrough tags)
        headline = item.get('headline', '').lower()
        if any(k in headline for k in ['sota', 'record', 'breakthrough', 'gpt-5', 'gpt-6', 'claude 4', 'llama 4', 'major', 'unveils', 'launches']):
            score += 5
        
        # Audience Match Bonus (Dev/Practitioner)
        if any(k in headline for k in ['code', 'agent', 'benchmark', 'mcp', 'api', 'sdk', 'training', 'inference']):
            score += 3
            
        # Cross-Agent Bonus
        agent_count = len(item.get('discovered_by_agents', []))
        if agent_count >= 3: score += 2
        
        item['combined_score'] = score
        ranked_items.append(item)

    ranked_items.sort(key=lambda x: x['combined_score'], reverse=True)
    
    # 5. Output Final Results
    final_output, _duplicate_count = replace_queue(
        ranked_items,
        metadata={
            **queue_metadata,
            "total_raw": len(all_raw_items),
            "total_verified": len(verified_items),
            "total_deduped": len(deduped),
        },
        max_items=int(queue_policy().get("active_queue_max_items", 1000)),
    )

    # 6. Save Run Log (Satisfies Hard Rule 7)
    agent_stats = {}
    for item in all_raw_items:
        agent = item.get('discovered_by', 'Unknown')
        agent_stats[agent] = agent_stats.get(agent, 0) + 1
        
    log_path = f'logs/agent_runs/news_hunt_{CURRENT_TIME.strftime("%Y%m%d_%H%M%S")}.json'
    run_log = {
        "timestamp": CURRENT_TIME.isoformat(),
        "agent_stats": agent_stats,
        "total_discovered": len(all_raw_items),
        "after_dedup": len(deduped),
        "archived_old_items": 0,
        "queue_size": final_output["total_items"],
        "top_10": ranked_items[:10]
    }
    
    os.makedirs('logs/agent_runs', exist_ok=True)
    with open(log_path, 'w') as f:
        json.dump(run_log, f, indent=2)

    # Markdown Table for User
    print("# Hybrid News Pipeline Dashboard — " + CURRENT_TIME.strftime("%Y-%m-%d"))
    print("\n## The Big Three (Headline Stories)")
    print("| # | Score | Agent | Headline | Source | Age |")
    print("|---|-------|-------|----------|--------|-----|")
    for i, item in enumerate(ranked_items[:3], 1):
        pub_at = parse_iso(item.get('published_at', ''))
        age_str = f"{int((CURRENT_TIME - pub_at).total_seconds() / 3600)}h" if pub_at else "??h"
        print(f"| {i} | {item['combined_score']:.1f} | {item['discovered_by']} | **{item['headline']}** | {item.get('source_name', 'Unknown')} | {age_str} |")

    print("\n## High-Signal News Queue")
    print("| # | Score | Agent | Headline | Source | Age |")
    print("|---|-------|-------|----------|--------|-----|")
    for i, item in enumerate(ranked_items[3:13], 4):
        pub_at = parse_iso(item.get('published_at', ''))
        age_str = f"{int((CURRENT_TIME - pub_at).total_seconds() / 3600)}h" if pub_at else "??h"
        print(f"| {i} | {item['combined_score']:.1f} | {item['discovered_by']} | {item['headline']} | {item.get('source_name', 'Unknown')} | {age_str} |")

if __name__ == "__main__":
    main()
