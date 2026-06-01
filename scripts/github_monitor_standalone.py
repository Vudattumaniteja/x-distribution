import requests
import json
import os
from datetime import datetime, timezone

from source_registry import github_orgs

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
    
    # Discovery cutoff (48 hours)
    MAX_AGE_HOURS = 48
    now = datetime.now(timezone.utc)
    
    for org in github_orgs():
        print(f"Scanning GitHub: {org}...")
        current_repos = fetch_gh_repos(org)
        
        if not current_repos:
            continue
            
        previous_data = history.get(org, {})
        
        for repo in current_repos:
            repo_id = str(repo['id'])
            last_push = repo['pushed_at']
            created_at = datetime.fromisoformat(repo['created_at'].replace('Z', '+00:00'))
            
            # Freshness check: Was this repo created recently?
            is_fresh = (now - created_at).total_seconds() / 3600 <= MAX_AGE_HOURS
            
            if repo_id not in previous_data and is_fresh:
                print(f"  NEW REPOSITORY DISCOVERED: {repo['full_name']}")
                new_discoveries.append({
                    "source": "GitHub",
                    "org": org,
                    "type": "new_repo",
                    "repo_name": repo['full_name'],
                    "url": repo['html_url'],
                    "description": repo.get('description', ''),
                    "discovered_at": datetime.now(timezone.utc).isoformat(),
                    "created_at": repo['created_at']
                })
            elif repo_id in previous_data and previous_data[repo_id] != last_push:
                # This repo existed but has been updated
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
