import argparse
import os
import sys

# We leverage the existing logic in the workspace.
from youtube_extractor import fetch_via_api, fetch_via_scrape, fetch_via_ytdlp
from youtube_channel_fetcher import fetch_recent_rss


INVALID_TRANSCRIPT_MARKERS = (
    "Google Sorry",
    "We're sorry",
    "automated queries",
    "To protect our users, we can't process your request right now",
)


def is_valid_transcript(content):
    if not content:
        return False
    if len(content.strip()) < 200:
        return False
    return not any(marker in content for marker in INVALID_TRANSCRIPT_MARKERS)


def get_transcript(url, output=None):
    video_id = url.split("v=")[-1] if "v=" in url else url.split("/")[-1]
    video_id = video_id.split("?")[0].split("&")[0]

    print(f"Fetching transcript for: {video_id}...")

    content = fetch_via_api(video_id)
    if not is_valid_transcript(content):
        print("API failed, trying scrape...")
        content = fetch_via_scrape(video_id)
    if not is_valid_transcript(content):
        print("Scrape failed, trying yt-dlp...")
        content = fetch_via_ytdlp(video_id)

    if is_valid_transcript(content):
        if output:
            with open(output, "w", encoding="utf-8") as file_handle:
                file_handle.write(content)
            print(f"Saved to {output}")
        else:
            print("\n--- Transcript Snippet ---")
            print(content[:500] + "...")
        return content

    print("FAILURE: Could not retrieve a valid transcript.")
    return None


def fetch_latest(channel_url, count=1, output_dir="data/transcripts"):
    from youtube_channel_fetcher import get_channel_id

    print(f"Fetching latest {count} videos from {channel_url}...")
    channel_id = get_channel_id(channel_url)
    if not channel_id:
        print("Could not resolve channel ID.")
        return

    videos = fetch_recent_rss(channel_id, days=7)
    if not videos:
        print("No recent videos found.")
        return

    os.makedirs(output_dir, exist_ok=True)

    for index, video in enumerate(videos[:count], start=1):
        print(f"\nProcessing Video {index}: {video['title']}")
        file_path = os.path.join(output_dir, f"transcript_{video['video_id']}.txt")
        transcript = get_transcript(video["video_id"], output=file_path)
        if not transcript and os.path.exists(file_path):
            os.remove(file_path)


def verify():
    print("Running self-test on known video (j2knrqAzYVY)...")
    result = get_transcript("j2knrqAzYVY")
    if result and "Claude" in result:
        print("\nVERIFY PASS: Transcript content validated.")
    else:
        print("\nVERIFY FAIL: Content mismatch.")


def main():
    parser = argparse.ArgumentParser(description="Unified YouTube Transcript CLI")
    subparsers = parser.add_subparsers(dest="command", help="Sub-command to run")

    get_parser = subparsers.add_parser("get", help="Fetch transcript for a single video")
    get_parser.add_argument("url", help="YouTube video URL or ID")
    get_parser.add_argument("-o", "--output", help="Save to file")

    latest_parser = subparsers.add_parser("latest", help="Pull latest videos + transcripts")
    latest_parser.add_argument("channel", help="Channel URL")
    latest_parser.add_argument("-n", "--count", type=int, default=1, help="Number of videos")
    latest_parser.add_argument(
        "-o",
        "--output_dir",
        default="data/transcripts",
        help="Output directory",
    )

    subparsers.add_parser("verify", help="Run self-test")

    args = parser.parse_args()

    if args.command == "get":
        get_transcript(args.url, args.output)
    elif args.command == "latest":
        fetch_latest(args.channel, args.count, args.output_dir)
    elif args.command == "verify":
        verify()
    else:
        parser.print_help()


if __name__ == "__main__":
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    main()
