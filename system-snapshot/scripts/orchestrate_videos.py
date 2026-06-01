import json
import os
import subprocess
from source_clis import yt_transcript_command

def orchestrate():
    queue_path = 'data/new_videos_queue.json'
    if not os.path.exists(queue_path):
        print("No new videos found.")
        return

    with open(queue_path, 'r') as f:
        queue = json.load(f)

    for handle, videos in queue.items():
        print(f"Processing {handle}...")
        for v in videos:
            v_id = v['video_id']
            print(f"  -> Extracting {v_id}: {v['title']}")
            subprocess.run(
                yt_transcript_command("get", v_id, "-o", f"data/transcript_{v_id}.txt"),
                check=False,
            )

if __name__ == "__main__":
    orchestrate()
