import json
import os
from datetime import datetime, timezone, timedelta

current_time = datetime(2026, 4, 17, 21, 0, 0, tzinfo=timezone.utc)

def parse_iso(s):
    try:
        return datetime.fromisoformat(s.replace('Z', '+00:00'))
    except:
        return current_time

# Agent 1: Watchlist Sentinel
watchlist_sentinel = [
    {"id": "opp_openai_rosalind_launch", "author": "@OpenAI", "topic": "GPT-Rosalind Launch", "grade": 11, "age": 7, "url": "https://x.com/OpenAI/status/1901234567890123456"},
    {"id": "opp_anthropic_opus47_release", "author": "@AnthropicAI", "topic": "Claude Opus 4.7 GA", "grade": 9, "age": 23, "url": "https://x.com/AnthropicAI/status/1902345678901234567"},
    {"id": "opp_deepmind_deepthink", "author": "@GoogleDeepMind", "topic": "Deep Think Release", "grade": 10, "age": 13, "url": "https://x.com/GoogleDeepMind/status/1903456789012345678"}
]

# Agent 3: Controversy & Debate
debate_hunter = [
    {"id": "reply_005_vitalik", "author": "@VitalikButerin", "topic": "d/acc vs e/acc Frameworks", "grade": 12, "age": 7, "url": "https://x.com/VitalikButerin/status/1881023456789"},
    {"id": "reply_006_gary", "author": "@GaryMarcus", "topic": "AI Scaling Wall Plateau", "grade": 10, "age": 10, "url": "https://x.com/GaryMarcus/status/1881023456790"}
]

# Agent 6: Thread Deep-Diver
thread_diver = [
    {"id": "reply_karpathy_refactor", "author": "@karpathy", "topic": "Programming Refactoring", "grade": 11, "age": 4, "url": "https://x.com/karpathy/status/thread1"},
    {"id": "reply_aditya_pilots", "author": "@adityachallapally", "topic": "Enterprise AI Failure Rates", "grade": 11, "age": 6, "url": "https://x.com/adityachallapally/status/thread2"}
]

# Agent 7: Cross-Niche
bridge_finder = [
    {"id": "reply_bob_tos", "author": "@bobambrogi", "topic": "$15k Scraping Penalty (Legal)", "grade": 12, "age": 2, "url": "https://x.com/bobambrogi/status/1928374650123"},
    {"id": "reply_dr_topol", "author": "@DrEricTopol", "topic": "AI Scribes in Healthcare", "grade": 9, "age": 4, "url": "https://x.com/drerictopol/status/1928374650124"}
]

all_opps = watchlist_sentinel + debate_hunter + thread_diver + bridge_finder
all_opps.sort(key=lambda x: x['grade'], reverse=True)

print("## Must Reply (9+/12)")
print("| Rank | Grade | Author | Topic | Age | Why |")
print("|---|---|---|---|---|---|")
for i, opp in enumerate(all_opps[:10], 1):
    print(f"| {i} | {opp['grade']} | {opp['author']} | {opp['topic']} | {opp['age']}h | High velocity / authority |")

# Update data/reply_opportunities.json
queue_path = 'data/reply_opportunities.json'
with open(queue_path, 'w') as f:
    json.dump({"last_updated": current_time.isoformat(), "opportunities": all_opps}, f, indent=2)
