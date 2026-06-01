"""Collect developer pain, adoption, and provider status signals."""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import feedparser
import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "developer_sentiment_sources.json"
RAW_OUTPUT_PATH = ROOT / "data" / "developer_sentiment_raw.json"
SIGNALS_OUTPUT_PATH = ROOT / "data" / "developer_sentiment_signals.json"
HEADERS = {"User-Agent": "XDistributionDeveloperSentiment/1.0 local-research contact: local"}


def load_config() -> dict[str, Any]:
    with CONFIG_PATH.open("r", encoding="utf-8") as file_handle:
        return json.load(file_handle)


def clean_text(raw: str | None) -> str:
    return re.sub(r"\s+", " ", BeautifulSoup(raw or "", "html.parser").get_text(" ", strip=True)).strip()


def parse_dt(entry: Any) -> datetime | None:
    parsed_struct = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed_struct:
        return datetime(*parsed_struct[:6], tzinfo=timezone.utc)
    for field in ["published", "updated"]:
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


def pain_hits(text: str, config: dict[str, Any]) -> list[str]:
    lower = text.lower()
    return [keyword for keyword in config.get("pain_keywords", []) if keyword.lower() in lower]


def make_signal(source: dict[str, Any], title: str, url: str, summary: str, published_at: str | None, config: dict[str, Any], method: str) -> dict[str, Any] | None:
    haystack = " ".join([title, summary, source.get("name", ""), source.get("source_type", "")])
    hits = pain_hits(haystack, config)
    if not hits and source.get("source_type") == "status_page":
        hits = ["status"]
    if not hits:
        return None
    return {
        "id": "developer_sentiment_" + re.sub(r"[^a-zA-Z0-9]+", "_", (url or title).lower()).strip("_")[:140],
        "title": title[:240] or "Developer status signal",
        "url": url,
        "source": source.get("name"),
        "source_region": source.get("source_region", "global"),
        "source_type": source.get("source_type", "developer_sentiment"),
        "tier": source.get("tier", "tier_2"),
        "published_at": published_at,
        "summary": summary[:800],
        "signal_type": "Developer Pain/Adoption Signal",
        "pain_keyword_hits": hits[:12],
        "discovery_method": method,
        "confidence": "provider_status_or_public_signal",
    }


def collect_rss(session: requests.Session, source: dict[str, Any], config: dict[str, Any], cutoff: datetime) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    diagnostics = {"source": source["name"], "mode": "rss", "endpoint": source["rss_url"]}
    try:
        response = session.get(source["rss_url"], headers=HEADERS, timeout=int(config.get("request_timeout_seconds", 25)))
        feed = feedparser.parse(response.content)
    except Exception as exc:
        diagnostics.update({"status": "ERROR", "error": str(exc), "items_seen": 0, "items_added": 0})
        return [], diagnostics
    items = []
    for entry in feed.entries[: int(config.get("max_items_per_source", 30))]:
        published_dt = parse_dt(entry)
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
    diagnostics.update({"status": "OK" if response.status_code < 400 else "FAILED", "http_status": response.status_code, "items_seen": len(feed.entries), "items_added": len(items), "parse_warning": bool(feed.bozo)})
    return items, diagnostics


def collect_html(session: requests.Session, source: dict[str, Any], config: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    diagnostics = {"source": source["name"], "mode": "html_index", "endpoint": source["url"]}
    try:
        response = session.get(source["url"], headers=HEADERS, timeout=int(config.get("request_timeout_seconds", 25)))
        soup = BeautifulSoup(response.text, "html.parser")
    except Exception as exc:
        diagnostics.update({"status": "ERROR", "error": str(exc), "items_seen": 0, "items_added": 0})
        return [], diagnostics
    candidates = []
    for anchor in soup.find_all("a", href=True):
        title = clean_text(anchor.get_text(" ", strip=True))
        if len(title) < 4:
            continue
        href = urljoin(response.url, anchor["href"]).split("#", 1)[0]
        context = clean_text(anchor.parent.get_text(" ", strip=True) if anchor.parent else title)
        candidates.append((title, href, context))
    seen = set()
    items = []
    for title, href, context in candidates[: int(config.get("max_items_per_source", 30)) * 3]:
        key = href or title
        if key in seen:
            continue
        seen.add(key)
        signal = make_signal(source, title, href, context, None, config, "html_index")
        if signal:
            items.append(signal)
        if len(items) >= int(config.get("max_items_per_source", 30)):
            break
    diagnostics.update({"status": "OK" if response.status_code < 400 else "FAILED", "http_status": response.status_code, "candidate_links": len(candidates), "items_seen": len(seen), "items_added": len(items)})
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
    with RAW_OUTPUT_PATH.open("w", encoding="utf-8") as file_handle:
        json.dump({"last_updated": timestamp, "total_items": len(items), "items": items, "source_health": diagnostics}, file_handle, indent=2, ensure_ascii=False)
    with SIGNALS_OUTPUT_PATH.open("w", encoding="utf-8") as file_handle:
        json.dump({"last_updated": timestamp, "signals": items, "source_health": diagnostics}, file_handle, indent=2, ensure_ascii=False)


def main() -> int:
    config = load_config()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=int(config.get("lookback_hours", 168)))
    session = requests.Session()
    items: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    for source in config.get("status_sources", []):
        print(f"Scanning developer/status source: {source['name']}")
        if source.get("mode") == "rss":
            source_items, health = collect_rss(session, source, config, cutoff)
        else:
            source_items, health = collect_html(session, source, config)
        items.extend(source_items)
        diagnostics.append(health)
        print(f"  -> {health['status']}; {health.get('items_added', 0)} signals")
        time.sleep(0.25)
    items = dedupe(items)
    write_outputs(items, diagnostics)
    print(f"Done. Saved {len(items)} developer sentiment/status signals.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
