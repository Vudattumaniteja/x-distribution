# Reference: Credibility Monitoring

> **Loaded by:** SKILL.md when checking credibility
> **Purpose:** Track trustworthiness of sources, accounts, and audit own posts
> **Output:** `data/credibility_scores.json`
> **Log:** `logs/agent_runs/credibility_check_TIMESTAMP.json`

---

## Credibility Score System

### Scale
- **0-100** integer
- Default starting score: 70
- Min: 0 (blacklisted), Max: 100 (gold standard)

### Tiers
| Score | Tier | Color | Action |
|-------|------|-------|--------|
| 80-100 | **Trusted** | Green | Use without extra verification |
| 60-79 | **Reliable** | Blue | Standard verification |
| 40-59 | **Caution** | Yellow | Extra verification + add caveats |
| 20-39 | **Unreliable** | Orange | Avoid as primary source |
| 0-19 | **Blacklist** | Red | Do not use, remove from watchlist |

### Score Adjustments
| Event | Change | Notes |
|-------|--------|-------|
| Claim verified by 2+ sources | +2 | Cumulative — consistent verification compounds |
| Claim debunked | -15 | Severe penalty — trust is hard to rebuild |
| Article retracted | -10 | Publisher acknowledged error |
| Called out by peers | -5 | Public criticism from credible sources |
| Consistent quality for 30 days | +3 | Streak bonus — rewards reliability |
| Deleted controversial post | -8 | Covering up is worse than being wrong |
| Post got ratioed | -5 | Public disagreement with content |
| Correction issued voluntarily | +1 | Transparency signal |
| Multiple independent sources | +3 | Cross-verification |
| Single source only | -2 | Unverified |
| Anonymous source | -5 | Cannot verify identity |
| Conflict of interest detected | -10 | Motivated reasoning |

---

## Mode A: Source Check (Default)

### Process per Entity
1. **Recent Events Search**
   ```
   "[source] debunked OR false OR misleading" (past 7 days)
   "[source] correction OR retraction OR apology" (past 7 days)
   "[source] criticized OR called out" (past 7 days)
   "[account] misinformation OR deleted post" (past 7 days)
   ```

2. **Quality Trend Analysis**
   - Content quality changing in last 30 days?
   - Publishing frequency changes?
   - Editorial stance shifts?
   - For X accounts: posting style changes (more engagement bait? more controversial?)

3. **AI-Specific Checks**
   - AI news sites: AI hallucination incidents?
   - AI companies: Misleading benchmark claims?
   - Researchers: Controversial stances affecting credibility?
   - Tool reviewers: Undisclosed sponsorships?

4. **Cross-Reference with Sent Posts**
   - Check `data/sent_posts.json` for posts citing this source
   - If cited source loses credibility → flag user's post for potential correction

### Recommendation Logic
| Score | Trend | Recommendation |
|-------|-------|----------------|
| 80+ | Any | KEEP |
| 60-79 | Improving | KEEP |
| 60-79 | Stable | KEEP |
| 60-79 | Declining | WATCH — increase monitoring |
| 40-59 | Improving | WATCH — may recover |
| 40-59 | Stable | REDUCE — use less often |
| 40-59 | Declining | REDUCE — verify independently |
| 20-39 | Any | REDUCE — treat as unreliable |
| 0-19 | Any | REMOVE — blacklist |

---

## Mode B: Post Audit

### Process per Sent Post
1. **Source Still Valid?**
   - Re-check original source
   - Corrections or retractions since posting?
   - New information contradicting the claim?

2. **Community Response Check**
   - Corrections in replies?
   - Anyone pointing out errors or context gaps?
   - Ratioed (more disagrees than agrees)?

3. **Engagement Quality Audit**
   - Replies substantive or spam?
   - High-authority accounts engaged?
   - Sparked meaningful conversation?

4. **Self-Correction Check**
   - Should you post a correction or follow-up?
   - Thread reply providing better context to amplify?
   - Reply teaching you something worth acknowledging publicly?

### Action Needed Categories
| Action | When |
|--------|------|
| none | Everything checks out |
| post_correction | Minor inaccuracy, worth correcting |
| delete_post | Major inaccuracy or source fully debunked |
| add_context_reply | Important context was missing |
| acknowledge_error | Someone provided useful correction — acknowledge it publicly |

---

## Auto-Populate New Entities

When agents discover new sources not in credibility tracker:
1. Create entry with starting score 70
2. Run initial credibility check (search for track record)
3. Adjust starting score based on findings (±15)
4. Add to `data/credibility_scores.json`

---

## Edge Cases

### Source is Brand New (No Track Record)
- Default to score 65 (slightly below starting score of 70)
- Mark as "new_source: true"
- After 30 days of consistent quality: bump to 70
- After 30 days of issues: drop to appropriate tier

### Source Has Mixed Record
- Some articles are excellent, others are poor
- Track per-topic credibility separately if possible
- Use the LOWER score for automated decisions
- Note in the entry: "Strong on [topic], weak on [topic]"

### Source Gets Acquired/Changes Ownership
- Reset credibility assessment after ownership change
- Note: "Ownership changed on [date] from [old] to [new]"
- Previous track record may not apply

### Source is Personal Blog of Well-Known Figure
- Individual credibility varies by topic
- Score based on their expertise IN THE SPECIFIC TOPIC, not overall fame
- A famous VC writing about AI markets = high credibility. Same VC writing about AI safety = moderate credibility.

### You Realize Your Own Post Was Wrong
- Action: post_correction (not delete)
- Acknowledge the error publicly and quickly
- Correcting your own mistakes INCREASES credibility over time
- The correction post should be straightforward: "In my earlier post about [X], I cited [source]. It turns out [correction]. [Updated claim]."

### Credibility Score Oscillation
- If a source's score fluctuates wildly (up 10, down 15, up 8, down 12), set to 50 and mark as "volatile: true"
- Volatile sources should be treated as Caution tier regardless of current score
- Reassess after 60 days of stability

---

## Output Format
```json
{
  "last_updated": "ISO timestamp",
  "entities": [
    {
      "id": "unique_id",
      "name": "string",
      "type": "news_source | x_account | company | researcher | tool",
      "score": "integer 0-100",
      "tier": "trusted | reliable | caution | unreliable | blacklist",
      "trend": "improving | stable | declining | volatile",
      "first_seen": "ISO timestamp",
      "last_checked": "ISO timestamp",
      "check_count": "integer",
      "score_history": [{"date": "ISO", "score": "int", "reason": "string"}],
      "events_log": [{"date": "ISO", "event": "string", "impact": "int", "source_url": "string"}],
      "recommendation": "KEEP | WATCH | REDUCE | REMOVE"
    }
  ]
}
```
