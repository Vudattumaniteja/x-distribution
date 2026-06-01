import subprocess
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from intelligence_queue import filter_recent_items, replace_queue
from source_clis import python_script_command
from source_registry import enabled_live_source_scripts, live_source_outputs, collection_runtime_policy
from x_collection_coordinator import collect_x_read_only

UTF8_ENV = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
PHASE1_LANE_HEALTH_PATH = "data/phase1_lane_health.json"

def collect_x_data():
    print("--- Lane A: X Feed Collection (Breadth Priority) ---")
    runtime = collection_runtime_policy()
    workers = max(1, int(runtime.get("x_workers", 3)))
    timeline_days = float(runtime.get("x_timeline_days", 7))
    tweets_per_account = int(runtime.get("x_tweets_per_account", 3))
    
    with open('config/followed_accounts.json', 'r', encoding='utf-8') as f:
        config = json.load(f)

    accounts_by_handle = {
        acc['handle'].replace('@', '').lower(): acc
        for acc in config['accounts']
    }
    result = collect_x_read_only(
        accounts_by_handle,
        workers=workers,
        days=timeline_days,
    )

    normalized = []
    per_account_counts = {}
    for tweet in result["tweets"]:
        scope = tweet.get("_x_collection_scope", "")
        handle = scope.partition(":")[2] if scope.startswith("watchlist:") else ""
        if handle:
            count = per_account_counts.get(handle, 0)
            if count >= tweets_per_account:
                continue
            per_account_counts[handle] = count + 1
            acc = accounts_by_handle.get(handle, {})
            signal_type = "Verified" if acc.get("category") == "corporate" else "High-Impact Rumor"
            discovered_by = f"X Watchlist ({acc.get('name', acc.get('handle', handle))})"
        else:
            signal_type = "Algorithm Trend"
            discovered_by = "X Home Feed"
        text = tweet.get("primary_text") or tweet.get("text") or tweet.get("quoted_text") or ""
        author = tweet.get("author") or tweet.get("source") or "X"
        headline = text.strip().replace("\n", " ")[:180] if text else f"X post from {author}"
        normalized.append({
            **tweet,
            "headline": headline,
            "summary": text or tweet.get("quoted_text", ""),
            "source": author,
            "url": tweet.get("url", ""),
            "signal_type": signal_type,
            "notes": discovered_by,
            "published_at": tweet.get("timestamp") or tweet.get("published_at"),
        })

    return normalized, result

def collect_rss_data():
    print("--- Lane B: Corporate RSS (Ground Truth) ---")
    from collection_adapter import RSSCollectionAdapter
    adapter = RSSCollectionAdapter()
    return adapter.collect()

def collect_youtube_data():
    print("--- Lane C: YouTube (Deep Signal Priority) ---")
    # Discover videos, then retrieve transcripts exclusively through YT Transcript CLI.
    import orchestrate_videos
    import orchestrate_all_latest
    try:
        orchestrate_videos.orchestrate()
        orchestrate_all_latest.pull_all_transcripts()
    except Exception as exc:
        print(f"YouTube discovery/transcript pull failed in-process: {exc}")
    return []


def signal_output_paths(source_name):
    return [
        path for path in live_source_outputs(source_name)
        if path.endswith("_signals.json") or not path.endswith("_raw.json")
    ]

def collect_community_data():
    print("--- Lane D: Community Discussion (Reddit + Hacker News) ---")
    from collection_adapter import HNCollectionAdapter, RedditCollectionAdapter
    
    hn_adapter = HNCollectionAdapter()
    reddit_adapter = RedditCollectionAdapter()
    
    community_items = hn_adapter.collect() + reddit_adapter.collect()
    return community_items

def collect_artifact_research_data():
    print("--- Lane E: Artifact + Research Sources (GitHub + Hugging Face + arXiv) ---")
    for script in enabled_live_source_scripts("github", "huggingface", "arxiv"):
        subprocess.run(python_script_command(script), check=False, env=UTF8_ENV)

    items = []
    for path in live_source_outputs("github", "huggingface", "arxiv"):
        if not os.path.exists(path):
            continue
        with open(path, 'r', encoding='utf-8') as f:
            payload = json.load(f)
        discoveries = payload if isinstance(payload, list) else payload.get('new_discoveries', [])
        for item in discoveries:
            items.append({
                "headline": item.get('title') or item.get('repo_name') or item.get('model_id') or item.get('release_name') or "Artifact/research discovery",
                "summary": item.get('summary') or item.get('description') or "",
                "source": item.get('source', 'GitHub/arXiv'),
                "url": item.get('url') or item.get('html_url') or item.get('source_url') or "",
                "signal_type": "Artifact/Research Source",
                "notes": "Collected through configured GitHub/Hugging Face/arXiv source lane",
                "published_at": item.get('published_at') or item.get('created_at') or item.get('updated_at'),
            })
    return items

def collect_finance_data():
    print("--- Lane F: Finance + Macro Intelligence ---")
    for script in enabled_live_source_scripts("finance"):
        subprocess.run(python_script_command(script), check=False, env=UTF8_ENV)

    items = []
    for path in signal_output_paths("finance"):
        if not os.path.exists(path):
            continue
        with open(path, 'r', encoding='utf-8') as f:
            payload = json.load(f)
        finance_items = payload.get('signals') or payload.get('items') or []
        for item in finance_items:
            items.append({
                "headline": item.get('title') or "AI market intelligence signal",
                "summary": item.get('summary', ''),
                "source": item.get('source', 'Finance Source'),
                "url": item.get('url', ''),
                "signal_type": "AI Market Intelligence",
                "notes": ", ".join(item.get('finance_signal_types', [])) or "finance/macro signal",
                "published_at": item.get('published_at'),
                "score": item.get('relevance_score'),
                "source_region": item.get('source_region'),
                "finance_signal_types": item.get('finance_signal_types', []),
                "ai_keyword_hits": item.get('ai_keyword_hits', []),
                "finance_keyword_hits": item.get('finance_keyword_hits', []),
            })
    return items

def collect_startup_funding_data():
    print("--- Lane G: Startup Funding + Product Signals ---")
    for script in enabled_live_source_scripts("startup_funding"):
        subprocess.run(python_script_command(script), check=False, env=UTF8_ENV)

    items = []
    for path in signal_output_paths("startup_funding"):
        if not os.path.exists(path):
            continue
        with open(path, 'r', encoding='utf-8') as f:
            payload = json.load(f)
        startup_items = payload.get('signals') or payload.get('items') or []
        for item in startup_items:
            funding_rounds = item.get('funding_rounds', [])
            round_label = ", ".join(funding_rounds) if funding_rounds else "startup/product signal"
            amount = item.get('funding_amount')
            notes = f"{round_label}; amount={amount}" if amount else round_label
            items.append({
                "headline": item.get('title') or "AI startup signal",
                "summary": item.get('summary', ''),
                "source": item.get('source', 'Startup Source'),
                "url": item.get('url', ''),
                "signal_type": item.get('signal_type', 'Startup Signal'),
                "notes": notes,
                "published_at": item.get('published_at'),
                "score": item.get('relevance_score'),
                "source_region": item.get('source_region'),
                "company": item.get('company'),
                "funding_rounds": funding_rounds,
                "funding_amount": amount,
                "lead_investor": item.get('lead_investor'),
                "ai_keyword_hits": item.get('ai_keyword_hits', []),
                "startup_keyword_hits": item.get('startup_keyword_hits', []),
                "funding_keyword_hits": item.get('funding_keyword_hits', []),
                "product_keyword_hits": item.get('product_keyword_hits', []),
            })
    return items

def collect_model_market_data():
    print("--- Lane H: Model Market Radar (OpenRouter) ---")
    for script in enabled_live_source_scripts("model_market"):
        subprocess.run(python_script_command(script), check=False, env=UTF8_ENV)

    items = []
    for path in signal_output_paths("model_market"):
        if not os.path.exists(path):
            continue
        with open(path, 'r', encoding='utf-8') as f:
            payload = json.load(f)
        for item in payload.get('signals') or payload.get('items') or []:
            items.append({
                "headline": item.get('title') or item.get('model_id') or "Model market signal",
                "summary": item.get('summary', ''),
                "source": item.get('source', 'OpenRouter'),
                "url": item.get('url', ''),
                "signal_type": item.get('signal_type', 'Model Market Signal'),
                "notes": ", ".join(item.get('model_signal_types', [])) or "model market signal",
                "published_at": item.get('published_at') or item.get('discovered_at'),
                "source_region": item.get('source_region'),
                "model_id": item.get('model_id'),
                "model_signal_types": item.get('model_signal_types', []),
                "confidence": item.get('confidence'),
            })
    return items

def collect_startup_collection_data():
    print("--- Lane I: Startup Collections + Missed Startup Radar ---")
    for script in enabled_live_source_scripts("startup_collections"):
        subprocess.run(python_script_command(script), check=False, env=UTF8_ENV)

    items = []
    for path in signal_output_paths("startup_collections"):
        if not os.path.exists(path):
            continue
        with open(path, 'r', encoding='utf-8') as f:
            payload = json.load(f)
        for item in payload.get('signals') or payload.get('items') or []:
            items.append({
                "headline": item.get('title') or "Startup collection signal",
                "summary": item.get('summary', ''),
                "source": item.get('source', 'Startup Collection'),
                "url": item.get('url', ''),
                "signal_type": item.get('signal_type', 'Startup Collection Signal'),
                "notes": f"amount_usd={item.get('detected_amount_usd')}; method={item.get('discovery_method')}",
                "published_at": item.get('published_at'),
                "source_region": item.get('source_region'),
                "detected_amount_usd": item.get('detected_amount_usd'),
                "topic_keyword_hits": item.get('topic_keyword_hits', []),
                "funding_keyword_hits": item.get('funding_keyword_hits', []),
                "confidence": item.get('confidence'),
            })
    return items

def collect_science_breakthrough_data():
    print("--- Lane K: Bio + Science Breakthrough Radar ---")
    for script in enabled_live_source_scripts("science_breakthroughs"):
        subprocess.run(python_script_command(script), check=False, env=UTF8_ENV)

    items = []
    for path in signal_output_paths("science_breakthroughs"):
        if not os.path.exists(path):
            continue
        with open(path, 'r', encoding='utf-8') as f:
            payload = json.load(f)
        for item in payload.get('signals') or payload.get('items') or []:
            items.append({
                "headline": item.get('title') or "Science breakthrough signal",
                "summary": item.get('summary', ''),
                "source": item.get('source', 'Science Source'),
                "url": item.get('url', ''),
                "signal_type": item.get('signal_type', 'Science/Deep-Tech Breakthrough'),
                "notes": ", ".join(item.get('science_keyword_hits', []) + item.get('breakthrough_keyword_hits', [])),
                "published_at": item.get('published_at'),
                "source_region": item.get('source_region'),
                "score": item.get('relevance_score'),
                "science_keyword_hits": item.get('science_keyword_hits', []),
                "breakthrough_keyword_hits": item.get('breakthrough_keyword_hits', []),
                "confidence": item.get('confidence'),
            })
    return items

def collect_developer_sentiment_data():
    print("--- Lane L: Developer Pain + Adoption Radar ---")
    for script in enabled_live_source_scripts("developer_sentiment"):
        subprocess.run(python_script_command(script), check=False, env=UTF8_ENV)

    items = []
    for path in signal_output_paths("developer_sentiment"):
        if not os.path.exists(path):
            continue
        with open(path, 'r', encoding='utf-8') as f:
            payload = json.load(f)
        for item in payload.get('signals') or payload.get('items') or []:
            items.append({
                "headline": item.get('title') or "Developer sentiment/status signal",
                "summary": item.get('summary', ''),
                "source": item.get('source', 'Developer Sentiment Source'),
                "url": item.get('url', ''),
                "signal_type": item.get('signal_type', 'Developer Pain/Adoption Signal'),
                "notes": ", ".join(item.get('pain_keyword_hits', [])),
                "published_at": item.get('published_at'),
                "source_region": item.get('source_region'),
                "pain_keyword_hits": item.get('pain_keyword_hits', []),
                "confidence": item.get('confidence'),
            })
    return items

def main():
    runtime = collection_runtime_policy()
    lane_workers = max(1, int(runtime.get("lane_workers", 5)))
    lanes = {
        "x": collect_x_data,
        "rss": collect_rss_data,
        "youtube": collect_youtube_data,
        "community": collect_community_data,
        "artifact_research": collect_artifact_research_data,
        "finance": collect_finance_data,
        "startup_funding": collect_startup_funding_data,
        "model_market": collect_model_market_data,
        "startup_collections": collect_startup_collection_data,
        "science": collect_science_breakthrough_data,
        "developer_sentiment": collect_developer_sentiment_data,
    }
    lane_results = {name: [] for name in lanes}
    lane_health = []
    x_collection = None

    with ThreadPoolExecutor(max_workers=min(lane_workers, len(lanes))) as executor:
        futures = {executor.submit(fn): name for name, fn in lanes.items()}
        for future in as_completed(futures):
            name = futures[future]
            try:
                value = future.result()
                if name == "x":
                    lane_results[name], x_collection = value
                    lane_health.append({
                        "lane": name,
                        "status": x_collection["status"],
                        "x_status": x_collection["status"],
                        "x_run_id": x_collection["run_id"],
                        "items": len(lane_results[name]),
                    })
                    continue
                lane_results[name] = value or []
                lane_health.append({
                    "lane": name,
                    "status": "OK",
                    "items": len(lane_results[name]),
                })
            except Exception as exc:
                lane_results[name] = []
                if name == "x":
                    x_collection = {"status": "FAILED", "run_id": None}
                lane_health.append({
                    "lane": name,
                    "status": "FAILED" if name == "x" else "ERROR",
                    **({"x_status": "FAILED", "x_run_id": None} if name == "x" else {}),
                    "error": str(exc),
                    "items": 0,
                })
                print(f"  Lane {name} failed; continuing: {exc}")
    
    # Load everything for the unified pool
    all_raw_items = (
        lane_results["x"]
        + lane_results["community"]
        + lane_results["artifact_research"]
        + lane_results["finance"]
        + lane_results["startup_funding"]
        + lane_results["model_market"]
        + lane_results["startup_collections"]
        + lane_results["science"]
        + lane_results["developer_sentiment"]
    )
    
    # Re-reading corporate announcements
    if os.path.exists('data/corporate_announcements.json'):
        with open('data/corporate_announcements.json', 'r', encoding='utf-8') as f:
            ann = json.load(f)
            for a in ann.get('announcements', []):
                all_raw_items.append({
                    "headline": a['title'],
                    "summary": a.get('summary', ''),
                    "source": a['source'],
                    "url": a['url'],
                    "signal_type": "Verified",
                    "notes": "Official Corporate Announcement",
                    "published_at": a.get('published_at')
                })
    
    # Re-reading youtube queue
    if os.path.exists('data/new_videos_queue.json'):
        with open('data/new_videos_queue.json', 'r', encoding='utf-8') as f:
            yt = json.load(f)
            for v in yt:
                all_raw_items.append({
                    "headline": v['title'],
                    "source": v.get('source_account', 'YouTube'),
                    "url": v['url'],
                    "signal_type": "Deep Signal",
                    "notes": f"Video Drop - Tier: {v.get('priority', 'Standard')}",
                    "published_at": v.get('published_at')
                })
    
    # Weekly collection replaces the active queue through the protected queue seam.
    recent_items = filter_recent_items(all_raw_items, days=7)
    output_data, duplicate_count = replace_queue(recent_items)
    with open(PHASE1_LANE_HEALTH_PATH, 'w', encoding='utf-8') as f:
        json.dump({
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "lane_workers": lane_workers,
            "lanes": sorted(lane_health, key=lambda item: item["lane"]),
        }, f, indent=2, ensure_ascii=False)
    
    print(
        f"\nPhase 1 Complete. Pooled {len(all_raw_items)} raw items into "
        f"data/news_queue.json ({output_data['total_items']} active; "
        f"{duplicate_count} duplicate(s) merged)"
    )
    return 1 if x_collection and x_collection["status"] == "FAILED" else 0

if __name__ == "__main__":
    sys.exit(main())
