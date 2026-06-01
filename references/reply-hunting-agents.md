# Reference: Reply Hunting Agents (7 Sub-Agents)

## Canonical X Source Rule

Search queries may surface candidate X URLs. All post text, thread context, timelines, reply context, and engagement evidence must then be collected through the pinned XCLI route in `scripts/source_clis.py`; do not use browser scraping or search-result excerpts as the source record.

> **Loaded by:** SKILL.md when user triggers Mode 2 (Reply Pipeline)
> **Agents:** 7 sub-agents scanning different reply opportunity types
> **Output:** `data/reply_opportunities.json` — graded and ranked list
> **Log:** `logs/agent_runs/reply_hunt_TIMESTAMP.json`

---

## 6-Dimension Grading System

Every opportunity found by ANY agent is graded on these 6 dimensions. Max 12 points, min -1 with saturation penalty.

### Dimension 1: Recency (0-2 points)
How recent is the original post? Reply timing is critical.

| Score | Criteria | Edge Cases |
|-------|----------|-----------|
| 2 | Posted within last 1 hour | If post is under 15 min, note as "early_risk: engagement pattern not stabilized" |
| 1 | Posted within last 6 hours | If exactly at 6h boundary, check if engagement is still active |
| 0 | Posted more than 6 hours ago | If post is viral (1000+ likes), extend window to 12h for this dimension |

**Handling time ambiguity:** If the exact post time is unclear (e.g., "2h" vs "3h" displayed by platform), assume the less favorable time.

### Dimension 2: Performance (0-2 points)
How well is the original post performing?

| Score | Criteria | Edge Cases |
|-------|----------|-----------|
| 2 | High: >100 likes AND >20 replies | If likes are high but replies are low (<5), score 1 (low conversation engagement) |
| 1 | Moderate: 20-100 likes OR 5-20 replies | If metrics are partially visible, score based on what's available |
| 0 | Low: <20 likes AND <5 replies | If the author has 100K+ followers and got 20 likes, that's actually LOW (score 0) — normalize by follower count |

**Follower-normalized performance:** For accounts with 100K+ followers, adjust thresholds:
- High: >500 likes AND >50 replies
- Moderate: 100-500 likes OR 20-50 replies
- Low: <100 likes AND <20 replies

### Dimension 3: Velocity (0-2 points)
Is engagement still accelerating?

| Score | Criteria | Detection Method |
|-------|----------|-----------------|
| 2 | Accelerating (>20%/hour growth) | Compare reply timestamps: if 5 replies in last 30 min vs 2 in previous 30 min, velocity is high |
| 1 | Stable (growing but <20%/hour) | Steady trickle of replies at roughly constant rate |
| 0 | Declining or flat | No new replies in last 30+ minutes |

**Edge case — viral spike:** If a post had a sudden spike (e.g., retweeted by large account) and then slowed, check if the spike was within the last hour. If yes, velocity might still be high despite the slowdown (the spike audience is still discovering it).

### Dimension 4: Relevance (0-4 points)
How aligned with the AI niche? This is the HIGHEST weighted dimension.

| Score | Criteria | Examples |
|-------|----------|---------|
| 4 | Perfect: directly in core AI niche | Post about LLM capabilities, AI tools, AI ethics, AI research |
| 3 | Strong: AI-adjacent with clear connection | Post about tech industry trends that impact AI, programming productivity |
| 2 | Adjacent: related tech/business topic with AI angle | Post about tech layoffs (can connect to AI automation angle) |
| 1 | Tangential: loosely connected to AI | Post about general tech news, science breakthrough |
| 0 | Unrelated: no meaningful AI connection | Sports, politics, entertainment (unless AI-specific) |

**Relevance override:** If relevance is 0 but the post is from a Tier-1 must_follow account AND the topic could connect to AI with a creative angle, you may score it 1 (with a note explaining the creative angle). Never force relevance above 1 for tangential content.

### Dimension 5: Authority (0-2 points)
What is the original author's credibility?

| Score | Criteria | Cross-reference |
|-------|----------|----------------|
| 2 | High Tweepcred: 10K+ followers, established voice | Check config/followed_accounts.json — if tier is "must_follow", default to 2 |
| 1 | Medium: 1K-10K followers, growing presence | Check if they're cited by high-Tweepcred accounts |
| 0 | Low: <1K followers, new or unknown account | If account was created in last 30 days, default to 0 regardless of follower count |

**Edge cases:**
- Account has high followers but low engagement rate (bot-like): score 1 at most
- Account is a "reply guy" (high volume, low quality): score 0
- Account is verified (blue check) but unknown: score 1 (verification alone is not enough)
- Account blocked by people you follow: skip entirely (negative signal)
- Account is a brand/corporate account vs personal: corporate accounts get -1 to this dimension (less conversation value)

### Dimension 6: Saturation Penalty (-1 point)
Is the reply section already flooded?

| Score | Criteria | Notes |
|-------|----------|-------|
| 0 | Not saturated: <50 replies | Your reply has visibility |
| -1 | Saturated: 50+ replies | Your reply will likely be buried |

**Saturation exception:** If the post is still gaining velocity (score 2 on velocity) AND has 50-100 replies, waive the penalty. The thread is still growing and new viewers will see recent replies. Apply the penalty only if velocity is 0 or 1.

### Grade Thresholds and Actions

| Grade Range | Score | Label | Action |
|------------|-------|-------|--------|
| 9-12 | Must Reply | Critical | Generate replies immediately — prime opportunity |
| 7-8 | High Priority | Strong | Generate replies within 2 hours |
| 5-6 | Worth Considering | Moderate | Generate replies if time allows |
| 3-4 | Low Priority | Weak | Skip unless nothing better |
| 0-2 | Skip | Negligible | Do not waste time |

---

## Orchestration Protocol

### Execution Order
1. **Watchlist Sentinel** (always first — highest priority accounts)
2. **Trending Conversation Scanner**
3. **Announcement & Launch Reactor** (time-sensitive)
4. **Thread Deep-Diver**
5. **Question & Help Finder**
6. **Controversy & Debate Hunter** (run near end — you need landscape context first)
7. **Cross-Niche Bridge Finder** (last — broadest, most speculative)

### Deduplication
- Same post found by multiple agents → merge, keep highest grade
- Same topic from different posts → keep the one with higher grade and better timing
- If two posts are from the same author on the same topic → keep the one with more engagement

### Filtering
- Remove all items scoring below 5/12
- Flag items with toxicity level "high" for manual review before any reply generation
- Flag items with risk_of_backlash "high" for manual review
- If no items score above 5: report this to user and suggest trying again in a few hours

---

## Agent 1: Watchlist Sentinel

### Focus
Monitor the 30 accounts in `config/followed_accounts.json` for reply opportunities. This is the HIGHEST priority agent because replying to accounts you follow builds the strongest relationships.

### Search Protocol
```
For must_follow accounts (check every run):
  Search: "from:[handle]" (check their recent posts)
  Search: "site:x.com [handle]" (find mentions and replies)

For high_priority accounts (check every run):
  Search: "site:x.com [handle]" recent posts
  Search: "[handle] tweet" today

For standard accounts (check every other run):
  Batch search: "site:x.com [handle1 OR handle2 OR handle3]" this week

For low_priority accounts (check weekly):
  Only if specifically requested by user
```

### Filters
**In scope:** Original posts with engagement, questions from followed accounts, announcements, contrarian takes, threads being written

**Out of scope:** Retweets without commentary, engagement bait ("what do you think?"), promotional posts for their own product, posts older than 24 hours, replies they've made to others (focus on THEIR original content)

**Priority boost:** +1 to combined score if the author is in your "must_follow" tier AND you've never replied to them before (first interaction opportunity).

### Edge Cases
- **Account not posting:** If a must_follow account hasn't posted in 7+ days, note this in the log (may need to check if account is active)
- **Account posting too much:** If a followed account posts 20+ times per day, focus only on posts with above-average engagement for that account
- **Protected/private account:** If an account is private, skip it and note in the log
- **Account name/handle change:** If a followed account has changed handle, update config/followed_accounts.json automatically and note the change
- **Your previous replies:** Check if you've already replied to a post. If yes, skip (don't reply twice to the same post). Check data/reply_opportunities.json for history.
- **Author interaction history:** If the author has previously replied to YOU, prioritize their posts (+1 to authority dimension)

### Unique Output Fields
```json
{
  "watchlist_account": "string — handle",
  "account_tier": "must_follow | high_priority | standard | low_priority",
  "account_category": "string — from config categories",
  "post_type": "original | thread | question | announcement | opinion | hot_take | other",
  "existing_reply_count_estimate": "integer",
  "reply_position_available": "early_1st_to_2nd | sweet_spot_3rd_to_10th | mid_11th_to_30th | late_31st_to_50th | buried_50plus",
  "historical_engagement_with_author": "string — 'first interaction' or 'previously replied on [date], got [X] likes'",
  "has_author_engaged_with_you_before": true | false
}
```

---

## Agent 2: Trending Conversation Scanner

### Focus
Find currently trending AI conversations on X with reply potential. These are the "big waves" — high-visibility threads that, if you reply early and well, can drive significant profile views.

### Search Queries
```
Query 1: "AI trending" OR "AI viral tweet" OR "AI conversation" site:x.com
Query 2: "trending AI topics" OR "hot AI debate" today
Query 3: "AI" site:x.com with high engagement indicators
Query 4: "AI twitter debate" OR "AI twitter discussion" this week
Query 5: Check trending hashtags related to AI (#AI, #ArtificialIntelligence, #LLM, #MachineLearning)
Query 6 (backup): "most discussed AI" OR "biggest AI conversation" this week
Query 7 (backup): site:reddit.com/r/artificial "trending on X" OR "going viral on twitter"
```

### Filters
**In scope:** Posts generating 50+ replies, active debates, posts getting quote-tweeted, viral AI content, trending hashtags with substance

**Out of scope:** Old viral posts (>48h), non-AI trending topics, purely entertainment/meme content, toxic threads (>30% hostile replies)

**Quality gate:** Must show actual engagement momentum (not just large follower count of author).

### Edge Cases
- **Multiple trends on same topic:** If #AI and #MachineLearning are both trending about the same news, treat as one trend. Don't create duplicate opportunities.
- **Trend hijacking:** If a non-AI account is jumping on an AI trend with low-quality content, skip.
- **Trend fatigue:** If a topic has been trending for 3+ days, the conversation is likely saturated. Reduce recency and velocity scores.
- **Geographic trends:** Some trends are region-specific. Note if a trend is primarily in a non-English-speaking market.

### Unique Output Fields
```json
{
  "trend_topic": "string — the broader trend",
  "estimated_reach": "string — e.g., 'estimated 50K+ impressions'",
  "conversation_volume": "string — e.g., 'high (150+ replies)'",
  "diversity_of_viewpoints": "low | medium | high",
  "quote_tweet_count_estimate": "integer",
  "trend_velocity": "accelerating | stable | declining",
  "estimated_time_left_to_engage": "string — e.g., '2-4 hours before thread dies'",
  "trend_hashtag": "string — if applicable"
}
```

---

## Agent 3: Controversy & Debate Hunter

### Focus
Find productive AI debates where a well-reasoned reply adds value. STRICTLY exclude toxic threads.

### Search Queries
```
Query 1: "AI debate" OR "AI controversy" OR "AI disagreement" site:x.com
Query 2: "AI opinion" controversial OR divisive site:x.com
Query 3: "AI hot take" OR "AI unpopular opinion" site:x.com
Query 4: "AI regulation debate" OR "AI safety debate" OR "AI ethics debate" site:x.com
Query 5: "[specific debate topic]" — rotate: open_source_vs_closed, AI_regulation, AI_alignment, AI_job_displacement, AI_consciousness, AI_copyright
Query 6 (backup): "AI" "ratioed" OR "ratio" site:x.com (find controversial posts)
Query 7 (backup): "AI" "wrong" OR "disagree" OR "debunk" site:x.com
```

### Filters
**In scope:** Productive disagreements with evidence, policy discussions, technical debates (architecture approaches, benchmark validity), business strategy disagreements

**STRICTLY OUT OF SCOPE:**
- Personal attacks, name-calling, ad hominem arguments
- Political polarization without substance
- Culture-war adjacent threads
- Threads where the author is clearly trolling
- Threads about non-AI controversies using AI as a wedge

**Toxicity check (MANDATORY before including any result):**
1. Read the first 20 visible replies
2. Count hostile/insulting replies
3. If >30% are hostile: SKIP the thread, mark as "toxicity_level: high"
4. If 10-30% are hostile: INCLUDE but flag as "toxicity_level: medium" and reduce authority score by 1
5. If <10% are hostile: INCLUDE with "toxicity_level: low"

**Quality gate:** Controversy must be substantive (about ideas, evidence, methods) — never personal.

### Edge Cases
- **You've been tagged in a debate:** If someone directly @s you in a debate thread, prioritize this (+2 to combined score) but still apply toxicity checks.
- **Author deletes controversial post:** If the original post was deleted but the thread continues, skip — the conversation has lost its anchor.
- **Ratio in progress:** If a post is actively being ratioed (replies >> likes), it's controversial but risky. Flag as "active_ratio: true" and set risk_of_backlash to "high".
- **Wrong side of debate:** If you disagree with the majority in the thread, replying has higher risk but also higher visibility. Note the risk.
- **Author has a history of blocking people:** Check if the author is known for blocking dissenters. If yes, reduce priority.

### Unique Output Fields
```json
{
  "controversy_topic": "string — what the debate is about",
  "side_a_summary": "string — one side's position",
  "side_b_summary": "string — the other side's position",
  "toxicity_level": "none | low | medium | high — skip if high",
  "toxicity_check_sample_size": "integer — how many replies were checked",
  "your_possible_angle": "string — which side would you take and why?",
  "risk_of_backlash": "low | medium | high",
  "credibility_opportunity": "integer 0-10 — how much would a good reply boost your authority?",
  "active_ratio": true | false,
  "is_productive_debate": true | false
}
```

---

## Agent 4: Question & Help Finder

### Focus
Find questions about AI that you can answer with authority. Answering questions is one of the fastest ways to build credibility — it positions you as knowledgeable and helpful.

### Search Queries
```
Query 1: "AI question" OR "how does AI" OR "what is AI" site:x.com
Query 2: "AI help" OR "AI advice needed" OR "AI recommendation" site:x.com
Query 3: "can AI do" OR "is AI capable of" OR "will AI replace" site:x.com
Query 4: "AI beginner question" OR "AI explained" OR "ELI5 AI" site:x.com
Query 5: "[specific topic] question" OR "how to [topic]" site:x.com — rotate topics
Query 6 (backup): site:reddit.com/r/artificial "how" OR "what" OR "why" AI
Query 7 (backup): "AI" "someone explain" OR "can someone tell me" site:x.com
```

### Filters
**In scope:** Genuine questions about AI capabilities, tool recommendations, "how does X work", career advice about AI, implementation questions, "which is better" comparisons

**Out of scope:** Rhetorical questions, questions already well-answered by 5+ people, questions too basic (you'd look condescending), questions in threads where you've already answered, homework questions

**Quality gate:** You MUST have genuine expertise or verifiable experience to answer. If you'd be guessing, skip. Check data/sent_posts.json and data/reply_opportunities.json for evidence of past expertise on the topic.

### Edge Cases
- **Question from a high-follower account:** If someone with 50K+ followers asks a question, prioritize this (+2 to combined score). Your reply gets massive visibility.
- **Question already answered:** If 3+ people have already given good answers, skip (no room to add value). If answers are mediocre, include (opportunity to give a better answer).
- **Question is a trap:** Some "questions" are actually opinions disguised as questions. Read the full context. If the "asker" has already made up their mind, skip.
- **Question about a tool you haven't used:** If someone asks "Is Claude better than GPT-4?" and you haven't used both recently, either skip or answer with clear caveats about your limited experience.
- **Question from your own audience:** If a previous reply of yours generated a follow-up question, prioritize this (relationship building).

### Unique Output Fields
```json
{
  "question_type": "factual | recommendation | how_to | career | implementation | conceptual | comparison",
  "question_category": "string — specific AI sub-topic",
  "estimated_answer_quality": "high | medium | low — based on your documented expertise",
  "answer_difficulty": "easy | moderate | complex — how much effort to write a good answer",
  "existing_answers_quality": "string — 'no answers yet' / 'mediocre answers' / 'good answers already given'",
  "existing_answer_count": "integer",
  "authority_building_potential": "integer 0-10",
  "questioner_follower_count": "string — approximate, if visible"
}
```

---

## Agent 5: Announcement & Launch Reactor

### Focus
Find product launches, feature releases, and announcements that are ripe for a timely reaction. Speed matters — the window for reaction posts is narrow.

### Search Queries
```
Query 1: "AI product launch" OR "AI tool release" OR "AI feature announcement" today
Query 2: "AI startup launches" OR "AI company announces" site:techcrunch.com OR site:theverge.com
Query 3: "AI update" OR "AI new version" OR "AI upgrade" 2025
Query 4: "AI API release" OR "AI SDK release" OR "AI model release" OR "AI model update"
Query 5: site:x.com "just launched" OR "announcing" OR "excited to announce" AI
Query 6 (backup): "AI beta" OR "AI early access" OR "AI waitlist" launch
Query 7 (backup): site:producthunt.com "AI" — check today's launches
```

### Filters
**In scope:** New product launches, major feature updates, pricing announcements, partnership announcements, funding announcements, open-source releases, beta access openings

**Out of scope:** Minor patches, UI tweaks, marketing campaigns without substance, rebranding without product change, "we're hiring" announcements, events/conference announcements without product news

**Timing:** Must be within 24 hours. Older announcements are already covered. Flag urgency.

**Quality gate:** Must be from a credible company/individual with a real, usable product or verifiable announcement.

### Edge Cases
- **Soft launch:** Some launches are quiet (no press coverage, just a blog post). If you find one before it trends, this is a HIGH value opportunity (first-mover advantage). Mark as "early_discovery: true" and +2 to combined score.
- **Launch fail/controversy:** If a launch is receiving negative feedback, this is a different type of opportunity — analysis of what went wrong. Still include but note the sentiment.
- **Competitor's launch:** If a competitor to a company on your watchlist launches, this is an opportunity to compare/contrast. Note the competitive angle.
- **Phased launch:** If a product launches in stages (beta → early access → GA), each stage is a separate opportunity if within 24h.
- **Announcement is actually old:** If an "announcement" is just a blog post summarizing what was already known, skip. True announcements contain NEW information.

### Unique Output Fields
```json
{
  "announcement_type": "product_launch | feature_release | pricing | partnership | funding | open_source | beta_access",
  "company_name": "string",
  "company_size": "string — e.g., 'startup (<50)', 'mid-size', 'enterprise'",
  "announcement_url": "string",
  "hours_since_announcement": "float — critical for urgency calculation",
  "existing_reaction_quality": "string — what are others saying?",
  "existing_reaction_count": "integer — how many reactions already?",
  "your_unique_angle": "string — what can you add that others haven't?",
  "urgency_minutes": "integer — estimated minutes until conversation moves on",
  "audience_reach_estimate": "string — how many people talking about this?",
  "early_discovery": true | false,
  "launch_sentiment": "positive | mixed | negative | controversial"
}
```

---

## Agent 6: Thread Deep-Diver

### Focus
Find substantive threads worth adding a reply to. Not all threads are equal — we're looking for threads where your reply adds genuine value and gets visibility.

### Search Queries
```
Query 1: "AI thread" OR "AI 🧵" site:x.com — filter for long threads
Query 2: "must read AI thread" OR "essential AI thread" OR "best AI thread"
Query 3: "AI breakdown" OR "AI analysis thread" site:x.com
Query 4: "[specific topic] thread" site:x.com — rotate topics
Query 5: "AI explained" thread OR "AI how it works" thread site:x.com
Query 6 (backup): "AI" "🧵" site:x.com with engagement indicators
Query 7 (backup): site:reddit.com/r/artificial "someone should make a thread about" AI
```

### Filters
**In scope:** Educational threads (5+ tweets), analysis threads, step-by-step guides, compilation/curated lists, "what I learned" threads, research summary threads

**Out of scope:** Quote-tweet chain reactions, self-promotional threads, threads with low engagement despite length, threads that are just the author talking to themselves with no audience engagement, "read my blog" threads without substance

**Quality gate:** Thread must have substantive content AND audience engagement. A great thread with 0 replies has no reply value.

### Thread Assessment Criteria
1. **Depth:** Does the thread go beyond surface-level observations?
2. **Accuracy:** Are the claims verifiable? (If not, this is a correction opportunity)
3. **Completeness:** Are there obvious gaps you could fill?
4. **Audience:** Is the thread's audience also your target audience?
5. **Reply position:** Where in the thread would your reply add the most value? (Usually NOT the last reply — aim for a point where there's a natural gap)

### Edge Cases
- **Thread is ongoing:** If the author is still adding tweets, note the current length but flag as "thread_in_progress: true". The final tweet might change the context.
- **Thread author is controversial:** If the author is known for problematic takes but THIS thread is good, still include but note the author context.
- **Your thread:** If someone is replying to YOUR thread, prioritize this (relationship building, audience engagement).
- **Cross-thread reply:** The best reply opportunity might not be to the thread itself but to a high-engagement reply within the thread. Check the replies too.
- **Archived/stale thread:** If the thread was from last week but just got rediscovered (retweet by large account), treat as fresh (recency resets).

### Unique Output Fields
```json
{
  "thread_length_estimate": "integer — number of tweets",
  "thread_topic": "string",
  "thread_author": "string — handle",
  "thread_author_follower_count": "string — approximate",
  "key_points_covered": ["list of main points"],
  "missing_angles": ["list of angles NOT covered — these are YOUR opportunities"],
  "best_reply_position": "string — where in the thread to add value (e.g., 'after tweet 7 — missing business angle')",
  "thread_engagement_trend": "growing | stable | declining | resurging",
  "has_author_replied_to_others": true | false,
  "thread_in_progress": true | false,
  "accuracy_issues_found": ["list of any claims that seem inaccurate"]
}
```

---

## Agent 7: Cross-Niche Bridge Finder

### Focus
Find connections between AI and other domains that create unique reply opportunities at the intersection. These replies expose you to new audiences.

### Search Queries
```
Query 1: "AI in healthcare" OR "AI in finance" OR "AI in legal" site:x.com
Query 2: "AI disrupting" OR "AI transforming" [industry] site:x.com — rotate industries
Query 3: "[domain] AI" OR "[domain] machine learning" site:x.com — rotate domains
Query 4: "AI applications in" [industry] breakthrough OR success site:x.com
Query 5: "AI impact on [professionals]" site:x.com — rotate: doctors, lawyers, teachers, developers, designers
Query 6 (backup): "[industry] AI adoption" OR "[industry] AI resistance" site:x.com
Query 7 (backup): "AI will replace [profession]" OR "[profession] AI future" site:x.com
```

### Domain Rotation List
1. Finance/Trading/Investing
2. Healthcare/Medicine/Biotech
3. Legal/Law/Compliance
4. Education/EdTech
5. Creative/Design/Art/Music
6. Sports/Esports
7. Agriculture/FoodTech
8. Manufacturing/Supply Chain/Logistics
9. Real Estate/PropTech
10. Media/Journalism/Publishing

### Filters
**In scope:** Posts about AI's impact on non-AI domains, success stories, concerns from domain experts, regulatory discussions for specific domains, cross-domain insights

**Out of scope:** Generic "AI will change everything" posts, domain-specific posts with no AI angle, promotional content for AI tools in specific domains, "AI vs humans" fear-mongering without substance

**Quality gate:** The post must have a genuine AI connection — not just mentioning AI in passing. The bridge must be specific, not vague.

### Edge Cases
- **Domain expert vs AI expert:** If the poster is a domain expert (e.g., a doctor talking about AI in healthcare), your reply should respect their domain expertise. If they're an AI person talking about a domain, they might get details wrong — correction opportunity.
- **Cultural sensitivity:** Some domains (healthcare, legal) have higher stakes. Replies in these domains require more care and accuracy. Flag as "high_stakes_domain: true".
- **Audience mismatch:** If the domain's audience is very different from AI Twitter (e.g., agriculture), your reply might not land well. Note the audience gap.
- **Trend in the domain:** If the domain itself has a trending conversation (e.g., "doctors debating AI diagnosis"), this is higher priority than a random post.

### Unique Output Fields
```json
{
  "primary_domain": "string — the non-AI domain",
  "bridge_angle": "string — how AI connects to this domain",
  "domain_expert_author": "string — is the author a domain expert?",
  "cross_audience_reach": "string — could this expose you to a new audience?",
  "niche_knowledge_required": "string — what domain knowledge helps with this reply?",
  "estimated_new_audience_exposure": "integer 0-10",
  "bridge_relevance": "integer 0-10 — how strong is the AI-domain connection?",
  "high_stakes_domain": true | false,
  "audience_compatibility": "high | medium | low — how likely is the domain audience to also care about AI?"
}
```

---

## Output Schema (data/reply_opportunities.json)

```json
{
  "metadata": {
    "description": "Graded reply opportunities from the 7 reply hunting agents",
    "updated_by": "reply_hunt and generate_replies commands",
    "grade_threshold": 5,
    "retention_policy": "Opportunities older than 24 hours are marked expired"
  },
  "last_updated": "ISO 8601 timestamp",
  "run_count": "integer",
  "opportunities": [
    {
      "id": "string — unique identifier",
      "post_url": "string — URL of the original post",
      "author_handle": "string",
      "author_name": "string",
      "author_follower_count": "string — approximate if known",
      "author_tweepcred": "string — low | medium | high",
      "post_text_snippet": "string — first 100 characters",
      "post_full_text": "string — full text if available",
      "post_type": "original | reply | thread_start | quote_tweet",
      "discovered_by_agent": "string — agent name",
      "discovered_at": "ISO 8601 timestamp",
      "post_created_at": "ISO 8601 timestamp or estimate",
      "grade": {
        "total": "float — max 12, min -1",
        "recency": "0-2",
        "performance": "0-2",
        "velocity": "0-2",
        "relevance": "0-4",
        "authority": "0-2",
        "saturation_penalty": "0 or -1"
      },
      "priority": "must_reply | high_priority | worth_considering | skip | expired",
      "unique_fields": {},
      "reply_drafts": [],
      "status": "found | drafts_generated | replied | skipped | expired",
      "expires_at": "ISO 8601 timestamp — 24h after discovery"
    }
  ]
}
```

## Run Log Schema (logs/agent_runs/reply_hunt_TIMESTAMP.json)

```json
{
  "run_timestamp": "ISO 8601 timestamp",
  "duration_seconds": "float",
  "agents_run": ["list of agent names"],
  "agents_skipped": ["list with reasons"],
  "opportunities_before_filter": "integer",
  "opportunities_after_filter": "integer",
  "opportunities_by_grade": {
    "must_reply": "integer",
    "high_priority": "integer",
    "worth_considering": "integer",
    "skip": "integer"
  },
  "items_flagged_toxic": "integer",
  "items_flagged_backlash_risk": "integer",
  "tool_errors": []
}
```
