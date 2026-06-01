"""Collect startup signals from collection-style sources.

Each source gets an explicit health record. If API access requires credentials,
the collector falls back to configured public pages instead of leaving the lane
incomplete.
"""

from __future__ import annotations

import json
import os
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import feedparser
import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "startup_collection_sources.json"
RAW_OUTPUT_PATH = ROOT / "data" / "startup_collections_raw.json"
SIGNALS_OUTPUT_PATH = ROOT / "data" / "startup_collections_signals.json"
HEADERS = {"User-Agent": "XDistributionStartupCollections/1.0 local-research contact: local"}


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


def amount_to_usd(text: str) -> int | None:
    match = re.search(r"\$\s?(\d+(?:\.\d+)?)\s?(k|m|million|b|billion)?", text, flags=re.I)
    if not match:
        return None
    value = float(match.group(1))
    unit = (match.group(2) or "").lower()
    multiplier = 1
    if unit in {"k"}:
        multiplier = 1_000
    elif unit in {"m", "million"}:
        multiplier = 1_000_000
    elif unit in {"b", "billion"}:
        multiplier = 1_000_000_000
    return int(value * multiplier)


def keyword_hits(text: str, keywords: list[str]) -> list[str]:
    lower = text.lower()
    return [keyword for keyword in keywords if keyword.lower() in lower]


def classify_item(text: str, config: dict[str, Any]) -> tuple[list[str], list[str], int | None]:
    topic_hits = keyword_hits(text, config.get("topic_keywords", []))
    funding_hits = keyword_hits(text, config.get("funding_keywords", []))
    amount = amount_to_usd(text)
    return topic_hits, funding_hits, amount


def make_signal(
    source: dict[str, Any],
    title: str,
    url: str,
    summary: str,
    published_at: str | None,
    config: dict[str, Any],
    method: str,
) -> dict[str, Any] | None:
    haystack = " ".join([title, summary, source.get("name", ""), source.get("source_type", ""), url])
    topic_hits, funding_hits, amount = classify_item(haystack, config)
    minimum = int(config.get("minimum_amount_usd", 1_000_000))
    is_relevant = bool(topic_hits) or bool(funding_hits) or (amount is not None and amount >= minimum)
    if not is_relevant:
        return None
    signal_type = "Startup Collection Signal"
    if amount and amount >= minimum:
        signal_type = "Funded Startup Signal"
    elif "revenue" in source.get("source_type", ""):
        signal_type = "Revenue Startup Signal"
    elif funding_hits:
        signal_type = "Startup Funding Signal"
    return {
        "id": "startup_collection_" + re.sub(r"[^a-zA-Z0-9]+", "_", (url or title).lower()).strip("_")[:140],
        "title": title[:240] or "Startup collection item",
        "url": url,
        "source": source.get("name"),
        "source_region": source.get("source_region", "unknown"),
        "source_type": source.get("source_type", "startup_collection"),
        "tier": source.get("tier", "collection_tier_3"),
        "published_at": published_at,
        "summary": summary[:900],
        "signal_type": signal_type,
        "topic_keyword_hits": topic_hits[:12],
        "funding_keyword_hits": funding_hits[:12],
        "detected_amount_usd": amount,
        "minimum_amount_usd": minimum,
        "discovery_method": method,
        "confidence": "public_source_signal",
    }


def collect_rss(session: requests.Session, source: dict[str, Any], config: dict[str, Any], cutoff: datetime) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    diagnostics = {"source": source["name"], "mode": "rss", "endpoint": source.get("rss_url")}
    try:
        response = session.get(source["rss_url"], headers=HEADERS, timeout=int(config.get("request_timeout_seconds", 25)))
        feed = feedparser.parse(response.content)
    except Exception as exc:
        diagnostics.update({"status": "ERROR", "error": str(exc), "items_added": 0, "items_seen": 0})
        return [], diagnostics
    items = []
    for entry in feed.entries[: int(config.get("max_items_per_source", 40))]:
        published_dt = parse_feed_datetime(entry)
        if published_dt and published_dt < cutoff:
            continue
        signal = make_signal(
            source,
            clean_text(entry.get("title", "")),
            entry.get("link", source.get("url", "")),
            clean_text(entry.get("summary", "") or entry.get("description", "")),
            published_dt.isoformat() if published_dt else None,
            config,
            "rss",
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


def collect_html_url(session: requests.Session, source: dict[str, Any], config: dict[str, Any], url: str, mode_label: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    diagnostics = {"source": source["name"], "mode": mode_label, "endpoint": url}
    try:
        response = session.get(url, headers=HEADERS, timeout=int(config.get("request_timeout_seconds", 25)))
        soup = BeautifulSoup(response.text, "html.parser")
    except Exception as exc:
        diagnostics.update({"status": "ERROR", "error": str(exc), "items_added": 0, "items_seen": 0})
        return [], diagnostics

    candidates: list[tuple[str, str, str]] = []
    for anchor in soup.find_all("a", href=True):
        text = clean_text(anchor.get_text(" ", strip=True))
        href = urljoin(response.url, anchor["href"]).split("#", 1)[0]
        if len(text) < 8 or href == response.url:
            continue
        parent_text = clean_text(anchor.parent.get_text(" ", strip=True) if anchor.parent else text)
        candidates.append((text, href, parent_text))

    seen = set()
    items = []
    for title, href, summary in candidates[: int(config.get("max_items_per_source", 40)) * 4]:
        key = href or title
        if key in seen:
            continue
        seen.add(key)
        signal = make_signal(source, title, href, summary, None, config, mode_label)
        if signal:
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


def collect_sitemap(session: requests.Session, source: dict[str, Any], config: dict[str, Any], cutoff: datetime) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    sitemap_url = source["sitemap_url"]
    diagnostics = {"source": source["name"], "mode": "sitemap", "endpoint": sitemap_url}
    try:
        response = session.get(sitemap_url, headers=HEADERS, timeout=int(config.get("request_timeout_seconds", 25)))
        root = ET.fromstring(response.content)
    except Exception as exc:
        diagnostics.update({"status": "ERROR", "error": str(exc), "items_added": 0, "items_seen": 0})
        return [], diagnostics

    ns = {
        "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
        "news": "http://www.google.com/schemas/sitemap-news/0.9",
    }
    include_terms = [term.lower() for term in source.get("include_url_terms", [])]
    candidates = []
    for entry in root.findall("sm:url", ns):
        loc = entry.findtext("sm:loc", namespaces=ns) or ""
        if include_terms and not any(term in loc.lower() for term in include_terms):
            continue
        title = entry.findtext("news:news/news:title", namespaces=ns) or loc.rstrip("/").split("/")[-1].replace("-", " ").title()
        published = entry.findtext("news:news/news:publication_date", namespaces=ns)
        published_dt = None
        if published:
            try:
                published_dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
            except ValueError:
                published_dt = None
        if published_dt and published_dt < cutoff:
            continue
        candidates.append((title, loc, published_dt.isoformat() if published_dt else None))

    items = []
    for title, url, published_at in candidates[: int(config.get("max_items_per_source", 40))]:
        signal = make_signal(source, clean_text(title), url, clean_text(title), published_at, config, "sitemap")
        if signal:
            items.append(signal)

    diagnostics.update(
        {
            "status": "OK" if response.status_code < 400 else "FAILED",
            "http_status": response.status_code,
            "candidate_urls": len(candidates),
            "items_seen": min(len(candidates), int(config.get("max_items_per_source", 40))),
            "items_added": len(items),
        }
    )
    return items, diagnostics


def collect_api_or_html(session: requests.Session, source: dict[str, Any], config: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    diagnostics = []
    api_key = os.environ.get(source.get("api_key_env", ""))
    if api_key:
        diagnostics.append({"source": source["name"], "mode": "api", "endpoint": source["url"], "status": "SKIPPED", "note": "API key route is configured but not used by this public collector yet."})
    else:
        diagnostics.append({"source": source["name"], "mode": "api", "endpoint": source["url"], "status": "AUTH_REQUIRED", "note": "API key not configured; using public HTML fallback URLs."})
    items = []
    for fallback_url in source.get("fallback_urls", [source.get("url")]):
        source_items, health = collect_html_url(session, source, config, fallback_url, "html_fallback")
        items.extend(source_items)
        diagnostics.append(health)
        time.sleep(0.25)
    return items, diagnostics


def dedupe(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged = {}
    for item in items:
        key = item.get("url") or item.get("title")
        if key and key not in merged:
            merged[key] = item
    return list(merged.values())


def write_outputs(items: list[dict[str, Any]], diagnostics: list[dict[str, Any]]) -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    RAW_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "last_updated": timestamp,
        "total_items": len(items),
        "items": items,
        "source_health": diagnostics,
    }
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

    for source in config.get("sources", []):
        mode = source.get("mode")
        print(f"Scanning startup collection: {source['name']} via {mode}")
        if mode == "rss":
            source_items, health = collect_rss(session, source, config, cutoff)
            items.extend(source_items)
            diagnostics.append(health)
        elif mode == "api_or_html":
            source_items, health_records = collect_api_or_html(session, source, config)
            items.extend(source_items)
            diagnostics.extend(health_records)
        elif mode == "sitemap":
            source_items, health = collect_sitemap(session, source, config, cutoff)
            items.extend(source_items)
            diagnostics.append(health)
        else:
            source_items, health = collect_html_url(session, source, config, source["url"], mode or "html_index")
            items.extend(source_items)
            diagnostics.append(health)
        print(f"  -> {sum(h.get('items_added', 0) for h in diagnostics if h.get('source') == source['name'])} total source signals")
        time.sleep(0.35)

    items = dedupe(items)
    write_outputs(items, diagnostics)
    print(f"Done. Saved {len(items)} startup collection signals.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
