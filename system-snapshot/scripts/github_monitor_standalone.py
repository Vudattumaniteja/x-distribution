import requests
import json
import os
from datetime import datetime, timezone

# Orgs to monitor on GitHub
GH_ORGS = ["openai", "anthropic-ai", "google-deepmind", "mistralai", "xai-org"]

HISTORY_FILE = 'data/github_history.json'
OUTPUT_FILE = 'data/github_discoveries.json'

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_history(history):
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)

def fetch_gh_repos(org):
    url = f"https://api.github.com/orgs/{org}/repos?sort=updated&direction=desc&per_page=10"
    headers = {"Accept": "application/vnd.github.v3+json"}
    try:
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching GitHub org {org}: {e}")
        return []

def main():
    history = load_history()
    new_discoveries = []
    
    for org in GH_ORGS:
        print(f"Scanning GitHub: {org}...")
        current_repos = fetch_gh_repos(org)
        
        if not current_repos:
            continue
            
        # We track repo IDs and their last push date
        previous_data = history.get(org, {})
        
        for repo in current_repos:
            repo_id = str(repo['id'])
            last_push = repo['pushed_at']
            
            if repo_id not in previous_data:
                print(f"  NEW REPOSITORY DISCOVERED: {repo['full_name']}")
                new_discoveries.append({
                    "source": "GitHub",
                    "org": org,
                    "type": "new_repo",
                    "repo_name": repo['full_name'],
                    "url": repo['html_url'],
                    "description": repo.get('description', ''),
                    "discovered_at": datetime.now(timezone.utc).isoformat()
                })
            elif previous_data[repo_id] != last_push:
                # Significant update - you could add logic here to filter for "major" updates
                # For now we'll just log it as an update if we want to be very sensitive
                pass
        
        # Update history
        history[org] = {str(r['id']): r['pushed_at'] for r in current_repos}

    save_history(history)
    
    if new_discoveries:
        with open(OUTPUT_FILE, 'w') as f:
            json.dump({
                "last_run": datetime.now(timezone.utc).isoformat(),
                "new_discoveries": new_discoveries
            }, f, indent=2)
    
    print(f"GitHub Scan complete. Total new discoveries: {len(new_discoveries)}")

if __name__ == "__main__":
    main()
