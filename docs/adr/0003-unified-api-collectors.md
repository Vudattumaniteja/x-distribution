# ADR-0003: Unified Collector Adapters for Lanes E-L

Date: 2026-05-31

## Status
Proposed

## Context
The collection lanes E-L currently rely on several standalone, shallow collector scripts. These scripts, including `github_monitor_standalone.py`, `arxiv_sentinel_standalone.py`, `finance_market_collector.py`, and `developer_sentiment_collector.py`, contain redundant transport, serialization, configuration, and execution boilerplate.

This duplication has several architectural drawbacks:
- **Low Depth**: The modules are shallow, exposing high interface complexity for low functional variety.
- **Poor Locality**: Transport parameters (timeouts, user-agent headers, and exponential backoff retry patterns) are scattered across multiple files.
- **Redundant Implementation**: Standard parsing logic (BeautifulSoup HTML extraction, feedparser RSS extraction, and XML parsing) is repeated in each script.
- **Fragile Interface**: Error handling and health diagnostics are inconsistent across lanes, lacking a standardized seam for monitoring raw transport health.

## Decision
We propose replacing the shallow scripts with a deep unified collector adapter framework.

1. **Implement a Deep Base Module**: Introduce a unified `CollectorBase` module. This deep module implements all raw transport tasks: HTTP session management, exponential backoff retries, JSON configuration loading, output serialization, and health diagnostics logs.
2. **Define a Minimal Extraction Interface**: The base module exposes a clean, narrow interface for content extraction. Concrete subclasses must only implement the raw extraction method.
3. **Refactor Collectors as Adapters**: Redefine the individual scrapers for GitHub, arXiv, finance, and other lanes as clean adapters. These adapters leverage the deep base transport module and map raw source structures (e.g., RSS, SEC filings, HTML BeautifulSoup trees) to standardized records.
4. **Establish Clear Seams**: Maintain a strict seam between data transport (handling network requests, retries, and rate limits) and content extraction (handling pattern matching, keywords, and document relevance).

## Consequences
- **High Locality**: Common behaviors like connection timeouts, health checks, and retry policies reside in a single deep module.
- **Clean Seams**: Scraper adapters can be tested independently of live networks by mocking the base transport interface.
- **Reduced Boilerplate**: Extraction adapters focus entirely on their core domain responsibility, reducing code size.
- **Uniform Error Handling**: All lanes inherit standard diagnostics, making data health reports consistent across the pipeline.
