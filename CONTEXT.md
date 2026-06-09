# X Distribution Domain Context

## Intelligence desk
The complete local system that collects public AI and technology signals, preserves source evidence, builds an active intelligence queue, and prepares manual editorial work.

## Source lane
A configured collection path for one evidence family, such as X, YouTube, community discussion, model-market signals, startup funding, or prediction markets.

## Collector output
A source-specific JSON artifact written by a source lane. Collector outputs preserve what the most recent source run observed.

## Active intelligence queue
The protected `data/news_queue.json` document used by downstream reporting, verification, and editorial workflows. It contains deduplicated recent signals from source lanes.

## Intelligence report
A categorized JSON, Markdown, or HTML view derived from the active intelligence queue. Reports are disposable views; the active intelligence queue remains authoritative.

## Protected state
High-value local data that must not be hard-deleted or casually overwritten. This includes the active intelligence queue, transcripts, verification ledgers, and collector history files.

## Editorial workflow
The downstream process that fact-checks signals and prepares post or reply artifacts for manual use. It does not publish automatically.
