import json
import os
from datetime import datetime, timezone, timedelta

# Today's date from session context: Friday, 17 April 2026
current_time = datetime(2026, 4, 17, 12, 0, 0, tzinfo=timezone.utc)
cutoff_48h = current_time - timedelta(hours=48)

def parse_iso(s):
    try:
        # Handle simple date strings like "2026-04-16"
        if len(s) == 10:
            s += "T00:00:00Z"
        return datetime.fromisoformat(s.replace('Z', '+00:00'))
    except Exception:
        return None

# RAW AGENT DATA (Corrected from sub-agent responses in history)
# Automation Scout: 2026nd April 15-16
automation_scout = [
    {"id": "hermes-agent-v0-8-0", "headline": "Nous Research Releases Hermes Agent v0.8.0 with Closed-Loop Learning", "published_at": "2026-04-15T09:00:00Z", "relevance_score": 10, "source_name": "GitHub / Nous Research", "agent": "Automation Scout"},
    {"id": "adobe-firefly-ai-assistant", "headline": "Adobe Launches Firefly AI Assistant for Multi-App Creative Orchestration", "published_at": "2026-04-15T14:00:00Z", "relevance_score": 9, "source_name": "Adobe News", "agent": "Automation Scout"},
    {"id": "velo-gapvelocity-launch", "headline": "GAPVelocity Launches VELO™: The First Agentic Platform for Legacy Modernization", "published_at": "2026-04-16T11:00:00Z", "relevance_score": 8, "source_name": "Morningstar", "agent": "Automation Scout"},
    {"id": "databricks-ai-gateway", "headline": "Databricks Unveils AI Gateway for Governed Agentic Workflows", "published_at": "2026-04-16T08:30:00Z", "relevance_score": 8, "source_name": "Databricks Blog", "agent": "Automation Scout"},
    {"id": "cloudflare-project-think", "headline": "Cloudflare Launches 'Project Think' SDK for Durable Serverless Agents", "published_at": "2026-04-16T15:00:00Z", "relevance_score": 8, "source_name": "Cloudflare Blog", "agent": "Automation Scout"}
]

# Corporate Watcher: 2026nd April 15-17
corporate_watcher = [
    {"id": "meta-coreweave-21b-deal", "headline": "Meta Secures $21B NVIDIA GPU Capacity with CoreWeave Through 2032", "published_at": "2026-04-17T05:38:00Z", "relevance_score": 10, "source_name": "CoreWeave Official", "agent": "Corporate Watcher"},
    {"id": "anthropic-claude-47-launch", "headline": "Anthropic Launches Claude Opus 4.7 with 1M Context and 'Extra High' Reasoning", "published_at": "2026-04-16T14:00:00Z", "relevance_score": 10, "source_name": "Anthropic Blog", "agent": "Corporate Watcher"},
    {"id": "openai-gpt-rosalind-launch", "headline": "OpenAI Unveils GPT-Rosalind: A Frontier Reasoning Model for Life Sciences", "published_at": "2026-04-16T16:00:00Z", "relevance_score": 9, "source_name": "OpenAI Blog", "agent": "Corporate Watcher"}
]

# Leak Hunter: 2026nd April 15-17
leak_hunter = [
    {"id": "anthropic-opus-4-7-efficiency-leak", "headline": "Claude Opus 4.7 Benchmarks Leak: +21% Intelligence Boost at 66% Lower Cost", "published_at": "2026-04-16T14:20:00Z", "relevance_score": 9, "source_name": "Reddit r/singularity", "agent": "Leak Hunter"},
    {"id": "openai-mythos-class-model-rumors", "headline": "OpenAI 'Mythos' Rumors: Secret Model Architecture to Rival Claude 4.7 Intelligence", "published_at": "2026-04-17T09:45:00Z", "relevance_score": 7, "source_name": "Reddit r/singularity", "agent": "Leak Hunter"},
    {"id": "claude-4-sonnet-metadata-leak", "headline": "Metadata Leak: Claude 4 Sonnet Name Surfaces in External Developer Tool Changelogs", "published_at": "2026-04-16T18:30:00Z", "relevance_score": 7, "source_name": "Firebender Changelog", "agent": "Leak Hunter"}
]

# Founder Insights: Contains stale 2025 news (Nadella, Altman) - FILTERING OUT
founder_insights = [
    {"id": "FI-ALTMAN-AGI-2025", "headline": "Altman: AGI path is 'basically clear' for 2025", "published_at": "2025-01-15T00:00:00Z", "relevance_score": 10, "source_name": "Bloomberg", "agent": "Founder Insights"},
    {"id": "FI-NADELLA-SAAS-DEATH", "headline": "Nadella: AI agents will render traditional SaaS UIs obsolete", "published_at": "2025-05-15T00:00:00Z", "relevance_score": 9, "source_name": "Microsoft Build 2025", "agent": "Founder Insights"}
]

all_items = automation_scout + corporate_watcher + leak_hunter + founder_insights
filtered_items = []

for item in all_items:
    pub_at = parse_iso(item['published_at'])
    if pub_at and pub_at >= cutoff_48h:
        item['age_hours'] = int((current_time - pub_at).total_seconds() / 3600)
        filtered_items.append(item)

filtered_items.sort(key=lambda x: x['relevance_score'], reverse=True)

print("| Rank | Relevance | Agent | Headline | Source | Age |")
print("|---|---|---|---|---|---|")
for i, item in enumerate(filtered_items[:10], 1):
    print(f"| {i} | {item['relevance_score']} | {item['agent']} | {item['headline']} | {item['source_name']} | {item['age_hours']}h |")
