# X Distribution Domain Context

The complete local system for AI-focused social media operations, tracking signals from collection to manual content drafting.

## Language

**Intelligence desk**:
The complete local system that collects public AI and technology signals, preserves source evidence, builds an active intelligence queue, and prepares manual editorial work.

**Source lane**:
A configured collection path for one evidence family, such as X, YouTube, community discussion, model-market signals, startup funding, or prediction markets.

**Collector output**:
A source-specific JSON artifact written by a source lane. Collector outputs preserve what the most recent source run observed.

**Active intelligence queue**:
The protected `data/news_queue.json` document used by downstream reporting, verification, and editorial workflows. It contains deduplicated recent signals from source lanes.

**Intelligence report**:
A categorized JSON, Markdown, or HTML view derived from the active intelligence queue. Reports are disposable views; the active intelligence queue remains authoritative.

**Protected state**:
High-value local data that must not be hard-deleted or casually overwritten. This includes the active intelligence queue, transcripts, verification ledgers, and collector history files.

**Editorial workflow**:
The downstream process that fact-checks signals and prepares post or reply artifacts for manual use. It does not publish automatically.

**High-facility decision**:
A design choice with complex structural dependencies or high risk, requiring prototyping or detailed verification of trade-offs before implementation.
_Avoid_: Architectural change, complex task

**Low-flexibility boundary**:
A rigid system integration or hardcoded data path that cannot be easily modified without breaking downstream consumers.
_Avoid_: Rigid component, fixed path

**Golden signal**:
A high-density raw data point (such as a full YouTube transcript or detailed Reddit comment thread) that contains high-value domain intelligence and must be protected from eviction or truncation in the pipeline.
_Avoid_: Key info, top item

**Data feed redirection**:
The routing of downstream subagents to scan locally cached raw collector outputs rather than making redundant external web search requests.
_Avoid_: Input redirection, local reading

**Relevance scoring bias**:
The heuristic error where static keyword matching filters out highly valuable atypical signals.
_Avoid_: Bad rating, incorrect score

**Atomic claim**:
A single, self-contained statement of fact, metric, or event extracted from source documents, including its specific citation and context.
_Avoid_: Point, assertion, summary item

**Unified extraction schema**:
The structured representation of extracted news items that preserves both standard meta-fields and dynamic, source-specific payloads (e.g., benchmarks, funding, comments).
_Avoid_: Standard format, news format

**Claim merging**:
The process of combining complementary details from multiple collector outputs referencing the same story, rather than selecting one and discarding the others.
_Avoid_: Simple deduping, discarding


