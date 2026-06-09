"""Shared transport helpers for source-lane collectors.

The module owns network/session mechanics, RSS entry normalization, source
health diagnostics, item dedupe, and collector-output persistence. Lane
collectors keep their own terminology, filtering, and scoring.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Callable

import feedparser
import requests
from bs4 import BeautifulSoup


ItemBuilder = Callable[
    [dict[str, Any], str, str, str | None, str, str],
    dict[str, Any] | None,
]


def request_timeout(config: dict[str, Any], default: int = 20) -> int:
    return int(config.get("request_timeout_seconds", default))


def create_session(headers: dict[str, str] | None = None) -> requests.Session:
    session = requests.Session()
    if headers:
        session.headers.update(headers)
    return session


def clean_text(raw: str | None) -> str:
    text = BeautifulSoup(raw or "", "html.parser").get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()


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


def collect_rss_source(
    session: requests.Session,
    source: dict[str, Any],
    config: dict[str, Any],
    cutoff: datetime,
    *,
    item_builder: ItemBuilder,
    headers: dict[str, str] | None = None,
    max_items_default: int = 25,
    timeout_default: int = 20,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    endpoint = source.get("rss_url")
    diagnostics: dict[str, Any] = {
        "source": source.get("name"),
        "mode": "rss",
        "endpoint": endpoint,
    }
    if not endpoint:
        diagnostics.update({"status": "ERROR", "error": "missing rss_url", "items_seen": 0, "items_added": 0})
        return [], diagnostics

    try:
        response = session.get(
            endpoint,
            headers=headers,
            timeout=request_timeout(config, timeout_default),
        )
        feed = feedparser.parse(response.content)
    except Exception as exc:
        diagnostics.update({"status": "ERROR", "error": str(exc), "items_seen": 0, "items_added": 0})
        return [], diagnostics

    items: list[dict[str, Any]] = []
    max_items = int(config.get("max_items_per_source", max_items_default))
    entries = feed.entries[:max_items]
    for entry in entries:
        published_dt = parse_feed_datetime(entry)
        if published_dt and published_dt < cutoff:
            continue
        title = clean_text(entry.get("title", "Untitled"))
        url = entry.get("link", source.get("url", ""))
        summary = clean_text(entry.get("summary", "") or entry.get("description", ""))
        item = item_builder(
            source,
            title,
            url,
            published_dt.isoformat() if published_dt else None,
            summary,
            endpoint,
        )
        if item:
            items.append(item)

    diagnostics.update(
        {
            "status": "OK" if response.status_code < 400 else "FAILED",
            "http_status": response.status_code,
            "feed_entries": len(feed.entries),
            "items_seen": len(entries),
            "items_added": len(items),
            "parse_warning": bool(feed.bozo),
        }
    )
    return items, diagnostics


def source_identity(item: dict[str, Any]) -> str:
    source = item.get("source") or item.get("source_name") or item.get("discovery_source") or "unknown"
    key = item.get("url") or item.get("source_url") or item.get("resolved_url") or item.get("title") or item.get("headline")
    return f"{source}\n{key}".lower()


def dedupe_by_source_identity(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[str, dict[str, Any]] = {}
    for item in items:
        key = source_identity(item)
        current = deduped.get(key)
        if current is None or item.get("relevance_score", 0) > current.get("relevance_score", 0):
            deduped[key] = item
    return sorted(
        deduped.values(),
        key=lambda item: (item.get("published_at") or "", item.get("relevance_score", 0)),
        reverse=True,
    )


def write_collector_outputs(
    *,
    raw_path: Path,
    signals_path: Path,
    items: list[dict[str, Any]],
    diagnostics: list[dict[str, Any]],
    cutoff: datetime,
) -> None:
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "cutoff": cutoff.isoformat(),
        "total_items": len(items),
        "items": items,
        "source_health": diagnostics,
    }
    with raw_path.open("w", encoding="utf-8") as file_handle:
        json.dump(payload, file_handle, indent=2, ensure_ascii=False)
    with signals_path.open("w", encoding="utf-8") as file_handle:
        json.dump(
            {
                "last_updated": payload["last_updated"],
                "signals": items,
                "source_health": diagnostics,
            },
            file_handle,
            indent=2,
            ensure_ascii=False,
        )
