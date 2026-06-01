import json
import os
import re
import time
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup


CONFIG_PATH = "config/community_sources.json"
OUTPUT_PATH = "data/hn_raw_standalone.json"
ALGOLIA_SEARCH_URL = "https://hn.algolia.com/api/v1/search_by_date"
ALGOLIA_ITEM_URL = "https://hn.algolia.com/api/v1/items/{object_id}"
HEADERS = {"User-Agent": "XDistributionCommunityDiscovery/2.0"}
REQUEST_TIMEOUT = 12


DEFAULT_CONFIG = {
    "hacker_news": {
        "lookback_hours": 72,
        "min_points": 20,
        "comment_limit": 10,
        "max_comment_fetch_items": 40,
        "queries": ["LLM", "Claude Code", "Codex", "Cursor", "MCP", "agent", "inference"],
    },
    "discussion_keywords": ["bug", "latency", "cost", "production", "local", "api", "agent"],
    "topic_keywords": ["ai", "llm", "openai", "anthropic", "claude", "codex", "cursor"],
}


def load_config():
    if not os.path.exists(CONFIG_PATH):
        return DEFAULT_CONFIG
    with open(CONFIG_PATH, "r", encoding="utf-8") as file_handle:
        loaded = json.load(file_handle)
    merged = DEFAULT_CONFIG.copy()
    merged.update(loaded)
    return merged


def clean_text(raw):
    text = BeautifulSoup(raw or "", "html.parser").get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()


def fetch_json(url, params=None):
    response = requests.get(url, params=params, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json(), response.url


def flatten_comments(children, limit, collected=None):
    if collected is None:
        collected = []
    for child in children or []:
        text = clean_text(child.get("text", ""))
        if text:
            collected.append(
                {
                    "id": child.get("id"),
                    "author": child.get("author"),
                    "created_at": child.get("created_at"),
                    "text": text[:900],
                }
            )
            if len(collected) >= limit:
                return collected
        flatten_comments(child.get("children", []), limit, collected)
        if len(collected) >= limit:
            return collected
    return collected


def fetch_hn_comments(object_id, comment_limit):
    if comment_limit <= 0:
        return []
    try:
        item, _ = fetch_json(ALGOLIA_ITEM_URL.format(object_id=object_id))
    except Exception:
        return []
    return flatten_comments(item.get("children", []), comment_limit)


def summarize_discussion(hit, comments, keywords):
    story_url = f"https://news.ycombinator.com/item?id={hit['objectID']}"
    matched_keywords = [
        keyword for keyword in keywords
        if keyword.lower() in f"{hit.get('title', '')} {' '.join(c['text'] for c in comments)}".lower()
    ]
    summary_parts = [
        f"Hacker News discussion with {hit.get('points', 0)} points and {hit.get('num_comments', 0)} comments.",
        f"HN discussion: {story_url}",
    ]
    if matched_keywords:
        summary_parts.append(f"Matched practitioner terms: {', '.join(matched_keywords[:8])}.")
    if comments:
        summary_parts.append(f"Representative comment: {comments[0]['text'][:300]}")
    return " ".join(summary_parts)


def has_topic_signal(hit, comments, topic_keywords):
    # Comments enrich a story, but they should not qualify an unrelated HN item.
    # Otherwise broad terms can pull in generic API/business stories where only a
    # reply mentions AI.
    haystack = " ".join([hit.get("title") or "", hit.get("url") or ""]).lower()
    return any(keyword_in_text(keyword, haystack) for keyword in topic_keywords)


def keyword_in_text(keyword, text):
    keyword = keyword.lower()
    if len(keyword) <= 3 and keyword.isalnum():
        return re.search(rf"\b{re.escape(keyword)}\b", text) is not None
    return keyword in text


def fetch_hn_discussions(config):
    hn_config = config.get("hacker_news", {})
    keywords = config.get("discussion_keywords", [])
    topic_keywords = config.get("topic_keywords", DEFAULT_CONFIG["topic_keywords"])
    created_after = int(time.time()) - (int(hn_config.get("lookback_hours", 72)) * 3600)
    min_points = int(hn_config.get("min_points", 20))
    comment_limit = int(hn_config.get("comment_limit", 10))
    max_comment_fetch_items = int(hn_config.get("max_comment_fetch_items", 40))
    seen = {}
    diagnostics = []

    for query in hn_config.get("queries", []):
        print(f"Scanning HN query: {query}")
        params = {
            "query": query,
            "tags": "story",
            "numericFilters": f"created_at_i>{created_after},points>{min_points}",
            "hitsPerPage": 50,
        }
        try:
            payload, requested_url = fetch_json(ALGOLIA_SEARCH_URL, params=params)
        except Exception as exc:
            diagnostics.append({"query": query, "status": "ERROR", "error": str(exc)})
            continue

        hits = payload.get("hits", [])
        diagnostics.append(
            {
                "query": query,
                "status": "OK",
                "hits": len(hits),
                "requested_url": requested_url,
            }
        )
        for hit in hits:
            object_id = hit.get("objectID")
            if not object_id:
                continue
            current = seen.get(object_id)
            points = hit.get("points") or 0
            if current and current.get("points", 0) >= points:
                continue
            seen[object_id] = hit | {"matched_query": query}
        time.sleep(0.8)

    discoveries = []
    for hit in sorted(seen.values(), key=lambda item: item.get("points") or 0, reverse=True)[:max_comment_fetch_items]:
        object_id = hit["objectID"]
        comments = fetch_hn_comments(object_id, comment_limit)
        if not has_topic_signal(hit, comments, topic_keywords):
            continue
        story_url = f"https://news.ycombinator.com/item?id={object_id}"
        item_url = hit.get("url") or story_url
        discoveries.append(
            {
                "id": f"hn_{object_id}",
                "title": hit.get("title") or hit.get("story_title") or "Untitled HN story",
                "url": item_url,
                "source": "Hacker News",
                "points": hit.get("points", 0),
                "num_comments": hit.get("num_comments", 0),
                "published_at": hit.get("created_at"),
                "summary": summarize_discussion(hit, comments, keywords),
                "hn_object_id": object_id,
                "hn_discussion_url": story_url,
                "matched_query": hit.get("matched_query"),
                "discussion_signal": "real_developer_talk",
                "top_comments": comments,
            }
        )
        time.sleep(0.5)

    return discoveries, diagnostics


def main():
    config = load_config()
    print("Scanning Hacker News for developer AI/model discussions...")
    discoveries, diagnostics = fetch_hn_discussions(config)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as file_handle:
        json.dump(
            {
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "new_discoveries": discoveries,
                "source_health": diagnostics,
            },
            file_handle,
            indent=2,
            ensure_ascii=False,
        )

    print(f"Done. Saved {len(discoveries)} HN discoveries to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
