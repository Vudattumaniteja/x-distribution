"""Compatibility X timeline collector routed exclusively through XCLI."""

import json
import os
from datetime import datetime, timezone

from xcli_utils import collect_timeline_tweets


def scrape_x_timeline(handle, count=5):
    safe_handle = handle.replace("@", "")
    return collect_timeline_tweets(
        safe_handle,
        days=7,
        output_path=f"cache/xcli_standalone_{safe_handle}.json",
    )[:count]


def main():
    config_path = "config/followed_accounts.json"
    output_path = "data/x_raw_standalone.json"
    if not os.path.exists(config_path):
        print("Config not found.")
        return

    with open(config_path, "r", encoding="utf-8") as file_handle:
        config = json.load(file_handle)

    all_tweets = []
    handles = [acc["handle"] for acc in config["accounts"] if acc["tier"] == "must_follow"][:10]
    for handle in handles:
        print(f"Collecting {handle} through XCLI...")
        all_tweets.extend(scrape_x_timeline(handle))

    with open(output_path, "w", encoding="utf-8") as file_handle:
        json.dump(
            {"last_updated": datetime.now(timezone.utc).isoformat(), "tweets": all_tweets},
            file_handle,
            indent=2,
        )
    print(f"Done. Saved {len(all_tweets)} tweets to {output_path}")


if __name__ == "__main__":
    main()
