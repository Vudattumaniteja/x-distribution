"""
yt-transcript — YouTube Transcript CLI
=======================================

A CLI tool for the X Distribution Pipeline that fetches YouTube transcripts
via NoteGPT.io using Playwright browser automation.

Commands:
    get     <url> [-o FILE]                 Fetch transcript for a single video
    latest  <channel> [--days N] [-o DIR]   Pull all videos in a day window & transcript them
    verify                                  Run a self-test on a known video to confirm everything works

Global access:
    This tool is registered at C:\\Users\\Manit\\bin\\yt-transcript.cmd
    so it can be called from anywhere: yt-transcript get <url>
"""
import sys
import os
import re
import json
import argparse
import time
from pathlib import Path
from datetime import datetime, timedelta, timezone

sys.stdout.reconfigure(encoding="utf-8")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
NOTEGPT = "https://notegpt.io/youtube-transcript-generator"
RESULT_URL_RE = re.compile(r"notegpt\.io/detail\?id=")

# A short, known-good video for the verify command
VERIFY_VIDEO = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
VERIFY_EXPECT_SUBSTR = "never gonna give you up"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRANSCRIPTS_DIR = PROJECT_ROOT / "data" / "transcripts"


# ===========================================================================
# Core: Transcript fetcher (from get_transcript.py — proven working)
# ===========================================================================
def fetch_transcript(youtube_url: str, output_file: str = None, quiet: bool = False) -> str | None:
    """Fetch a YouTube transcript via NoteGPT. Returns transcript text or None."""
    from playwright.sync_api import sync_playwright

    def log(msg):
        if not quiet:
            print(msg)

    log(f"  URL: {youtube_url}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            permissions=["clipboard-read", "clipboard-write"],
        )
        page = context.new_page()

        try:
            # STEP 1: Load NoteGPT
            log("  [1/5] Loading NoteGPT...")
            page.goto(NOTEGPT, wait_until="networkidle", timeout=30_000)

            # STEP 2: Fill URL
            log("  [2/5] Filling YouTube URL...")
            textbox = page.get_by_role("textbox", name="Paste the YouTube video link")
            textbox.click()
            page.wait_for_timeout(300)
            textbox.fill(youtube_url)
            page.wait_for_timeout(300)

            # STEP 3: Click Generate → navigate to /detail?id=VIDEO_ID
            log("  [3/5] Clicking Generate Transcript...")
            page.get_by_role("button", name="Generate Transcript").click()

            log("        Waiting for result page...")
            page.wait_for_url(RESULT_URL_RE, wait_until="load", timeout=30_000)
            page.wait_for_load_state("networkidle", timeout=60_000)

            # STEP 4: Wait for the Copy button in the DOM, then click via JS
            log("  [4/5] Waiting for transcript (up to 90s)...")

            copy_selector = 'button[id^="reka-popover-trigger-"]'
            page.wait_for_selector(copy_selector, state="attached", timeout=90_000)

            # Poll until a Copy button with text="Copy" appears
            for _ in range(20):
                found = page.evaluate("""
                    () => {
                        const btns = document.querySelectorAll(
                            'button[id^="reka-popover-trigger-"]'
                        );
                        for (const btn of btns) {
                            if (btn.textContent.trim() === 'Copy') return true;
                        }
                        return false;
                    }
                """)
                if found:
                    break
                page.wait_for_timeout(2000)
            else:
                log("  ERROR: Copy button never appeared in the DOM.")
                return None

            log("        Transcript ready. Clicking Copy via JS...")

            # JS click the first Copy popover trigger (bypasses visibility)
            page.evaluate("""
                () => {
                    const btns = document.querySelectorAll(
                        'button[id^="reka-popover-trigger-"]'
                    );
                    for (const btn of btns) {
                        if (btn.textContent.trim() === 'Copy') {
                            btn.click();
                            return;
                        }
                    }
                }
            """)
            page.wait_for_timeout(1500)

            # Click "Copy with timestamp"
            menu_item = page.get_by_text("Copy with timestamp")
            if menu_item.count() > 0:
                try:
                    menu_item.first.click(timeout=3000)
                    log("        Clicked 'Copy with timestamp'.")
                except Exception:
                    page.evaluate("""
                        () => {
                            const items = document.querySelectorAll('*');
                            for (const el of items) {
                                if (el.textContent.trim() === 'Copy with timestamp') {
                                    el.click(); return;
                                }
                            }
                        }
                    """)
                    log("        Clicked 'Copy with timestamp' (JS fallback).")
            else:
                log("        'Copy with timestamp' not found, trying 'Copy Transcript'...")
                page.evaluate("""
                    () => {
                        const btns = document.querySelectorAll(
                            'button[id^="reka-popover-trigger-"]'
                        );
                        for (const btn of btns) {
                            if (btn.textContent.trim() === 'Copy Transcript') {
                                btn.click(); return;
                            }
                        }
                    }
                """)

            page.wait_for_timeout(1500)

            # STEP 5: Read clipboard
            log("  [5/5] Reading clipboard...")
            transcript = page.evaluate("navigator.clipboard.readText()")

            if not transcript:
                log("  ERROR: Clipboard was empty.")
                return None

            line_count = transcript.count("\n") + 1
            char_count = len(transcript)
            log(f"  SUCCESS: {line_count} lines, {char_count:,} chars")

            if output_file:
                Path(output_file).parent.mkdir(parents=True, exist_ok=True)
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(transcript)
                log(f"  Saved: {output_file}")

            return transcript

        except Exception as e:
            log(f"  ERROR: {e}")
            return None

        finally:
            context.close()
            browser.close()


# ===========================================================================
# Feature: Pull latest videos from a channel (via yt-dlp + RSS)
# ===========================================================================
def parse_upload_datetime(entry: dict) -> datetime | None:
    timestamp = entry.get("timestamp") or entry.get("release_timestamp")
    if timestamp:
        try:
            return datetime.fromtimestamp(int(timestamp), tz=timezone.utc)
        except (TypeError, ValueError, OSError):
            pass
    upload_date = entry.get("upload_date") or entry.get("release_date")
    if upload_date:
        try:
            return datetime.strptime(upload_date, "%Y%m%d").replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return None


def enrich_video_metadata(video: dict) -> dict:
    """Fetch per-video metadata when flat playlist entries omit upload dates."""
    import yt_dlp

    if video.get("published_at"):
        return video
    ydl_opts = {"quiet": True, "no_warnings": True, "skip_download": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(video["url"], download=False)
        except Exception:
            return video
    published = parse_upload_datetime(info or {})
    if published:
        video["published_at"] = published.isoformat()
    if info:
        video["duration"] = video.get("duration") or info.get("duration")
        video["title"] = video.get("title") or info.get("title", "Unknown")
    return video


def get_latest_videos(
    channel_url: str,
    count: int | None = 1,
    days: int | None = None,
    max_scan: int = 500,
) -> list[dict]:
    """Return videos from a YouTube channel using yt-dlp.

    If days is set and count is None, return every video found inside the time
    window, bounded only by max_scan as a guard against accidentally walking a
    whole large channel history.
    """
    import yt_dlp

    # Normalize URL
    base = channel_url.rstrip("/")
    if not base.endswith("/videos"):
        base += "/videos"

    playlist_end = max_scan if days and count is None else (count or 1)
    ydl_opts = {
        "extract_flat": True,
        "quiet": True,
        "no_warnings": True,
        "playlistend": playlist_end,
    }

    cutoff = None
    if days is not None and days > 0:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    videos = []
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(base, download=False)
            if info and "entries" in info:
                for entry in info["entries"]:
                    if not entry:
                        continue
                    vid_url = entry.get("url") or f"https://www.youtube.com/watch?v={entry.get('id', '')}"
                    published = parse_upload_datetime(entry)
                    video = {
                        "title": entry.get("title", "Unknown"),
                        "url": vid_url,
                        "id": entry.get("id", ""),
                        "duration": entry.get("duration"),
                        "published_at": published.isoformat() if published else None,
                    }
                    if cutoff and not video["published_at"]:
                        video = enrich_video_metadata(video)
                    if cutoff:
                        if not video.get("published_at"):
                            continue
                        try:
                            video_dt = datetime.fromisoformat(video["published_at"].replace("Z", "+00:00"))
                            if video_dt < cutoff:
                                if count is None:
                                    break
                                continue
                        except ValueError:
                            continue
                    videos.append(video)
        except Exception as e:
            print(f"  ERROR fetching channel: {e}")

    return videos if count is None else videos[:count]


# ===========================================================================
# Commands
# ===========================================================================
def cmd_get(args):
    """Fetch transcript for a single YouTube video."""
    print(f"\n{'='*60}")
    print(f"  yt-transcript get")
    print(f"{'='*60}")

    transcript = fetch_transcript(args.url, args.output)

    if transcript and not args.output:
        print(f"\n{'-'*60}")
        print(transcript[:1000])
        if len(transcript) > 1000:
            print(f"\n... [{transcript.count(chr(10))+1} total lines — use -o FILE to save]")
        print(f"{'-'*60}")

    return 0 if transcript else 1


def cmd_latest(args):
    """Pull latest video(s) from a channel and transcript them."""
    print(f"\n{'='*60}")
    print(f"  yt-transcript latest")
    print(f"  Channel: {args.channel}")
    if args.count:
        print(f"  Count:   {args.count}")
    else:
        print(f"  Count:   all videos in window")
    if args.days:
        print(f"  Days:    {args.days}")
        print(f"  MaxScan: {args.max_scan}")
    print(f"{'='*60}\n")

    # Step 1: Get latest video URLs
    print("[STEP 1] Fetching latest videos from channel...")
    videos = get_latest_videos(args.channel, args.count, args.days, args.max_scan)

    if not videos:
        print("ERROR: No videos found on this channel.")
        return 1

    print(f"  Found {len(videos)} video(s):\n")
    for i, v in enumerate(videos, 1):
        duration_str = f" ({v['duration']}s)" if v.get("duration") else ""
        published_str = f" [{v['published_at']}]" if v.get("published_at") else ""
        print(f"  {i}. {v['title']}{duration_str}{published_str}")
        print(f"     {v['url']}")
    print()

    # Step 2: Transcript each video
    out_dir = Path(args.output_dir) if args.output_dir else TRANSCRIPTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for i, video in enumerate(videos, 1):
        print(f"\n[STEP 2.{i}] Transcribing: {video['title']}")
        print(f"{'-'*60}")

        # Build output filename from video ID
        vid_id = video.get("id") or re.sub(r"[^\w]", "_", video["url"][-11:])
        safe_title = re.sub(r'[<>:"/\\|?*]', '_', video["title"])[:60]
        out_file = out_dir / f"{vid_id}_{safe_title}.txt"

        transcript = fetch_transcript(video["url"], str(out_file))

        result = {
            "video": video,
            "transcript_file": str(out_file) if transcript else None,
            "success": transcript is not None,
            "lines": transcript.count("\n") + 1 if transcript else 0,
            "chars": len(transcript) if transcript else 0,
            "timestamp": datetime.now().isoformat(),
        }
        results.append(result)

    # Summary
    ok = sum(1 for r in results if r["success"])
    fail = len(results) - ok

    print(f"\n{'='*60}")
    print(f"  RESULTS: {ok} succeeded, {fail} failed")
    print(f"{'='*60}")
    for r in results:
        status = "✓" if r["success"] else "✗"
        print(f"  {status} {r['video']['title'][:50]}")
        if r["success"]:
            print(f"    → {r['transcript_file']} ({r['lines']} lines, {r['chars']:,} chars)")
        else:
            print(f"    → FAILED")

    # Save manifest
    manifest_file = out_dir / "_latest_run.json"
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n  Manifest: {manifest_file}")

    return 0 if fail == 0 else 1


def cmd_verify(args):
    """Self-test: transcript a known video and validate the output."""
    print(f"\n{'='*60}")
    print(f"  yt-transcript verify")
    print(f"  Testing with: {VERIFY_VIDEO}")
    print(f"{'='*60}\n")

    start = time.time()
    transcript = fetch_transcript(VERIFY_VIDEO)
    elapsed = time.time() - start

    print(f"\n{'-'*60}")
    print(f"  Time:     {elapsed:.1f}s")

    if not transcript:
        print(f"  Status:   FAIL — no transcript returned")
        print(f"  Action:   Check if NoteGPT is reachable and Playwright browsers are installed")
        print(f"{'-'*60}")
        return 1

    lines = transcript.count("\n") + 1
    chars = len(transcript)
    has_timestamps = bool(re.search(r"\d{2}:\d{2}:\d{2}", transcript))
    has_expected = VERIFY_EXPECT_SUBSTR.lower() in transcript.lower()

    print(f"  Lines:    {lines}")
    print(f"  Chars:    {chars:,}")
    print(f"  Stamps:   {'YES ✓' if has_timestamps else 'NO ✗'}")
    print(f"  Content:  {'MATCH ✓' if has_expected else 'NO MATCH ✗'}")

    all_ok = lines > 5 and chars > 200 and has_timestamps
    print(f"  Status:   {'PASS ✓' if all_ok else 'FAIL ✗'}")
    print(f"{'-'*60}")

    if all_ok:
        print("\n  ✓ Transcript pipeline is working correctly.")
    else:
        print("\n  ✗ Something is off. Check:")
        if lines <= 5:
            print("    - Transcript too short (expected >5 lines)")
        if not has_timestamps:
            print("    - No timestamps found (expected HH:MM:SS format)")
        if chars <= 200:
            print("    - Too few characters (expected >200)")

    return 0 if all_ok else 1


# ===========================================================================
# CLI Entry Point
# ===========================================================================
def main():
    parser = argparse.ArgumentParser(
        prog="yt-transcript",
        description="YouTube Transcript CLI — fetch, batch, and verify transcripts via NoteGPT",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  yt-transcript get "https://youtu.be/abc123"
  yt-transcript get "https://youtu.be/abc123" -o transcript.txt
  yt-transcript latest "https://www.youtube.com/@mkbhd" --days 2
  yt-transcript latest "https://www.youtube.com/@mkbhd" -n 3 --days 2
  yt-transcript latest "https://www.youtube.com/@mkbhd" -n 1 -o ./transcripts
  yt-transcript verify
        """,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # --- get ---
    p_get = sub.add_parser("get", help="Fetch transcript for a single YouTube video")
    p_get.add_argument("url", help="YouTube video URL")
    p_get.add_argument("-o", "--output", help="Save transcript to file")

    # --- latest ---
    p_latest = sub.add_parser("latest", help="Pull latest video(s) from a channel & transcript them")
    p_latest.add_argument("channel", help="YouTube channel URL (e.g. https://www.youtube.com/@mkbhd)")
    p_latest.add_argument("-n", "--count", type=int, help="Optional cap on videos to transcript")
    p_latest.add_argument("--days", type=int, default=2, help="Only keep videos published in the last N days (default: 2)")
    p_latest.add_argument("--max-scan", type=int, default=500, help="Safety cap for playlist items inspected when count is omitted")
    p_latest.add_argument("-o", "--output-dir", help=f"Output directory (default: data/transcripts/)")

    # --- verify ---
    sub.add_parser("verify", help="Self-test: transcript a known video to verify the pipeline")

    args = parser.parse_args()

    if args.command == "get":
        sys.exit(cmd_get(args))
    elif args.command == "latest":
        sys.exit(cmd_latest(args))
    elif args.command == "verify":
        sys.exit(cmd_verify(args))


if __name__ == "__main__":
    main()
