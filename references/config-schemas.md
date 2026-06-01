# Reference: Config & Data Schemas

> **Loaded by:** SKILL.md when creating or validating config/data files
> **Purpose:** Authoritative schema reference for all JSON files
> **Usage:** Create new files with these schemas, validate existing files

---

## Config Files

### followed_accounts.json
```json
{
  "metadata": {
    "description": "45-account X watchlist for monitoring",
    "total_slots": 45,
    "populated": "integer",
    "last_updated": "ISO timestamp or null"
  },
  "accounts": [
    {
      "id": "integer 1-45",
      "handle": "string — @username",
      "name": "string — display name",
      "category": "corporate | founder_researcher | journalist | analyst | builder | vc_investor | community",
      "tier": "must_follow | high_priority | standard | low_priority",
      "tweepcred_estimate": "very_high | high | medium | low | unknown",
      "notes": "string — why following, what to watch for",
      "reply_priority": "high | medium | low | skip",
      "added_date": "ISO timestamp"
    }
  ],
  "categories": {
    "corporate": "Official company accounts",
    "founder_researcher": "Individual founders, CTOs, lead researchers",
    "journalist": "Tech journalists who break AI news",
    "analyst": "Industry analysts and commentators",
    "builder": "Developers building AI tools",
    "vc_investor": "VCs tracking AI market",
    "community": "AI community builders and aggregators"
  },
  "tiers": {
    "must_follow": "Check every run, highest priority",
    "high_priority": "Check most runs",
    "standard": "Check every other run",
    "low_priority": "Check weekly only"
  }
}
```

### grading_weights.json
```json
{
  "metadata": {"description": "All scoring formulas and thresholds"},
  "post_grading": {
    "max_score": 100,
    "dimensions": {
      "hook_strength": {"max_points": 15},
      "algorithm_signal_potential": {"max_points": 20},
      "phoenix_potential": {"max_points": 15},
      "voice_compliance": {"max_points": 20},
      "dark_social_potential": {"max_points": 15},
      "risk_penalties": {"max_points": 0, "min_points": -15}
    },
    "thresholds": {
      "excellent": 85, "good": 70, "acceptable": 55,
      "needs_work": 40, "skip": 25
    }
  },
  "reply_grading": {
    "max_score": 12,
    "dimensions": {
      "recency": {"max_points": 2},
      "performance": {"max_points": 2},
      "velocity": {"max_points": 2},
      "relevance": {"max_points": 4},
      "authority": {"max_points": 2},
      "saturation_penalty": {"points": -1}
    },
    "thresholds": {
      "must_reply": 9, "high_priority": 7,
      "worth_considering": 5, "skip": 4
    }
  },
  "credibility_scoring": {
    "scale": {"min": 0, "max": 100, "starting_score": 70},
    "tiers": {
      "trusted": "80-100", "reliable": "60-79",
      "caution": "40-59", "unreliable": "20-39", "blacklist": "0-19"
    }
  }
}
```

### post_templates.json
```json
{
  "metadata": {"description": "5 post variants, 5 reply angles, hard rules"},
  "post_variants": [
    {
      "id": 1, "name": "Hook-Accuracy",
      "strategy": "Pattern-interruption hook + precise claim",
      "best_for": ["Announcements", "Fundraising", "Launches"],
      "avoid_for": ["Opinion", "Complex tutorials"],
      "char_budget": "under 260 chars"
    }
  ],
  "reply_angles": [
    {
      "id": 1, "name": "Add Insight",
      "strategy": "Share relevant data/experience the original missed",
      "risk_level": "low",
      "trigger_when": "Original makes a claim you can strengthen"
    }
  ],
  "hard_rules": {
    "max_tweet_length": 280,
    "max_emoji_per_tweet": 1,
    "emoji_placement": "end_only",
    "forbidden_words": ["insane", "mind-blowing", "game-changing", "revolutionary"],
    "forbidden_openers": ["Thread 🧵", "Hot take:", "Just in:", "Unpopular opinion:"]
  }
}
```

### source_registry.json
```json
{
  "metadata": {"description": "Central registry for live source collectors and queue policy"},
  "queue_policy": {
    "active_queue_max_items": 1000,
    "dedupe_url_fields": ["source_url", "url", "resolved_url", "hn_discussion_url"],
    "prefer_categories": ["deep-discovery", "community-discussion", "video-discovery"]
  },
  "youtube_discovery": {
    "method": "yt-transcript-latest",
    "lookback_days": 2,
    "max_scan_per_channel": 500,
    "transcript_count_per_channel": null,
    "transcript_timeout_seconds": 7200,
    "rss_fallback": false
  },
  "runtime_paths": {
    "python_exe_env": "X_DISTRIBUTION_PYTHON",
    "xcli_script_env": "XCLI_SCRIPT",
    "yt_transcript_cli_env": "YT_TRANSCRIPT_CLI",
    "yt_transcript_py_script_env": "YT_TRANSCRIPT_PY_SCRIPT",
    "default_xcli_script": "absolute path",
    "default_yt_transcript_cli": "absolute path",
    "default_yt_transcript_py_script": "absolute path"
  },
  "artifact_sources": {
    "hugging_face_orgs": ["org"],
    "github_orgs": ["org"],
    "github_release_repos": [{"org": "org", "repo": "repo"}]
  },
  "live_sources": {
    "reddit": {
      "enabled": true,
      "scripts": ["reddit_mcp_buddy_collect.py"],
      "outputs": ["data/reddit_raw_standalone.json"]
    },
    "finance": {
      "enabled": true,
      "scripts": ["finance_market_collector.py"],
      "outputs": ["data/finance_raw_standalone.json", "data/finance_signals.json"]
    },
    "startup_funding": {
      "enabled": true,
      "scripts": ["startup_funding_collector.py"],
      "outputs": ["data/startup_funding_raw.json", "data/startup_funding_signals.json"]
    },
    "github": {
      "enabled": true,
      "scripts": ["github_monitor_standalone.py", "github_releases_discovery.py"],
      "outputs": ["data/github_discoveries.json", "data/release_discoveries.json"]
    },
    "arxiv": {
      "enabled": true,
      "scripts": ["arxiv_sentinel_standalone.py"],
      "outputs": ["data/arxiv_raw_standalone.json"]
    }
  },
  "collector_outputs": ["data/source_output.json"],
  "stale_file_policy": {
    "archive_root": "cache/stale_archive",
    "archive_patterns": ["glob"],
    "review_only_patterns": ["glob"]
  }
}
```

### startup_sources.json
```json
{
  "metadata": {"description": "Startup fundraising and product-launch sources scoped to AI and developer tooling"},
  "lookback_hours": 168,
  "request_timeout_seconds": 20,
  "max_items_per_source": 30,
  "min_relevance_score": 5,
  "ai_keywords": ["ai", "llm", "agent", "machine learning", "developer tool"],
  "startup_keywords": ["startup", "founder", "yc", "backed", "venture"],
  "funding_keywords": ["raises", "funding", "series a", "series b", "series c", "valuation"],
  "product_keywords": ["launch", "unveils", "product", "platform", "api", "tool"],
  "round_patterns": {
    "series_a": "\\bseries\\s+a\\b",
    "series_b": "\\bseries\\s+b\\b",
    "series_c": "\\bseries\\s+c\\b"
  },
  "rss_sources": [
    {
      "name": "TechCrunch Fundraising",
      "url": "https://techcrunch.com/category/startups/fundraising/",
      "rss_url": "https://techcrunch.com/category/startups/fundraising/feed/",
      "source_region": "global",
      "tier": "tier_1",
      "source_type": "startup_funding"
    }
  ]
}
```

### finance_sources.json
```json
{
  "metadata": {"description": "Finance, market, and macro sources scoped to AI market intelligence"},
  "lookback_hours": 96,
  "request_timeout_seconds": 20,
  "max_items_per_source": 25,
  "min_relevance_score": 4,
  "ai_keywords": ["ai", "llm", "openai", "nvidia", "gpu", "data center"],
  "finance_keywords": ["funding", "valuation", "earnings", "revenue", "capex", "stock"],
  "signal_rules": {
    "funding_signal": ["funding", "valuation", "series"],
    "earnings_signal": ["earnings", "revenue", "guidance"],
    "capex_signal": ["capex", "data center", "power"],
    "chip_supply_signal": ["nvidia", "gpu", "tsmc"]
  },
  "rss_sources": [
    {
      "name": "Bloomberg Markets",
      "url": "https://www.bloomberg.com/markets",
      "rss_url": "https://feeds.bloomberg.com/markets/news.rss",
      "source_region": "global",
      "tier": "tier_1",
      "source_type": "market_news"
    }
  ],
  "sec_companies": [
    {"name": "NVIDIA", "ticker": "NVDA", "cik": "0001045810"}
  ],
  "sec_forms": ["8-K", "10-Q", "10-K", "S-1", "424B4"]
}
```

### source_tiers.json
```json
{
  "tiers": {
    "T1": {"weight": 1.0, "description": "Primary sources", "domains": ["openai.com"]},
    "T2": {"weight": 0.8, "description": "High-signal secondary sources", "domains": ["reuters.com"]},
    "T3": {"weight": 0.5, "description": "Specialist commentary", "domains": ["artificialanalysis.ai"]},
    "T4": {"weight": 0.1, "description": "Low-priority aggregators", "domains": ["medium.com"]}
  },
  "quarantine": ["domain-or-source-fragment"]
}
```

### community_sources.json
```json
{
  "reddit": {
    "lookback": "day",
    "limit_per_listing": 25,
    "comment_limit": 8,
    "rss_timeout_seconds": 20,
    "rss_delay_seconds": 0.8,
    "rss_search_queries_per_subreddit": 2,
    "mcp_buddy": {
      "enabled": true,
      "command": ["npx.cmd", "-y", "reddit-mcp-buddy"],
      "startup_timeout_seconds": 45,
      "request_timeout_seconds": 60,
      "search_queries_per_subreddit": 0,
      "max_subreddits_per_run": 1,
      "max_detail_fetch_items": 0,
      "fallback_script": "reddit_scraper_standalone.py"
    },
    "subreddits": [
      {"name": "LocalLLaMA", "role": "local_model_practitioners", "queries": ["llm", "model"]}
    ]
  },
  "hacker_news": {
    "queries": ["AI agent", "LLM"],
    "lookback_hours": 72,
    "limit": 50
  }
}
```

---

## Data Files

### news_queue.json
```json
{
  "metadata": {"description": "Active intelligence queue", "max_items_kept": 1000, "dedupe": "canonical_url"},
  "last_updated": "ISO or null",
  "run_count": 0,
  "items": [
    {
      "id": "string",
      "headline": "string under 100 chars",
      "summary": "string 2-3 sentences",
      "source_url": "string",
      "source_name": "string",
      "source_type": "news_outlet | blog | social_media | arxiv | official",
      "discovered_by_agent": "string",
      "relevance_score": "float 0-10",
      "combined_score": "float 0-16",
      "fact_check_status": "pending | verified | debunked | skipped",
      "tags": ["list"],
      "unique_fields": {}
    }
  ]
}
```

### approved_posts.json
```json
{
  "metadata": {"description": "Tweet variants with grades"},
  "last_updated": "ISO or null",
  "posts": [
    {
      "id": "string",
      "news_item_id": "string",
      "variants": [
        {
          "variant_id": 1,
          "variant_name": "string",
          "text": "string",
          "char_count": "integer",
          "grade_score": "integer or null",
          "status": "draft | approved | sent"
        }
      ]
    }
  ]
}
```

### sent_posts.json
```json
{
  "metadata": {"description": "Posts user has sent (manual updates)"},
  "last_updated": "ISO or null",
  "sent_posts": [
    {
      "post_id": "string",
      "posted_at": "ISO",
      "text": "string",
      "variant_type": "string",
      "grade_at_posting": "integer",
      "engagement": {
        "likes": 0, "reposts": 0, "replies": 0,
        "bookmarks": 0, "impressions": 0,
        "new_followers": 0,
        "collected_at": "ISO",
        "collection_hours_after_post": 24
      },
      "phoenix_triggered": "unknown"
    }
  ]
}
```

### reply_opportunities.json
```json
{
  "metadata": {"description": "Graded reply targets + drafts"},
  "last_updated": "ISO or null",
  "run_count": 0,
  "opportunities": [
    {
      "id": "string",
      "post_url": "string",
      "author_handle": "string",
      "grade": {"total": 0, "recency": 0, "performance": 0, "velocity": 0, "relevance": 0, "authority": 0, "saturation_penalty": 0},
      "priority": "must_reply | high_priority | worth_considering | skip",
      "reply_drafts": [],
      "status": "found | drafts_generated | replied | skipped | expired",
      "expires_at": "ISO"
    }
  ]
}
```

### performance_history.json
```json
{
  "metadata": {"description": "Historical performance reports"},
  "entries": [
    {
      "report_date": "ISO",
      "period": "string",
      "posts_analyzed": 0,
      "summary": {},
      "recommendations": []
    }
  ]
}
```

### credibility_scores.json
```json
{
  "last_updated": "ISO or null",
  "entities": [
    {
      "id": "string",
      "name": "string",
      "type": "news_source | x_account | company | researcher | tool",
      "score": 70,
      "tier": "reliable",
      "trend": "stable",
      "recommendation": "KEEP | WATCH | REDUCE | REMOVE"
    }
  ]
}
```

### evolution_state.json
```json
{
  "metadata": {"description": "Current self-evolution state"},
  "last_updated": "ISO or null",
  "cycle_count": 0,
  "current_phase": "idle | auditing | researching | awaiting_approval | implementing | validating | monitoring",
  "last_audit": "object or null",
  "last_research_plan": "object or null",
  "last_approved_plan": "object or null",
  "last_implementation": "object or null",
  "validation_status": "not_run | passed | failed | partial",
  "open_questions": []
}
```

### evolution_backlog.json
```json
{
  "metadata": {
    "description": "Ranked backlog of pipeline evolution opportunities",
    "priority_formula": "impact + confidence + unblock_value - implementation_risk - complexity"
  },
  "last_updated": "ISO or null",
  "items": [
    {
      "id": "string",
      "title": "string",
      "source": "audit | research | monitoring | user_request",
      "priority_score": "integer",
      "priority": "P0 | P1 | P2 | P3",
      "evidence": [{"file": "path", "line": 0, "note": "string"}],
      "recommended_fix": "string",
      "status": "open | approved | in_progress | implemented | rejected | deferred",
      "validation_plan": []
    }
  ]
}
```
