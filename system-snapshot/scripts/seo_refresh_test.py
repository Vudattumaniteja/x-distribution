import json
import os
from datetime import datetime, timezone, timedelta
from scripts.temporal_sentinel import TemporalSentinel

def run_seo_refresh_tests():
    sentinel = TemporalSentinel()
    
    # Current Date: May 6, 2026
    now = datetime(2026, 5, 6, 12, 0, 0, tzinfo=timezone.utc)
    
    # Real-world "SEO Refresh" cases identified in search
    test_cases = [
        {
            "name": "Altman 'AI washing' (TechRadar May 5)",
            "item": {
                "headline": "Sam Altman says some companies are 'AI washing'",
                "primary_url": "https://www.techradar.com/pro/sam-altman-says-some-companies-are-ai-washing...",
                "source_date": "2026-05-05T09:00:00Z",
                "tier": 2,
                "novel_phrase": "Sam Altman AI washing layoffs quote"
            },
            # Search finds hits from India AI Summit (Feb 2026)
            "search_mock": {"status": "SUCCESS", "result_count": 45, "query": '... before:2026-05-03'}
        },
        {
            "name": "Huang 'Coding is a task' (Decoder May 2)",
            "item": {
                "headline": "NVIDIA CEO Jensen Huang: Engineering is Not Typing Code",
                "primary_url": "https://the-decoder.com/nvidia-ceo-jensen-huang-is-pushing-back...",
                "source_date": "2026-05-02T10:00:00Z",
                "tier": 2,
                "novel_phrase": "coding is a task Jensen Huang engineering"
            },
            # Search finds hits from Feb 2024
            "search_mock": {"status": "SUCCESS", "result_count": 1200, "query": '... before:2026-04-30'}
        },
        {
            "name": "Karpathy 'Verifiability Thesis' (May 2)",
            "item": {
                "headline": "Andrej Karpathy's Verifiability Thesis",
                "primary_url": "https://mindstudio.ai/blog/andrej-karpathy-verifiability-thesis",
                "source_date": "2026-05-02T18:00:00Z",
                "tier": 3,
                "novel_phrase": "Andrej Karpathy Verifiability Thesis Sequoia"
            },
            # Search finds 0 hits before this event
            "search_mock": {"status": "SUCCESS", "result_count": 0, "query": '... before:2026-04-30'}
        }
    ]

    print(f"{'CASE':<40} | {'VERDICT':<15} | {'EVENT DATE':<12} | {'RATIONALE'}")
    print("-" * 120)
    
    for tc in test_cases:
        res = sentinel.get_verdict(tc['item'], search_result=tc['search_mock'])
        print(f"{tc['name']:<40} | {res['verdict']:<15} | {str(res['event_date']):<12} | {res.get('verdict_evidence')[-1].get('result_count', 'N/A')} hits found before source date")

if __name__ == "__main__":
    run_seo_refresh_tests()
