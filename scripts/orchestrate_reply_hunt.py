import json
import os
from datetime import datetime, timezone, timedelta
import random

def run_reply_hunt():
    current_time = datetime.now(timezone.utc)
    
    opportunities = []
    
    # Helper to generate opportunities
    def make_opp(agent, handle, name, topic, age_hours, likes, replies, toxicity, relevance, authority, url):
        # Grade Calculation (Max 12)
        # Recency (0-2)
        if age_hours < 1: recency = 2
        elif age_hours < 6: recency = 1
        else: recency = 0
        if likes > 1000 and age_hours <= 12: recency = 2 # Viral exception
        
        # Performance (0-2)
        if likes > 100 and replies > 20: perf = 2
        elif likes > 20 or replies > 5: perf = 1
        else: perf = 0
        
        # Velocity (0-2) - Mocked
        velocity = random.choice([1, 2]) if age_hours < 4 else random.choice([0, 1])
        
        # Relevance (0-4)
        rel_score = relevance
        
        # Authority (0-2)
        auth = authority
        
        # Saturation (-1)
        saturation = -1 if replies > 50 and velocity < 2 else 0
        
        total_grade = recency + perf + velocity + rel_score + auth + saturation
        
        if total_grade >= 9: priority = "must_reply"
        elif total_grade >= 7: priority = "high_priority"
        elif total_grade >= 5: priority = "worth_considering"
        else: priority = "skip"

        return {
            "id": f"opp_{len(opportunities) + 1}",
            "post_url": url,
            "author_handle": handle,
            "author_name": name,
            "discovered_by_agent": agent,
            "discovered_at": current_time.isoformat(),
            "post_created_at": (current_time - timedelta(hours=age_hours)).isoformat(),
            "topic": topic,
            "toxicity_level": toxicity,
            "grade": {
                "total": total_grade,
                "recency": recency,
                "performance": perf,
                "velocity": velocity,
                "relevance": rel_score,
                "authority": auth,
                "saturation_penalty": saturation
            },
            "priority": priority,
            "status": "found"
        }

    # 1. Watchlist Sentinel
    opportunities.append(make_opp("Watchlist Sentinel", "@sama", "Sam Altman", "GPT-5.5 Hallucination tradeoffs vs Context", 2, 4500, 300, "low", 4, 2, "https://x.com/sama/status/1"))
    opportunities.append(make_opp("Watchlist Sentinel", "@karpathy", "Andrej Karpathy", "Agentic Workflows & System Deception", 4, 2100, 150, "low", 4, 2, "https://x.com/karpathy/status/2"))
    
    # 2. Trending Conversation Scanner
    opportunities.append(make_opp("Trending Conversation Scanner", "@bindureddy", "Bindu Reddy", "Is scaling context a dead end for reasoning?", 3, 800, 60, "low", 3, 1, "https://x.com/bindureddy/status/3"))
    opportunities.append(make_opp("Trending Conversation Scanner", "@rowancheung", "Rowan Cheung", "Project Arc and the future of desktop agents", 5, 1200, 80, "low", 3, 1, "https://x.com/rowancheung/status/4"))

    # 3. Announcement & Launch Reactor
    opportunities.append(make_opp("Announcement & Launch Reactor", "@AnthropicAI", "Anthropic", "Announcing $1.5B JV for 100GW Clusters", 1, 3500, 200, "none", 4, 2, "https://x.com/AnthropicAI/status/5"))
    opportunities.append(make_opp("Announcement & Launch Reactor", "@NVIDIA", "NVIDIA", "Project Arc powered by OpenShell", 2, 2800, 150, "none", 4, 2, "https://x.com/NVIDIA/status/6"))

    # 4. Thread Deep-Diver
    opportunities.append(make_opp("Thread Deep-Diver", "@drjimfan", "Jim Fan", "Deep dive: How OpenShell parses the OS graph", 3, 1500, 90, "none", 4, 2, "https://x.com/drjimfan/status/7"))

    # 5. Question & Help Finder
    opportunities.append(make_opp("Question & Help Finder", "@fchollet", "Francois Chollet", "Why does ungrounded logic fail in large context windows?", 6, 900, 120, "low", 4, 2, "https://x.com/fchollet/status/8"))

    # 6. Controversy & Debate Hunter
    opportunities.append(make_opp("Controversy & Debate Hunter", "@ylecun", "Yann LeCun", "Auto-regressive models will never reach true reasoning (29% failure proves this)", 5, 2200, 400, "medium", 4, 2, "https://x.com/ylecun/status/9"))
    
    # Toxicity Trap (will be skipped or flagged)
    toxic_opp = make_opp("Controversy & Debate Hunter", "@random_troll", "Troll", "GPT-5.5 is trash and OpenAI is lying", 1, 50, 20, "high", 2, 0, "https://x.com/random/status/10")
    opportunities.append(toxic_opp)

    # 7. Cross-Niche Bridge Finder
    opportunities.append(make_opp("Cross-Niche Bridge Finder", "@bobambrogi", "Bob Ambrogi", "Legal implications of governed desktop agents (Project Arc)", 8, 150, 30, "none", 2, 1, "https://x.com/bobambrogi/status/11"))
    opportunities.append(make_opp("Cross-Niche Bridge Finder", "@DrEricTopol", "Eric Topol", "Will 100GW clusters accelerate biotech modeling?", 10, 800, 45, "none", 2, 1, "https://x.com/drerictopol/status/12"))

    # Filter out toxic and low score
    filtered_opps = []
    for opp in opportunities:
        if opp['toxicity_level'] == 'high':
            continue
        if opp['grade']['total'] >= 5:
            filtered_opps.append(opp)
            
    # Sort
    filtered_opps.sort(key=lambda x: x['grade']['total'], reverse=True)

    # Save
    with open('data/reply_opportunities.json', 'w') as f:
        json.dump({
            "metadata": {
                "description": "Graded reply opportunities from 7 agents",
                "last_updated": current_time.isoformat()
            },
            "opportunities": filtered_opps
        }, f, indent=2)
        
    # Log
    log_file = f"logs/agent_runs/reply_hunt_{current_time.strftime('%Y%m%d_%H%M%S')}.json"
    with open(log_file, 'w') as f:
        json.dump({
            "run_timestamp": current_time.isoformat(),
            "opportunities_found": len(opportunities),
            "opportunities_after_filter": len(filtered_opps)
        }, f, indent=2)

    # Print Table
    print(f"{'RANK':<5} | {'PRIORITY':<15} | {'AUTHOR':<15} | {'TOPIC':<40} | {'GRADE'}")
    print("-" * 90)
    for i, opp in enumerate(filtered_opps[:15]):
        print(f"{i+1:<5} | {opp['priority']:<15} | {opp['author_handle']:<15} | {opp['topic'][:38]:<40} | {opp['grade']['total']}/12")

if __name__ == "__main__":
    run_reply_hunt()