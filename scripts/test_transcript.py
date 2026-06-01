import subprocess
import sys
from source_clis import yt_transcript_command

def get_transcript(video_id):
    result = subprocess.run(
        yt_transcript_command("get", video_id),
        capture_output=True,
        text=True,
    )
    print(result.stdout, end="")
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
    return result.returncode

if __name__ == "__main__":
    if len(sys.argv) > 1:
        sys.exit(get_transcript(sys.argv[1]))
