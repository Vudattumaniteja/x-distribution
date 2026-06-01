import json
import os
import re
import time
from datetime import datetime, timezone
from urllib.parse import quote_plus

import requests


CONFIG_PATH = "config/community_sources.json"
OUTPUT_PATH = "data/reddit_raw_standalone.json"
HEADERS = {
    "User-Agent": "XDistributionCommunityDiscovery/2.0 "
    "(developer discussion monitor; contact: local)"
}
REQUEST_TIMEOUT = 20


DEFAULT_CONFIG = {
    "reddit": {
        "lookback": "day",
        "limit_per_listing": 25,
        "comment_limit": 8,
        "subreddits": [
            {"name": "LocalLLaMA", "role": "local_model_practitioners", "queries": ["llm", "model"]},
            {"name": "MachineLearning", "role": "research_practitioners", "queries": ["paper", "benchmark"]},
            {"name": "OpenAI", "role": "openai_users", "queries": ["model", "api"]},
            {"name": "ClaudeAI", "role": "claude_users", "queries": ["claude code", "mcp"]},
            {"name": "programming", "role": "general_developers", "queries": ["AI", "LLM"]},
        ],
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


def get_json(url):
    response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def clean_text(text):
    return " ".join((text or "").split())


def reddit_post_url(post):
    return f"https://www.reddit.com{post['permalink']}"


def normalize_post(post, subreddit_name, subreddit_role, surface):
    return {
        "id": post["id"],
        "title": clean_text(post.get("title")),
        "url": reddit_post_url(post),
        "external_url": post.get("url_overridden_by_dest") or post.get("url"),
        "author": post.get("author"),
        "score": post.get("score", 0),
        "upvote_ratio": post.get("upvote_ratio"),
        "num_comments": post.get("num_comments", 0),
        "created_utc": post.get("created_utc"),
        "published_at": datetime.fromtimestamp(post.get("created_utc", 0), tz=timezone.utc).isoformat(),
        "subreddit": subreddit_name,
        "subreddit_role": subreddit_role,
        "surface": surface,
        "text": clean_text(post.get("selftext", ""))[:1200],
    }


def fetch_listing(subreddit, role, surface, url):
    try:
        payload = get_json(url)
    except Exception as exc:
        print(f"Error fetching r/{subreddit} {surface}: {exc}")
        return []

    posts = []
    for child in payload.get("data", {}).get("children", []):
        post = child.get("data", {})
        if post.get("stickied") or not post.get("id"):
            continue
        posts.append(normalize_post(post, subreddit, role, surface))
    return posts


def fetch_comments(permalink, limit):
    if limit <= 0:
        return []
    url = f"https://www.reddit.com{permalink}.json?sort=top&limit={limit}"
    try:
        payload = get_json(url)
    except Exception:
        return []
    if not isinstance(payload, list) or len(payload) < 2:
        return []

    comments = []
    for child in payload[1].get("data", {}).get("children", []):
        data = child.get("data", {})
        body = clean_text(data.get("body", ""))
        if not body or body in {"[deleted]", "[removed]"}:
            continue
        comments.append(
            {
                "author": data.get("author"),
                "score": data.get("score", 0),
                "body": body[:700],
                "url": f"https://www.reddit.com{data.get('permalink', permalink)}",
            }
        )
        if len(comments) >= limit:
            break
    return comments


def discussion_score(post, keywords):
    title_text = f"{post.get('title', '')} {post.get('text', '')}".lower()
    keyword_hits = [keyword for keyword in keywords if keyword.lower() in title_text]
    return post.get("score", 0) + (post.get("num_comments", 0) * 2) + (len(keyword_hits) * 25)


def to_discovery(post, keywords):
    top_comments = post.get("top_comments", [])
    top_comment = top_comments[0]["body"] if top_comments else ""
    keyword_hits = [
        keyword for keyword in keywords
        if keyword.lower() in f"{post.get('title', '')} {post.get('text', '')} {top_comment}".lower()
    ]
    summary_parts = [
        f"Reddit r/{post['subreddit']} discussion with {post['score']} score and {post['num_comments']} comments.",
    ]
    if keyword_hits:
        summary_parts.append(f"Matched practitioner terms: {', '.join(keyword_hits[:8])}.")
    if top_comment:
        summary_parts.append(f"Top comment: {top_comment[:300]}")

    return {
        "id": f"reddit_{post['id']}",
        "title": post["title"],
        "url": post["url"],
        "source": f"Reddit r/{post['subreddit']}",
        "published_at": post.get("published_at"),
        "summary": " ".join(summary_parts),
        "score": post.get("score", 0),
        "num_comments": post.get("num_comments", 0),
        "subreddit_role": post.get("subreddit_role"),
        "surface": post.get("surface"),
        "discussion_signal": "real_developer_talk",
        "top_comments": top_comments,
    }


def has_topic_signal(post, topic_keywords):
    haystack = " ".join(
        [
            post.get("title", ""),
            post.get("text", ""),
            " ".join(comment.get("body", "") for comment in post.get("top_comments", [])),
        ]
    ).lower()
    return any(keyword_in_text(keyword, haystack) for keyword in topic_keywords)


def keyword_in_text(keyword, text):
    keyword = keyword.lower()
    if len(keyword) <= 3 and keyword.isalnum():
        return re.search(rf"\b{re.escape(keyword)}\b", text) is not None
    return keyword in text


def collect_reddit_posts(config):
    reddit_config = config.get("reddit", {})
    lookback = reddit_config.get("lookback", "day")
    limit = int(reddit_config.get("limit_per_listing", 25))
    comment_limit = int(reddit_config.get("comment_limit", 8))
    keywords = config.get("discussion_keywords", [])
    seen = {}

    for subreddit in reddit_config.get("subreddits", []):
        name = subreddit["name"]
        role = subreddit.get("role", "community")
        print(f"Scraping r/{name}...")

        listing_urls = [
            (
                "top_day",
                f"https://www.reddit.com/r/{name}/top.json?t={lookback}&limit={limit}",
            ),
            (
                "hot",
                f"https://www.reddit.com/r/{name}/hot.json?limit={limit}",
            ),
        ]
        for query in subreddit.get("queries", [])[:5]:
            listing_urls.append(
                (
                    f"search:{query}",
                    f"https://www.reddit.com/r/{name}/search.json"
                    f"?q={quote_plus(query)}&restrict_sr=1&sort=new&t=week&limit={max(10, limit // 2)}",
                )
            )

        for surface, url in listing_urls:
            for post in fetch_listing(name, role, surface, url):
                existing = seen.get(post["id"])
                if existing and discussion_score(existing, keywords) >= discussion_score(post, keywords):
                    continue
                seen[post["id"]] = post
            time.sleep(1.2)

    ranked_posts = sorted(seen.values(), key=lambda item: discussion_score(item, keywords), reverse=True)
    for post in ranked_posts[:75]:
        permalink = post["url"].replace("https://www.reddit.com", "")
        post["top_comments"] = fetch_comments(permalink, comment_limit)
        post["discussion_score"] = discussion_score(post, keywords)
        time.sleep(0.8)

    return ranked_posts


def load_existing_output():
    if not os.path.exists(OUTPUT_PATH):
        return None
    try:
        with open(OUTPUT_PATH, "r", encoding="utf-8") as file_handle:
            payload = json.load(file_handle)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    posts = payload.get("posts", [])
    discoveries = payload.get("new_discoveries", [])
    if posts or discoveries:
        return payload
    return None


def main():
    config = load_config()
    existing_output = load_existing_output()
    posts = collect_reddit_posts(config)
    topic_keywords = config.get("topic_keywords", DEFAULT_CONFIG["topic_keywords"])
    discoveries = [
        to_discovery(post, config.get("discussion_keywords", []))
        for post in posts
        if has_topic_signal(post, topic_keywords)
    ]

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    if not posts and not discoveries and existing_output:
        existing_output["last_attempted"] = datetime.now(timezone.utc).isoformat()
        existing_output["collection_status"] = "live_failed_preserved_previous"
        existing_output["last_error"] = "Reddit live collection returned zero posts/discoveries; preserved previous non-empty output."
        with open(OUTPUT_PATH, "w", encoding="utf-8") as file_handle:
            json.dump(existing_output, file_handle, indent=2, ensure_ascii=False)
        print(
            "Done. Reddit live collection returned 0 items; preserved previous "
            f"{len(existing_output.get('posts', []))} posts and "
            f"{len(existing_output.get('new_discoveries', []))} discoveries in {OUTPUT_PATH}"
        )
        return

    with open(OUTPUT_PATH, "w", encoding="utf-8") as file_handle:
        json.dump(
            {
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "collection_status": "live_ok",
                "posts": posts,
                "new_discoveries": discoveries,
            },
            file_handle,
            indent=2,
            ensure_ascii=False,
        )

    print(f"Done. Saved {len(posts)} posts and {len(discoveries)} discoveries to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
