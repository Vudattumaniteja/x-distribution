"""Compatibility entrypoint routed to the canonical YT Transcript CLI."""

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


def _video_ids_from_queue(queue):
    if isinstance(queue, list):
        return [item["video_id"] for item in queue if "video_id" in item]
    ids = []
    for videos in queue.values():
        ids.extend(item["video_id"] for item in videos if "video_id" in item)
    return ids


if __name__ == "__main__":
    if len(sys.argv) > 1:
        sys.exit(0 if scrape_transcript(sys.argv[1]) else 1)

    queue_path = "data/new_videos_queue.json"
    if os.path.exists(queue_path):
        with open(queue_path, "r", encoding="utf-8") as file_handle:
            for video_id in _video_ids_from_queue(json.load(file_handle)):
                transcript_path = f"data/transcript_{video_id}.txt"
                if not os.path.exists(transcript_path) or os.path.getsize(transcript_path) <= 500:
                    scrape_transcript(video_id)
