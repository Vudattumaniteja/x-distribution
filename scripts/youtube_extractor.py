import requests
import re
import json
import sys
import os
import subprocess
from youtube_transcript_api import YouTubeTranscriptApi

def fetch_via_api(video_id):
    """Option A: youtube-transcript-api"""
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join([t['text'] for t in transcript])
    except Exception:
        return None

def fetch_via_scrape(video_id):
    """Option B: Direct player data scrape"""
    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=15)
        html = response.text
        
        # Extract ytInitialPlayerResponse
        match = re.search(r'ytInitialPlayerResponse\s*=\s*({.*?});', html)
        if not match:
            return None
            
        data = json.loads(match.group(1))
        # Navigate to caption tracks
        caption_tracks = data.get('captions', {}).get('playerCaptionsTracklistRenderer', {}).get('captionTracks', [])
        
        if not caption_tracks:
            return None
            
        # Get the first available track (usually English)
        caption_url = caption_tracks[0]['baseUrl']
        xml_response = requests.get(caption_url, timeout=10)
        
        # Simple XML tag stripping to get plain text
        text = re.sub(r'<[^>]*>', ' ', xml_response.text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    except Exception as e:
        print(f"Scrape error for {video_id}: {e}")
        return None

def fetch_via_ytdlp(video_id):
    """Option C: yt-dlp for auto-subs"""
    import subprocess
    import glob
    try:
        # Download only the description and auto-subs, no video
        cmd = [
            sys.executable,
            '-m',
            'yt_dlp',
            '--skip-download', 
            '--write-auto-subs', 
            '--sub-lang', 'en', 
            '--sub-format', 'vtt',
            '--output', f'data/sub_{video_id}',
            f'https://www.youtube.com/watch?v={video_id}'
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        
        # Find the downloaded file
        files = glob.glob(f'data/sub_{video_id}.en.vtt')
        if files:
            with open(files[0], 'r', encoding='utf-8') as f:
                content = f.read()
            # Clean VTT tags
            text = re.sub(r'WEBVTT.*?\n\n', '', content, flags=re.DOTALL)
            text = re.sub(r'\d{2}:\d{2}:\d{2}\.\d{3}.*?\n', '', text)
            text = re.sub(r'<[^>]*>', '', text)
            text = re.sub(r'\s+', ' ', text).strip()
            # Cleanup file
            os.remove(files[0])
            return text
    except Exception as e:
        print(f"yt-dlp error for {video_id}: {e}")
    return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python youtube_extractor.py VIDEO_ID")
        sys.exit(1)

    # Retained as a backend module for yt_transcript_cli.py; direct execution
    # is routed through the canonical transcript CLI.
    from yt_transcript_cli import get_transcript
    output_path = f"data/transcript_{sys.argv[1]}.txt"
    res = get_transcript(sys.argv[1], output=output_path)
    sys.exit(0 if res is not None else 1)
