import requests
import json
import hashlib
import time
import re
from datetime import datetime, timezone

class TruthOracle:
    def __init__(self, cache_path='cache/timestamp_oracle.json'):
        self.cache_path = cache_path
        self.cache = self._load_cache()
        self.headers = {
            "User-Agent": "TemporalSentinel/1.0.0 (Intelligence Integrity Pipeline; contact@manit.ai)"
        }

    def _load_cache(self):
        try:
            with open(self.cache_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"version": "1.0.0", "entries": {}}

    def _save_cache(self):
        with open(self.cache_path, 'w') as f:
            json.dump(self.cache, f, indent=2)

    def normalize_string(self, s):
        # sha256(normalized_string) where normalization = lowercase, strip whitespace, strip punctuation except internal hyphens
        s = s.lower().strip()
        s = re.sub(r'[^\w\s-]', '', s) # Remove punctuation except hyphens
        return re.sub(r'\s+', ' ', s) # Collapse whitespace

    def get_hash(self, s):
        return hashlib.sha256(self.normalize_string(s).encode()).hexdigest()

    def fetch_github_release(self, org, repo, tag=None):
        cache_key = f"github:{org}/{repo}:{tag or 'latest'}"
        if cache_key in self.cache['entries']:
            return self.cache['entries'][cache_key]

        url = f"https://api.github.com/repos/{org}/{repo}/releases"
        if tag:
            url += f"/tags/{tag}"
        else:
            url += "/latest"
            
        try:
            # Note: Using public API, might need token if rate limited
            response = requests.get(url, headers=self.headers, timeout=15)
            if response.status_code == 200:
                data = response.json()
                entry = {
                    "source": "github_release",
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "timestamp": data['published_at'],
                    "raw": {"tag_name": data['tag_name'], "published_at": data['published_at']},
                    "ttl_days": 365
                }
                self.cache['entries'][cache_key] = entry
                self._save_cache()
                return entry
        except Exception as e:
            print(f"GH Error: {e}")
        return None

    def fetch_hf_lastmodified(self, model_id):
        cache_key = f"hf:{model_id}"
        if cache_key in self.cache['entries']:
            return self.cache['entries'][cache_key]

        # Try API first
        url = f"https://huggingface.co/api/models/{model_id}"
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            if response.status_code == 200:
                data = response.json()
                entry = {
                    "source": "huggingface_lastmodified",
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "timestamp": data['lastModified'],
                    "raw": {"lastModified": data['lastModified']},
                    "ttl_days": 30
                }
                self.cache['entries'][cache_key] = entry
                self._save_cache()
                return entry
        except Exception as e:
            print(f"HF API Error: {e}")

        # Fallback to huggingface_hub library
        try:
            from huggingface_hub import model_info
            model = model_info(model_id)
            ts = model.last_modified.isoformat() if hasattr(model.last_modified, 'isoformat') else str(model.last_modified)
            entry = {
                "source": "huggingface_hub_lib",
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "timestamp": ts,
                "raw": {"last_modified": ts},
                "ttl_days": 30
            }
            self.cache['entries'][cache_key] = entry
            self._save_cache()
            return entry
        except Exception as e:
            print(f"HF Lib Error: {e}")
        
        return None

    def fetch_wayback_first_seen(self, target_url):
        cache_key = f"wayback:{target_url}"
        if cache_key in self.cache['entries']:
            return self.cache['entries'][cache_key]

        # Wayback CDX API - get first snapshot
        url = f"https://web.archive.org/cdx/search/cdx?url={target_url}&output=json&limit=1&sort=timestamp:asc"
        try:
            time.sleep(1.0) # Increased delay for Wayback stability
            response = requests.get(url, headers=self.headers, timeout=60) # Massive timeout for Wayback
            if response.status_code == 200:
                data = response.json()
                if len(data) > 1: # data[0] is header
                    snapshot = data[1]
                    # Format: [urlkey, timestamp, original, mimetype, statuscode, digest, length]
                    ts_str = snapshot[1] # YYYYMMDDHHMMSS
                    ts_iso = datetime.strptime(ts_str, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc).isoformat()
                    
                    entry = {
                        "source": "wayback_cdx",
                        "type": "first_snapshot",
                        "fetched_at": datetime.now(timezone.utc).isoformat(),
                        "timestamp": ts_iso,
                        "raw": {"first_snapshot": ts_str},
                        "ttl_days": 90
                    }
                    self.cache['entries'][cache_key] = entry
                    self._save_cache()
                    return entry
        except Exception as e:
            print(f"Wayback Error: {e}")
        return None

    def fetch_sec_edgar(self, ticker, form_type="8-K"):
        # This is a simplified mockup as SEC requires specific headers and 
        # often multi-stage lookup (CIK -> Submissions). 
        # For Stage 1, we establish the pattern.
        cache_key = f"sec:{ticker}:{form_type}"
        if cache_key in self.cache['entries']:
            return self.cache['entries'][cache_key]
        
        # Real implementation would hit: https://data.sec.gov/submissions/CIK{cik}.json
        # For now, we'll return a stub to show the schema alignment.
        return None

# Test Diagnostic
if __name__ == "__main__":
    oracle = TruthOracle()
    print("--- GitHub Test ---")
    print(oracle.fetch_github_release("openai", "openai-python"))
    print("\n--- HF Test (Public Model) ---")
    print(oracle.fetch_hf_lastmodified("gpt2")) # GPT-2 is public and non-gated
    print("\n--- Wayback Test ---")
    print(oracle.fetch_wayback_first_seen("https://openai.com/index/gpt-5-5-instant/"))
