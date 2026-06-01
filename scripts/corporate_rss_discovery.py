import json
import os
import re
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin

import feedparser
import requests
from bs4 import BeautifulSoup


CONFIG_PATH = "config/corporate_blogs.json"
OUTPUT_PATH = "data/corporate_announcements.json"
HEADERS = {"User-Agent": "XDistributionCorporateDiscovery/2.0"}
REQUEST_TIMEOUT = 25
DATE_PATTERN = re.compile(
    r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|"
    r"Dec(?:ember)?)\s+\d{1,2},\s+\d{4}\b"
)


def parse_visible_date(text):
    match = DATE_PATTERN.search(text)
    if not match:
        return None
    for fmt in ("%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(match.group(0), fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return None


def get_page(session, url):
    return session.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, allow_redirects=True)


def clean_text(raw):
    return " ".join(BeautifulSoup(raw or "", "html.parser").get_text(" ", strip=True).split())


def verify_article(session, url):
    try:
        response = get_page(session, url)
    except requests.RequestException as exc:
        return None, {
            "url_verified": False,
            "url_status": "ERROR",
            "url_error": str(exc),
        }

    verification = {
        "url_verified": response.status_code < 400,
        "url_status": response.status_code,
        "resolved_url": response.url,
    }
    if response.status_code >= 400:
        return None, verification

    soup = BeautifulSoup(response.text, "html.parser")
    page_text = clean_text(soup.get_text(" ", strip=True))
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    return {
        "title": title,
        "text": page_text,
    }, verification


def verify_articles(urls):
    if not urls:
        return []
    with ThreadPoolExecutor(max_workers=min(12, len(urls))) as executor:
        return list(executor.map(lambda url: verify_article(requests, url), urls))


def make_item(blog, title, url, published_dt, summary, method, origin_url, verification):
    return {
        "title": title,
        "url": url,
        "published_at": published_dt.isoformat(),
        "source": blog["name"],
        "tier": blog["tier"],
        "summary": summary[:300],
        "discovery_method": method,
        "discovery_source": origin_url,
        **verification,
    }


def completeness_label(mode):
    labels = {
        "rss": "rss_only",
        "official_index": "official_index_visible_links",
        "official_sitemap": "official_sitemap_recent_lastmod",
        "hacker_news_algolia": "hn_algolia_query_window",
        "health_only": "monitored_elsewhere_or_health_only",
    }
    return labels.get(mode, "unknown")


def collect_rss(session, blog, cutoff):
    rss_url = blog["rss_url"]
    diagnostics = {"source": blog["name"], "mode": "rss", "endpoint": rss_url}
    try:
        response = get_page(session, rss_url)
        feed = feedparser.parse(response.content)
    except requests.RequestException as exc:
        diagnostics.update({"status": "ERROR", "error": str(exc), "items_added": 0})
        return [], diagnostics

    diagnostics.update(
        {
            "http_status": response.status_code,
            "feed_entries": len(feed.entries),
            "parse_warning": bool(feed.bozo),
            "completeness": completeness_label("rss"),
            "completeness_note": "Uses feed entries exposed by the configured RSS endpoint; does not prove an official site has no unlinked or non-RSS posts.",
        }
    )
    recent_entries = []
    for entry in feed.entries:
        published_struct = entry.get("published_parsed") or entry.get("updated_parsed")
        if not published_struct:
            continue
        published_dt = datetime(*published_struct[:6], tzinfo=timezone.utc)
        if published_dt < cutoff:
            continue
        recent_entries.append((entry, published_dt))

    items = []
    verifications = verify_articles([entry.link for entry, _ in recent_entries])
    for (entry, published_dt), (_, verification) in zip(recent_entries, verifications):
        items.append(
            make_item(
                blog,
                entry.title,
                entry.link,
                published_dt,
                clean_text(entry.get("summary", "")),
                "rss",
                rss_url,
                verification,
            )
        )
    diagnostics["status"] = "OK" if response.status_code < 400 else "FAILED"
    diagnostics["items_added"] = len(items)
    return items, diagnostics


def collect_hacker_news(session, blog, cutoff):
    endpoint = blog["algolia_url"]
    diagnostics = {
        "source": blog["name"],
        "mode": "hacker_news_algolia",
        "endpoint": endpoint,
        "completeness": completeness_label("hacker_news_algolia"),
        "completeness_note": "Uses HN Algolia over the configured tag/query window and point threshold; captures community traction, not primary company announcements.",
    }
    created_after = int(cutoff.timestamp())
    min_points = int(blog.get("min_points", 50))
    queries = blog.get("queries", ["AI"])
    seen = {}
    request_count = 0
    errors = []

    for query in queries:
        params = {
            "tags": blog.get("tags", "story"),
            "numericFilters": f"created_at_i>{created_after},points>{min_points}",
        }
        if query:
            params["query"] = query
        try:
            response = session.get(endpoint, params=params, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            request_count += 1
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            errors.append(f"{query}: {exc}")
            continue

        for hit in payload.get("hits", []):
            object_id = hit.get("objectID")
            if not object_id:
                continue
            created_i = hit.get("created_at_i")
            if not created_i:
                continue
            published_dt = datetime.fromtimestamp(created_i, tz=timezone.utc)
            story_url = f"https://news.ycombinator.com/item?id={object_id}"
            item_url = hit.get("url") or story_url
            title = hit.get("title") or hit.get("story_title") or "Untitled HN story"
            points = hit.get("points") or 0
            comments = hit.get("num_comments") or 0
            current = seen.get(object_id)
            if current and current["points"] >= points:
                continue
            seen[object_id] = {
                "title": title,
                "url": item_url,
                "published_at": published_dt.isoformat(),
                "source": blog["name"],
                "tier": blog["tier"],
                "summary": f"Hacker News story with {points} points and {comments} comments. HN discussion: {story_url}",
                "discovery_method": "hacker_news_algolia",
                "discovery_source": response.url,
                "url_verified": True,
                "url_status": 200,
                "resolved_url": item_url,
                "hn_object_id": object_id,
                "hn_discussion_url": story_url,
                "points": points,
                "num_comments": comments,
                "matched_query": query or blog.get("tags", "front_page"),
            }

    items = sorted(seen.values(), key=lambda item: (item["points"], item["published_at"]), reverse=True)
    diagnostics.update(
        {
            "status": "OK" if not errors else "PARTIAL",
            "queries": queries,
            "request_count": request_count,
            "min_points": min_points,
            "lookback_hours": blog.get("lookback_hours", 48),
            "items_added": len(items),
        }
    )
    if errors:
        diagnostics["errors"] = errors
    return items, diagnostics


def index_urls(session, blog):
    response = get_page(session, blog["url"])
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    prefix = blog["article_prefix"].rstrip("/") + "/"
    urls = []
    for anchor in soup.find_all("a", href=True):
        url = urljoin(response.url, anchor["href"]).split("#", 1)[0]
        if url.startswith(prefix) and url.rstrip("/") != blog["url"].rstrip("/") and url not in urls:
            urls.append(url)
    return urls, response.status_code


def parse_sitemap_datetime(raw):
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def sitemap_urls(session, blog, cutoff):
    sitemap_url = blog["sitemap_url"]
    response = get_page(session, sitemap_url)
    response.raise_for_status()
    root = ET.fromstring(response.content)
    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    prefix = blog["article_prefix"].rstrip("/") + "/"
    urls = []
    source_url_count = 0
    candidate_cutoff = cutoff - timedelta(days=1)
    visited = set()

    def walk(current_url, depth=0):
        nonlocal source_url_count
        if depth > 2 or current_url in visited:
            return
        visited.add(current_url)
        current_response = response if current_url == sitemap_url else get_page(session, current_url)
        current_response.raise_for_status()
        current_root = ET.fromstring(current_response.content)

        sitemap_entries = current_root.findall("sm:sitemap", namespace)
        if sitemap_entries:
            for entry in sitemap_entries[:50]:
                child_url = entry.findtext("sm:loc", default="", namespaces=namespace)
                lastmod = parse_sitemap_datetime(entry.findtext("sm:lastmod", default="", namespaces=namespace))
                if not child_url:
                    continue
                if lastmod and lastmod < candidate_cutoff:
                    continue
                walk(child_url, depth + 1)
            return

        for entry in current_root.findall("sm:url", namespace):
            url = entry.findtext("sm:loc", default="", namespaces=namespace)
            if url.startswith(prefix):
                source_url_count += 1
                lastmod = parse_sitemap_datetime(entry.findtext("sm:lastmod", default="", namespaces=namespace))
                if not lastmod or lastmod >= candidate_cutoff:
                    urls.append(url)

    walk(sitemap_url)
    return urls, response.status_code, source_url_count


def collect_official_pages(session, blog, cutoff):
    mode = blog["discovery_type"]
    diagnostics = {"source": blog["name"], "mode": mode, "endpoint": blog["url"]}
    try:
        if mode == "official_sitemap":
            urls, status_code, source_url_count = sitemap_urls(session, blog, cutoff)
            diagnostics["sitemap_url"] = blog["sitemap_url"]
            diagnostics["sitemap_article_urls"] = source_url_count
            diagnostics["completeness"] = completeness_label(mode)
            diagnostics["completeness_note"] = "Uses official sitemap URLs under the configured article prefix, narrowed by recent lastmod before opening each candidate article."
        else:
            urls, status_code = index_urls(session, blog)
            diagnostics["completeness"] = completeness_label(mode)
            diagnostics["completeness_note"] = "Uses currently visible official index links under the configured article prefix; cannot see hidden API-only or unlinked posts."
    except (requests.RequestException, ET.ParseError) as exc:
        diagnostics.update({"status": "ERROR", "error": str(exc), "items_added": 0})
        return [], diagnostics

    items = []
    undated = 0
    inaccessible = 0
    verified_articles = verify_articles(urls)
    for url, (article, verification) in zip(urls, verified_articles):
        if not verification["url_verified"]:
            inaccessible += 1
            continue
        published_dt = parse_visible_date(article["text"])
        if not published_dt:
            undated += 1
            continue
        if published_dt < cutoff:
            continue
        title = article["title"].split(" | ", 1)[0].strip()
        items.append(
            make_item(
                blog,
                title,
                url,
                published_dt,
                article["text"],
                mode,
                blog.get("sitemap_url", blog["url"]),
                verification,
            )
        )

    diagnostics.update(
        {
            "status": "OK",
            "http_status": status_code,
            "candidate_urls": len(urls),
            "undated_candidates": undated,
            "inaccessible_candidates": inaccessible,
            "items_added": len(items),
        }
    )
    return items, diagnostics


def collect_health_only(session, blog):
    fallback_sources = blog.get("fallback_sources", [])
    status = "MONITORED_ELSEWHERE" if fallback_sources else "HEALTH_ONLY"
    diagnostics = {
        "source": blog["name"],
        "mode": "health_only",
        "endpoint": blog["url"],
        "items_added": 0,
        "status": status,
        "completeness": completeness_label("health_only"),
        "completeness_note": "Source is intentionally monitored without a dated primary feed; related coverage is expected through configured fallback lanes when listed.",
        "note": blog.get("note", "Source is monitored but not ingested."),
        "fallback_sources": fallback_sources,
    }
    try:
        response = get_page(session, blog["url"])
        diagnostics["http_status"] = response.status_code
    except requests.RequestException as exc:
        diagnostics["error"] = str(exc)
    return [], diagnostics


def parse_corporate_feeds():
    if not os.path.exists(CONFIG_PATH):
        print(f"Config not found: {CONFIG_PATH}")
        return

    with open(CONFIG_PATH, "r", encoding="utf-8") as file_handle:
        config = json.load(file_handle)

    default_cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    all_announcements = []
    diagnostics = []
    session = requests.Session()

    for blog in config["blogs"]:
        mode = blog.get("discovery_type", "rss")
        lookback_hours = blog.get("lookback_hours")
        cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours) if lookback_hours else default_cutoff
        print(f"Parsing {blog['name']} via {mode}...")
        if mode == "rss":
            items, health = collect_rss(session, blog, cutoff)
        elif mode == "health_only":
            items, health = collect_health_only(session, blog)
        elif mode == "hacker_news_algolia":
            items, health = collect_hacker_news(session, blog, cutoff)
        else:
            items, health = collect_official_pages(session, blog, cutoff)
        all_announcements.extend(items)
        diagnostics.append(health)
        print(f"  -> {health['status']}; {health.get('items_added', 0)} items")

    deduplicated = {}
    for item in all_announcements:
        current = deduplicated.get(item["url"])
        if current is None or item["published_at"] > current["published_at"]:
            deduplicated[item["url"]] = item
    all_announcements = sorted(
        deduplicated.values(), key=lambda item: item["published_at"], reverse=True
    )

    with open(OUTPUT_PATH, "w", encoding="utf-8") as file_handle:
        json.dump(
            {
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "cutoff": cutoff.isoformat(),
                "announcements": all_announcements,
                "source_health": diagnostics,
            },
            file_handle,
            indent=2,
            ensure_ascii=False,
        )

    verified_count = sum(1 for item in all_announcements if item["url_verified"])
    print(
        f"Done. Saved {len(all_announcements)} announcements "
        f"({verified_count} URL-verified) to {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    parse_corporate_feeds()
