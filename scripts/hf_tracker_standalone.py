import requests
import json
import os
from datetime import datetime, timezone

from source_registry import hugging_face_orgs

HISTORY_FILE = 'data/hf_history.json'
OUTPUT_FILE = 'data/hf_discoveries.json'

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_history(history):
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)

def fetch_hf_models(org):
    url = f"https://huggingface.co/api/models?author={org}&sort=lastModified&direction=-1&limit=10"
    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching HF org {org}: {e}")
        return []

def main():
    history = load_history()
    new_discoveries = []
    
    for org in hugging_face_orgs():
        print(f"Scanning Hugging Face: {org}...")
        current_models = fetch_hf_models(org)
        
        if not current_models:
            continue
            
        previous_ids = set(history.get(org, []))
        
        for model in current_models:
            model_id = model['id']
            if model_id not in previous_ids:
                print(f"  NEW MODEL DISCOVERED: {model_id}")
                new_discoveries.append({
                    "source": "Hugging Face",
                    "org": org,
                    "model_id": model_id,
                    "url": f"https://huggingface.co/{model_id}",
                    "last_modified": model.get('lastModified'),
                    "discovered_at": datetime.now(timezone.utc).isoformat()
                })
        
        # Update history with current top 50 IDs to keep it lean
        history[org] = [m['id'] for m in current_models]

    save_history(history)
    
    if new_discoveries:
        with open(OUTPUT_FILE, 'w') as f:
            json.dump({
                "last_run": datetime.now(timezone.utc).isoformat(),
                "new_discoveries": new_discoveries
            }, f, indent=2)
    
    print(f"HF Scan complete. Total new discoveries: {len(new_discoveries)}")

if __name__ == "__main__":
    main()
