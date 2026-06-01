# Reference: News Hunting Agents (7 Sub-Agents)

> **Loaded by:** SKILL.md when user triggers Mode 1 (News Pipeline)
> **Agents:** 7 sub-agents scanning different facets of the AI landscape
> **Output:** `data/news_queue.json` — ranked list of news items
> **Log:** `logs/agent_runs/news_hunt_TIMESTAMP.json`

---

## Orchestration Protocol

### Execution Order
Run agents **1 through 7 sequentially**. Each agent completes fully before the next begins. This order is deliberate:
1. Automation Scout (quick wins, usually most items)
2. Corporate Watcher (high-priority company news)
3. Leak Hunter (high-value but lower reliability)
4. Research Tracker (niche but high-authority)
5. Economics Analyst (market context)
6. Founder Insights (narrative and opinion)
7. Tool Spotlight (practical, actionable)

### Per-Agent Execution Protocol
For EACH agent:
1. Execute ALL specified search queries (minimum 5 per agent)
2. For each search result: fetch the full article/page content
3. Apply the agent's filters to determine inclusion
4. Extract all specified output fields
5. Assign relevance score (0-10)
6. If fewer than 3 items found: run 3 additional backup queries
7. If still 0 items: log the failure and continue

### Search Tool Protocol
- Use `web_search` (or `google_search`) for initial discovery
- Use `web_fetch` (or `web-reader`) to read full article content
- Search may identify a candidate X post URL, but any X/Twitter post, thread, author timeline, or engagement detail must be retrieved through the pinned XCLI route in `scripts/source_clis.py` and `scripts/xcli_utils.py` (`twitter_read`, validated `twitter_timeline`, or `twitter_home`).
- If a fetch fails: try the URL with `https://r.jina.ai/[URL]` as fallback
- If a search returns 0 results: rephrase the query (different keywords, broader/narrower scope)
- If a search returns > 50 results: add specificity constraints (date filters, site restrictions)
- Never make the exact same search query twice in one run

### Deduplication Protocol
After all 7 agents complete:
1. **Story Grouping:** Group items that reference the same event/topic (even from different angles)
   - Same company + same event = same story (e.g., "OpenAI raises funding" from TechCrunch AND Bloomberg)
   - Same research paper from different sources = same story
   - Same product launch from different angles = same story
   - Different products from same company on same day = different stories
2. **Merge:** Keep the entry with the highest relevance score. Merge all unique output fields from each agent.
3. **Cross-Agent Bonus:** If 3+ agents find the same story, add +1 to relevance (signals broad importance)
4. **Rank:** Apply the ranking formula below

### Ranking Formula
```
Combined Score = Relevance (0-10) + Timeliness Bonus + Audience Match Bonus + Cross-Agent Bonus

Timeliness Bonus:
  +3 if story is less than 6 hours old
  +1 if story is 6-24 hours old
  0 if story is 24-72 hours old
  -2 if story is over 72 hours old (should rarely appear)

Audience Match Bonus:
  +2 if story directly targets AI practitioners (developers, researchers, builders)
  +1 if story targets tech-curious general audience
  0 if story is only relevant to AI researchers (very niche papers)
  -1 if story is only relevant to non-AI audience (tangential)

Cross-Agent Bonus:
  +1 if 3+ agents independently found the same story
  0 if 2 agents found it
  -1 if only 1 agent found it BUT it's from a tier-1 source

Max possible score: 16
Min possible score: -3
```

### Presentation Protocol
After ranking, present to user:
```
# News Queue — [Date] | [Total Items: X] | [After Dedup: Y]

| # | Score | Agent | Headline | Source | Age |
|---|-------|-------|----------|--------|-----|
| 1 | 14.5 | Corp Watcher | OpenAI announces GPT-5 | TechCrunch | 2h |
| 2 | 13.0 | Leak Hunter | GPT-5 benchmark leak | Reddit | 45m |

## Top 3 Recommended for Fact-Checking: #1, #2, #5

**Agent Performance:**
- Automation Scout: 12 items found
- Corporate Watcher: 8 items found
- Leak Hunter: 3 items found (1 debunked during dedup)
- Research Tracker: 5 items found
- Economics Analyst: 7 items found
- Founder Insights: 4 items found
- Tool Spotlight: 9 items found

**Items saved to data/news_queue.json**
**Log saved to logs/agent_runs/news_hunt_[timestamp].json**
```

---

## Agent 1: Automation Scout

### Focus
Discover new AI automation tools, frameworks, and integrations that save time or replace manual workflows. This agent casts the widest net — looking for anything that helps people do things faster with AI.

### Search Queries (execute ALL)
```
Query 1: "new AI automation tool launch" site:techcrunch.com OR site:producthunt.com OR site:theverge.com
Query 2: "AI workflow automation" site:medium.com OR site:dev.to
Query 3: "AI agent framework release" OR "AI agent SDK" OR "AI agent platform"
Query 4: "automate coding with AI" OR "automate writing with AI" OR "automate data with AI"
Query 5: "AI no-code platform launch" OR "AI low-code" release OR beta
Query 6 (backup): site:reddit.com/r/artificial "new AI tool" OR "useful AI tool" OR "AI automation"
Query 7 (backup): "AI productivity tool" launch OR release OR announce
```

### Filters
**In scope:**
- New tool launches and beta releases
- Major version updates (v1.0 → v2.0, not patch releases)
- Open-source releases with actual usable code
- Integrations between existing AI tools
- New features in existing tools that change workflows significantly

**Out of scope:**
- Generic "AI is changing everything" articles without specific tool mentions
- Tools without specific features described
- Articles older than 72 hours
- Paid promotions disguised as news
- "Top 10 AI tools" listicles without original reviews
- Graduate student projects without users or real use cases

**Quality gate:** Must mention at least ONE of: a specific feature name, a benchmark number, a use case, a pricing detail, or a comparison to an existing tool.

### Edge Cases
- **Tool rebranded:** If a tool has been renamed, treat as update not new launch. Note: "[Old name] → [New name] rebrand"
- **Paid vs free:** Always note pricing model. Free/open-source tools get +1 relevance. Expensive enterprise-only tools get -1.
- **Demo-only tools:** If the tool only has a demo video and no public access, flag as "demo_only: true" and reduce relevance by 2.
- **Same tool, multiple launches:** If a tool appears in multiple launch contexts (Product Hunt, tech blog, HN), deduplicate but note the traction across platforms.

### Unique Output Fields
```json
{
  "tool_name": "string — the name of the tool",
  "tool_url": "string — official URL",
  "category": "coding | writing | data | design | support | research | general | video | audio | image",
  "pricing_model": "free | freemium | paid | open_source | enterprise | unknown",
  "key_feature": "string — the single most notable feature (one sentence)",
  "replaces": "string — what manual process or existing tool it replaces",
  "innovation_score": "integer 0-10 — how novel is this approach? (0 = incremental, 10 = paradigm shift)",
  "existing_alternatives": ["list of competing tools"],
  "availability": "public_beta | private_beta | waitlist | generally_available | demo_only",
  "traction_signals": "string — e.g., '500+ upvotes on HN' or 'Trending on Product Hunt'"
}
```

---

## Agent 2: Corporate Watcher

### Focus
Track announcements, strategy shifts, and business moves from major AI companies. This agent monitors the top 20 AI companies by market cap/funding.

### Monitored Companies (Tier 1 — check every run)
OpenAI, Anthropic, Google DeepMind, Meta AI, Microsoft AI, Amazon (Bedrock/AWS AI), Apple AI, Mistral, xAI

### Monitored Companies (Tier 2 — check every other run)
Cohere, Inflection, Adept, Stability AI, Jasper, Typeface, Glean, Databricks, Snowflake, Salesforce AI, IBM (watsonx), Nvidia AI

### Search Queries (execute ALL)
```
Query 1: "OpenAI announcement" OR "press release" (repeat for each Tier 1 company)
Query 2: "OpenAI" OR "Anthropic" OR "DeepMind" "launch" OR "release" OR "announce" today
Query 3: "[Company name]" strategy OR pivot OR restructure OR acquire (rotate through Tier 1)
Query 4: "[Company name]" funding OR investment OR valuation (rotate through Tier 1)
Query 5: "AI company IPO" OR "AI startup acquisition" OR "AI company merger"
Query 6 (backup): "OpenAI" OR "Anthropic" OR "Mistral" OR "xAI" site:reuters.com OR site:bloomberg.com
Query 7 (backup): "[Company name]" partnership OR collaboration OR integration (rotate)
```

### Filters
**In scope:**
- Product launches, major updates, and new API releases
- Funding rounds (Series A+), IPOs, and acquisitions
- Leadership changes (CEO, CTO, Board)
- Strategy pivots and new business lines
- Partnerships between major companies
- API pricing changes and usage policy changes
- Regulatory responses and policy statements

**Out of scope:**
- Unsubstantiated rumors without any source
- Generic company news ("hiring 100 engineers")
- Employee reviews, salary discussions, or job postings
- Founder personal life news (unless directly relevant to company strategy)
- Old announcements being recirculated

**Quality gate:** Must cite a specific event with a date and a primary source.

### Edge Cases
- **Multiple events same day:** If one company has 2+ events on the same day (e.g., product launch AND funding), create separate entries for each.
- **Revenue vs valuation:** Clearly distinguish between revenue numbers and valuation numbers. Revenue = actual income. Valuation = theoretical worth.
- **Stealth vs announced:** If a company is "in stealth" but news leaks, note as "unconfirmed" with reduced relevance (-2).
- **Government/regulatory:** If a company faces regulatory action, include it but flag as "regulatory" category. These often generate different tweet angles (opinion vs news).
- **Competitor cross-reference:** When reporting Company A's news, check if it impacts Company B. Note: "Also affects: [companies]"

### Unique Output Fields
```json
{
  "company": "string — company name",
  "company_tier": "tier_1 | tier_2",
  "event_type": "launch | funding | acquisition | leadership | partnership | pricing | policy | regulatory | other",
  "financial_impact": "string — dollar amount, valuation, market cap change, or 'none'",
  "strategic_significance": "integer 0-10 — how much does this shift the competitive landscape?",
  "competitors_affected": ["list of competitor companies directly impacted"],
  "timeline_impact": "string — when will the effects be felt? (immediate / 3-6 months / 12+ months / unknown)",
  "is_confirmed": true | false,
  "source_count": "integer — how many independent sources report this?"
}
```

---

## Agent 3: Leak Hunter

### Focus
Find credible leaks, rumors, and early information about unannounced AI products or features. This agent has the highest risk/reward ratio — leaks can be huge scoops, but also easily debunked.

### Search Queries (execute ALL)
```
Query 1: "AI leak" OR "leaked" OR "internal document" site:reddit.com OR site:theverge.com OR site:9to5google.com
Query 2: "OpenAI leak" OR "Anthropic leak" OR "DeepMind leak" unreleased OR beta OR internal
Query 3: "GPT-5" OR "Claude 4" OR "Gemini 2" OR "Llama 4" leak OR rumor OR benchmark
Query 4: "AI model benchmark leak" OR "internal benchmarks" OR "eval results leak"
Query 5: "AI unreleased feature" OR "hidden feature" OR "disabled feature" OR "beta feature"
Query 6 (backup): site:reddit.com/r/singularity OR r/machinelearning "leak" OR "rumor" AI
Query 7 (backup): "AI product leak" screenshot OR video OR demo
```

### Filters
**In scope:**
- Screenshots of unreleased UI or features
- Benchmark leaks with actual numbers
- Internal documents or slides
- Credible insider claims with track record
- Beta feature discoveries by users
- Regulatory filings that reveal product plans
- Code-level discoveries (API endpoints, model IDs in code)

**Out of scope:**
- Unverified anonymous claims with zero evidence
- Obvious fakes or attention-seeking posts
- Old leaks being recirculated as new
- Speculation without ANY supporting evidence
- "My uncle works at OpenAI" type posts

**Quality gate:** Must have at least ONE form of indirect evidence:
- Screenshot or image
- Benchmark data table
- Code snippet or API reference
- Regulatory filing
- Pattern of behavior (company has done similar before)
- Credible leaker with history

**Verification urgency:** Flag ALL leak items for immediate fact-checking before any post generation.

### Evidence Reliability Scale
| Evidence Type | Confidence | Notes |
|--------------|------------|-------|
| Official regulatory filing | Very High | SEC filing, patent application |
| Code-level evidence (API, model IDs) | High | Reversibly verifiable |
| Multiple independent leaks corroborating | High | Reddit + Verge + Bloomberg all say same thing |
| Single credible screenshot | Medium | Could be mocked but pattern matches |
| Single insider claim (anonymous) | Low | Unverifiable without corroboration |
| "Trust me bro" post | Very Low | Skip entirely |

### Edge Cases
- **Leak confirmed vs debunked:** If a leak was previously debunked but resurfaces, flag as "previously_debunked" and set relevance to 0. Do not include in results.
- **Partial leak:** If only part of a leak is confirmed (e.g., the product name is real but the specs are fake), note which parts are confirmed.
- **Controlled leak:** Some leaks are intentional (companies seeding info). If the timing is suspiciously perfect (leak drops 48h before official event), flag as "possible_controlled_leak".
- **Translation issues:** If a leak is in a non-English source, translate before processing. Note original language.
- **Deleted leak:** If the original source was deleted, check web archives (archive.org). If found in archive, note as "source_was_deleted" with reduced confidence (-2).

### Unique Output Fields
```json
{
  "leak_source": "string — where the leak came from (site, platform, person)",
  "evidence_type": "screenshot | benchmark | document | filing | insider_claim | code_reference | video",
  "confidence": "very_high | high | medium | low | very_low",
  "verification_status": "confirmed | partially_confirmed | unverified | disputed | debunked",
  "breakout_potential": "integer 0-10 — how much attention will this get when/if confirmed?",
  "risk_of_being_wrong": "integer 0-10 — what's the chance this is fabricated?",
  "time_to_confirmation": "string — estimated time until official confirmation (hours / days / weeks / never)",
  "requires_immediate_fact_check": true,
  "corroborating_sources": ["list of URLs that partially or fully corroborate"]
}
```

---

## Agent 4: Research Tracker

### Focus
New AI research papers, preprints, and academic breakthroughs relevant to practitioners — not purely theoretical. This agent prioritizes papers with practical implications.

### Primary Sources
- arxiv.org (categories: cs.AI, cs.CL, cs.LG, cs.CV, cs.RO)
- Papers With Code (paperswithcode.com)
- Hugging Face Papers (huggingface.co/papers)
- Google Scholar alerts
- Semantic Scholar
- MIT Technology Review
- Nature / Science AI sections
- Journal of Machine Learning Research

### Search Queries (execute ALL)
```
Query 1: site:arxiv.org "artificial intelligence" OR "large language model" OR "diffusion model" OR "reinforcement learning"
Query 2: "new AI research paper" breakthrough OR state-of-the-art OR SOTA
Query 3: site:paperswithcode.com new benchmark OR new result
Query 4: "AI research" practical application OR real-world result OR production
Query 5: "[topic rotation]" paper — rotate: reasoning, multimodal, alignment, efficiency, robotics, safety, interpretability, neurosymbolic
Query 6 (backup): "arxiv" AI paper trending OR viral OR discussed
Query 7 (backup): site:reddit.com/r/MachineLearning "paper" OR "arxiv" AI
```

### Filters
**In scope:**
- Papers with practical production implications
- New state-of-the-art (SOTA) results on standard benchmarks
- Novel architectures or approaches
- Alignment and safety research with concrete findings
- Efficiency breakthroughs (faster, cheaper, smaller models)
- Multimodal advances (vision+language, audio+vision, etc.)
- Open-source releases with code

**Out of scope:**
- Incremental improvements less than 1% on existing benchmarks
- Theoretical papers without any practical application path
- Papers without benchmark results (unless the theoretical contribution is major)
- Survey papers (unless they contain novel meta-analysis)
- Papers older than 7 days (arxiv updates are frequent — focus on recent)

**Quality gate:** Must have at least ONE of: a specific benchmark result, a code availability link, a clear practical application description, or a comparison to existing approaches.

### Paper Assessment Criteria
When reading a paper, assess:
1. **Novelty:** Is the approach genuinely new or an incremental improvement?
2. **Reproducibility:** Is code available? Are the experiments well-described?
3. **Practicality:** Could this be used in production within 12 months?
4. **Significance:** Does this change how we think about the problem?
5. **Accessibility:** Can a non-researcher understand the key contribution?

### Edge Cases
- **Preprint vs published:** Preprints (arxiv) are fine but note the status. If a paper is later published in a top venue (NeurIPS, ICML, ICLR), upgrade relevance by +1.
- **Code not available:** If the paper has no code, reduce practicality score. Note: "No code — reproducibility uncertain".
- **Retracted papers:** If a paper has been retracted, DO NOT include it. If suspected of issues, flag for fact-checking.
- **Authors from industry vs academia:** Both are valid. Note the affiliation — industry papers often have more practical implications, academic papers often have more rigor.
- **Benchmark selection bias:** If a paper only reports results on benchmarks they created, flag potential bias. Cross-reference with community discussion.
- **Multimodal papers:** These often have visually impressive results but may not generalize. Note the limitations mentioned in the paper.

### Unique Output Fields
```json
{
  "paper_title": "string — full title",
  "paper_url": "string — arxiv or publisher URL",
  "authors": "string — first author + 'et al.' if 3+ authors",
  "institution": "string — primary institution",
  "arxiv_id": "string if applicable (e.g., '2401.12345')",
  "venue": "string — arxiv preprint / NeurIPS 2025 / ICML 2025 / Nature / etc.",
  "key_result": "string — the single most important finding (one sentence)",
  "benchmark_improvement": "string — specific numbers (e.g., '92.3% on MMLU, +4.1% over previous SOTA')",
  "code_available": true | false,
  "code_url": "string if available",
  "practical_impact": "integer 0-10 — how soon could this be used in production?",
  "accessibility": "integer 0-10 — how understandable is this to a non-researcher?",
  "reproducibility": "integer 0-10 — how reproducible are the experiments?"
}
```

---

## Agent 5: Economics Analyst

### Focus
Track the business economics of AI — market sizing, pricing trends, compute costs, talent markets, investment flows, and industry disruption metrics. Numbers-focused agent.

### Search Queries (execute ALL)
```
Query 1: "AI market size" OR "AI industry revenue" 2025 OR 2026
Query 2: "GPU pricing" OR "compute cost" OR "cloud AI pricing" trend OR change
Query 3: "AI startup funding" OR "AI investment" this week OR this month
Query 4: "AI job market" OR "AI salaries" OR "AI talent shortage" OR "AI layoffs"
Query 5: "[industry rotation]" AI adoption statistics — rotate: healthcare, finance, legal, education, creative, manufacturing, agriculture, retail
Query 6 (backup): "AI revenue" OR "AI ARR" OR "AI growth rate" report
Query 7 (backup): "AI economics" OR "AI cost" OR "AI spending" analysis
```

### Filters
**In scope:**
- Market data with specific numbers (market size, growth rate, TAM)
- Pricing changes (GPU costs, API prices, subscription changes)
- Investment data (funding rounds, VC activity, M&A)
- Revenue numbers (company earnings, ARR, growth rate)
- Adoption statistics (enterprise adoption %, user growth)
- Workforce impact data (job displacement, new job categories)
- Cost analysis (cost per token, cost per inference, TCO comparisons)

**Out of scope:**
- Opinion pieces about AI economics without data
- Predictions without methodology or basis
- Generic "AI is a big market" articles without numbers
- Historical analysis without current relevance
- Country-level policy discussions without economic data

**Quality gate:** Must include at least ONE specific number (dollar amount, percentage, headcount, growth rate).

### Data Quality Assessment
| Source Type | Base Quality | Adjustment |
|-------------|-------------|------------|
| Investment bank report (Goldman, Morgan Stanley) | High | +1 if methodology described |
| Consulting firm (McKinsey, Gartner, Forrester) | Medium-High | -1 if no methodology, +1 if primary data |
| Government statistics (BLS, Eurostat) | High | +2 for official data |
| Company earnings call | High | +1 if independently verifiable |
| Journalist analysis | Medium | -1 if no primary sourcing |
| Blogger/Newsletter opinion | Low | -2, requires 2+ corroboration |
| Industry survey | Medium | Depends on sample size (>500 = +1) |

### Edge Cases
- **Inflation adjustment:** When comparing dollar amounts across years, note whether figures are inflation-adjusted.
- **Currency:** Standardize to USD. If a source uses EUR, GBP, etc., convert and note the exchange rate used.
- **Survey vs actual data:** Surveys (what people say) ≠ actual data (what people do). Flag survey-based numbers as "survey_based".
- **Forecast vs actual:** Clearly distinguish between what has happened and what is predicted. Forecasts get -2 relevance vs actuals.
- **Cherry-picked statistics:** If a number seems unusually good or bad, check if it's being selectively quoted from a larger dataset. Look for context.
- **Conflicting data:** If two credible sources report different numbers for the same metric, include BOTH and note the discrepancy.

### Unique Output Fields
```json
{
  "data_point": "string — the key number or finding (e.g., '$45.2B global AI market in 2025')",
  "source": "string — data source with URL",
  "category": "market_size | pricing | investment | adoption | workforce | cost | revenue | forecast",
  "trend_direction": "increasing | decreasing | stable | volatile | unknown",
  "industry_impact": ["list of industries this affects"],
  "contrarian_angle": "string — is there a counter-narrative? (e.g., 'While revenue grows 40%, customer acquisition costs are also rising 60%')",
  "data_quality": "integer 0-10 — how reliable is this data source and methodology?",
  "is_forecast": true | false,
  "time_period": "string — what time period does this data cover?"
}
```

---

## Agent 6: Founder Insights

### Focus
Quotes, tweets, blog posts, and public statements from AI founders, CTOs, and lead researchers that reveal strategy, beliefs, or predictions. This agent captures the human narrative of AI.

### Primary People List
Sam Altman (OpenAI), Dario Amodei (Anthropic), Demis Hassabis (DeepMind), Yann LeCun (Meta), Andrej Karpathy (independent), Andrew Ng (Landing AI), Jensen Huang (NVIDIA), Satya Nadella (Microsoft), Sundar Pichai (Alphabet), Alexandr Wang (Scale AI), Aidan Gomez (Cohere), Arthur Mensch (Mistral), Harrison Chase (LangChain), Jerry Liu (LlamaIndex), Emad Mostaque (Stability AI), Thomas Wolf (Hugging Face), Aravind Srinivas (Perplexity), Alexandr Wang (Scale AI)

### Search Queries (execute ALL)
```
Query 1: "[person name]" interview OR podcast OR blog post AI — rotate through primary list
Query 2: "[person name]" says OR predicts OR believes OR warns AI
Query 3: "[person name]" X post OR tweet OR thread recent
Query 4: "[person name]" keynote OR presentation OR talk AI
Query 5: "AI founder" predictions OR outlook OR forecast 2025 OR 2026
Query 6 (backup): site:reddit.com/r/artificial "[person name]" OR "[company] CEO"
Query 7 (backup): "[person name]" controversy OR debate OR disagreement
```

### Filters
**In scope:**
- Direct quotes with clear source attribution
- Predictions about AI's future trajectory
- Strategy reveals about company direction
- Warnings, concerns, or cautionary statements
- Philosophy statements about AI development
- Product teases or hints (with source context)
- Replies to other prominent figures in AI

**Out of scope:**
- Generic motivational quotes disconnected from AI
- Old statements being recirculated (> 30 days)
- Out-of-context quotes (verify against full source)
- Summaries of what someone thinks (need their actual words)
- Retweets without original commentary
- Personal non-AI content

**Quality gate:** Must be a direct quote or very close paraphrase with source (podcast name + timestamp, blog URL, event name, X post URL).

### Quote Assessment
When evaluating a quote for inclusion:
1. **Is it verifiable?** Can you find the original source?
2. **Is it recent?** Within the last 30 days preferred. Older quotes only if newly relevant (e.g., prediction came true).
3. **Is it specific?** "AI will be important" is useless. "AI will reduce coding time by 80% within 3 years" is gold.
4. **Is it actionable?** Can this become a tweet or reply angle?
5. **Is it from their domain?** Jensen Huang on chip design = high credibility. Jensen Huang on AI safety = moderate.

### Edge Cases
- **Quote out of context:** ALWAYS read the full source before including. Many AI quotes are stripped of nuance. If the full context changes the meaning, either use the full quote with context or skip.
- **Deleted tweet/post:** If someone deleted a statement, it might still be relevant if it was widely discussed. Note: "Originally posted on [date], later deleted."
- **Translated quote:** If the original is in another language, translate and note the original language.
- **Quote from non-English podcast:** Same — translate and note source timestamp.
- **Joke vs serious:** Some founders make sarcastic or joking statements that get reported as serious. Check the tone of the source.
- **Contradiction:** If a founder said the opposite 6 months ago, note the evolution: "Previously said [X] in [date], now says [Y]."

### Unique Output Fields
```json
{
  "person": "string — name and current role",
  "handle": "string — X handle if applicable",
  "quote": "string — the exact quote or very close paraphrase",
  "source": "string — where they said it (podcast name, blog URL, event, X post URL)",
  "source_date": "string — when they said it",
  "source_type": "interview | podcast | blog_post | tweet | keynote | panel | earnings_call | other",
  "topic": "string — what the quote is about",
  "contrarian": true | false,
  "actionable_angle": "string — how can this become an X post? (specific idea)",
  "credibility_signal": "integer 0-10 — how authoritative is this person on this specific topic?",
  "previous_position": "string — if they've changed their stance, note what they said before"
}
```

---

## Agent 7: Tool Spotlight

### Focus
Deep-dive on specific AI tools gaining traction — user reviews, benchmark comparisons, and hands-on analysis. This agent goes beyond "new tool launches" to assess real-world user experience.

### Search Queries (execute ALL)
```
Query 1: "best AI tool for coding" OR "best AI tool for writing" 2025
Query 2: "[tool name]" review OR "hands-on" OR benchmark OR test — rotate popular tools
Query 3: "AI tool comparison" OR "AI tool vs" [popular tools]
Query 4: "AI tool" site:reddit.com review OR experience
Query 5: "AI productivity tool" roundup OR "list" OR comparison 2025
Query 6 (backup): site:reddit.com/r/artificial "what AI tool" OR "best AI for" OR "switched to"
Query 7 (backup): "AI tool" problems OR limitations OR issues OR bugs
```

### Filters
**In scope:**
- Hands-on reviews with specific performance data
- Tool comparisons with benchmarks
- User experience reports from real usage
- Newly trending tools (gaining traction on social platforms)
- Workflow integration examples (how people actually use it)
- Honest pros and cons assessments

**Out of scope:**
- Promotional content without substance
- Listicles without individual reviews ("Top 50 AI Tools" with one line each)
- Sponsored content disguised as reviews
- Reviews that only list pros (no cons)
- Generic "AI is great" commentary
- Affiliate marketing content

**Quality gate:** Must include specific performance data, user experience details, or honest pros/cons. If a review is universally positive with zero criticism, it's likely promotional — skip or heavily discount.

### Review Quality Assessment
| Signal | Quality Indicator |
|--------|-----------------|
| Includes benchmarks or specific metrics | High quality |
| Shows real usage examples/screenshots | High quality |
| Lists both pros AND cons | High quality |
| Compares to alternatives | Medium-High quality |
| Based on extended use (weeks, not hours) | High quality |
| Based on first impression only | Low quality |
| No specific metrics or examples | Very Low quality |
| Universal praise, no criticism | Likely promotional — Low quality |

### Edge Cases
- **Sponsored content:** Check if the review discloses sponsorship. If not disclosed but the tone is uniformly positive and links to a referral/affiliate, flag as "likely_sponsored" and reduce relevance by 3.
- **Outdated review:** If a review is > 60 days old, the tool may have been updated. Note: "Review from [date] — tool may have changed."
- **Platform differences:** A tool might work great on web but poorly on mobile (or vice versa). Note the platform tested.
- **Regional availability:** Some tools are geo-restricted. Note if the tool is available globally or region-limited.
- **Free tier vs paid:** If a review is based on the paid version, note this. Free tier experience may differ significantly.
- **Creator response:** If the tool creator has responded to criticism in comments, include that context.

### Unique Output Fields
```json
{
  "tool_name": "string",
  "tool_url": "string",
  "category": "string — what the tool does",
  "trending_on": "string — where it's gaining traction (Hacker News, Reddit r/artificial, Product Hunt, X, etc.)",
  "trending_score": "integer 0-10 — how much traction? (based on upvotes, comments, shares)",
  "user_sentiment": "positive | mixed | negative",
  "key_strength": "string — what it does best (one sentence)",
  "key_weakness": "string — what it struggles with (one sentence)",
  "vs_competitors": "string — how does it compare to alternatives?",
  "pricing": "string — pricing model and cost",
  "best_for": "string — who is this tool best for?",
  "not_recommended_for": "string — who should avoid this?",
  "review_sources": ["list of URLs with reviews"],
  "review_quality": "integer 0-10 — how trustworthy are the reviews found?",
  "adoption_signal": "integer 0-10 — how fast is this growing?"
}
```

---

## Output Schema (data/news_queue.json)

```json
{
  "metadata": {
    "description": "Raw news items discovered by the 7 news hunting agents",
    "updated_by": "news_hunt command",
    "max_items_kept": 100,
    "retention_policy": "Items older than 14 days are archived (not deleted)"
  },
  "last_updated": "ISO 8601 timestamp",
  "run_count": "integer — total number of news_hunt runs",
  "last_run_duration_seconds": "float — how long the last run took",
  "items": [
    {
      "id": "string — unique identifier (uuid or timestamp-based)",
      "headline": "string — concise headline (under 100 chars)",
      "summary": "string — 2-3 sentence summary of the news",
      "source_url": "string — URL of the primary source",
      "source_name": "string — name of the source outlet",
      "source_type": "news_outlet | blog | social_media | arxiv | official_statement | press_release",
      "discovered_by_agent": "string — agent name(s), comma-separated if multiple",
      "discovered_at": "ISO 8601 timestamp",
      "published_at": "ISO 8601 timestamp or 'unknown'",
      "relevance_score": "float 0-10 — assigned by the discovering agent",
      "combined_score": "float — after timeliness + audience + cross-agent bonuses",
      "fact_check_status": "pending | verified | likely_true | unverified | likely_false | debunked | skipped",
      "fact_check_data": {},
      "tags": ["list of topic tags for filtering"],
      "unique_fields": {
        "all agent-specific fields merged here"
      },
      "duplicate_of": "string — ID of primary item if this is a duplicate, null otherwise"
    }
  ]
}
```

## Run Log Schema (logs/agent_runs/news_hunt_TIMESTAMP.json)

```json
{
  "run_timestamp": "ISO 8601 timestamp",
  "duration_seconds": "float",
  "agents_run": ["list of agent names executed"],
  "agents_skipped": ["list of agent names skipped (with reason)"],
  "searches_performed": "integer — total search queries executed",
  "searches_failed": "integer — queries that returned no results or errored",
  "fetches_performed": "integer — total URL fetches",
  "fetches_failed": "integer — fetches that failed",
  "items_before_dedup": "integer",
  "items_after_dedup": "integer",
  "duplicates_removed": "integer",
  "tool_errors": [
    {"tool": "string", "query": "string", "error": "string", "timestamp": "ISO timestamp"}
  ]
}
```
