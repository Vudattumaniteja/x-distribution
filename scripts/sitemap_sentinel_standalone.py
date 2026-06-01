import requests
import xml.etree.ElementTree as ET
import json
import os
from datetime import datetime, timezone

# Target Sitemaps for Deep Signal Discovery
SITEMAPS = {
    "OpenAI": "https://openai.com/sitemap.xml",
    "Anthropic": "https://www.anthropic.com/sitemap.xml",
    "Google DeepMind": "https://deepmind.google/sitemap.xml",
    "Mistral": "https://mistral.ai/sitemap.xml",
    "xAI": "https://x.ai/sitemap.xml",
    "Moonshot": "https://www.moonshot.cn/sitemap.xml",
    "Qwen": "https://qwenlm.github.io/sitemap.xml"
}

HISTORY_FILE = 'data/sitemap_history.json'
OUTPUT_FILE = 'data/sitemap_discoveries.json'

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_history(history):
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)

def fetch_sitemap_urls(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Handle sitemap indexes (nested sitemaps)
        root = ET.fromstring(response.content)
        namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        
        urls = []
        # Check for <sitemap> tags (index) or <url> tags (direct)
        sitemaps = root.findall('.//ns:sitemap/ns:loc', namespace)
        if sitemaps:
            for s in sitemaps:
                urls.extend(fetch_sitemap_urls(s.text))
        else:
            locs = root.findall('.//ns:url/ns:loc', namespace)
            urls = [loc.text for loc in locs]
            
        return list(set(urls))
    except Exception as e:
        print(f"Error fetching sitemap {url}: {e}")
        return []

def main():
    history = load_history()
    new_discoveries = []
    
    for company, sitemap_url in SITEMAPS.items():
        print(f"Scanning {company} Sitemap...")
        current_urls = fetch_sitemap_urls(sitemap_url)
        
        if current_urls:
            previous_urls = set(history.get(company, []))
            new_links = [u for u in current_urls if u not in previous_urls]
            
            if new_links:
                print(f"  -> DISCOVERED {len(new_links)} new pages!")
                for link in new_links:
                    new_discoveries.append({
                        "company": company,
                        "url": link,
                        "discovered_at": datetime.now(timezone.utc).isoformat()
                    })
        else:
            print(f"  -> FAILURE: Could not retrieve URLs for {company}")
            continue
        
        # Update history
        history[company] = current_urls

    save_history(history)
    
    with open(OUTPUT_FILE, 'w') as f:
        json.dump({
            "last_run": datetime.now(timezone.utc).isoformat(),
            "new_discoveries": new_discoveries
        }, f, indent=2)
    
    print(f"Scan complete. Total new discoveries: {len(new_discoveries)}")

if __name__ == "__main__":
    main()
