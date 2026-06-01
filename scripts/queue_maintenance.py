"""Normalize and deduplicate the active news queue."""

from __future__ import annotations

from intelligence_queue import QUEUE_PATH, load_queue, replace_queue


def sort_key(item: dict) -> tuple:
    category_rank = {
        "deep-discovery": 3,
        "community-discussion": 2,
        "video-discovery": 1,
    }
    return (
        float(item.get("combined_score") or 0),
        category_rank.get(item.get("category"), 0),
        item.get("published_at") or "",
    )


def main() -> None:
    if not QUEUE_PATH.exists():
        print(f"Queue not found: {QUEUE_PATH}")
        return

    metadata, items = load_queue()
    output, duplicate_count = replace_queue(items, metadata=metadata, sort_key=sort_key)

    print(f"Queue normalized: {len(items)} -> {output['total_items']} items; duplicates merged: {duplicate_count}")


if __name__ == "__main__":
    main()
