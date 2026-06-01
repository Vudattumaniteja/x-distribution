# Product Requirement Document: Prediction Market (Polymarket) Source Lane

## Problem Statement

The intelligence pipeline lacks access to prediction market data. Downstream editorial agents are blind to market speculation, pricing dynamics, and breaking tech rumors (such as OpenAI leadership changes, imminent product launches, or IPO estimations) that typically appear on prediction platforms like Polymarket before hitting traditional news RSS feeds or blogs.

## Solution

Establish a new, stateless local `prediction_market` source lane. This lane will scan Polymarket’s public, free Gamma API for active markets matching key tech, AI, executive, and IPO keywords. It will implement a "Smoke Detector" relative growth scoring algorithm to filter out low-volume noise and prioritize markets experiencing rapid velocity shifts or probability changes, updating their odds in the `news_queue.json` queue dynamically.

## User Stories

1. As an editorial AI writing agent, I want to see prediction market odds and volume for AI-related topics, so that I can gauge the consensus probability of future industry events.
2. As a content curator, I want to filter out stagnant or low-volume prediction markets, so that I do not spend time reviewing noise.
3. As a writer, I want to see markets that have had a sudden relative volume jump in the last 24 hours, so that I can write about breaking trends and rumors before they become mainstream news.
4. As an analyst, I want to see the leading outcomes and their probabilities for multi-outcome prediction markets, so that I can report who is leading in startup and IPO races.
5. As a system engineer, I want the prediction market collector to degrade gracefully if the API fails, so that it doesn't block the rest of the collection pipeline.
6. As a queue maintainer, I want duplicate prediction market items to update their odds in the active queue instead of being ignored, so that downstream reports always show the latest market prices.
7. As a data analyst, I want to store Polymarket-specific metadata inside a dedicated `unique_fields` block, so that the main `news_queue.json` schema remains flat and backwards-compatible with existing downstream scripts.
8. As a developer, I want all Polymarket search queries and thresholds to be stored in a central config file, so that I can easily expand the watchlist keywords.
9. As a DevOps engineer, I want the validation script to verify the format of my prediction market config file, so that incorrect formatting is caught before running pipeline collections.
10. As a content consumer, I want headlines to display both the market question and the current YES odds (or leading odds) clearly, so that I can grasp the signal at a glance without reading the full summary.

## Implementation Decisions

- **Source Registration:** Register `prediction_market` as an enabled live source lane in the central registry.
- **Config Storage:** Create a new `config/prediction_market_sources.json` to store queries (e.g. OpenAI, Anthropic, DeepSeek, IPO, AGI), minimum volume thresholds, and price change limits.
- **Stateless Collection:** Implement `scripts/polymarket_collector.py` using simple HTTP requests to Polymarket's free, public Gamma API (`/public-search` endpoint), avoiding any API keys or credentials.
- **Smoke Detector Scoring:**
  - Base relevance score: `5.0`.
  - Size bonus: Logarithmic scaling on total volume ($\log_{10}(Volume)$).
  - Velocity bonus: Ratio of 24-hour volume to total volume (`volume24hr / total_volume`).
  - Volatility bonus: Absolute daily price change (`oneDayPriceChange`).
  - Priority bonus: Matches high-priority keywords.
  - Final cap: Capped at `10.0`.
- **Deduplication & Integration:** Integrate the collector into `scripts/phase1_collect.py`. Update duplicate merging in `scripts/intelligence_queue.py` to allow overwriting headline, summary, score, and unique fields for prediction markets.
- **Schema Validation:** Update schema checks to parse and validate the new prediction market configuration schema.

## Testing Decisions

- Test the pipeline collection seam by running the collector locally and checking that it produces a valid `prediction_market_signals.json` artifact containing scored signals.
- Test the schema validation seam by running validation checks after creating/modifying config files.
- Test queue integration by running a mock queue merge and verifying that duplicate prediction markets correctly update their odds while maintaining manual status flags.
- Prior art: existing validation tests (`validate_schemas.py`) and pipeline integration smoke tests.

## Out of Scope

- Direct trading, order book operations, or portfolio tracking on Polymarket (CLOB API).
- Automatic posting or editing of content to X or external platforms.
- Supporting non-Polymarket prediction platforms (like Kalshi or Manifold Markets) in the initial release.

## Further Notes

- Web search confirmed that Polymarket's Gamma API requires no API keys or access tokens for read-only event search queries, making this collector stateless and easy to run locally without environment variables.
