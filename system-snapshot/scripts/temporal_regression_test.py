import json
import hashlib
import os
import re
from datetime import datetime, timezone, timedelta
from scripts.truth_oracle import TruthOracle

class TemporalSentinel:
    def __init__(self, ledger_path='cache/claim_ledger.json'):
        self.ledger_path = ledger_path
        self.oracle = TruthOracle()
        self.ledger = self._load_ledger()
        self.version = "1.0.0"

    def _load_ledger(self):
        try:
            with open(self.ledger_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"version": "1.0.0", "window_days": 14, "entries": {}}

    def _save_ledger(self):
        cutoff = (datetime.now(timezone.utc) - timedelta(days=self.ledger.get('window_days', 14))).isoformat()
        self.ledger['entries'] = {k: v for k, v in self.ledger['entries'].items() if v['last_seen_at'] > cutoff}
        with open(self.ledger_path, 'w', encoding='utf-8') as f:
            json.dump(self.ledger, f, indent=2)

    def get_verdict(self, item):
        """
        Decision Tree based on User Contract (v1.0)
        """
        # 1. IDENTIFIERS & HASHS
        primary_url = item.get('primary_url', '')
        headline = item.get('headline', '')
        novel_phrase = item.get('novel_phrase', '')
        event_date_str = item.get('event_date')
        
        item_id = f"sha256:{self.oracle.get_hash(primary_url + headline)}"
        topic_hash = f"sha256:{self.oracle.get_hash(item.get('topic', 'general'))}"
        # SUB-EVENT HASH: Combines novel_phrase + event_date (normalized)
        sub_event_hash = f"sha256:{self.oracle.get_hash(novel_phrase + (event_date_str or ''))}"

        # 2. EVIDENCE COLLECTION
        evidence = []
        event_date = None
        confidence_tier = "none"

        # TIER 1: System Timestamps (High Confidence)
        if item.get('event_date_source') in ['github_release', 'huggingface_lastmodified', 'sec_filing', 'arxiv']:
            if event_date_str:
                event_date = datetime.fromisoformat(event_date_str.replace('Z', '+00:00'))
                confidence_tier = "high"
                evidence.append({"source": "system_timestamp", "type": item['event_date_source'], "timestamp": event_date_str})

        # TIER 2: Wayback First-Seen (Medium Confidence) - FALLBACK
        if not event_date and primary_url:
            wayback = self.oracle.fetch_wayback_first_seen(primary_url)
            if wayback:
                event_date = datetime.fromisoformat(wayback['timestamp'].replace('Z', '+00:00'))
                confidence_tier = "medium"
                evidence.append(wayback)

        # 3. VERDICT DECISION RULES
        now = datetime.now(timezone.utc)
        verdict = "UNVERIFIABLE"
        verdict_reason = "Insufficient evidence or confidence"
        verdict_confidence = 0.0

        if event_date:
            diff = now - event_date
            
            # RULE: FRESH
            if timedelta(days=0) <= diff <= timedelta(days=3):
                if confidence_tier in ['high', 'medium']:
                    if item.get('tier', 4) <= 2 or item.get('corroborating_independent_count', 0) >= 1:
                        verdict = "FRESH"
                        verdict_reason = f"{confidence_tier} confidence timestamp within 72h window"
                        verdict_confidence = 0.95 if confidence_tier == "high" else 0.75
            
            # RULE: BREAKING_PREVIEW
            elif event_date > now:
                if item.get('event_date_source') in ['company_blog', 'sec_filing', 'official_calendar']:
                    verdict = "BREAKING_PREVIEW"
                    verdict_reason = "Future event date from T1 source"
                    verdict_confidence = 0.90
            
            # RULE: RECIRCULATED
            elif diff > timedelta(days=3):
                if confidence_tier in ['high', 'medium']:
                    verdict = "RECIRCULATED"
                    verdict_reason = f"Verified event date ({event_date.strftime('%Y-%m-%d')}) is >72h old"
                    verdict_confidence = 1.0

        # 4. FINAL QUALITY GATE (Mandate 0.6 Confidence)
        if verdict_confidence < 0.6 and verdict != "UNVERIFIABLE":
            verdict = "UNVERIFIABLE"
            verdict_reason += " (Confidence below 0.6 threshold)"

        # 5. UPDATE LEDGER
        self._update_ledger(sub_event_hash, topic_hash, verdict, primary_url, novel_phrase)

        return {
            "item_id": item_id,
            "sub_event_hash": sub_event_hash,
            "topic_hash": topic_hash,
            "headline": headline,
            "verdict": verdict,
            "verdict_confidence": verdict_confidence,
            "verdict_reason": verdict_reason,
            "verdict_evidence": evidence,
            "event_date": event_date.strftime('%Y-%m-%d') if event_date else None,
            "event_date_confidence": confidence_tier,
            "checked_at": now.isoformat(),
            "sentinel_version": self.version
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
        self._save_ledger()

if __name__ == "__main__":
    sentinel = TemporalSentinel()
    
    # REGRESSION TEST SUITE
    test_cases = [
        {
            "name": "Project Arc (May 5 announcement)",
            "item": {
                "headline": "NVIDIA and ServiceNow launch Project Arc",
                "primary_url": "https://newsroom.servicenow.com/arc",
                "event_date": "2026-05-05T14:00:00Z",
                "event_date_source": "sec_filing", # Hypothetical high-confidence
                "tier": 1,
                "novel_phrase": "Project Arc autonomous desktop agent OpenShell"
            }
        },
        {
            "name": "GPT-5.5 Instant System Card (May 5)",
            "item": {
                "headline": "GPT-5.5 Instant System Card Released",
                "topic": "GPT-5.5",
                "event_date": "2026-05-05T10:00:00Z",
                "event_date_source": "company_blog",
                "tier": 1,
                "novel_phrase": "GPT-5.5 Instant System Card rollout details"
            }
        },
        {
            "name": "GPT-5.5 main release (April 23)",
            "item": {
                "headline": "Introducing GPT-5.5",
                "topic": "GPT-5.5",
                "event_date": "2026-04-23T10:00:00Z",
                "event_date_source": "company_blog",
                "tier": 1,
                "novel_phrase": "GPT-5.5 official launch and benchmarks"
            }
        },
        {
            "name": "Amodei 'country of geniuses' essay",
            "item": {
                "headline": "Dario Amodei: The Adolescence of Technology",
                "primary_url": "https://darioamodei.com/essay", # This would hit Wayback in real run
                "event_date": "2026-01-15T09:00:00Z", 
                "event_date_source": "wayback_cdx", # Simulate wayback find
                "tier": 2,
                "novel_phrase": "country of geniuses in a datacenter essay"
            }
        },
        {
            "name": "sus-column + Glacier conflation",
            "item": {
                "headline": "GPT-6 suspect Glacier leaked on LMSYS",
                "event_date": None,
                "event_date_source": None,
                "tier": 4,
                "novel_phrase": "sus-column Glacier GPT-6 leak"
            }
        }
    ]

    print(f"{'CASE':<40} | {'VERDICT':<15} | {'DATE':<12} | {'REASON'}")
    print("-" * 100)
    for tc in test_cases:
        res = sentinel.get_verdict(tc['item'])
        print(f"{tc['name']:<40} | {res['verdict']:<15} | {str(res['event_date']):<12} | {res['verdict_reason']}")
