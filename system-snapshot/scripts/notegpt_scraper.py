"""Snapshot compatibility entrypoint routed to the canonical YT Transcript CLI."""

import json
import os
import subprocess
import sys

from source_clis import yt_transcript_command


def scrape_transcript(video_id):
    output_path = f"data/transcript_{video_id}.txt"
    os.makedirs("data", exist_ok=True)
    result = subprocess.run(
        yt_transcript_command("get", video_id, "-o", output_path),
        capture_output=True,
        text=True,
    )
    if result.returncode == 0 and os.path.exists(output_path):
        print(f"[SUCCESS] Transcript saved through YT Transcript CLI: {output_path}")
        return True
    print(f"[FAILURE] YT Transcript CLI failed for {video_id}: {result.stderr.strip()}")
    return False


if __name__ == "__main__":
    if len(sys.argv) > 1:
        sys.exit(0 if scrape_transcript(sys.argv[1]) else 1)
    if os.path.exists("data/new_videos_queue.json"):
        with open("data/new_videos_queue.json", "r", encoding="utf-8") as file_handle:
            queue = json.load(file_handle)
        for videos in queue.values():
            for video in videos:
                scrape_transcript(video["video_id"])
