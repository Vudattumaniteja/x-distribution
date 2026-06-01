"""Collect model-market signals from OpenRouter.

This lane is built for quiet model drops and capability/pricing changes. It is
not treated as ground truth about broad developer preference by itself; it is a
marketplace/routing signal that should be cross-checked against community and
official sources.
"""

from __future__ import annotations

import json
import re
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning


warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "model_market_sources.json"
RAW_OUTPUT_PATH = ROOT / "data" / "model_market_raw.json"
SIGNALS_OUTPUT_PATH = ROOT / "data" / "model_market_signals.json"
HISTORY_PATH = ROOT / "data" / "model_market_history.json"
HEADERS = {"User-Agent": "XDistributionModelMarket/1.0 local-research contact: local"}


DEFAULT_CONFIG: dict[str, Any] = {
    "request_timeout_seconds": 30,
    "max_models": 800,
    "openrouter": {
        "enabled": True,
        "models_url": "https://openrouter.ai/api/v1/models",
        "tool_models_url": "https://openrouter.ai/api/v1/models?supported_parameters=tools",
        "source_region": "global",
        "tier": "tier_1",
    },
    "tracked_change_fields": [
        "context_length",
        "pricing",
        "supported_parameters",
        "architecture",
        "top_provider",
        "per_request_limits",
    ],
    "watch_terms": [],
    "catalog_sources": [],
}


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return DEFAULT_CONFIG
    with CONFIG_PATH.open("r", encoding="utf-8") as file_handle:
        parsed = json.load(file_handle)
    merged = DEFAULT_CONFIG | parsed
    merged["openrouter"] = DEFAULT_CONFIG["openrouter"] | parsed.get("openrouter", {})
    return merged


def load_history() -> dict[str, Any]:
    if not HISTORY_PATH.exists():
        return {"models": {}}
    with HISTORY_PATH.open("r", encoding="utf-8") as file_handle:
        return json.load(file_handle)


def stable_model_snapshot(model: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": model.get("id"),
        "name": model.get("name"),
        "created": model.get("created"),
        "context_length": model.get("context_length"),
        "pricing": model.get("pricing"),
        "supported_parameters": sorted(model.get("supported_parameters") or []),
        "architecture": model.get("architecture"),
        "top_provider": model.get("top_provider"),
        "per_request_limits": model.get("per_request_limits"),
    }


def fetch_models(session: requests.Session, url: str, timeout: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    diagnostics = {"source": "OpenRouter", "mode": "api", "endpoint": url}
    try:
        response = session.get(url, headers=HEADERS, timeout=timeout)
        payload = response.json()
    except Exception as exc:
        diagnostics.update({"status": "ERROR", "error": str(exc), "items_seen": 0})
        return [], diagnostics
    models = payload.get("data", []) if isinstance(payload, dict) else []
    diagnostics.update(
        {
            "status": "OK" if response.status_code < 400 else "FAILED",
            "http_status": response.status_code,
            "items_seen": len(models),
        }
    )
    return models, diagnostics


def watched_model(model: dict[str, Any], watch_terms: list[str]) -> bool:
    if not watch_terms:
        return True
    haystack = json.dumps(model, ensure_ascii=False).lower()
    return any(term.lower() in haystack for term in watch_terms)


def build_signals(
    models: list[dict[str, Any]],
    tool_model_ids: set[str],
    history: dict[str, Any],
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    previous_models = history.get("models", {})
    tracked_fields = config.get("tracked_change_fields", [])
    watch_terms = config.get("watch_terms", [])
    signals: list[dict[str, Any]] = []

    for model in models:
        model_id = model.get("id")
        if not model_id:
            continue
        snapshot = stable_model_snapshot(model)
        previous = previous_models.get(model_id)
        signal_types = []
        changed_fields = []
        if previous is None:
            signal_types.append("new_model_listing")
        else:
            for field in tracked_fields:
                if previous.get(field) != snapshot.get(field):
                    changed_fields.append(field)
            if changed_fields:
                signal_types.append("model_capability_or_pricing_change")
        if model_id in tool_model_ids:
            signal_types.append("tool_calling_supported")
        if ":free" in model_id or "free" in str(model.get("name", "")).lower():
            signal_types.append("free_model_available")
        if not signal_types and not watched_model(model, watch_terms):
            continue
        if not signal_types:
            signal_types.append("watched_model_market_snapshot")

        pricing = model.get("pricing") or {}
        architecture = model.get("architecture") or {}
        signals.append(
            {
                "id": f"model_market_{model_id.replace('/', '_').replace(':', '_')}",
                "title": model.get("name") or model_id,
                "model_id": model_id,
                "url": f"https://openrouter.ai/{model_id}",
                "source": "OpenRouter",
                "source_region": "global",
                "source_type": "model_market",
                "tier": "tier_1",
                "published_at": None,
                "discovered_at": datetime.now(timezone.utc).isoformat(),
                "signal_type": "Model Market Signal",
                "model_signal_types": sorted(set(signal_types)),
                "changed_fields": changed_fields,
                "context_length": model.get("context_length"),
                "prompt_price": pricing.get("prompt"),
                "completion_price": pricing.get("completion"),
                "architecture_modality": architecture.get("modality"),
                "supported_parameters": model.get("supported_parameters") or [],
                "summary": (
                    f"OpenRouter model-market signal for {model_id}. "
                    f"Signals: {', '.join(sorted(set(signal_types)))}."
                ),
                "confidence": "confirmed_api_signal",
            }
        )
    return signals


def clean_text(raw: str | None) -> str:
    return re.sub(r"\s+", " ", BeautifulSoup(raw or "", "html.parser").get_text(" ", strip=True)).strip()


def collect_catalog_source(session: requests.Session, source: dict[str, Any], config: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    diagnostics = {"source": source.get("name"), "mode": source.get("mode", "html_index"), "endpoint": source.get("url")}
    try:
        response = session.get(source["url"], headers=HEADERS, timeout=int(config.get("request_timeout_seconds", 30)))
        soup = BeautifulSoup(response.text, "html.parser")
    except Exception as exc:
        diagnostics.update({"status": "ERROR", "error": str(exc), "items_seen": 0, "items_added": 0})
        return [], diagnostics

    candidates = []
    for anchor in soup.find_all("a", href=True):
        title = clean_text(anchor.get_text(" ", strip=True))
        href = requests.compat.urljoin(response.url, anchor["href"]).split("#", 1)[0]
        if len(title) < 3 or href == response.url:
            continue
        context = clean_text(anchor.parent.get_text(" ", strip=True) if anchor.parent else title)
        haystack = " ".join([title, context, href]).lower()
        if any(term in haystack for term in ["model", "llm", "gpt", "claude", "qwen", "deepseek", "gemini", "llama", "groq", "leaderboard", "replicate", "together", "fireworks"]):
            candidates.append((title, href, context))

    seen = set()
    signals = []
    for title, href, context in candidates[:80]:
        key = href or title
        if key in seen:
            continue
        seen.add(key)
        signals.append(
            {
                "id": "model_catalog_" + re.sub(r"[^a-zA-Z0-9]+", "_", key.lower()).strip("_")[:140],
                "title": title[:240],
                "model_id": None,
                "url": href,
                "source": source.get("name"),
                "source_region": source.get("source_region", "global"),
                "source_type": source.get("source_type", "model_catalog"),
                "tier": source.get("tier", "tier_2"),
                "published_at": None,
                "discovered_at": datetime.now(timezone.utc).isoformat(),
                "signal_type": "Model Catalog Signal",
                "model_signal_types": ["catalog_presence"],
                "summary": context[:700] or f"Model catalog signal from {source.get('name')}.",
                "confidence": "public_catalog_signal",
            }
        )

    diagnostics.update(
        {
            "status": "OK" if response.status_code < 400 else "FAILED",
            "http_status": response.status_code,
            "candidate_links": len(candidates),
            "items_seen": len(seen),
            "items_added": len(signals),
        }
    )
    return signals, diagnostics


def write_outputs(models: list[dict[str, Any]], signals: list[dict[str, Any]], diagnostics: list[dict[str, Any]]) -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    RAW_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with RAW_OUTPUT_PATH.open("w", encoding="utf-8") as file_handle:
        json.dump(
            {
                "last_updated": timestamp,
                "total_items": len(models),
                "items": models,
                "source_health": diagnostics,
            },
            file_handle,
            indent=2,
            ensure_ascii=False,
        )
    with SIGNALS_OUTPUT_PATH.open("w", encoding="utf-8") as file_handle:
        json.dump(
            {
                "last_updated": timestamp,
                "signals": signals,
                "source_health": diagnostics,
            },
            file_handle,
            indent=2,
            ensure_ascii=False,
        )
    with HISTORY_PATH.open("w", encoding="utf-8") as file_handle:
        json.dump(
            {
                "last_updated": timestamp,
                "models": {model["id"]: stable_model_snapshot(model) for model in models if model.get("id")},
            },
            file_handle,
            indent=2,
            ensure_ascii=False,
        )


def main() -> int:
    config = load_config()
    openrouter = config.get("openrouter", {})
    if not openrouter.get("enabled", True):
        write_outputs([], [], [{"source": "OpenRouter", "status": "DISABLED"}])
        return 0

    session = requests.Session()
    timeout = int(config.get("request_timeout_seconds", 30))
    models, health = fetch_models(session, openrouter["models_url"], timeout)
    tool_models, tool_health = fetch_models(session, openrouter["tool_models_url"], timeout)
    max_models = int(config.get("max_models", 800))
    models = models[:max_models]
    tool_model_ids = {model.get("id") for model in tool_models if model.get("id")}
    history = load_history()
    signals = build_signals(models, tool_model_ids, history, config)
    diagnostics = [health, tool_health]
    for source in config.get("catalog_sources", []):
        catalog_signals, catalog_health = collect_catalog_source(session, source, config)
        signals.extend(catalog_signals)
        diagnostics.append(catalog_health)
    write_outputs(models, signals, diagnostics)
    print(f"Done. Saved {len(models)} model records and {len(signals)} model-market signals.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
