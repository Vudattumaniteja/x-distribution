"""Snapshot compatibility X timeline collector routed through XCLI."""

import json
import os
import subprocess
from datetime import datetime, timezone

from source_clis import xcli_command


def scrape_x_timeline(handle, count=5):
    result = subprocess.run(
        xcli_command("twitter_scrape", "--handle", handle.replace("@", ""), "--count", str(count)),
        capture_output=True,
        text=True,
        timeout=180,
    )
    start = result.stdout.find("[")
    end = result.stdout.rfind("]")
    return json.loads(result.stdout[start:end + 1]) if start >= 0 and end > start else []


def main():
    config_path = "config/followed_accounts.json"
    output_path = "data/x_raw_standalone.json"
    if not os.path.exists(config_path):
        print("Config not found.")
        return
    with open(config_path, "r", encoding="utf-8") as file_handle:
        config = json.load(file_handle)
    handles = [acc["handle"] for acc in config["accounts"] if acc["tier"] == "must_follow"][:10]
    tweets = []
    for handle in handles:
        tweets.extend(scrape_x_timeline(handle))
    with open(output_path, "w", encoding="utf-8") as file_handle:
        json.dump({"last_updated": datetime.now(timezone.utc).isoformat(), "tweets": tweets}, file_handle, indent=2)


if __name__ == "__main__":
    main()
