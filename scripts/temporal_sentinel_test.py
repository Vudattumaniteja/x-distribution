import json
import os
from datetime import datetime, timezone, timedelta
from scripts.temporal_sentinel import TemporalSentinel

def run_regression_tests():
    sentinel = TemporalSentinel()
    
    # Mock Current Date: May 6, 2026
    now = datetime(2026, 5, 6, 12, 0, 0, tzinfo=timezone.utc)
    
    # 8 Contract Regression Cases
    test_cases = [
        {
            "id": "project-arc",
            "name": "Project Arc (May 5 announcement)",
            "item": {
                "headline": "NVIDIA and ServiceNow launch Project Arc",
                "primary_url": "https://newsroom.servicenow.com/arc",
                "event_date": "2026-05-05T14:00:00Z",
                "event_date_source": "sec_filing",
                "tier": 1,
                "novel_phrase": "Project Arc autonomous desktop agent OpenShell"
            },
            "search_mock": {"status": "SUCCESS", "result_count": 0, "query": '... before:2026-05-03'}
        },
        {
            "id": "anthropic-jv",
            "name": "Anthropic/Goldman JV (May 4)",
            "item": {
                "headline": "Anthropic and Goldman Sachs Launch $1.5B JV",
                "primary_url": "https://www.anthropic.com/news/jv",
                "event_date": "2026-05-04T10:00:00Z",
                "event_date_source": "company_blog",
                "tier": 1,
                "novel_phrase": "Anthropic Goldman Sachs $1.5B joint venture"
            },
            "search_mock": {"status": "SUCCESS", "result_count": 2, "query": '... before:2026-05-02'} # WSJ leak caught in tolerance
        },
        {
            "id": "gpt55-instant",
            "name": "GPT-5.5 Instant System Card (May 5)",
            "item": {
                "headline": "GPT-5.5 Instant System Card Released",
                "topic": "GPT-5.5",
                "event_date": "2026-05-05T10:00:00Z",
                "event_date_source": "company_blog",
                "tier": 1,
                "novel_phrase": "GPT-5.5 Instant System Card rollout details"
            },
            "search_mock": {"status": "SUCCESS", "result_count": 0, "query": '... before:2026-05-03'}
        },
        {
            "id": "gpt55-main",
            "name": "GPT-5.5 main release (April 23)",
            "item": {
                "headline": "Introducing GPT-5.5",
                "topic": "GPT-5.5",
                "event_date": "2026-04-23T10:00:00Z",
                "event_date_source": "company_blog",
                "tier": 1,
                "novel_phrase": "GPT-5.5 official launch and benchmarks"
            },
            "search_mock": {"status": "SUCCESS", "result_count": 500, "query": '... before:2026-04-21'}
        },
        {
            "id": "amodei-essay",
            "name": "Amodei 'country of geniuses' essay",
            "item": {
                "headline": "Dario Amodei: The Adolescence of Technology",
                "primary_url": "https://darioamodei.com/essay",
                "event_date": "2026-01-15T09:00:00Z",
                "event_date_source": "wayback_cdx", # Found via wayback
                "tier": 2,
                "novel_phrase": "country of geniuses in a datacenter essay"
            },
            "search_mock": {"status": "SUCCESS", "result_count": 1200, "query": '... before:2026-01-13'}
        },
        {
            "id": "altman-washing",
            "name": "Altman 'AI washing' Fortune piece",
            "item": {
                "headline": "Sam Altman warns of AI washing in layoffs",
                "source_date": "2026-05-04T12:00:00Z", # Article date
                "tier": 2,
                "novel_phrase": "Sam Altman AI washing layoffs quote"
            },
            # This would trigger Search Fallback since no system timestamp
            "search_mock": {"status": "SUCCESS", "result_count": 45, "query": '... before:2026-05-02'}
        },
        {
            "id": "conflation",
            "name": "sus-column + Glacier conflation",
            "item": {
                "headline": "GPT-6 suspect Glacier leaked on LMSYS",
                "tier": 4,
                "novel_phrase": "sus-column Glacier GPT-6 leak"
            },
            "search_mock": {"status": "SUCCESS", "result_count": 1, "query": '...'} 
        },
        {
            "id": "unsloth",
            "name": "Unsloth Studio Beta",
            "item": {
                "headline": "Unsloth Studio Beta Launch",
                "event_date": "2026-03-17T10:00:00Z",
                "event_date_source": "github_release",
                "tier": 1,
                "novel_phrase": "Unsloth Studio Beta local LLM training"
            },
            "search_mock": {"status": "SUCCESS", "result_count": 300, "query": '...'}
        }
    ]

    print(f"{'CASE':<40} | {'VERDICT':<15} | {'CONF':<5} | {'EVIDENCE'}")
    print("-" * 120)
    
    results = []
    for tc in test_cases:
        # We manually pass the search_mock to simulate Stage 3 success
        res = sentinel.get_verdict(tc['item'], search_result=tc['search_mock'])
        
        evidence_types = [e.get('type', e.get('source', 'unknown')) for e in res['verdict_evidence']]
        evidence_str = ",".join(evidence_types) if evidence_types else "None"
        
        print(f"{tc['name']:<40} | {res['verdict']:<15} | {res['verdict_confidence']:<5.2f} | {evidence_str}")
        results.append(res)

    # Final Output to JSON for Review
    with open('logs/sentinel_regression_results.json', 'w') as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    run_regression_tests()
