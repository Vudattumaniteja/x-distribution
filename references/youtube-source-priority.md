# YouTube Source Priority

Updated: 2026-05-29

## Current Count

The system currently monitors 24 YouTube channels in `config/youtube_channels.json`.

## Default Discovery Policy

YouTube recency must come from `yt-transcript latest`, not YouTube RSS.

Configured policy in `config/source_registry.json`:

```json
{
  "method": "yt-transcript-latest",
  "lookback_days": 2,
  "max_scan_per_channel": 500,
  "transcript_count_per_channel": null,
  "transcript_timeout_seconds": 7200,
  "rss_fallback": false
}
```

Meaning:

- Scan the channel's latest videos through yt-dlp-backed `yt-transcript latest`.
- Keep every video published in the last 2 days.
- Pull transcripts for every in-window video.
- `max_scan_per_channel` is only a safety guard, not the ranking cap.

## Priority Bands

| Priority | Meaning |
|---|---|
| P-2 | Highest-priority expert source; any upload is urgent regardless of length |
| P-1 | Above-P0 top-tier source; handled before normal P0 |
| P0 | High-cadence fast-update radar or official primary source |
| P1 | Strong AI/product/model source |
| P2 | Context, strategy, regional, or interview source |
| P3 | Broad tech context, lower urgency |

## Channel Map

| Channel | Priority | Category | Role |
|---|---:|---|---|
| `AndrejKarpathy` | P-2 | expert_primary | Highest-priority AI expert source; any upload is urgent regardless of length |
| `LexFridman` | P-1 | longform_interview | Above-P0 AI researcher/founder interview source |
| `TBPNLive` | P-1 | tech_business_show | Above-P0 AI/startup/market operator discussion |
| `@JulianGoldieSEO` | P0 | fast_update_creator | Very high-cadence AI product/update radar |
| `@OpenAI` | P0 | official_primary | OpenAI launches and demos |
| `@anthropic-ai` | P0 | official_primary | Anthropic announcements and talks |
| `@claude` | P0 | official_primary | Claude product updates |
| `Google` | P0 | official_primary | Google/Gemini/AI Studio |
| `KimiMoonshot` | P0 | official_primary_china | Kimi/Moonshot model and product updates |
| `@AlexFinnOfficial` | P0 | growth_distribution_creator | X/growth/distribution mechanics and creator-market signal |
| `@vaibhavsisinty` | P0 | growth_creator | AI/growth/automation/business tactics |
| `JayE-RoboNuggets` | P0 | workflow_orchestration | Cover every video; workflow orchestration and practical agent systems |
| `AICodeKing` | P0 | coding_agent_creator | Coding-agent workflows |
| `airevolutionx` | P0 | ai_news_creator | Broad fast AI update radar |
| `@intheworldofai` | P0 | fast_ai_tool_creator | WorldofAI fast AI tool, coding, agent, and automation updates |
| `MatthewBerman` | P0 | ai_model_creator | Models, tools, benchmarks |
| `PeterDiamandis` | P0 | future_business_creator | AI/startups/future framing |
| `@n8n-io` | P1 | official_tooling | Automation/workflow tooling |
| `@100xEngineers` | P2 | india_builder_creator | India developer/builder perspective |
| `@IshanSharma7390` | P2 | india_business_creator | India startup/business interviews |
| `@VarunMayya` | P2 | india_ai_business_creator | India AI/startup commentary |
| `@BuildersCentral` | P2 | builder_creator | Builder/product execution |
| `@nicksaraev` | P2 | automation_creator | AI automation/SEO |
| `AndroidAuthority` | P3 | consumer_tech | Consumer/on-device AI context |

Removed: `@NetworkChuck`, per source-priority cleanup.

The machine-readable version is `config/youtube_channel_profiles.json`.

## Julian-Specific Finding

With the 2-day window and no transcript count cap, Julian returned 32 videos. This confirms he is a high-cadence source and cannot be handled with a fixed `-n 5` style cap.
