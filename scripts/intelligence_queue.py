"""Protected intelligence queue storage and normalization.

This module is the authoritative seam for reading and writing the active
``data/news_queue.json`` state. Queue writers should use this module so legacy
shape handling, URL identity, duplicate merging, and atomic persistence stay
local to one implementation.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.parse import urlparse, urlunparse

from source_registry import queue_policy


ROOT = Path(__file__).resolve().parents[1]
QUEUE_PATH = ROOT / "data" / "news_queue.json"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_url(raw_url: str | None) -> str:
    """Return the stable URL identity used for queue deduplication."""
    if not raw_url:
        return ""
    parsed = urlparse(raw_url)
    if not parsed.scheme or not parsed.netloc:
        return raw_url.strip()
    normalized_path = parsed.path.rstrip("/") or "/"
    return urlunparse(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            normalized_path,
            "",
            parsed.query,
            "",
        )
    )


def item_url(item: dict[str, Any]) -> str:
    for field in queue_policy().get(
        "dedupe_url_fields",
        ["source_url", "url", "resolved_url", "hn_discussion_url"],
    ):
        if item.get(field):
            return str(item[field])
    return ""


def item_key(item: dict[str, Any]) -> str:
    return canonical_url(item_url(item)) or str(
        item.get("id") or item.get("headline") or item.get("title") or ""
    ).strip()


def items_from_document(document: Any) -> list[dict[str, Any]]:
    """Read items from the canonical document or the historical list shape."""
    if isinstance(document, list):
        return [item for item in document if isinstance(item, dict)]
    if isinstance(document, dict):
        return [item for item in document.get("items", []) if isinstance(item, dict)]
    return []


def load_queue(path: Path = QUEUE_PATH) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not path.exists():
        return {}, []
    with path.open("r", encoding="utf-8") as file_handle:
        document = json.load(file_handle)
    metadata = document.get("metadata", {}) if isinstance(document, dict) else {}
    return metadata, items_from_document(document)


def load_queue_document(path: Path = QUEUE_PATH) -> dict[str, Any]:
    """Read the complete active queue document dictionary."""
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as file_handle:
        document = json.load(file_handle)
    return document if isinstance(document, dict) else {}



def merge_duplicate(current: dict[str, Any], duplicate: dict[str, Any]) -> None:
    """Preserve useful provenance without replacing the first-ranked item."""
    provenance = current.setdefault("provenance_sources", [])
    for candidate in (
        current.get("source_name") or current.get("source"),
        duplicate.get("source_name") or duplicate.get("source"),
    ):
        if candidate and candidate not in provenance:
            provenance.append(candidate)
    if duplicate.get("top_comments") and not current.get("top_comments"):
        current["top_comments"] = duplicate["top_comments"]


def dedupe_items(items: Iterable[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    deduped: dict[str, dict[str, Any]] = {}
    duplicate_count = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        key = item_key(item)
        if not key:
            continue
        current = deduped.get(key)
        if current is None:
            deduped[key] = item
            continue
        duplicate_count += 1
        merge_duplicate(current, item)
    return list(deduped.values()), duplicate_count


def filter_recent_items(
    items: Iterable[dict[str, Any]],
    *,
    days: float,
    keep_undated: bool = True,
) -> list[dict[str, Any]]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    recent = []
    for item in items:
        published_at = item.get("published_at")
        if not published_at:
            if keep_undated:
                recent.append(item)
            continue
        try:
            published = datetime.fromisoformat(str(published_at).replace("Z", "+00:00"))
        except ValueError:
            if keep_undated:
                recent.append(item)
            continue
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)
        if published >= cutoff:
            recent.append(item)
    return recent


def atomic_json_write(path: Path, document: Any) -> None:
    """Replace a JSON file atomically so interrupted writes keep old state."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as file_handle:
            temp_path = Path(file_handle.name)
            json.dump(document, file_handle, indent=2, ensure_ascii=False)
            file_handle.flush()
            os.fsync(file_handle.fileno())
        temp_path.replace(path)
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink()


def queue_document(
    items: list[dict[str, Any]],
    *,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    policy = queue_policy()
    merged_metadata = {
        "description": "Active intelligence queue aggregated from configured source registry outputs",
        "max_items_kept": int(policy.get("active_queue_max_items", 1000)),
        "dedupe": "canonical_url",
        **(metadata or {}),
    }
    return {
        "metadata": merged_metadata,
        "last_updated": utc_now_iso(),
        "total_items": len(items),
        "items": items,
    }


def replace_queue(
    items: Iterable[dict[str, Any]],
    *,
    path: Path = QUEUE_PATH,
    metadata: dict[str, Any] | None = None,
    sort_key: Callable[[dict[str, Any]], Any] | None = None,
    max_items: int | None = None,
) -> tuple[dict[str, Any], int]:
    normalized, duplicate_count = dedupe_items(items)
    if sort_key:
        normalized.sort(key=sort_key, reverse=True)
    limit = max_items if max_items is not None else int(
        queue_policy().get("active_queue_max_items", 1000)
    )
    normalized = normalized[:limit]
    document = queue_document(normalized, metadata=metadata)
    document["metadata"]["max_items_kept"] = limit
    atomic_json_write(path, document)
    return document, duplicate_count


def merge_queue(
    new_items: Iterable[dict[str, Any]],
    *,
    path: Path = QUEUE_PATH,
    metadata: dict[str, Any] | None = None,
    sort_key: Callable[[dict[str, Any]], Any] | None = None,
    max_items: int | None = None,
) -> tuple[dict[str, Any], int, int]:
    existing_metadata, existing_items = load_queue(path)
    existing_keys = {item_key(item) for item in existing_items}
    unique_new_items = [
        item for item in new_items if item_key(item) and item_key(item) not in existing_keys
    ]
    document, duplicate_count = replace_queue(
        unique_new_items + existing_items,
        path=path,
        metadata={**existing_metadata, **(metadata or {})},
        sort_key=sort_key,
        max_items=max_items,
    )
    return document, len(unique_new_items), duplicate_count

