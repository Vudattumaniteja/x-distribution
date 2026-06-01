import urllib.request
import xml.etree.ElementTree as ET
import json
import time
import os
from datetime import datetime, timezone
import re

HEADERS = {"User-Agent": "XDistributionArxivSentinel/2.0 (contact: local-run)"}
HEALTH_PATH = "data/arxiv_source_health.json"


def fetch_bytes(url, timeout=30):
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def fetch_arxiv_with_retry(url, retries=2, delay=8):
    """Fetch ArXiv API with exponential backoff to handle 2026 high-load issues."""
    for i in range(retries):
        try:
            print(f"  (Attempt {i+1}) Connecting to ArXiv API...")
            return fetch_bytes(url, timeout=30)
        except Exception as e:
            if i == retries - 1:
                raise e
            print(f"  (RETRY) Error: {e}. Retrying in {delay}s...")
            time.sleep(delay)
            delay *= 2 # Exponential backoff

def fetch_arxiv_wildcards():
    # Query cs.AI and cs.CL for the last 100 results
    # We look for specific high-signal keywords in the abstract
    url = "http://export.arxiv.org/api/query?search_query=cat:cs.AI+OR+cat:cs.CL&sortBy=submittedDate&sortOrder=descending&max_results=100"
    
    keywords = ["sota", "state-of-the-art", "outperforms", "new model", "benchmark", "million token", "billion parameter", "skillos", "emergent modularity"]
    discoveries = []
    
    try:
        xml_data = fetch_arxiv_with_retry(url)
        root = ET.fromstring(xml_data)
        
        namespace = {'atom': 'http://www.w3.org/2005/Atom'}
        
        for entry in root.findall('atom:entry', namespace):
            title = entry.find('atom:title', namespace).text.replace('\n', ' ').strip()
            summary = entry.find('atom:summary', namespace).text.replace('\n', ' ').strip()
            published = entry.find('atom:published', namespace).text
            link = entry.find('atom:id', namespace).text
            
            # Check if abstract contains our high-signal keywords
            summary_lower = summary.lower()
            title_lower = title.lower()
            if any(kw in summary_lower or kw in title_lower for kw in keywords):
                discoveries.append({
                    "id": f"arxiv_{link.split('/')[-1]}",
                    "title": f"ArXiv: {title}",
                    "url": link,
                    "source": "ArXiv",
                    "published_at": published,
                    "summary": summary[:500] + "..."
                })
    except Exception as e:
        print(f"  API unavailable after retry; falling back to arXiv RSS: {e}")
        discoveries = fetch_arxiv_rss_fallback(keywords)
        
    return discoveries


def fetch_arxiv_rss_fallback(keywords):
    discoveries = []
    urls = [
        "https://rss.arxiv.org/rss/cs.AI",
        "https://rss.arxiv.org/rss/cs.CL",
        "https://rss.arxiv.org/rss/cs.LG",
    ]
    for rss_url in urls:
        try:
            xml_data = fetch_bytes(rss_url, timeout=20)
            root = ET.fromstring(xml_data)
        except Exception as exc:
            print(f"  RSS fallback unavailable for {rss_url}: {exc}")
            continue
        for item in root.findall(".//item"):
            title = (item.findtext("title") or "").replace("\n", " ").strip()
            summary = (item.findtext("description") or "").replace("\n", " ").strip()
            link = (item.findtext("link") or "").strip()
            published = item.findtext("pubDate") or datetime.now(timezone.utc).isoformat()
            haystack = f"{title} {summary}".lower()
            if any(keyword in haystack for keyword in keywords):
                discoveries.append({
                    "id": f"arxiv_{link.rsplit('/', 1)[-1]}",
                    "title": f"ArXiv: {title}",
                    "url": link,
                    "source": "ArXiv RSS",
                    "published_at": published,
                    "summary": summary[:500] + ("..." if len(summary) > 500 else ""),
                    "discovery_method": "arxiv_rss_fallback",
                })
    deduped = {item["url"]: item for item in discoveries if item.get("url")}
    return list(deduped.values())

def main():
    print("Scanning ArXiv for technical breakthroughs...")
    discoveries = fetch_arxiv_wildcards()
    
    output_path = 'data/arxiv_raw_standalone.json'
    health = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "status": "OK" if discoveries else "NO_NEW_DISCOVERIES_OR_USING_EXISTING_CACHE",
        "items": len(discoveries),
        "cache_preserved": bool(not discoveries and os.path.exists(output_path)),
    }
    os.makedirs("data", exist_ok=True)
    with open(HEALTH_PATH, "w", encoding="utf-8") as f:
        json.dump(health, f, indent=2)

    # Preserve existing discoveries if live API/RSS yields no matches.
    if not discoveries and os.path.exists(output_path):
        print("No new ArXiv discoveries from live API/RSS; keeping existing cache.")
        return

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "new_discoveries": discoveries
        }, f, indent=2)
    
    print(f"Done. Saved {len(discoveries)} ArXiv discoveries to {output_path}")

if __name__ == "__main__":
    main()
