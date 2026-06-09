"""Collect AI startup fundraising and product-launch signals.

This collector is narrower than the finance lane. It is optimized for finding
new startups, Series A/B/C rounds, funding amounts, investors, and product
launches that matter to the AI/devtools landscape.
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
    collect_rss_source as collect_rss_transport,
    create_session,
    dedupe_by_source_identity,
    write_collector_outputs,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "startup_sources.json"
RAW_OUTPUT_PATH = ROOT / "data" / "startup_funding_raw.json"
SIGNALS_OUTPUT_PATH = ROOT / "data" / "startup_funding_signals.json"
HEADERS = {"User-Agent": "XDistributionStartupIntel/1.0 local-research contact: local"}


DEFAULT_CONFIG: dict[str, Any] = {
    "lookback_hours": 168,
    "request_timeout_seconds": 20,
    "max_items_per_source": 30,
    "min_relevance_score": 5,
    "ai_keywords": ["ai", "artificial intelligence", "agent", "llm", "machine learning"],
    "startup_keywords": ["startup", "founder", "venture", "company", "platform"],
    "funding_keywords": ["raises", "raised", "funding", "series a", "series b", "series c"],
    "product_keywords": ["launch", "launches", "unveils", "product", "platform", "tool"],
    "round_patterns": {
        "series_a": r"\bseries\s+a\b",
        "series_b": r"\bseries\s+b\b",
        "series_c": r"\bseries\s+c\b",
    },
    "rss_sources": [],
}


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return DEFAULT_CONFIG
    with CONFIG_PATH.open("r", encoding="utf-8") as file_handle:
        loaded = json.load(file_handle)
    return DEFAULT_CONFIG | loaded


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


def detect_rounds(text: str, round_patterns: dict[str, str]) -> list[str]:
    lower = text.lower()
    rounds = []
    for label, pattern in round_patterns.items():
        if re.search(pattern, lower, flags=re.IGNORECASE):
            rounds.append(label)
    return rounds


def extract_amount(text: str) -> str | None:
    match = re.search(
        r"(?P<amount>[$€£]\s?\d+(?:\.\d+)?\s?(?:m|million|b|billion|k|thousand))",
        text,
        flags=re.IGNORECASE,
    )
    return re.sub(r"\s+", " ", match.group("amount")).strip() if match else None


def extract_lead_investor(text: str) -> str | None:
    match = re.search(r"\bled by\s+([^.;:]+?)(?:,|\sand\b|\.|$)", text, flags=re.IGNORECASE)
    if not match:
        return None
    investor = match.group(1).strip()
    return investor[:100] if investor else None


def extract_company(title: str) -> str | None:
    patterns = [
        r"^(.+?)\s+(?:raises|raised|lands|landed|secures|secured|closes|closed|snags|snagged|bags|bagged|nabs|nabbed)\b",
        r"^(.+?)\s+(?:launches|launched|unveils|introduces|debuts|ships)\b",
        r"^(.+?)\s+(?:nears|hits|tops)\b",
        r"^(.+?)\s+gets\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, title, flags=re.IGNORECASE)
        if match:
            company = match.group(1).strip(" -:|")
            company = re.sub(r"^exclusive:\s*", "", company, flags=re.IGNORECASE).strip()
            if "," in company:
                company = company.split(",", 1)[0].strip()
            return company[:120] if company else None
    return None


def classify_signal(rounds: list[str], funding_hits: list[str], product_hits: list[str]) -> str:
    if rounds:
        return "Startup Fundraising"
    if funding_hits:
        return "Startup Funding Signal"
    if product_hits:
        return "Startup Product Signal"
    return "Startup Signal"


def has_product_launch_action(title: str) -> bool:
    return bool(
        re.search(
            r"\b(launches|launched|launch|unveils|introduces|debuts|ships|announces)\b",
            title,
            flags=re.IGNORECASE,
        )
    )


def relevance_score(
    *,
    rounds: list[str],
    ai_hits: list[str],
    startup_hits: list[str],
    funding_hits: list[str],
    product_hits: list[str],
    source_tier: str,
    amount: str | None,
) -> int:
    score = len(ai_hits) * 2
    score += len(startup_hits)
    score += len(funding_hits) * 2
    score += len(product_hits)
    score += len(rounds) * 3
    if amount:
        score += 2
    if source_tier == "tier_1":
        score += 2
    elif source_tier == "tier_2":
        score += 1
    return min(score, 10)


def stable_id(source: str, key: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", f"{source}_{key}".lower()).strip("_")
    return "startup_" + cleaned[:140]


def make_signal(
    *,
    source: dict[str, Any],
    title: str,
    url: str,
    published_at: str | None,
    summary: str,
    discovery_source: str,
    config: dict[str, Any],
) -> dict[str, Any] | None:
    haystack = " ".join([title, summary, source.get("name", ""), source.get("source_type", ""), url])
    ai_hits = keyword_hits(haystack, config.get("ai_keywords", []))
    startup_hits = keyword_hits(haystack, config.get("startup_keywords", []))
    funding_hits = keyword_hits(haystack, config.get("funding_keywords", []))
    product_hits = keyword_hits(haystack, config.get("product_keywords", []))
    rounds = detect_rounds(haystack, config.get("round_patterns", {}))
    amount = extract_amount(haystack)
    company = extract_company(title)
    funding_action = bool(
        re.search(
            r"\b(raises|raised|lands|landed|secures|secured|closes|closed|snags|snagged|bags|bagged|nabs|nabbed)\b",
            haystack,
            flags=re.IGNORECASE,
        )
    )

    funding_match = bool(
        funding_action
        or (amount and funding_hits and company)
        or (rounds and company)
    )
    product_match = bool(
        product_hits
        and (
            source.get("source_type") == "product_launch"
            or (has_product_launch_action(title) and startup_hits)
        )
    )
    if not ai_hits or not (funding_match or product_match):
        return None

    lead_investor = extract_lead_investor(haystack)
    score = relevance_score(
        rounds=rounds,
        ai_hits=ai_hits,
        startup_hits=startup_hits,
        funding_hits=funding_hits,
        product_hits=product_hits,
        source_tier=source.get("tier", "tier_3"),
        amount=amount,
    )
    if score < int(config.get("min_relevance_score", 5)):
        return None

    signal_type = classify_signal(rounds, funding_hits, product_hits)
    if source.get("source_type") == "product_launch" and not rounds and not amount:
        signal_type = "Startup Product Signal"

    return {
        "id": stable_id(source.get("name", "startup"), url or title),
        "title": title,
        "url": url,
        "source": source.get("name", "Startup Source"),
        "source_region": source.get("source_region", "unknown"),
        "source_type": source.get("source_type", "startup_news"),
        "tier": source.get("tier", "tier_3"),
        "published_at": published_at,
        "summary": summary[:900],
        "signal_type": signal_type,
        "company": company,
        "funding_rounds": rounds,
        "funding_amount": amount,
        "lead_investor": lead_investor,
        "ai_keyword_hits": ai_hits[:12],
        "startup_keyword_hits": startup_hits[:12],
        "funding_keyword_hits": funding_hits[:12],
        "product_keyword_hits": product_hits[:12],
        "relevance_score": score,
        "discovery_method": "rss",
        "discovery_source": discovery_source,
    }


def collect_rss_source(
    session: requests.Session,
    source: dict[str, Any],
    config: dict[str, Any],
    cutoff: datetime,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    return collect_rss_transport(
        session,
        source,
        config,
        cutoff,
        headers=HEADERS,
        max_items_default=30,
        item_builder=lambda source, title, url, published_at, summary, discovery_source: make_signal(
            source=source,
            title=title,
            url=url,
            published_at=published_at,
            summary=summary,
            discovery_source=discovery_source,
            config=config,
        ),
    )


def write_outputs(items: list[dict[str, Any]], diagnostics: list[dict[str, Any]], cutoff: datetime) -> None:
    write_collector_outputs(
        raw_path=RAW_OUTPUT_PATH,
        signals_path=SIGNALS_OUTPUT_PATH,
        items=items,
        diagnostics=diagnostics,
        cutoff=cutoff,
    )


def main() -> int:
    config = load_config()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=int(config.get("lookback_hours", 168)))
    session = create_session(HEADERS)
    items: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []

    for source in config.get("rss_sources", []):
        print(f"Scanning startup RSS: {source['name']}")
        source_items, health = collect_rss_source(session, source, config, cutoff)
        items.extend(source_items)
        diagnostics.append(health)
        print(f"  -> {health['status']}; {health.get('items_added', 0)} signals")
        time.sleep(0.35)

    items = dedupe_by_source_identity(items)
    write_outputs(items, diagnostics, cutoff)
    print(f"Done. Saved {len(items)} startup signals to {RAW_OUTPUT_PATH} and {SIGNALS_OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
