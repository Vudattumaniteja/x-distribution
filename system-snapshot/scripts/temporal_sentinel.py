import json
import hashlib
import os
import re
import time
from datetime import datetime, timezone, timedelta
from scripts.truth_oracle import TruthOracle

class TemporalSentinel:
    def __init__(self, ledger_path='cache/claim_ledger.json', search_cache_path='cache/search_results.json'):
        self.ledger_path = ledger_path
        self.search_cache_path = search_cache_path
        self.oracle = TruthOracle()
        self.ledger = self._load_json(self.ledger_path, {"version": "1.0.0", "window_days": 14, "entries": {}})
        self.search_cache = self._load_json(self.search_cache_path, {"version": "1.0.0", "entries": {}})
        self.version = "1.0.0"

    def _load_json(self, path, default):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return default

    def _save_json(self, path, data):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def _save_caches(self):
        # Prune ledger
        cutoff = (datetime.now(timezone.utc) - timedelta(days=self.ledger.get('window_days', 14))).isoformat()
        self.ledger['entries'] = {k: v for k, v in self.ledger['entries'].items() if v['last_seen_at'] > cutoff}
        self._save_json(self.ledger_path, self.ledger)
        
        # Prune search cache (24h TTL)
        search_cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        self.search_cache['entries'] = {k: v for k, v in self.search_cache['entries'].items() if v['fetched_at'] > search_cutoff}
        self._save_json(self.search_cache_path, self.search_cache)

    def perform_temporal_sabotage(self, novel_phrase, source_date_str):
        """
        STAGE 3: The Search Fallback
        Checks if the 'novel_phrase' existed on the web before the source_date (with tolerance).
        """
        phrase_hash = f"sha256:{self.oracle.get_hash(novel_phrase)}"
        if phrase_hash in self.search_cache['entries']:
            return self.search_cache['entries'][phrase_hash]

        # Calculate before_date with 48h tolerance window for leaks/pre-reporting
        source_date = datetime.fromisoformat(source_date_str.replace('Z', '+00:00'))
        before_date = (source_date - timedelta(days=2)).strftime('%Y-%m-%d')
        
        query = f'"{novel_phrase}" before:{before_date}'
        print(f"Running Temporal Sabotage Search: {query}")
        
        # This will be replaced by the actual google_search tool call in the main pipeline
        # For this script, we return a mock structure that the pipeline will populate
        result = {
            "novel_phrase": novel_phrase,
            "before_date": before_date,
            "query": query,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "result_count": 0, # To be filled by tool
            "status": "PENDING_TOOL_CALL"
        }
        return result

    def get_verdict(self, item, search_result=None):
        """
        Decision Tree incorporating Stage 1 (Oracle), Stage 2 (Logic), and Stage 3 (Search)
        """
        now = datetime.now(timezone.utc)
        
        # 1. IDENTIFIERS
        primary_url = item.get('primary_url', '')
        headline = item.get('headline', '')
        novel_phrase = item.get('novel_phrase', '')
        source_date_str = item.get('source_date', now.isoformat())
        event_date_str = item.get('event_date')
        
        item_id = f"sha256:{self.oracle.get_hash(primary_url + headline)}"
        topic_hash = f"sha256:{self.oracle.get_hash(item.get('topic', 'general'))}"
        sub_event_hash = f"sha256:{self.oracle.get_hash(novel_phrase + (event_date_str or ''))}"

        # 2. EVIDENCE COLLECTION
        evidence = []
        event_date = None
        confidence_tier = "none"

        # TIER 1: System Timestamps (Oracle)
        if item.get('event_date_source') in ['github_release', 'huggingface_lastmodified', 'sec_filing', 'arxiv']:
            if event_date_str:
                event_date = datetime.fromisoformat(event_date_str.replace('Z', '+00:00'))
                confidence_tier = "high"
                evidence.append({"source": "system_timestamp", "type": item['event_date_source'], "timestamp": event_date_str})

        # TIER 2: Wayback Fallback
        if not event_date and primary_url:
            wayback = self.oracle.fetch_wayback_first_seen(primary_url)
            if wayback:
                event_date = datetime.fromisoformat(wayback['timestamp'].replace('Z', '+00:00'))
                confidence_tier = "medium"
                evidence.append(wayback)

        # TIER 3: Search Fallback (Stage 3)
        if search_result and search_result.get('status') == 'SUCCESS':
            evidence.append({
                "source": "google_search",
                "type": "temporal_sabotage",
                "query": search_result['query'],
                "result_count": search_result['result_count']
            })
            if search_result['result_count'] > 5: # Threshold for 'recycled'
                item['is_recycled'] = True
                confidence_tier = "medium" # We are confident it is OLD
                if not event_date: # If we don't have a date, assume it's at least older than tolerance
                    event_date = now - timedelta(days=7) 
            elif not event_date:
                # If zero pre-existing hits, we can infer the source_date as a low-confidence event_date
                event_date = datetime.fromisoformat(source_date_str.replace('Z', '+00:00'))
                confidence_tier = "low"

        # 3. VERDICT DECISION
        verdict = "UNVERIFIABLE"
        verdict_reason = "Insufficient evidence"
        verdict_confidence = 0.0

        if event_date:
            diff = now - event_date
            
            # FRESH
            if timedelta(days=0) <= diff <= timedelta(days=3):
                if not item.get('is_recycled', False):
                    # For FRESH, we need at least medium confidence OR low confidence with T1/T2
                    if confidence_tier in ['high', 'medium'] or (confidence_tier == 'low' and item.get('tier', 4) <= 2):
                        verdict = "FRESH"
                        verdict_confidence = 0.95 if confidence_tier == "high" else (0.75 if confidence_tier == "medium" else 0.65)
                        verdict_reason = f"{confidence_tier} confidence timestamp verified"
            
            # BREAKING_PREVIEW
            elif event_date > now:
                if item.get('event_date_source') in ['company_blog', 'sec_filing']:
                    verdict = "BREAKING_PREVIEW"
                    verdict_confidence = 0.90
                    verdict_reason = "Future event from T1 source"
            
            # RECIRCULATED
            elif diff > timedelta(days=3) or item.get('is_recycled', False):
                verdict = "RECIRCULATED"
                verdict_confidence = 1.0
                verdict_reason = "Event date >72h or pre-existing hits found"

        # 4. QUALITY GATE
        if verdict_confidence < 0.6 and verdict != "UNVERIFIABLE":
            verdict = "UNVERIFIABLE"

        # 5. PERSIST
        self._update_ledger(sub_event_hash, topic_hash, verdict, primary_url, novel_phrase)
        self._save_caches()

        return {
            "item_id": item_id,
            "sub_event_hash": sub_event_hash,
            "verdict": verdict,
            "verdict_confidence": verdict_confidence,
            "verdict_evidence": evidence,
            "event_date": event_date.strftime('%Y-%m-%d') if event_date else None,
            "checked_at": now.isoformat()
        }

    def _update_ledger(self, sub_hash, topic_hash, verdict, url, phrase):
        now = datetime.now(timezone.utc).isoformat()
        if sub_hash not in self.ledger['entries']:
            self.ledger['entries'][sub_hash] = {
                "sub_event_hash": sub_hash,
                "topic_hash": topic_hash,
                "first_seen_at": now,
                "first_seen_url": url,
                "novel_phrase": phrase,
                "last_seen_at": now,
                "seen_count": 1,
                "verdict_history": [verdict]
            }
        else:
            entry = self.ledger['entries'][sub_hash]
            entry['last_seen_at'] = now
            entry['seen_count'] += 1
            entry['verdict_history'].append(verdict)
