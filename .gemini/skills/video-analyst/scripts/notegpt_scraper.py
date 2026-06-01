import json
import os
import sys
import time
from playwright.sync_api import sync_playwright

def scrape_transcript(video_id):
    # NoteGPT Generator Home
    home_url = "https://notegpt.io/youtube-transcript-generator"
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    
    print(f"[*] Processing {video_id} via {home_url}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        try:
            # 1. Go to generator home
            page.goto(home_url, wait_until="networkidle", timeout=60000)
            
            # 2. Fill the YouTube link
            page.get_by_role("textbox", name="Paste the YouTube video link").fill(video_url)
            
            # 3. Click Generate
            page.get_by_role("button", name="Generate Transcript").click()
            
            # 4. Wait for the transcript detail page to load
            # It redirects to /detail?id=...
            print("[*] Waiting for redirection and transcript render...")
            page.wait_for_url(f"**/detail?id={video_id}**", timeout=30000)
            
            # 5. Wait for the 'Copy' menu trigger (The popover trigger from codegen)
            # The ID might be dynamic (#reka-popover-trigger-v-0-50), so we use a more stable locator
            # Looking at the UI, there's usually a copy icon or menu
            time.sleep(10) # Heavy wait for AI processing
            
            # Attempt to click the copy menu if it exists, otherwise scrape directly
            try:
                # Based on codegen, there's a trigger for a menu
                # We can try to click any button that looks like a copy or more menu
                page.locator("button:has-text('Copy'), button:has-text('More')").first.click(timeout=5000)
                page.get_by_text("Copy without timestamp").click(timeout=5000)
                
                # After clicking 'Copy', the text is in the clipboard. 
                # Since we can't easily access the OS clipboard in headless, 
                # we'll scrape the rendered list which is now definitely loaded.
                print("[+] Copy triggered, now scraping rendered text...")
            except:
                print("[!] Copy menu interaction failed, falling back to direct scrape...")

            # 6. Scrape the list
            elements = page.query_selector_all(".transcript-item, [class*='transcript-item']")
            if elements:
                transcript_text = " ".join([el.inner_text() for el in elements])
            else:
                # Broad fallback
                transcript_text = page.inner_text("body")

            if transcript_text and len(transcript_text) > 300:
                # Clean up
                import re
                clean_text = transcript_text.replace("\n", " ").strip()
                clean_text = re.sub(r'\d{1,2}:\d{2}', '', clean_text)
                clean_text = re.sub(r'\[.*?\]', '', clean_text)
                
                output_path = f"data/transcript_{video_id}.txt"
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(clean_text)
                print(f"[SUCCESS] Transcript saved for {video_id} ({len(clean_text)} chars)")
                return True
            else:
                print(f"[FAILURE] No valid transcript found for {video_id}")
                # Save debug screenshot
                if not os.path.exists('logs'): os.makedirs('logs')
                page.screenshot(path=f"logs/debug_scrape_{video_id}.png")
                return False
                
        except Exception as e:
            print(f"[ERROR] {e}")
            if not os.path.exists('logs'): os.makedirs('logs')
            page.screenshot(path=f"logs/error_{video_id}.png")
            return False
        finally:
            browser.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        scrape_transcript(sys.argv[1])
    else:
        if os.path.exists("data/new_videos_queue.json"):
            with open("data/new_videos_queue.json", "r") as f:
                queue = json.load(f)
            
            for channel, videos in queue.items():
                for video in videos:
                    v_id = video['video_id']
                    # Process if missing or just a CAPTCHA/Error
                    t_path = f"data/transcript_{v_id}.txt"
                    if os.path.exists(t_path) and os.path.getsize(t_path) > 500:
                        continue
                    
                    scrape_transcript(v_id)
                    time.sleep(5)
