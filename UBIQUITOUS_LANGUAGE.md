# Ubiquitous Language

## Intelligence System

| Term | Definition | Aliases to avoid |
| --- | --- | --- |
| **Intelligence Desk** | The complete local system that collects public AI and technology signals, preserves evidence, builds the active queue, and prepares manual editorial work. | X bot, posting bot, scraper, content machine |
| **Public Signal** | A public source observation that may indicate a relevant AI, technology, market, research, or startup development. | News item, lead, post, rumor |
| **Source Lane** | A configured collection path for one evidence family, such as X, YouTube, Reddit, GitHub, arXiv, finance, startups, or prediction markets. | Collector, source, feed, agent |
| **Source Registry** | The central configuration that declares enabled source lanes, outputs, route policy, queue policy, and cleanup policy. | Config file, source list, lane list |
| **Pinned Route** | A machine-specific external CLI path that must be used for X and YouTube collection instead of browser scraping or ad hoc commands. | Scrape path, browser route, direct automation |
| **Collector Output** | A source-specific JSON artifact that preserves what the latest source lane run observed. | Queue item, report, raw data, result |
| **Lane Health** | A diagnostic record describing whether a source lane produced usable output, partial output, cached output, or a failure. | Status, log, success flag |

## Source Lanes

| Term | Definition | Aliases to avoid |
| --- | --- | --- |
| **X Lane** | The authenticated read-only X collection lane using the pinned local XCLI route and bounded browser-tab coordination. | Twitter scraper, browser scrape, social lane |
| **YouTube Lane** | The video discovery and transcript collection lane using the pinned YT Transcript CLI route. | Video scraper, transcript scraper |
| **Community Lane** | The Reddit and Hacker News lane for public discussion signals, including RSS fallback when Reddit direct routes fail. | Forum lane, social chatter |
| **Artifact Research Lane** | The GitHub, Hugging Face, release, and arXiv lane for code, model, paper, and release signals. | OSS lane, repo lane, research lane |
| **Finance Lane** | The market, macro, newsletter, SEC, and public-finance lane for AI-linked business signals. | Market feed, money lane |
| **Startup Lane** | The funding, product-launch, directory, and regional startup discovery lane. | Startup feed, launch lane |
| **Model Market Lane** | The source lane for model catalog, pricing, provider, and OpenRouter-style market signals. | Model feed, marketplace lane |
| **Science Lane** | The bio, science, and deep-tech source lane for breakthrough-style signals. | Research lane, deep-tech feed |
| **Developer Sentiment Lane** | The source lane for provider status, outages, latency, pricing pain, and adoption friction. | Dev pain feed, status lane |
| **Prediction Market Lane** | The Polymarket source lane that tracks active market odds, volume, volatility, and rumor velocity as public evidence. | Polymarket lane, rumor lane, betting lane |

## Queue And Evidence Lifecycle

| Term | Definition | Aliases to avoid |
| --- | --- | --- |
| **Active Intelligence Queue** | The protected `data/news_queue.json` document containing deduplicated recent signals used by reports, verification, and editorial workflows. | News file, report, collection output, post queue |
| **Queue Item** | A single normalized signal inside the active intelligence queue. | Article, tweet, story, post |
| **Protected Queue Seam** | The authoritative `scripts/intelligence_queue.py` interface for reading, merging, filtering, and atomically replacing the active intelligence queue. | Queue helper, write utility, persistence code |
| **Canonical URL Identity** | The stable identity rule that treats items with the same normalized URL as the same queue item. | Dedup key, link matching |
| **Duplicate Provenance Merge** | The process of combining evidence from multiple source observations that refer to the same queue item. | Simple dedupe, overwrite, collapse |
| **Dynamic Queue Update** | A queue merge that refreshes changing fields such as prediction-market odds while preserving manual flags and provenance. | Re-add, duplicate ignore, overwrite all |
| **Atomic Replacement** | A persistence operation that replaces the queue only after a complete new JSON document is ready. | Save, write, dump |
| **Protected State** | High-value local state that must not be hard-deleted or casually overwritten. | Cache, temp data, generated files |
| **Collector History** | Dedupe memory that helps a source lane avoid rediscovering already-seen items. | Cache, old data |
| **Stale Archive** | The managed archive location for obsolete generated files moved by the cleanup policy. | Trash, delete folder |

## Verification And Truth

| Term | Definition | Aliases to avoid |
| --- | --- | --- |
| **Atomic Claim** | A single self-contained factual statement, metric, or event extracted from a queue item with its citation context. | Point, assertion, summary |
| **Fact-Check Verdict** | The final verification classification for a queue item or claim. | Status, score, approval |
| **VERIFIED** | A fact-check verdict for a claim confirmed by independent sources with no material context gaps. | Approved, true, safe |
| **LIKELY_TRUE** | A fact-check verdict for a claim supported by credible evidence but still carrying minor gaps or caution. | Probably true, verified enough |
| **UNVERIFIED** | A fact-check verdict for a claim that lacks sufficient independent confirmation. | Pending, false, unknown |
| **LIKELY_FALSE** | A fact-check verdict for a claim contradicted by evidence or weakened by significant gaps. | Bad, rejected |
| **DEBUNKED** | A fact-check verdict for a claim confirmed false or misleading by multiple reliable sources. | False, rejected |
| **UNVERIFIABLE_PREDICTION** | A verdict for forward-looking claims that cannot be factually verified yet. | Prediction, rumor, speculative |
| **Confidence Score** | A 0-100 verification score derived from evidence quality, source credibility, context gaps, contradictions, and market corroboration. | Relevance score, quality score |
| **Prediction Market Corroboration** | The use of active market questions and YES odds as supporting evidence for a claim, not as proof by itself. | Truth oracle, market truth, betting proof |
| **YES Odds** | The current market-implied probability for the affirmative outcome of a prediction market question. | Confidence, truth score, probability of fact |
| **Claim Ledger** | Durable verification memory that records checked claims and prevents repeated work or repeated trust errors. | Cache, fact file |

## Editorial Workflow

| Term | Definition | Aliases to avoid |
| --- | --- | --- |
| **Editorial Workflow** | The downstream process that verifies signals and prepares post or reply artifacts for manual use. | Autoposting, content generation, publishing |
| **Manual Drafting Packet** | An empty structured packet for a human to write from after the source item is VERIFIED or LIKELY_TRUE. | Generated post, tweet draft, approved post |
| **Manual Copy Only** | The publishing policy that artifacts are prepared for human review and copying, never automatic posting. | Ready to publish, autopublish, automated reply |
| **Approved Posts File** | The `data/approved_posts.json` artifact containing verified-only manual drafting packets. | Published posts, generated tweets |
| **Reply Opportunity** | A candidate X reply target or conversation artifact selected for manual consideration. | Auto reply, comment draft |
| **Sent Post Record** | A manual ledger of posts the operator has actually sent. | Published queue, approved queue |

## Reports And Views

| Term | Definition | Aliases to avoid |
| --- | --- | --- |
| **Intelligence Report** | A disposable categorized JSON, Markdown, or HTML view derived from the active intelligence queue. | Queue, source output, dashboard |
| **Categorized View** | A report grouping queue items into reader-facing categories such as model market, company announcements, community reality, startup funding, or developer pain. | Source data, queue state |
| **Dashboard** | An interactive report surface for filtering and reviewing derived intelligence views. | Database, source of truth |
| **Report Export** | A regenerated artifact under `data/exports/reports/` derived from the active intelligence queue. | Canonical data, protected state |

## System Boundaries

| Term | Definition | Aliases to avoid |
| --- | --- | --- |
| **Read-Only Collection** | Source acquisition that gathers public signals without posting, replying, trading, following, or mutating external accounts. | Automation, engagement, bot activity |
| **Three-Worker X Coordinator** | The bounded X collection coordinator that uses one home slot and up to three watchlist slots with serialized fallback. | X scraper pool, browser workers |
| **Fresh Cache Fallback** | A fail-soft path that uses recent cached output when a live source route is unstable. | Stale data, fallback success |
| **Compatibility Shim** | A transitional path that preserves legacy consumers while storage or route layout is migrated. | Legacy code, old route |
| **Storage Migration** | The incremental movement from mixed `data/` artifacts toward raw, normalized, verified, content, state, and export layers. | Cleanup, refactor, reorg |

## Relationships

- An **Intelligence Desk** contains many **Source Lanes**.
- A **Source Lane** reads **Source Registry** configuration and writes one or more **Collector Outputs**.
- A **Pinned Route** belongs to a source lane when collection depends on machine-specific CLIs.
- A **Collector Output** may contribute zero or more **Queue Items** to the **Active Intelligence Queue**.
- The **Protected Queue Seam** is the only canonical writer for the **Active Intelligence Queue**.
- A **Queue Item** may have many provenance entries after a **Duplicate Provenance Merge**.
- A **Prediction Market Lane** produces market signals and may also provide **Prediction Market Corroboration** for an **Atomic Claim**.
- A **Fact-Check Verdict** belongs to one **Atomic Claim** or one **Queue Item**.
- A **Manual Drafting Packet** can be created only from a **Queue Item** with a **VERIFIED** or **LIKELY_TRUE** verdict.
- An **Intelligence Report** is derived from the **Active Intelligence Queue** and is not authoritative state.
- A **Dashboard** renders **Report Exports**; it does not replace the **Active Intelligence Queue**.
- **Protected State** includes the **Active Intelligence Queue**, transcript corpora, ledgers, collector history, and manual editorial state.

## Example Dialogue

> **Dev:** "Can I write new Polymarket results directly into `data/news_queue.json`?"
>
> **Domain expert:** "No. The **Prediction Market Lane** writes a **Collector Output**, then the **Protected Queue Seam** performs a **Dynamic Queue Update** on the **Active Intelligence Queue**."
>
> **Dev:** "If YES odds are 82%, should the item become **VERIFIED**?"
>
> **Domain expert:** "No. **Prediction Market Corroboration** can raise the **Confidence Score**, but the **Fact-Check Verdict** still depends on source verification, claim verification, recency, context, and conflicts."
>
> **Dev:** "Once a queue item is **LIKELY_TRUE**, do we generate a tweet?"
>
> **Domain expert:** "We generate a **Manual Drafting Packet** with **Manual Copy Only** policy. The system prepares structure for the operator; it does not publish or invent factual copy."
>
> **Dev:** "So the dashboard is safe to regenerate?"
>
> **Domain expert:** "Yes. A **Dashboard** is a derived **Intelligence Report**. The **Active Intelligence Queue** and other **Protected State** are the durable records."

## Flagged Ambiguities

- "News item" is overloaded across the repo to mean raw source observations, normalized queue items, and report entries; use **Public Signal**, **Queue Item**, or **Categorized View** depending on the lifecycle stage.
- "Source" can mean a publication, a config entry, a source lane, or a collector output; use **Source Lane** for the configured pipeline path and **Collector Output** for the written artifact.
- "Report" and "dashboard" can be mistaken for canonical data; use **Intelligence Report** or **Dashboard** only for regenerated views derived from the **Active Intelligence Queue**.
- "Approved posts" suggests publish-ready content; use **Approved Posts File** only for the artifact name and **Manual Drafting Packet** for the domain object.
- "Verified" appears in both lowercase schema fields and uppercase verdict labels; use **VERIFIED** when referring to the domain verdict.
- "Prediction market" can sound like a truth source; use **Prediction Market Corroboration** to emphasize that market odds are evidence, not proof.
- "Cache" is too broad for this repo because some cached files are durable memory; use **Fresh Cache Fallback**, **Collector History**, **Claim Ledger**, or **Protected State**.
- "Scraper" is misleading for X and YouTube because the repo has pinned CLI routes; use **Pinned Route**, **X Lane**, or **YouTube Lane**.
- "Queue" can mean a video discovery queue, an active intelligence queue, or an editorial queue; use **Active Intelligence Queue**, **YouTube Lane** discovery output, or **Manual Drafting Packet** explicitly.
- "Cleanup" can imply deletion; use **Stale Archive** for the sanctioned path and reserve deletion for explicitly approved archive removal.
