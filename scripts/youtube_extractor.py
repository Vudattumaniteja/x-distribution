import os
import sys
import re
import json
import requests
import tempfile
import glob
import html
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from youtube_transcript_api import YouTubeTranscriptApi

PROJECT_ROOT = Path(__file__).resolve().parent.parent

def extract_video_id(url_or_id: str) -> str | None:
    if not url_or_id:
        return None
    url_or_id = url_or_id.strip()
    if len(url_or_id) == 11 and re.match(r'^[a-zA-Z0-9_-]{11}$', url_or_id):
        return url_or_id
    v_match = re.search(r'(?:v=|\/v\/|embed\/|shorts\/|youtu\.be\/|\/embed\/|\/watch\?v=|\?v=)([a-zA-Z0-9_-]{11})', url_or_id)
    if v_match:
        return v_match.group(1)
    if len(url_or_id) >= 11:
        end_match = re.search(r'([a-zA-Z0-9_-]{11})(?:[?&]|$)', url_or_id)
        if end_match:
            return end_match.group(1)
    return None

def format_timestamp(seconds: float) -> str:
    total_seconds = int(seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    return f"[{hours:02d}:{minutes:02d}:{secs:02d}]"

def fetch_via_api(video_id: str) -> str | None:
    """Option A: youtube-transcript-api"""
    try:
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'en-US'])
        except Exception:
            transcript_list = None
            try:
                transcripts = YouTubeTranscriptApi.list_transcripts(video_id)
                for t in transcripts:
                    transcript_list = t.fetch()
                    break
            except Exception:
                pass
                
        if not transcript_list:
            return None
            
        lines = []
        for entry in transcript_list:
            start = entry.get('start', 0.0)
            text = entry.get('text', '').strip()
            if text:
                text = text.replace('\n', ' ')
                lines.append(f"{format_timestamp(start)} {text}")
        if lines:
            return "\n".join(lines)
    except Exception as e:
        print(f"youtube-transcript-api error for {video_id}: {e}")
    return None

def parse_xml_transcript(xml_content: str) -> str | None:
    try:
        if not xml_content.strip().startswith('<transcript'):
            xml_content = re.sub(r'<\?xml[^>]*\?>', '', xml_content)
            xml_content = f"<transcript>{xml_content}</transcript>"
        
        root = ET.fromstring(xml_content.encode('utf-8'))
        lines = []
        for child in root.iter('text'):
            start_val = child.attrib.get('start', '0.0')
            try:
                start_sec = float(start_val)
            except ValueError:
                start_sec = 0.0
            
            text_parts = []
            if child.text:
                text_parts.append(child.text)
            for sub in child:
                if sub.text:
                    text_parts.append(sub.text)
                if sub.tail:
                    text_parts.append(sub.tail)
            text = "".join(text_parts)
            text = html.unescape(text).strip()
            text = text.replace('\n', ' ')
            text = re.sub(r'<[^>]*>', '', text)
            if text:
                lines.append(f"{format_timestamp(start_sec)} {text}")
        if lines:
            return "\n".join(lines)
    except Exception:
        lines = []
        matches = re.findall(r'<text[^>]+start="([^"]+)"[^>]*>([^<]*)</text>', xml_content)
        for start_val, text_val in matches:
            try:
                start_sec = float(start_val)
            except ValueError:
                start_sec = 0.0
            text = html.unescape(text_val).strip()
            text = text.replace('\n', ' ')
            text = re.sub(r'<[^>]*>', '', text)
            if text:
                lines.append(f"{format_timestamp(start_sec)} {text}")
        if lines:
            return "\n".join(lines)
    return None

def fetch_via_scrape(video_id: str) -> str | None:
    """Option B: Direct player data scrape of ytInitialPlayerResponse XML caption track"""
    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        html_text = response.text
        
        match = re.search(r'ytInitialPlayerResponse\s*=\s*({.*?});\s*(?:var|meta|script|</script>)', html_text) or re.search(r'ytInitialPlayerResponse\s*=\s*({.*?});', html_text)
        if not match:
            return None
            
        data = json.loads(match.group(1))
        caption_tracks = data.get('captions', {}).get('playerCaptionsTracklistRenderer', {}).get('captionTracks', [])
        
        if not caption_tracks:
            return None
            
        caption_url = None
        for track in caption_tracks:
            lang_code = track.get('languageCode', '')
            if lang_code.startswith('en'):
                caption_url = track.get('baseUrl')
                break
        if not caption_url and caption_tracks:
            caption_url = caption_tracks[0].get('baseUrl')
            
        if not caption_url:
            return None
            
        xml_response = requests.get(caption_url, headers=headers, timeout=10)
        xml_content = xml_response.text
        if not xml_content or len(xml_content.strip()) == 0:
            return None
            
        return parse_xml_transcript(xml_content)
    except Exception as e:
        print(f"Scrape error for {video_id}: {e}")
    return None

def parse_vtt_transcript(vtt_content: str) -> str | None:
    lines = vtt_content.splitlines()
    blocks = []
    current_time = None
    current_text = []
    
    timestamp_re = re.compile(r'(?:(\d{2}):)?(\d{2}):(\d{2})\.(\d{3})\s+-->')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        m = timestamp_re.match(line)
        if m:
            if current_time is not None and current_text:
                text_str = " ".join(current_text).strip()
                text_str = re.sub(r'<[^>]*>', '', text_str)
                text_str = re.sub(r'\s+', ' ', text_str).strip()
                if text_str:
                    blocks.append((current_time, text_str))
            
            hrs = m.group(1)
            mins = m.group(2)
            secs = m.group(3)
            
            h = int(hrs) if hrs else 0
            m_int = int(mins)
            s_int = int(secs)
            
            current_time = f"[{h:02d}:{m_int:02d}:{s_int:02d}]"
            current_text = []
        elif current_time is not None:
            if line.startswith("WEBVTT") or line.startswith("Kind:") or line.startswith("Language:") or line.startswith("Style:"):
                continue
            current_text.append(line)
            
    if current_time is not None and current_text:
        text_str = " ".join(current_text).strip()
        text_str = re.sub(r'<[^>]*>', '', text_str)
        text_str = re.sub(r'\s+', ' ', text_str).strip()
        if text_str:
            blocks.append((current_time, text_str))
            
    deduped_blocks = []
    for t_str, txt in blocks:
        txt = re.sub(r'<[^>]*>', '', txt)
        txt = re.sub(r'\s+', ' ', txt).strip()
        if not txt:
            continue
        if deduped_blocks and deduped_blocks[-1][1] == txt:
            continue
        deduped_blocks.append((t_str, txt))
        
    if deduped_blocks:
        return "\n".join([f"{t_str} {txt}" for t_str, txt in deduped_blocks])
    return None

def fetch_via_ytdlp(video_id: str) -> str | None:
    """Option C: Auto-subs via yt-dlp --skip-download --write-auto-subs"""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_template = os.path.join(tmpdir, "sub")
        cmd = [
            sys.executable,
            '-m',
            'yt_dlp',
            '--skip-download', 
            '--write-auto-subs', 
            '--sub-lang', 'en', 
            '--sub-format', 'vtt',
            '--output', output_template,
            f'https://www.youtube.com/watch?v={video_id}'
        ]
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=60)
            vtt_files = glob.glob(os.path.join(tmpdir, "*.vtt"))
            if vtt_files:
                vtt_file = vtt_files[0]
                with open(vtt_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                return parse_vtt_transcript(content)
        except Exception as e:
            print(f"yt-dlp error for {video_id}: {e}")
    return None

def fetch_via_notegpt(youtube_url: str, quiet: bool = False) -> str | None:
    """Option D: NoteGPT Playwright scraping as a final fallback"""
    from playwright.sync_api import sync_playwright

    NOTEGPT = "https://notegpt.io/youtube-transcript-generator"
    RESULT_URL_RE = re.compile(r"notegpt\.io/detail\?id=")

    def log(msg):
        if not quiet:
            print(msg)

    log(f"  [Option D] Running Playwright fallback for URL: {youtube_url}")

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(
                viewport={"width": 1280, "height": 720},
                permissions=["clipboard-read", "clipboard-write"],
            )
            page = context.new_page()

            log("  [1/5] Loading NoteGPT...")
            page.goto(NOTEGPT, wait_until="networkidle", timeout=30_000)

            log("  [2/5] Filling YouTube URL...")
            textbox = page.get_by_role("textbox", name="Paste the YouTube video link")
            textbox.click()
            page.wait_for_timeout(300)
            textbox.fill(youtube_url)
            page.wait_for_timeout(300)

            log("  [3/5] Clicking Generate Transcript...")
            page.get_by_role("button", name="Generate Transcript").click()

            log("        Waiting for result page...")
            page.wait_for_url(RESULT_URL_RE, wait_until="load", timeout=30_000)
            page.wait_for_load_state("networkidle", timeout=60_000)

            log("  [4/5] Waiting for transcript (up to 90s)...")
            copy_selector = 'button[id^="reka-popover-trigger-"]'
            page.wait_for_selector(copy_selector, state="attached", timeout=90_000)

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

            log("  [5/5] Reading clipboard...")
            transcript = page.evaluate("navigator.clipboard.readText()")

            if not transcript:
                log("  ERROR: Clipboard was empty.")
                return None

            line_count = transcript.count("\n") + 1
            char_count = len(transcript)
            log(f"  SUCCESS: {line_count} lines, {char_count:,} chars")
            return transcript

        except Exception as e:
            log(f"  ERROR NoteGPT Playwright: {e}")
            return None
        finally:
            try:
                context.close()
                browser.close()
            except Exception:
                pass

def mark_transcript_unavailable(video_id_or_url: str):
    video_id = extract_video_id(video_id_or_url)
    video_url = video_id_or_url if video_id_or_url.startswith("http") else f"https://www.youtube.com/watch?v={video_id}"
    
    unavailable_file = PROJECT_ROOT / "data" / "transcripts_unavailable.json"
    unavailable_file.parent.mkdir(parents=True, exist_ok=True)
    
    data = {}
    if unavailable_file.exists():
        try:
            with open(unavailable_file, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    data = json.loads(content)
        except Exception:
            data = {}
            
    if not isinstance(data, dict):
        data = {}
        
    if "videos" not in data or not isinstance(data["videos"], dict):
        data["videos"] = {}
        
    data["last_updated"] = datetime.now(timezone.utc).isoformat()
    
    if video_id not in data["videos"]:
        data["videos"][video_id] = {
            "title": "Unavailable/Music/No Captions",
            "channel": "Unknown",
            "url": video_url,
            "reason": "no_manual_or_automatic_captions_detected",
            "last_checked": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            temp_file = unavailable_file.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(temp_file, unavailable_file)
        except Exception as e:
            print(f"Warning: could not write transcripts_unavailable.json: {e}")

def fetch_transcript(youtube_url: str, output_file: str = None, quiet: bool = False) -> str | None:
    """Fetch transcript using prioritized fallback sequence (Option A -> B -> C -> D)."""
    video_id = extract_video_id(youtube_url)
    if not video_id:
        if not quiet:
            print(f"ERROR: Could not extract video ID from {youtube_url}")
        return None
        
    transcript = None
    
    # Try Option A: youtube-transcript-api
    if not quiet:
        print(f"Trying Option A (youtube-transcript-api) for {video_id}...")
    transcript = fetch_via_api(video_id)
    if transcript:
        if not quiet:
            print("  Option A Succeeded.")
    else:
        # Try Option B: Direct player scrape
        if not quiet:
            print(f"Trying Option B (Direct Player Scrape) for {video_id}...")
        transcript = fetch_via_scrape(video_id)
        if transcript:
            if not quiet:
                print("  Option B Succeeded.")
        else:
            # Try Option C: yt-dlp auto-subs
            if not quiet:
                print(f"Trying Option C (yt-dlp auto-subs) for {video_id}...")
            transcript = fetch_via_ytdlp(video_id)
            if transcript:
                if not quiet:
                    print("  Option C Succeeded.")
            else:
                # Try Option D: NoteGPT Playwright
                if not quiet:
                    print(f"Trying Option D (NoteGPT Playwright) for {video_id}...")
                transcript = fetch_via_notegpt(youtube_url, quiet=quiet)
                if transcript:
                    if not quiet:
                        print("  Option D Succeeded.")
                        
    if transcript:
        if output_file:
            try:
                out_path = Path(output_file)
                out_path.parent.mkdir(parents=True, exist_ok=True)
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(transcript)
                if not quiet:
                    print(f"  Saved: {output_file}")
            except Exception as e:
                print(f"Error saving transcript to {output_file}: {e}")
        return transcript
    else:
        print(f"Warning: No captions/transcript available across all methods for video: {youtube_url}")
        mark_transcript_unavailable(youtube_url)
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python youtube_extractor.py VIDEO_ID_OR_URL")
        sys.exit(1)

    video_input = sys.argv[1]
    if not video_input.startswith("http"):
        video_url = f"https://www.youtube.com/watch?v={video_input}"
    else:
        video_url = video_input
        
    video_id = extract_video_id(video_url)
    output_path = f"data/transcript_{video_id}.txt"
    res = fetch_transcript(video_url, output_file=output_path)
    sys.exit(0 if res is not None else 1)
