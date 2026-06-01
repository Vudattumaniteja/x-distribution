"""Prepare verified-only manual drafting packets for X posts.

This intentionally does not invent post copy. The editorial workflow requires
fact-checking before drafting, and final posts remain manual-copy artifacts.
"""

from __future__ import annotations

from typing import Any

from intelligence_queue import ROOT, atomic_json_write, load_queue, utc_now_iso


OUTPUT_PATH = ROOT / "data" / "approved_posts.json"
TEMPLATE_PATH = ROOT / "config" / "post_templates.json"
ALLOWED_VERDICTS = {"VERIFIED", "LIKELY_TRUE"}


def verification_verdict(item: dict[str, Any]) -> str:
    if not isinstance(item, dict):
        return ""
    candidates = [
        item.get("fact_check_status"),
        item.get("verdict"),
        item.get("fact_check_data", {}).get("verdict")
        if isinstance(item.get("fact_check_data"), dict)
        else None,
    ]
    for candidate in candidates:
        if candidate:
            return str(candidate).upper()
    return ""


def eligible_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        item for item in items
        if isinstance(item, dict) and verification_verdict(item) in ALLOWED_VERDICTS
    ]


def load_templates() -> list[dict[str, Any]]:
    import json

    with TEMPLATE_PATH.open("r", encoding="utf-8") as file_handle:
        return json.load(file_handle).get("post_variants", [])


def build_draft_packets(
    items: list[dict[str, Any]],
    templates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    packets = []
    for item in eligible_items(items):
        packets.append(
            {
                "item_id": item.get("id"),
                "headline": item.get("headline") or item.get("title"),
                "source_url": item.get("source_url") or item.get("url"),
                "source_name": item.get("source_name") or item.get("source"),
                "verification_verdict": verification_verdict(item),
                "status": "needs_manual_draft",
                "variants": [
                    {
                        "template_id": template.get("id"),
                        "type": template.get("name"),
                        "strategy": template.get("strategy"),
                        "structure": template.get("structure", []),
                        "status": "needs_manual_draft",
                        "text": "",
                    }
                    for template in templates
                ],
            }
        )
    return packets


def finalize_posts() -> int:
    _metadata, items = load_queue()
    packets = build_draft_packets(items, load_templates())
    atomic_json_write(
        OUTPUT_PATH,
        {
            "metadata": {
                "description": "Verified-only manual X drafting packets",
                "generated_at": utc_now_iso(),
                "publishing": "manual_copy_only",
            },
            "total_items": len(packets),
            "items": packets,
        },
    )
    print(f"Prepared {len(packets)} verified-only manual drafting packet(s): {OUTPUT_PATH}")
    if not packets:
        print("No queue items have VERIFIED or LIKELY_TRUE fact-check status yet.")
    return 0


if __name__ == "__main__":
    raise SystemExit(finalize_posts())
