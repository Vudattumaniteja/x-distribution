import requests
import json
from datetime import datetime, timezone
import os

def fetch_paper_by_id(arxiv_id):
    url = f"https://api.semanticscholar.org/graph/v1/paper/ARXIV:{arxiv_id}?fields=title,url,abstract,publicationDate,externalIds"
    print(f"Fetching paper ARXIV:{arxiv_id} from Semantic Scholar...")
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"  → Failed (Status: {response.status_code})")
    except Exception as e:
        print(f"  → Error: {e}")
    return None

def search_paper_by_query(query):
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "limit": 1,
        "fields": "title,url,abstract,publicationDate,externalIds"
    }
    print(f"Searching for '{query}' on Semantic Scholar...")
    try:
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data.get('data'):
                return data['data'][0]
        else:
            print(f"  → Failed (Status: {response.status_code})")
    except Exception as e:
        print(f"  → Error: {e}")
    return None

def main():
    papers_to_find = [
        {"id": "2605.06614", "label": "SkillOS"},
        {"query": "EMO: Emergent Modularity in Mixture-of-Experts", "label": "EMO"}
    ]
    
    discoveries = []
    
    for item in papers_to_find:
        paper = None
        if "id" in item:
            paper = fetch_paper_by_id(item['id'])
        if not paper and "query" in item:
            paper = search_paper_by_query(item['query'])
            
        if paper:
            print(f"  → Found: {paper.get('title')}")
            # Format to match news_queue/arxiv_raw schema
            discoveries.append({
                "id": f"semantic_{paper.get('paperId', 'unknown')}",
                "title": paper.get('title'),
                "url": paper.get('url') or (f"https://arxiv.org/abs/{paper['externalIds']['ArXiv']}" if 'externalIds' in paper and 'ArXiv' in paper['externalIds'] else ""),
                "source": "Semantic Scholar / ArXiv",
                "published_at": paper.get('publicationDate') + "T00:00:00Z" if paper.get('publicationDate') else datetime.now(timezone.utc).isoformat(),
                "summary": paper.get('abstract', 'No abstract available')[:500] + "..."
            })

    if discoveries:
        output_path = 'data/arxiv_raw_standalone.json'
        # Load existing if any
        if os.path.exists(output_path):
            try:
                with open(output_path, 'r') as f:
                    existing = json.load(f)
                    # Merge
                    seen_urls = {d['url'] for d in discoveries}
                    for old in existing.get('new_discoveries', []):
                        if old['url'] not in seen_urls:
                            discoveries.append(old)
            except:
                pass
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "new_discoveries": discoveries
            }, f, indent=2)
        print(f"Successfully updated {output_path} with {len(discoveries)} total papers.")
    else:
        print("No papers found.")

if __name__ == "__main__":
    main()
