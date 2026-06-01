import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime, timezone
import re

def fetch_direct_tldr():
    # Use today's date for the URL
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    url = f"https://tldr.tech/ai/{today_str}"
    print(f"Attempting to fetch direct issue: {url}")
    
    try:
        response = requests.get(url, timeout=15)
        if response.status_code != 200:
            print(f"  → Issue not found for {today_str} (Status: {response.status_code})")
            return
        
        soup = BeautifulSoup(response.text, 'html.parser')
        announcements = []
        
        # TLDR 2026 structure uses <a> tags with specific UTM sources for headlines
        # They are often inside <h3> or just bare <a> with (X minute read)
        links = soup.find_all('a', href=re.compile(r'utm_source=tldrai'))
        
        for link_tag in links:
            title = link_tag.get_text().strip()
            # Clean up (X minute read) from title
            title = re.sub(r'\s*\(\d+\s*minute\s*read\)', '', title, flags=re.I)
            url_link = link_tag['href']
            
            # The summary is usually the next sibling or parent's next sibling
            summary = ""
            parent = link_tag.parent
            # Try to get the text after the link
            full_text = parent.get_text()
            summary = full_text.replace(link_tag.get_text(), "").strip()[:300]
            
            if not summary and parent.next_sibling:
                summary = parent.next_sibling.get_text().strip()[:300]

            if title and url_link and len(title) > 10:
                announcements.append({
                    "title": title,
                    "url": url_link,
                    "published_at": datetime.now(timezone.utc).isoformat(),
                    "source": "TLDR AI (Direct)",
                    "tier": "tier_2",
                    "summary": summary
                })
        
        if not announcements:
            print("  → Could not parse any articles from the page. Trying backup selector...")
            # Fallback to general link search if UTM matching fails
            for h3 in soup.find_all('h3'):
                a = h3.find('a')
                if a:
                    announcements.append({
                        "title": a.get_text().strip(),
                        "url": a['href'],
                        "published_at": datetime.now(timezone.utc).isoformat(),
                        "source": "TLDR AI (Direct)",
                        "tier": "tier_2",
                        "summary": h3.parent.get_text().replace(a.get_text(), "").strip()[:300]
                    })

        if not announcements:
             print("  → Failed to extract data.")
             return

        # Load existing data to merge
        output_path = 'data/corporate_announcements.json'
        if os.path.exists(output_path):
            with open(output_path, 'r') as f:
                existing_data = json.load(f)
        else:
            existing_data = {"announcements": []}
            
        # Add new announcements
        existing_data['announcements'] = announcements + existing_data['announcements']
        existing_data['last_updated'] = datetime.now(timezone.utc).isoformat()
        
        # Deduplicate and sort by date (if possible, otherwise keep order)
        seen_urls = set()
        unique_announcements = []
        for a in existing_data['announcements']:
            if a['url'] not in seen_urls:
                unique_announcements.append(a)
                seen_urls.add(a['url'])
        
        existing_data['announcements'] = unique_announcements
        
        with open(output_path, 'w') as f:
            json.dump(existing_data, f, indent=2)
            
        print(f"Success! Ingested {len(announcements)} fresh items from TLDR {today_str}")

    except Exception as e:
        print(f"  → Error fetching direct issue: {e}")

if __name__ == "__main__":
    fetch_direct_tldr()
