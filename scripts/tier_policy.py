"""Source tier helpers backed by config/source_tiers.json."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_TIERS_PATH = ROOT / "config" / "source_tiers.json"


def load_source_tiers() -> dict:
    if not SOURCE_TIERS_PATH.exists():
        return {"tiers": {}, "quarantine": []}
    with SOURCE_TIERS_PATH.open("r", encoding="utf-8") as file_handle:
        return json.load(file_handle)


def tier_domains(tier_name: str) -> list[str]:
    return list(load_source_tiers().get("tiers", {}).get(tier_name, {}).get("domains", []))


def is_tier_source(source_name: str, tier_name: str = "T1") -> bool:
    source_lower = (source_name or "").lower()
    if not source_lower:
        return False
    return any(domain.lower().split(".")[0] in source_lower or domain.lower() in source_lower for domain in tier_domains(tier_name))


def is_quarantined(source_name: str) -> bool:
    source_lower = (source_name or "").lower()
    return any(domain.lower() in source_lower for domain in load_source_tiers().get("quarantine", []))
