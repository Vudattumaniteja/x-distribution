# Reference: Performance Tracking & Learning Loop

> **Loaded by:** SKILL.md when running performance reports
> **Purpose:** Analyze post/reply performance, identify patterns, generate recommendations
> **Output:** `data/performance_history.json` (new entry appended)
> **Log:** `logs/agent_runs/performance_TIMESTAMP.json`

---

## Data Collection Protocol

### User Updates `data/sent_posts.json` With:
```json
{
  "post_id": "unique_id",
  "posted_at": "ISO timestamp",
  "text": "string — full tweet text",
  "variant_type": "Hook-Accuracy | Value-Driven | Data_Bomb | Founder-Focused | Technical_Deep | Reply_[angle]",
  "news_source": "string",
  "grade_at_posting": "integer — score from grade_post",
  "engagement": {
    "likes": "integer",
    "reposts": "integer",
    "replies": "integer",
    "bookmarks": "integer",
    "impressions": "integer",
    "link_clicks": "integer",
    "profile_visits": "integer",
    "new_followers": "integer",
    "collected_at": "ISO timestamp",
    "collection_hours_after_post": "integer"
  },
  "performance_notes": "string — user's observation",
  "phoenix_triggered": true | false | unknown,
  "grade_vs_actual": "string — was the grade accurate?"
}
```

### Collection Windows
- **Primary:** 24 hours after posting (most predictive)
- **Extended:** 72 hours (long-tail performance)
- Phoenix typically kicks in 6-12 hours after posting

---

## Analysis Modules

### Module 1: Content Performance

**Variant Performance:**
```
Per variant: avg likes, reposts, bookmarks, replies, impressions
Per variant: bookmark rate (bookmarks/impressions × 100)
Per variant: repost rate (reposts/impressions × 100)
Per variant: Phoenix trigger rate
Per variant: best/worst individual post
```

**Reply Angle Performance:**
```
Per angle: avg likes, reposts, replies
Per angle: reply chain depth
Per angle: original author engagement rate
Per angle: new follower attribution
Per angle: best target account types
```

**Topic Analysis:**
```
Per topic: avg engagement
Per topic: best variant
Per topic: posting frequency (avoid oversaturation)
Per topic: trend direction (growing or declining?)
```

### Module 2: Algorithm Learning

**Phoenix Detection Signals:**
```
Signs of Phoenix:
- Impressions > 3× follower count
- Reposts from non-network accounts
- New followers untraceable to existing audience
- Engagement growing after 6 hours

Per Phoenix post: variant, grade, time, topic, hook pattern
```

**High Performer Patterns (top 20%):**
```
- Common traits (what do they share?)
- Hook patterns that work
- Length patterns
- Topic patterns
- Timing patterns
```

**Low Performer Patterns (bottom 20%):**
```
- Common traits (what do they share?)
- What went wrong?
- Was the grade accurate?
- Was the timing off?
```

**Grade Accuracy:**
```
- Avg grade of top 20% vs avg grade of bottom 20%
- Cases where grade was wrong
- Which grading dimensions are most predictive?
- Which need recalibration?
```

### Module 3: Source Effectiveness
```
Per source: avg engagement of posts citing it
Per source: Phoenix trigger rate
Per source: credibility score vs performance correlation
Per source: best/worst performing
Per reply target: which account types generate best results?
Per reply target: reply position effectiveness
```

### Module 4: Temporal Analysis
```
Per day of week: avg engagement
Per hour of day: avg engagement
Per time-since-news: performance by how soon after breaking
Posting frequency: effect on individual post performance
Reply frequency: effect on original post performance
```

### Module 5: Trend Analysis
```
Current period vs previous periods:
- Engagement trends (improving/stable/declining)
- Follower growth rate
- Phoenix trigger rate
- Content mix changes
- Grade accuracy trend
```

---

## Recommendation Engine

Generate 5 specific, actionable recommendations:

### Format
```json
{
  "id": 1,
  "type": "content | timing | strategy | source | format",
  "priority": "high | medium | low",
  "recommendation": "specific, actionable, no vague advice",
  "evidence": "what data supports this",
  "expected_impact": "what improvement to expect",
  "implementation": "exactly how to act on this"
}
```

### Example Recommendations
- "Post more Data Bomb variants — they trigger Phoenix 60% of the time vs 25% for other variants"
- "Shift posting window to 9-11 AM weekdays — 2.1x impression boost observed"
- "Prioritize researcher accounts for replies — 3x more follower growth than corporate accounts"
- "Your contrarian posts perform well but carry higher risk — limit to 1 per week"
- "Reduce [topic] posting from 3×/week to 1×/week — diminishing returns observed"

---

## Edge Cases

### Insufficient Data for Analysis
- If fewer than 5 posts in the analysis period: report "Insufficient data — need at least 5 posts for meaningful analysis"
- If fewer than 3 data points for any metric: mark that metric as "insufficient_data"
- Never fabricate trends from tiny sample sizes

### All Posts Performed Below Expected Grade
- This suggests grading system is miscalibrated (grades too high)
- Recommend recalibrating grading_weights.json
- Look for systematic over-scoring in specific dimensions

### All Posts Performed Above Expected Grade
- Grades may be too conservative
- Or your content strategy has improved and the grading hasn't kept up
- Recommend reviewing if grading thresholds should be adjusted

### No Posts Since Last Report
- Report: "No new posts since last report. No analysis to perform."
- Suggest: "Consider running a news hunt or reply hunt to generate content."

### Performance Dropped Suddenly
- Check for: algorithm changes, posting time changes, content quality changes, topic saturation
- If the drop coincides with a platform update, note it as external factor
- If the drop is gradual over multiple weeks, it's likely content quality or audience fatigue

### One Post Significantly Outperformed All Others
- Analyze what made it different: variant, topic, timing, hook
- If it's replicable (not a one-time viral event), suggest doing more of whatever made it work
- If it was a viral fluke (e.g., retweeted by Elon Musk), note it as non-replicable

### User Hasn't Updated Sent Posts
- If sent_posts.json hasn't been updated in 14+ days, flag this
- "Performance tracking requires updated engagement data. Please update data/sent_posts.json with recent post metrics."

---

## NotebookLM Query (If Available)
```
"I have performance data: [key metrics summary]. Top variant: [name]. Phoenix rate: [X]%.
What strategy adjustments would you recommend based on these metrics and current X dynamics?"
```

---

## Output Format
```json
{
  "entries": [
    {
      "report_date": "ISO timestamp",
      "period": "string — e.g., 'Last 7 days'",
      "posts_analyzed": "integer",
      "replies_analyzed": "integer",
      "summary": {
        "total_impressions": "integer",
        "total_engagement": "integer",
        "avg_engagement_per_post": "float",
        "phoenix_trigger_rate": "float",
        "follower_growth": "integer",
        "best_variant": "string",
        "best_reply_angle": "string",
        "best_source": "string",
        "best_posting_time": "string"
      },
      "modules": {
        "content_performance": {},
        "algorithm_learning": {},
        "source_effectiveness": {},
        "temporal_analysis": {},
        "trend_analysis": {}
      },
      "recommendations": [],
      "notebooklm_insights": "string",
      "data_quality_notes": "string — any caveats about data completeness"
    }
  ]
}
```
