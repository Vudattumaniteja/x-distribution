"""Collect Polymarket prediction market signals.

Filters free public search query endpoint, scores markets via a "Smoke Detector"
algorithm, and outputs raw and filtered signals.
"""

from __future__ import annotations

import json
import math
import os
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "prediction_market_sources.json"
OUTPUT_PATH = ROOT / "data" / "prediction_market_raw.json"
SIGNALS_PATH = ROOT / "data" / "prediction_market_signals.json"
HEADERS = {
    "User-Agent": "XDistributionPolymarketIntel/1.0 local-research contact: local"
}

DEFAULT_CONFIG: dict[str, Any] = {
    "watchlist_queries": [
        "OpenAI", "Anthropic", "DeepSeek", "Google Gemini", "Claude",
        "Sam Altman", "GPT-5", "Llama", "Nvidia", "IPO",
        "acquisition", "merger", "valuation", "fundraising"
    ],
    "min_volume": 5000,
    "min_price_change_24h": 0.03,
    "max_creation_age_hours": 48
}


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return DEFAULT_CONFIG
    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as file_handle:
            loaded = json.load(file_handle)
        return DEFAULT_CONFIG | loaded
    except Exception:
        return DEFAULT_CONFIG


def parse_iso_datetime(dt_str: str | None) -> datetime | None:
    if not dt_str:
        return None
    try:
        if dt_str.endswith("Z"):
            dt_str = dt_str[:-1] + "+00:00"
        dt_str = dt_str.replace(" ", "T")
        dt = datetime.fromisoformat(dt_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def calculate_smoke_detector_score(market: dict[str, Any], min_volume: float) -> float:
    # Base Score
    score = 5.0

    # Total Volume
    total_volume = float(market.get("volumeNum") or market.get("volume") or 0.0)

    # Size Bonus: 1.0 * log10(total_volume / min_volume) capped at 2.0
    size_bonus = 0.0
    if min_volume > 0 and total_volume > 0:
        ratio = total_volume / min_volume
        size_bonus = 1.0 * math.log10(ratio)
    size_bonus = max(0.0, min(2.0, size_bonus))
    score += size_bonus

    # Growth Velocity (Option A): 3.0 * (volume24hr / total_volume) (where total_volume > 0)
    volume24h = float(market.get("volume24hr") or market.get("volume24hrClob") or 0.0)
    growth_velocity = 0.0
    if total_volume > 0:
        growth_velocity = 3.0 * (volume24h / total_volume)
    score += growth_velocity

    # Volatility (24h Price Change): 10.0 * abs(oneDayPriceChange) capped at 2.0
    one_day_price_change = float(market.get("oneDayPriceChange") or 0.0)
    volatility = min(2.0, 10.0 * abs(one_day_price_change))
    score += volatility

    # Priority Bonus: +1.0 if matching high-priority keywords
    priority_keywords = ["OpenAI", "AGI", "IPO", "Anthropic"]
    haystack = f"{market.get('question') or ''} {market.get('slug') or ''} {market.get('description') or ''}".lower()
    priority_bonus = 0.0
    if any(kw.lower() in haystack for kw in priority_keywords):
        priority_bonus = 1.0
    score += priority_bonus

    # Final Cap: Capped at 10.0
    return min(10.0, max(0.0, score))


def format_odds_and_prices(market: dict[str, Any]) -> tuple[str, str]:
    odds_list = []
    try:
        outcomes = json.loads(market.get("outcomes") or "[]")
        prices = json.loads(market.get("outcomePrices") or "[]")
        if outcomes and prices and len(outcomes) == len(prices):
            for o, p in zip(outcomes, prices):
                try:
                    pct = float(p) * 100
                    odds_list.append(f"{o}: {pct:.1f}%")
                except ValueError:
                    odds_list.append(f"{o}: {p}")
    except Exception:
        pass

    odds_suffix = ""
    if odds_list:
        odds_suffix = f" [{ ' | '.join(odds_list) }]"

    title = f"{market.get('question') or 'Untitled Market'}{odds_suffix}"
    summary = market.get("description") or market.get("question") or "No description available."
    if odds_list:
        summary = f"{summary} | Odds: {', '.join(odds_list)}"

    return title, summary


def make_signal(market: dict[str, Any], score: float, query: str) -> dict[str, Any]:
    market_id = market.get("id") or "unknown"
    title, summary = format_odds_and_prices(market)

    # Format signal
    return {
        "id": f"prediction_market_{market_id}",
        "title": title,
        "url": f"https://polymarket.com/event/{market.get('slug')}" if market.get("slug") else "https://polymarket.com",
        "source": "Polymarket",
        "source_region": "global",
        "source_type": "prediction_market",
        "tier": "tier_1",
        "published_at": market.get("createdAt") or market.get("startDate") or datetime.now(timezone.utc).isoformat(),
        "summary": summary[:700],
        "signal_type": "Prediction Market Signal",
        "prediction_market_signal_types": ["rumor_speculation"],
        "relevance_score": round(score, 2),
        "discovery_method": "polymarket_api",
        "discovery_source": f"https://gamma-api.polymarket.com/public-search?q={query}",
        "unique_fields": {
            "market_id": market_id,
            "volume": float(market.get("volumeNum") or market.get("volume") or 0.0),
            "volume24h": float(market.get("volume24hr") or market.get("volume24hrClob") or 0.0),
            "one_day_price_change": float(market.get("oneDayPriceChange") or 0.0),
            "outcomes": market.get("outcomes"),
            "outcome_prices": market.get("outcomePrices"),
            "slug": market.get("slug"),
        }
    }


def main() -> int:
    config = load_config()
    min_volume = float(config.get("min_volume", 5000))
    min_price_change_24h = float(config.get("min_price_change_24h", 0.03))
    max_creation_age_hours = float(config.get("max_creation_age_hours", 48))
    queries = config.get("watchlist_queries", [])

    session = requests.Session()
    deduplicated_markets: dict[str, tuple[dict[str, Any], str]] = {}
    diagnostics: list[dict[str, Any]] = []

    for query in queries:
        print(f"Scanning Polymarket for query: {query}")
        endpoint = f"https://gamma-api.polymarket.com/public-search?q={query}"
        diag = {
            "source": f"Polymarket: {query}",
            "mode": "public-search",
            "endpoint": endpoint,
            "items_seen": 0,
            "items_added": 0
        }
        try:
            response = session.get(endpoint, headers=HEADERS, timeout=20)
            if response.status_code >= 400:
                diag.update({"status": "FAILED", "http_status": response.status_code})
                diagnostics.append(diag)
                print(f"  -> Failed (HTTP {response.status_code})")
                continue
            
            data = response.json()
            events = data.get("events", [])
            seen_count = 0
            added_count = 0

            for event in events:
                for market in event.get("markets", []):
                    # Check if market is active (active=True, closed=False)
                    is_active = market.get("active") is True and market.get("closed") is False
                    if not is_active:
                        continue
                    
                    market_id = market.get("id")
                    if not market_id:
                        continue
                    
                    seen_count += 1
                    # Deduplicate: if duplicate, we keep the one matching query
                    if market_id not in deduplicated_markets:
                        deduplicated_markets[market_id] = (market, query)
                        added_count += 1

            diag.update({
                "status": "OK",
                "http_status": response.status_code,
                "items_seen": seen_count,
                "items_added": added_count
            })
            print(f"  -> OK; {added_count} active markets added")
        except Exception as exc:
            diag.update({"status": "ERROR", "error": str(exc)})
            print(f"  -> Error: {exc}")
        
        diagnostics.append(diag)
        time.sleep(0.5)

    now = datetime.now(timezone.utc)
    raw_signals: list[dict[str, Any]] = []
    filtered_signals: list[dict[str, Any]] = []

    # Process all deduplicated active markets
    for market_id, (market, query) in deduplicated_markets.items():
        score = calculate_smoke_detector_score(market, min_volume)
        signal = make_signal(market, score, query)
        raw_signals.append(signal)

        # Filters for signals:
        # 1. Volume threshold check
        vol = signal["unique_fields"]["volume"]
        vol_pass = vol >= min_volume

        # 2. Volatility threshold check
        change = signal["unique_fields"]["one_day_price_change"]
        change_pass = abs(change) >= min_price_change_24h

        # 3. Creation age check
        created_at_str = market.get("createdAt") or market.get("startDate")
        created_at = parse_iso_datetime(created_at_str)
        
        age_pass = True
        if created_at:
            age_hours = (now - created_at).total_seconds() / 3600.0
            age_pass = age_hours <= max_creation_age_hours

        if vol_pass and change_pass and age_pass:
            filtered_signals.append(signal)

    # Sort signals by relevance score (Smoke Detector score) and volume
    raw_signals.sort(key=lambda s: (s.get("relevance_score", 0.0), s["unique_fields"]["volume"]), reverse=True)
    filtered_signals.sort(key=lambda s: (s.get("relevance_score", 0.0), s["unique_fields"]["volume"]), reverse=True)

    # Output raw data
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    raw_payload = {
        "last_updated": now.isoformat(),
        "total_items": len(raw_signals),
        "items": raw_signals,
        "source_health": diagnostics
    }
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(raw_payload, f, indent=2, ensure_ascii=False)

    # Output filtered signals
    signals_payload = {
        "last_updated": now.isoformat(),
        "total_items": len(filtered_signals),
        "signals": filtered_signals,
        "source_health": diagnostics
    }
    with SIGNALS_PATH.open("w", encoding="utf-8") as f:
        json.dump(signals_payload, f, indent=2, ensure_ascii=False)

    print(f"Collection finished. Raw active markets saved: {len(raw_signals)}. Filtered signals saved: {len(filtered_signals)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
