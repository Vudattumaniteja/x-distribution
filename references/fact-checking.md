# Reference: Fact-Checking Pipeline

> **Loaded by:** SKILL.md when user triggers fact-checking
> **Purpose:** Verify claims before they become posts — 5 verification checks
> **Output:** Updates `data/news_queue.json` with verification status
> **Log:** `logs/fact_checks/fact_check_TIMESTAMP.json`

---

## Verification Protocol (5 Checks)

### Check 1: Source Verification
**Question:** Is the original source credible?

**Steps:**
1. Identify the PRIMARY source (not the aggregator)
2. Check domain history: established outlet, editorial standards, Wikipedia page?
3. Check the specific author: specialty area, track record
4. Check editorial independence: sponsored? paid content? financial relationship with subject?
5. Cross-reference with `data/credibility_scores.json` if the source has been previously tracked

**Output:** Source credibility rating (0-100)

### Check 2: Claim Verification
**Question:** Can specific claims be confirmed?

**Steps:**
1. Extract key factual claims (usually 1-3 per item)
2. Search for each claim independently with 2+ source requirement
3. Cross-reference numbers across sources — do they match?
4. Check for primary data (benchmarks, financial reports, papers)
5. Query Polymarket Gamma Search endpoint for active prediction markets to corroborate claims (fetch question, URL, and YES odds)
6. Flag anything traceable to only one source

**Search Templates:**
```
Data claims: "[number]" "[topic]" site:reuters.com OR site:bloomberg.com OR site:techcrunch.com
Capability claims: "[tool/model]" "[capability]" benchmark OR test OR review
Business claims: "[company]" "[event]" funding OR acquisition OR valuation
Debunk check: "[claim]" debunked OR false OR misleading OR correction
Prediction market corroboration: Gamma query "[keywords]"
```

**Output:** Per-claim verification status (confirmed / unconfirmed / contradicted)

### Check 3: Recency Check
**Question:** Is this current or old news being recirculated?

**Steps:**
1. Find earliest publication date
2. Check for updates or superseding information
3. Look for recirculation patterns (old screenshots, old articles resurfacing)
4. Verify date on source URLs matches claimed timeline

**Red Flags:**
- No date on source article
- URL date doesn't match claimed timeline
- Same story covered months ago with no new development
- Social media posts with old engagement timestamps

**Output:** Recency status (current / updated_available / outdated / recirculated)

### Check 4: Context Check
**Question:** Is the claim being presented without important context?

**Steps:**
1. Read the FULL source article, not just headline/summary
2. Check for omitted caveats: conditions, limitations, sample size
3. Verify headline matches article content
4. Look for what the source says but doesn't emphasize

**Common Context Gaps:**
- "AI achieves X accuracy" → but only on a narrow benchmark
- "Company raises $Y" → but at lower valuation than previous round
- "Study shows AI is better than humans" → but task is highly constrained
- "Tool has 1 million users" → but mostly free-tier inactive users

**Output:** Context gaps list with severity (none / minor / significant)

### Check 5: Conflict of Interest Check
**Question:** Does the source have incentive to misrepresent?

**Steps:**
1. Financial relationship with the subject?
2. Competitive dynamics (competitor publishing negative coverage? partner publishing positive?)
3. Author's disclosed conflicts of interest?
4. Overall coverage pattern of this topic by the source?

**Output:** Conflict assessment (none detected / mild / significant)

---

## Verdict System

| Verdict | Criteria | Recommendation | Confidence Range |
|---------|----------|----------------|-----------------|
| **VERIFIED** | 2+ independent sources confirm, no context gaps, credible | **PROCEED** | 80-100% |
| **LIKELY TRUE** | 1 primary + supporting evidence, minor gaps | **PROCEED_WITH_CAUTION** | 60-79% |
| **UNVERIFIED** | Single source only, no independent confirmation | **INVESTIGATE_FURTHER** | 40-59% |
| **LIKELY FALSE** | Contradicting evidence, significant gaps | **SKIP** | 20-39% |
| **DEBUNKED** | Multiple sources confirm false/misleading | **SKIP** + flag source | 0-19% |

---

## Confidence Score Calculation

```
Base Score: 50

Bonuses:
  +15 per independent confirming source (max +45)
  +10 if primary source is top-tier (Reuters, Bloomberg, official company blog)
  +5 if claim includes specific verifiable numbers
  +5 if official statement or press release exists
  +10 if Polymarket YES odds are >70%

Penalties:
  -15 if any source contradicts the claim
  -10 if only one source exists
  -10 if source has known bias or conflict of interest
  -5 per significant context gap
  -5 if source has issued corrections recently
  -5 if date is ambiguous or disputed
  -15 if Polymarket YES odds are <15%

Range: 0-100
```

---

## Edge Cases

### Claim is a Prediction/Forecast
- Predictions cannot be "verified" in the traditional sense
- Verdict: "UNVERIFIABLE_PREDICTION"
- Note the source's track record on past predictions
- Recommendation: PROCEED_WITH_CAUTION if source has >70% prediction accuracy

### Source is an Anonymous Leak
- Automatically reduce confidence by 20
- Check if the leak has been corroborated by any named source
- If no corroboration exists within 48 hours, verdict defaults to UNVERIFIED

### Multiple Sources Report Different Numbers
- Present all versions to the user
- Default to the highest-credibility source for automated decisions
- Note the discrepancy clearly

### Claim is About a Non-English Source
- Translate and verify from the original language
- Note translation accuracy caveats
- If the claim depends on translation nuance, mark as UNVERIFIED

### Source is Official Company Statement
- Company statements are generally credible but inherently biased
- Default confidence: 70 (RELIABLE)
- Apply standard verification checks on specific claims within the statement
- Watch for selective disclosure (emphasizing positive, omitting negative)

### Fact Check Reveals Previously Debunked Source
- If a source in the news queue has been debunked before, check credibility_scores.json
- If source score is < 40 (CAUTION tier), auto-set verdict to LIKELY_FALSE
- Inform the user of the source's track record

---

## Output Format

### Per-Item Result
```json
{
  "item_id": "string from news_queue",
  "verdict": "VERIFIED | LIKELY_TRUE | UNVERIFIED | LIKELY_FALSE | DEBUNKED | UNVERIFIABLE_PREDICTION",
  "confidence": "integer 0-100",
  "recommendation": "PROCEED | PROCEED_WITH_CAUTION | INVESTIGATE_FURTHER | SKIP",
  "checks": {
    "source_verification": {"rating": "0-100", "notes": "string"},
    "claim_verification": {"claims_checked": ["list"], "results": {}},
    "recency_check": {"status": "string", "original_date": "string"},
    "context_check": {"gaps": ["list"], "severity": "string"},
    "conflict_of_interest": {"detected": "boolean", "description": "string"}
  },
  "sources_checked": ["list of URLs"],
  "timestamp": "ISO timestamp"
}
```
