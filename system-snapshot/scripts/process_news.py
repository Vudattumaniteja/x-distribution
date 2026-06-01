import json
import os
from datetime import datetime, timezone

current_time = datetime(2026, 4, 16, 19, 45, 0, tzinfo=timezone.utc)

def parse_iso(s):
    try:
        return datetime.fromisoformat(s.replace('Z', '+00:00'))
    except:
        return None

# Load agent data
automation_scout_items = [
    {"id": "canva-ai-2-0-launch", "published_at": "2026-04-16T09:00:00Z", "relevance_score": 9, "category": "design", "source_name": "Marketing-Interactive", "headline": "Canva AI 2.0: The 'Agentic' Design Shift"},
    {"id": "alibaba-meoo-no-code", "published_at": "2026-04-16T11:30:00Z", "relevance_score": 9, "category": "coding", "source_name": "Pandaily", "headline": "Alibaba Launches Meoo: Free No-Code Full-Stack Builder"},
    {"id": "hapax-proactive-ai", "published_at": "2026-04-14T08:00:00Z", "relevance_score": 9, "category": "agents", "source_name": "Product Hunt", "headline": "Hapax Launches Proactive AI: Building Agents by Observing Human Workflows"},
    {"id": "stonebranch-robi-ai", "published_at": "2026-04-15T14:00:00Z", "relevance_score": 8, "category": "general", "source_name": "Business Wire", "headline": "Stonebranch Robi AI: Adaptive IT Orchestration with Native MCP Integration"},
    {"id": "zapier-agents-ga", "published_at": "2026-04-15T10:00:00Z", "relevance_score": 9, "category": "agents", "source_name": "Product Hunt", "headline": "Zapier Agents Hits GA: Bringing Autonomous Reasoning to 7,000+ Apps"},
    {"id": "google-chrome-skills", "published_at": "2026-04-16T16:00:00Z", "relevance_score": 9, "category": "general", "source_name": "Google Blog", "headline": "Skills in Chrome: Google Embeds One-Click AI Prompt Workflows"},
    {"id": "benchling-ai-connectors", "published_at": "2026-04-16T12:00:00Z", "relevance_score": 8, "category": "research", "source_name": "PR Newswire", "headline": "Biotech Automation: Benchling Launches MCP-Based Scientific Data Connectors"}
]

corp_watcher_items = [
    {"id": "openai-122b-funding-superapp", "published_at": "2026-04-15T08:00:00Z", "relevance_score": 10, "company": "OpenAI", "source_name": "OpenAI", "headline": "OpenAI Closes Historic $122B Round; Unveils ChatGPT 'SuperApp' Strategy"},
    {"id": "anthropic-claude-opus-4-7", "published_at": "2026-04-16T10:00:00Z", "relevance_score": 9, "company": "Anthropic", "source_name": "Anthropic", "headline": "Anthropic Launches Claude Opus 4.7"},
    {"id": "meta-muse-spark-broadcom", "published_at": "2026-04-14T14:00:00Z", "relevance_score": 8, "company": "Meta AI", "source_name": "Meta Newsroom", "headline": "Meta Releases Muse Spark Frontier Model; Inks Deal with Broadcom"},
    {"id": "microsoft-mai-image-2-e", "published_at": "2026-04-14T11:00:00Z", "relevance_score": 7, "company": "Microsoft AI", "source_name": "Microsoft", "headline": "Microsoft AI Drops High-Efficiency Image Model"}
]

leak_hunter_items = [
    {"id": "leak-2026-04-16-anthropic-mythos", "published_at": "2026-03-26T14:30:00Z", "relevance_score": 10, "source_name": "Mashable", "headline": "Anthropic 'Claude Mythos' Leaked via Source Code Exposure"},
    {"id": "leak-2026-04-16-openai-spud", "published_at": "2026-04-05T09:00:00Z", "relevance_score": 9, "source_name": "EvoLink", "headline": "OpenAI Completes Pre-training for GPT-5.5 'Spud'"},
    {"id": "leak-2026-04-16-meta-fudge", "published_at": "2026-04-12T11:15:00Z", "relevance_score": 8, "source_name": "FT", "headline": "Yann LeCun Admits Llama 4 Benchmarks Were 'Fudged'"},
    {"id": "leak-2026-04-16-xai-grok-5", "published_at": "2026-04-14T20:00:00Z", "relevance_score": 7, "source_name": "TestingCatalog", "headline": "Grok-3.5 Beta Spotted; Grok 5 Training on 100k Blackwell Cluster"}
]

research_tracker_items = [
    {"id": "arxiv-2604-16001", "published_at": "2026-04-16T08:00:00Z", "relevance_score": 10, "source_name": "arxiv", "headline": "Neuro-Symbolic AI Slashes Robot Training Energy by 100x"},
    {"id": "arxiv-2604-15231", "published_at": "2026-04-15T10:00:00Z", "relevance_score": 9, "source_name": "arxiv", "headline": "TREX: Multi-Agent System Automates Entire LLM Fine-tuning Life-cycle"},
    {"id": "arxiv-2604-11216", "published_at": "2026-04-14T14:00:00Z", "relevance_score": 9, "source_name": "arxiv", "headline": "PRISM Benchmark Reveals 4:4 Split in AI Value Hierarchies"},
    {"id": "google-turboquant-2026", "published_at": "2026-04-10T09:00:00Z", "relevance_score": 10, "source_name": "arxiv", "headline": "TurboQuant Slashes KV Cache Memory by 6x"},
    {"id": "sakana-ai-scientist-v2-2026", "published_at": "2026-04-12T11:00:00Z", "relevance_score": 10, "source_name": "Sakana AI", "headline": "AI Scientist-v2: Fully AI-Generated Paper Accepted in 'Nature'"},
    {"id": "hle-benchmark-2026", "published_at": "2026-04-09T16:00:00Z", "relevance_score": 10, "source_name": "Nature", "headline": "Humanity's Last Exam: New AI Ceiling Revealed"}
]

econ_analyst_items = [
    {"id": "econ_2026_001_funding_surge", "published_at": "2026-04-01T12:00:00Z", "relevance_score": 10, "source_name": "AI Funding Tracker", "headline": "AI Startups Capture 80% of Global VC in Q1 2026"},
    {"id": "econ_2026_002_gpu_pricing", "published_at": "2026-03-20T09:00:00Z", "relevance_score": 9, "source_name": "Spheron", "headline": "NVIDIA B200 Compute Hits $4.40/hr"},
    {"id": "econ_2026_003_adoption_gap", "published_at": "2026-04-10T08:00:00Z", "relevance_score": 9, "source_name": "Gartner", "headline": "Enterprise AI Spending Forecast to Hit $2.52T in 2026"},
    {"id": "econ_2026_004_api_pricing", "published_at": "2026-04-12T15:00:00Z", "relevance_score": 8, "source_name": "Finout", "headline": "AI API Price War: New 'Nano' Tiers at $0.10/1M Tokens"},
    {"id": "econ_2026_005_workforce_premium", "published_at": "2026-03-15T10:00:00Z", "relevance_score": 8, "source_name": "WEF", "headline": "AI Skills Command 40% Salary Premium"},
    {"id": "econ_2026_006_industry_rotation", "published_at": "2026-04-05T11:00:00Z", "relevance_score": 8, "source_name": "IDC", "headline": "Healthcare Becomes Fastest-Growing AI Sector"}
]

founder_insights_items = [
    {"id": "lecun-world-models-2026", "published_at": "2026-04-16T09:00:00Z", "relevance_score": 9, "person": "Yann LeCun", "source_name": "Brown University", "headline": "Yann LeCun: 'LLM-to-AGI path is complete BS'"},
    {"id": "amodei-chessboard-scaling-2026", "published_at": "2026-04-09T14:30:00Z", "relevance_score": 8, "person": "Dario Amodei", "source_name": "CFR", "headline": "Dario Amodei: 'The shocks of 2026 will catch the world off guard'"},
    {"id": "altman-ring-of-power-2026", "published_at": "2026-04-11T10:00:00Z", "relevance_score": 8, "person": "Sam Altman", "source_name": "samaltman.com", "headline": "Sam Altman warns of the 'Ring of Power' dynamic"},
    {"id": "karpathy-rag-to-wiki-2026", "published_at": "2026-04-13T18:00:00Z", "relevance_score": 7, "person": "Andrej Karpathy", "source_name": "GitHub", "headline": "Andrej Karpathy: 'RAG is stateless; the future is the LLM Wiki'"},
    {"id": "srinivas-computer-pivot-2026", "published_at": "2026-04-16T08:15:00Z", "relevance_score": 7, "person": "Aravind Srinivas", "source_name": "Business Today", "headline": "Aravind Srinivas: 'Perplexity is no longer a search engine'"},
    {"id": "hassabis-gemini-reasoning-2026", "published_at": "2026-04-16T11:00:00Z", "relevance_score": 7, "person": "Demis Hassabis", "source_name": "Fast Company", "headline": "Demis Hassabis: 'Gemini Deep Think mode is our Move 37 moment'"},
    {"id": "sutskever-different-mountain-2026", "published_at": "2026-04-14T15:00:00Z", "relevance_score": 8, "person": "Ilya Sutskever", "source_name": "SSI", "headline": "Ilya Sutskever: 'We are climbing a different mountain'"}
]

tool_spotlight_items = [
    {"id": "ts-20260416-claude-opus-47-regressions", "published_at": "2026-04-16T14:00:00Z", "relevance_score": 7, "source_name": "Reddit", "headline": "Claude Opus 4.7: Vision Leap Marred by Retrieval Collapse"},
    {"id": "ts-20260416-amd-claude-audit", "published_at": "2026-04-16T09:00:00Z", "relevance_score": 9, "source_name": "GitHub", "headline": "AMD Audit Proves 73% Reasoning Collapse in Claude"},
    {"id": "ts-20260416-mano-p-sota", "published_at": "2026-04-15T18:00:00Z", "relevance_score": 9, "source_name": "GitHub", "headline": "Mano-P 1.0: Vision-Only Agent Shatters OSWorld SOTA"},
    {"id": "ts-20260416-maxhermes-token-tax", "published_at": "2026-04-16T12:00:00Z", "relevance_score": 6, "source_name": "Reddit", "headline": "MaxHermes Agent Hits Friction Over 14k Token Tax"},
    {"id": "ts-20260416-gemini-3-pro-reality-check", "published_at": "2026-04-16T16:00:00Z", "relevance_score": 7, "source_name": "Reddit", "headline": "Gemini 3 Pro: HLE Benchmark King vs Real-World Overthinking"},
    {"id": "ts-20260416-claude-code-leak-analysis", "published_at": "2026-04-16T10:00:00Z", "relevance_score": 8, "source_name": "Dev.to", "headline": "Claude Code Source Leak Reveals Anti-Distillation"}
]

all_agent_data = [
    {"agent": "Automation Scout", "items": automation_scout_items},
    {"agent": "Corporate Watcher", "items": corp_watcher_items},
    {"agent": "Leak Hunter", "items": leak_hunter_items},
    {"agent": "Research Tracker", "items": research_tracker_items},
    {"agent": "Economics Analyst", "items": econ_analyst_items},
    {"agent": "Founder Insights", "items": founder_insights_items},
    {"agent": "Tool Spotlight", "items": tool_spotlight_items}
]

# Flatten and assign metadata
master_list = []
for data in all_agent_data:
    agent_name = data['agent']
    for item in data['items']:
        item['discovered_by'] = agent_name
        master_list.append(item)

# Deduplication
deduped = {}
for item in master_list:
    key = item['headline'].lower()
    if 'opus 4.7' in key or 'claude 4.7' in key: key = 'claude-opus-4.7'
    if 'openai' in key and ('funding' in key or 'valuation' in key): key = 'openai-funding'
    if 'gpt-5' in key or 'gpt-5.4' in key: key = 'gpt-5-news'
    if 'hle' in key or 'humanity\'s last exam' in key: key = 'hle-benchmark'
    if 'muse spark' in key: key = 'meta-muse-spark'
    if 'mcp' in key: key = 'mcp-integration'
    
    if key not in deduped:
        deduped[key] = item
        deduped[key]['discovered_by_agents'] = [item['discovered_by']]
    else:
        existing = deduped[key]
        if item['relevance_score'] > existing['relevance_score']:
            item['discovered_by_agents'] = list(set(existing['discovered_by_agents'] + [item['discovered_by']]))
            deduped[key] = item
        else:
            existing['discovered_by_agents'] = list(set(existing['discovered_by_agents'] + [item['discovered_by']]))

# Ranking Formula
tier_1_sources = ['OpenAI', 'Anthropic', 'Google', 'Meta', 'Microsoft', 'arxiv', 'Nature', 'Gartner', 'WEF', 'FT', 'Business Wire']
final_items = []
for item in deduped.values():
    score = item['relevance_score']
    
    pub_at = parse_iso(item['published_at'])
    if pub_at:
        diff = (current_time - pub_at).total_seconds() / 3600
        if diff < 6: score += 3
        elif diff < 24: score += 1
        elif diff < 72: score += 0
        else: score -= 2
    
    if any(k in item['headline'].lower() for k in ['coding', 'benchmark', 'agent', 'architecture', 'mcp', 'sota', 'fine-tuning']):
        score += 2
    else:
        score += 1
        
    agent_count = len(item['discovered_by_agents'])
    if agent_count >= 3: score += 1
    elif agent_count == 2: score += 0
    else:
        if item.get('source_name') not in tier_1_sources:
            score -= 1
            
    item['combined_score'] = score
    final_items.append(item)

final_items.sort(key=lambda x: x['combined_score'], reverse=True)
top_10 = final_items[:10]

run_log = {
    'timestamp': current_time.isoformat(),
    'agent_stats': {d['agent']: len(d['items']) for d in all_agent_data},
    'total_discovered': len(master_list),
    'after_dedup': len(final_items),
    'top_10': top_10
}

os.makedirs('data', exist_ok=True)
with open('data/news_queue.json', 'w') as f:
    json.dump(final_items, f, indent=2)

log_path = f'logs/agent_runs/news_hunt_{current_time.strftime("%Y%m%d_%H%M%S")}.json'
os.makedirs('logs/agent_runs', exist_ok=True)
with open(log_path, 'w') as f:
    json.dump(run_log, f, indent=2)

print(json.dumps(top_10, indent=2))
