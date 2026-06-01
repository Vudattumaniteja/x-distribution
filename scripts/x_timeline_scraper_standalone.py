"""Compatibility X timeline collector routed exclusively through XCLI."""

import json
import os
import sys
from datetime import datetime, timezone

from source_registry import collection_runtime_policy
from x_collection_coordinator import collect_x_read_only

CONFIG_PATH = "config/followed_accounts.json"
OUTPUT_PATH = "data/x_raw_standalone.json"

def main():
    if not os.path.exists(CONFIG_PATH):
        print("Config not found.")
        return 1

    with open(CONFIG_PATH, "r", encoding="utf-8") as file_handle:
        config = json.load(file_handle)

    all_tweets = []
    handles = [acc["handle"] for acc in config["accounts"] if acc["tier"] == "must_follow"][:10]
    workers = max(1, int(collection_runtime_policy().get("x_workers", 3)))
    print(f"Collecting compatibility watchlist timelines through {workers} coordinator worker(s)...")
    result = collect_x_read_only(
        handles,
        workers=workers,
        days=7,
        skip_home=True,
    )
    per_account_counts = {}
    for tweet in result["tweets"]:
        handle = tweet.get("_x_collection_scope", "").partition(":")[2]
        count = per_account_counts.get(handle, 0)
        if count >= 5:
            continue
        per_account_counts[handle] = count + 1
        all_tweets.append(tweet)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as file_handle:
        json.dump(
            {
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "run_id": result["run_id"],
                "status": result["status"],
                "tweets": all_tweets,
            },
            file_handle,
            indent=2,
        )
    print(f"Done. Saved {len(all_tweets)} tweets to {OUTPUT_PATH}")
    return 1 if result["status"] == "FAILED" else 0


if __name__ == "__main__":
    sys.exit(main())
