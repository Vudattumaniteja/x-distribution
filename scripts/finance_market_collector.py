"""Collect AI-linked finance, market, and macro signals.

This is intentionally not a generic finance scraper. It watches business,
market, newsletter, and SEC surfaces, then keeps only items that connect finance
or macro conditions to the AI landscape.
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests

from source_lane_transport import (
    clean_text,
    collect_rss_source as collect_rss_transport,
    create_session,
    dedupe_by_source_identity,
    parse_feed_datetime,
    request_timeout,
    write_collector_outputs,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "finance_sources.json"
OUTPUT_PATH = ROOT / "data" / "finance_raw_standalone.json"
SIGNALS_PATH = ROOT / "data" / "finance_signals.json"
SEC_BASE = "https://data.sec.gov/submissions/CIK{cik}.json"
HEADERS = {
    "User-Agent": "XDistributionFinanceIntel/1.0 local-research contact: local"
}


DEFAULT_CONFIG: dict[str, Any] = {
    "lookback_hours": 96,
    "request_timeout_seconds": 20,
    "max_items_per_source": 25,
    "min_relevance_score": 4,
    "ai_keywords": ["ai", "artificial intelligence", "llm", "openai", "nvidia", "gpu"],
    "finance_keywords": ["funding", "valuation", "earnings", "revenue", "capex", "stock"],
    "signal_rules": {
        "funding_signal": ["funding", "valuation", "raises", "raised"],
        "earnings_signal": ["earnings", "revenue", "profit", "guidance"],
        "capex_signal": ["capex", "data center", "datacenter", "power"],
        "chip_supply_signal": ["nvidia", "gpu", "chip", "tsmc"],
        "market_sentiment_signal": ["stock", "shares", "market", "ipo"],
        "regulatory_signal": ["regulation", "export control", "tariff", "sec"],
        "labor_signal": ["layoffs", "hiring", "workforce"],
    },
    "rss_sources": [],
    "sec_companies": [],
    "sec_forms": ["8-K", "10-Q", "10-K", "S-1", "424B4"],
}


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return DEFAULT_CONFIG
    with CONFIG_PATH.open("r", encoding="utf-8") as file_handle:
        loaded = json.load(file_handle)
    merged = DEFAULT_CONFIG | loaded
    merged["signal_rules"] = DEFAULT_CONFIG["signal_rules"] | loaded.get("signal_rules", {})
    return merged


def keyword_hits(text: str, keywords: list[str]) -> list[str]:
    lower = text.lower()
    hits = []
    for keyword in keywords:
        needle = keyword.lower()
        if len(needle) <= 3 and needle.isalnum():
            if re.search(rf"\b{re.escape(needle)}\b", lower):
                hits.append(keyword)
        elif needle in lower:
            hits.append(keyword)
    return hits


def classify_signals(text: str, signal_rules: dict[str, list[str]]) -> list[str]:
    labels = []
    for label, keywords in signal_rules.items():
        if keyword_hits(text, keywords):
            labels.append(label)
    return labels or ["finance_context_signal"]


def relevance_score(ai_hits: list[str], finance_hits: list[str], labels: list[str], source_tier: str) -> int:
    score = (len(ai_hits) * 2) + len(finance_hits) + len(labels)
    if source_tier == "tier_1":
        score += 2
    elif source_tier == "tier_2":
        score += 1
    return min(score, 10)


def make_signal(
    *,
    source: dict[str, Any],
    title: str,
    url: str,
    published_at: str | None,
    summary: str,
    discovery_method: str,
    discovery_source: str,
    config: dict[str, Any],
    extra: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    haystack = " ".join([title, summary, source.get("name", ""), url])
    ai_hits = keyword_hits(haystack, config.get("ai_keywords", []))
    finance_hits = keyword_hits(haystack, config.get("finance_keywords", []))
    if not ai_hits or not finance_hits:
        return None
    labels = classify_signals(haystack, config.get("signal_rules", {}))
    score = relevance_score(ai_hits, finance_hits, labels, source.get("tier", "tier_3"))
    if score < int(config.get("min_relevance_score", 4)):
        return None
    item = {
        "id": stable_id(source.get("name", "finance"), url or title),
        "title": title,
        "url": url,
        "source": source.get("name", "Finance Source"),
        "source_region": source.get("source_region", "unknown"),
        "source_type": source.get("source_type", "finance_news"),
        "tier": source.get("tier", "tier_3"),
        "published_at": published_at,
        "summary": summary[:700],
        "signal_type": "AI Market Intelligence",
        "finance_signal_types": labels,
        "ai_keyword_hits": ai_hits[:12],
        "finance_keyword_hits": finance_hits[:12],
        "relevance_score": score,
        "discovery_method": discovery_method,
        "discovery_source": discovery_source,
    }
    if extra:
        item.update(extra)
    return item


def stable_id(source: str, key: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", f"{source}_{key}".lower()).strip("_")
    return "finance_" + cleaned[:140]


def collect_rss_source(session: requests.Session, source: dict[str, Any], config: dict[str, Any], cutoff: datetime) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    return collect_rss_transport(
        session,
        source,
        config,
        cutoff,
        headers=HEADERS,
        max_items_default=25,
        item_builder=lambda source, title, url, published_at, summary, discovery_source: make_signal(
            source=source,
            title=title,
            url=url,
            published_at=published_at,
            summary=summary,
            discovery_method="rss",
            discovery_source=discovery_source,
            config=config,
        ),
    )


def collect_sec_company(session: requests.Session, company: dict[str, Any], config: dict[str, Any], cutoff: datetime) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    cik = str(company["cik"]).zfill(10)
    url = SEC_BASE.format(cik=cik)
    source = {
        "name": f"SEC EDGAR {company['ticker']}",
        "source_region": "us",
        "source_type": "sec_filing",
        "tier": "tier_1",
    }
    diagnostics = {
        "source": source["name"],
        "mode": "sec_submissions",
        "endpoint": url,
    }
    try:
        response = session.get(url, headers=HEADERS, timeout=request_timeout(config, 20))
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        diagnostics.update({"status": "ERROR", "error": str(exc), "items_seen": 0, "items_added": 0})
        return [], diagnostics

    recent = payload.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    filing_dates = recent.get("filingDate", [])
    accession_numbers = recent.get("accessionNumber", [])
    primary_docs = recent.get("primaryDocument", [])
    descriptions = recent.get("primaryDocDescription", [])
    accepted_forms = set(config.get("sec_forms", []))
    items = []
    seen = 0
    for index, form in enumerate(forms[:80]):
        if form not in accepted_forms:
            continue
        seen += 1
        filing_date = filing_dates[index] if index < len(filing_dates) else ""
        try:
            published_dt = datetime.fromisoformat(filing_date).replace(tzinfo=timezone.utc)
        except ValueError:
            published_dt = None
        if published_dt and published_dt < cutoff:
            continue
        accession = accession_numbers[index] if index < len(accession_numbers) else ""
        primary_doc = primary_docs[index] if index < len(primary_docs) else ""
        accession_path = accession.replace("-", "")
        filing_url = (
            f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession_path}/{primary_doc}"
            if accession and primary_doc
            else url
        )
        description = descriptions[index] if index < len(descriptions) else ""
        title = f"{company['name']} {form} filing"
        summary = f"{company['name']} filed {form}. {description}".strip()
        extra_keywords = " ".join([company["name"], company["ticker"], "AI cloud compute GPU data center earnings revenue capex"])
        item = make_signal(
            source=source,
            title=title,
            url=filing_url,
            published_at=published_dt.isoformat() if published_dt else None,
            summary=f"{summary} {extra_keywords}",
            discovery_method="sec_submissions",
            discovery_source=url,
            config=config,
            extra={"company": company["name"], "ticker": company["ticker"], "sec_form": form},
        )
        if item:
            items.append(item)

    diagnostics.update(
        {
            "status": "OK",
            "http_status": response.status_code,
            "items_seen": seen,
            "items_added": len(items),
        }
    )
    return items, diagnostics


def write_outputs(items: list[dict[str, Any]], diagnostics: list[dict[str, Any]], cutoff: datetime) -> None:
    write_collector_outputs(
        raw_path=OUTPUT_PATH,
        signals_path=SIGNALS_PATH,
        items=items,
        diagnostics=diagnostics,
        cutoff=cutoff,
    )


def main() -> int:
    config = load_config()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=int(config.get("lookback_hours", 96)))
    session = create_session(HEADERS)
    items: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []

    for source in config.get("rss_sources", []):
        print(f"Scanning finance RSS: {source['name']}")
        source_items, health = collect_rss_source(session, source, config, cutoff)
        items.extend(source_items)
        diagnostics.append(health)
        print(f"  -> {health['status']}; {health.get('items_added', 0)} signals")
        time.sleep(0.4)

    for company in config.get("sec_companies", []):
        print(f"Scanning SEC filings: {company['ticker']}")
        source_items, health = collect_sec_company(session, company, config, cutoff)
        items.extend(source_items)
        diagnostics.append(health)
        print(f"  -> {health['status']}; {health.get('items_added', 0)} signals")
        time.sleep(0.2)

    items = dedupe_by_source_identity(items)
    write_outputs(items, diagnostics, cutoff)
    print(f"Done. Saved {len(items)} finance signals to {OUTPUT_PATH} and {SIGNALS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
