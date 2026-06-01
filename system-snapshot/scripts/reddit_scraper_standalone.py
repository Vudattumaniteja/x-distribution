import requests
import json
import time
from datetime import datetime, timezone

SUBREDDITS = [
    "MachineLearning",
    "singularity",
    "OpenAI",
    "LocalLLaMA",
    "ArtificialInteligence"
]

def fetch_reddit_posts(subreddit):
    url = f"https://www.reddit.com/r/{subreddit}/new.json?limit=25"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        posts = []
        for post in data['data']['children']:
            p = post['data']
            posts.append({
                "id": p['id'],
                "title": p['title'],
                "url": f"https://www.reddit.com{p['permalink']}",
                "author": p['author'],
                "score": p['score'],
                "num_comments": p['num_comments'],
                "created_utc": p['created_utc'],
                "subreddit": subreddit,
                "text": p.get('selftext', '')[:500]
            })
        return posts
    except Exception as e:
        print(f"Error fetching r/{subreddit}: {e}")
        return []

def main():
    all_posts = []
    for sub in SUBREDDITS:
        print(f"Scraping r/{sub}...")
        posts = fetch_reddit_posts(sub)
        all_posts.extend(posts)
        time.sleep(2) # Avoid rate limits
    
    # Save to a temporary standalone file for integration
    output_path = 'data/reddit_raw_standalone.json'
    with open(output_path, 'w') as f:
        json.dump({
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "posts": all_posts
        }, f, indent=2)
    
    print(f"Done. Saved {len(all_posts)} posts to {output_path}")

if __name__ == "__main__":
    main()
