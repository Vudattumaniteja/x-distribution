"""Collect bio, science, and deep-tech breakthrough signals."""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

import feedparser
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "science_sources.json"
RAW_OUTPUT_PATH = ROOT / "data" / "science_breakthrough_raw.json"
SIGNALS_OUTPUT_PATH = ROOT / "data" / "science_breakthrough_signals.json"
HEADERS = {"User-Agent": "XDistributionScienceIntel/1.0 local-research contact: local"}


def load_config() -> dict[str, Any]:
    with CONFIG_PATH.open("r", encoding="utf-8") as file_handle:
        return json.load(file_handle)


def clean_text(raw: str | None) -> str:
    return re.sub(r"\s+", " ", BeautifulSoup(raw or "", "html.parser").get_text(" ", strip=True)).strip()


def parse_feed_datetime(entry: Any) -> datetime | None:
    parsed_struct = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed_struct:
        return datetime(*parsed_struct[:6], tzinfo=timezone.utc)
    for field in ["published", "updated", "created"]:
        value = entry.get(field)
        if not value:
            continue
        try:
            parsed = parsedate_to_datetime(value)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except (TypeError, ValueError):
            continue
    return None


def hits(text: str, keywords: list[str]) -> list[str]:
    lower = text.lower()
    return [keyword for keyword in keywords if keyword.lower() in lower]


def make_signal(source: dict[str, Any], title: str, url: str, published_at: str | None, summary: str | None, config: dict[str, Any]) -> dict[str, Any] | None:
    title = title or "Untitled science signal"
    summary = summary or ""
    haystack = " ".join([title, summary, source.get("name", ""), source.get("source_type", "")])
    science_hits = hits(haystack, config.get("science_keywords", []))
    breakthrough_hits = hits(haystack, config.get("breakthrough_keywords", []))
    score = len(science_hits) * 2 + len(breakthrough_hits)
    if source.get("tier") == "tier_1":
        score += 2
    elif source.get("tier") == "tier_2":
        score += 1
    if score < int(config.get("min_relevance_score", 4)):
        return None
    return {
        "id": "science_" + re.sub(r"[^a-zA-Z0-9]+", "_", (url or title).lower()).strip("_")[:140],
        "title": title,
        "url": url,
        "source": source.get("name"),
        "source_region": source.get("source_region", "unknown"),
        "source_type": source.get("source_type", "science_news"),
        "tier": source.get("tier", "tier_3"),
        "published_at": published_at,
        "summary": summary[:900],
        "signal_type": "Science/Deep-Tech Breakthrough",
        "science_keyword_hits": science_hits[:12],
        "breakthrough_keyword_hits": breakthrough_hits[:12],
        "relevance_score": min(score, 10),
        "discovery_method": "rss",
        "confidence": "public_source_signal",
    }


def collect_source(session: requests.Session, source: dict[str, Any], config: dict[str, Any], cutoff: datetime) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    diagnostics = {"source": source["name"], "mode": "rss", "endpoint": source["rss_url"]}
    try:
        response = session.get(source["rss_url"], headers=HEADERS, timeout=int(config.get("request_timeout_seconds", 25)))
        feed = feedparser.parse(response.content)
    except Exception as exc:
        diagnostics.update({"status": "ERROR", "error": str(exc), "items_seen": 0, "items_added": 0})
        return [], diagnostics
    items = []
    for entry in feed.entries[: int(config.get("max_items_per_source", 40))]:
        published_dt = parse_feed_datetime(entry)
        if published_dt and published_dt < cutoff:
            continue
        signal = make_signal(
            source,
            clean_text(entry.get("title", "Untitled")),
            entry.get("link", source.get("url", "")),
            published_dt.isoformat() if published_dt else None,
            clean_text(entry.get("summary", "") or entry.get("description", "")),
            config,
        )
        if signal:
            items.append(signal)
    diagnostics.update(
        {
            "status": "OK" if response.status_code < 400 else "FAILED",
            "http_status": response.status_code,
            "feed_entries": len(feed.entries),
            "items_seen": min(len(feed.entries), int(config.get("max_items_per_source", 40))),
            "items_added": len(items),
            "parse_warning": bool(feed.bozo),
        }
    )
    return items, diagnostics


def collect_html_source(session: requests.Session, source: dict[str, Any], config: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    diagnostics = {"source": source["name"], "mode": "html_index", "endpoint": source["url"]}
    try:
        response = session.get(source["url"], headers=HEADERS, timeout=int(config.get("request_timeout_seconds", 25)))
        if response.status_code >= 400:
            raise requests.HTTPError(f"HTTP {response.status_code} for {source['url']}")
        soup = BeautifulSoup(response.text, "html.parser")
    except Exception as exc:
        if source.get("search_fallback_query"):
            items, fallback_health = collect_search_fallback(session, source, config)
            diagnostics.update({
                "status": "FALLBACK",
                "error": str(exc),
                "items_seen": fallback_health.get("items_seen", 0),
                "items_added": len(items),
                "fallback": fallback_health,
            })
            return items, diagnostics
        diagnostics.update({"status": "ERROR", "error": str(exc), "items_seen": 0, "items_added": 0})
        return [], diagnostics
    candidates = []
    for anchor in soup.find_all("a", href=True):
        title = clean_text(anchor.get_text(" ", strip=True))
        href = urljoin(response.url, anchor["href"]).split("#", 1)[0]
        if len(title) < 8 or href == response.url:
            continue
        context = clean_text(anchor.parent.get_text(" ", strip=True) if anchor.parent else title)
        candidates.append((title, href, context))
    seen = set()
    items = []
    for title, href, context in candidates[: int(config.get("max_items_per_source", 40)) * 4]:
        key = href or title
        if key in seen:
            continue
        seen.add(key)
        signal = make_signal(source, title, href, None, context, config)
        if signal:
            signal["discovery_method"] = "html_index"
            items.append(signal)
        if len(items) >= int(config.get("max_items_per_source", 40)):
            break
    diagnostics.update(
        {
            "status": "OK" if response.status_code < 400 else "FAILED",
            "http_status": response.status_code,
            "candidate_links": len(candidates),
            "items_seen": len(seen),
            "items_added": len(items),
        }
    )
    return items, diagnostics


def collect_search_fallback(session: requests.Session, source: dict[str, Any], config: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    query = source["search_fallback_query"]
    endpoint = "https://duckduckgo.com/html/?q=" + quote(query)
    diagnostics = {"source": source["name"], "mode": "search_fallback", "endpoint": endpoint}
    try:
        response = session.get(endpoint, headers=HEADERS, timeout=int(config.get("request_timeout_seconds", 25)))
        soup = BeautifulSoup(response.text, "html.parser")
    except Exception as exc:
        diagnostics.update({"status": "ERROR", "error": str(exc), "items_seen": 0, "items_added": 0})
        return [], diagnostics
    items = []
    for anchor in soup.select("a.result__a")[: int(config.get("max_items_per_source", 40))]:
        title = clean_text(anchor.get_text(" ", strip=True))
        href = anchor.get("href") or source["url"]
        signal = make_signal(source, title, href, None, title, config)
        if signal:
            signal["discovery_method"] = "search_fallback"
            signal["confidence"] = "search_index_fallback"
            items.append(signal)
    diagnostics.update({"status": "OK" if response.status_code < 400 else "FAILED", "http_status": response.status_code, "items_seen": len(items), "items_added": len(items)})
    return items, diagnostics


def dedupe(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged = {}
    for item in items:
        key = item.get("url") or item.get("title")
        if key and key not in merged:
            merged[key] = item
    return sorted(merged.values(), key=lambda item: (item.get("published_at") or "", item.get("relevance_score", 0)), reverse=True)


def write_outputs(items: list[dict[str, Any]], diagnostics: list[dict[str, Any]], cutoff: datetime) -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    RAW_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {"last_updated": timestamp, "cutoff": cutoff.isoformat(), "total_items": len(items), "items": items, "source_health": diagnostics}
    with RAW_OUTPUT_PATH.open("w", encoding="utf-8") as file_handle:
        json.dump(payload, file_handle, indent=2, ensure_ascii=False)
    with SIGNALS_OUTPUT_PATH.open("w", encoding="utf-8") as file_handle:
        json.dump({"last_updated": timestamp, "signals": items, "source_health": diagnostics}, file_handle, indent=2, ensure_ascii=False)


def main() -> int:
    config = load_config()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=int(config.get("lookback_hours", 168)))
    session = requests.Session()
    items: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    for source in config.get("rss_sources", []):
        print(f"Scanning science source: {source['name']}")
        source_items, health = collect_source(session, source, config, cutoff)
        items.extend(source_items)
        diagnostics.append(health)
        print(f"  -> {health['status']}; {health.get('items_added', 0)} signals")
        time.sleep(0.35)
    for source in config.get("html_sources", []):
        print(f"Scanning science source: {source['name']}")
        source_items, health = collect_html_source(session, source, config)
        items.extend(source_items)
        diagnostics.append(health)
        print(f"  -> {health['status']}; {health.get('items_added', 0)} signals")
        time.sleep(0.35)
    items = dedupe(items)
    write_outputs(items, diagnostics, cutoff)
    print(f"Done. Saved {len(items)} science/deep-tech signals.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
