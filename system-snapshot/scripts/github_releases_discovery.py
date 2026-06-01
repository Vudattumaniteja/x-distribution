import requests
import json
import os
from datetime import datetime, timezone

# Target Repos for Release Discovery
REPOS = [
    ("openai", "openai-python"),
    ("anthropic-ai", "anthropic-sdk-python"),
    ("google-deepmind", "gemma"),
    ("mistralai", "mistral-common"),
    ("meta-llama", "llama-models")
]

HISTORY_FILE = 'data/release_history.json'
OUTPUT_FILE = 'data/release_discoveries.json'

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_history(history):
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)

def fetch_latest_release(org, repo):
    url = f"https://api.github.com/repos/{org}/{repo}/releases/latest"
    headers = {"Accept": "application/vnd.github.v3+json"}
    try:
        response = requests.get(url, headers=headers, timeout=20)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching release for {org}/{repo}: {e}")
        return None

def main():
    history = load_history()
    new_discoveries = []
    
    for org, repo in REPOS:
        full_name = f"{org}/{repo}"
        print(f"Checking GitHub Releases: {full_name}...")
        release = fetch_latest_release(org, repo)
        
        if not release:
            continue
            
        release_id = str(release['id'])
        last_release_id = history.get(full_name)
        
        if release_id != last_release_id:
            print(f"  🔥 NEW RELEASE DISCOVERED: {release['tag_name']}")
            new_discoveries.append({
                "source": "GitHub Release",
                "org": org,
                "repo": repo,
                "tag": release['tag_name'],
                "url": release['html_url'],
                "published_at": release['published_at'],
                "discovered_at": datetime.now(timezone.utc).isoformat(),
                "summary": release.get('body', '')[:300]
            })
            history[full_name] = release_id

    save_history(history)
    
    if new_discoveries:
        with open(OUTPUT_FILE, 'w') as f:
            json.dump({
                "last_run": datetime.now(timezone.utc).isoformat(),
                "new_discoveries": new_discoveries
            }, f, indent=2)
    
    print(f"GitHub Release Scan complete. New: {len(new_discoveries)}")

if __name__ == "__main__":
    main()
