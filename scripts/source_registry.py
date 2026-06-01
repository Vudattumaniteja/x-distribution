"""Central source registry accessors for X Distribution collectors."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = WORKSPACE_ROOT / "config" / "source_registry.json"
RUNTIME_PATHS_PATH = WORKSPACE_ROOT / "config" / "runtime_paths.json"


DEFAULT_REGISTRY: dict[str, Any] = {
    "queue_policy": {
        "active_queue_max_items": 1000,
        "dedupe_url_fields": ["source_url", "url", "resolved_url", "hn_discussion_url"],
        "prefer_categories": ["deep-discovery", "community-discussion", "video-discovery"],
    },
    "youtube_discovery": {
        "method": "yt-transcript-latest",
        "lookback_days": 2,
        "max_scan_per_channel": 500,
        "discovery_workers": 4,
        "disabled_channels": [],
        "transcript_count_per_channel": None,
        "transcript_workers": 2,
        "transcript_per_video_timeout_seconds": 360,
        "transcript_timeout_seconds": 7200,
        "rss_fallback": False,
    },
    "collection_runtime": {
        "lane_workers": 5,
        "x_workers": 1,
        "x_timeline_days": 7,
        "x_tweets_per_account": 3,
    },
    "runtime_paths": {
        "python_exe_env": "X_DISTRIBUTION_PYTHON",
        "xcli_script_env": "XCLI_SCRIPT",
        "yt_transcript_cli_env": "YT_TRANSCRIPT_CLI",
        "yt_transcript_py_script_env": "YT_TRANSCRIPT_PY_SCRIPT",
        "default_xcli_script": "",
        "default_yt_transcript_cli": "",
        "default_yt_transcript_py_script": "",
    },
    "artifact_sources": {
        "hugging_face_orgs": [
            "openai",
            "anthropic",
            "meta-llama",
            "mistralai",
            "google",
            "xai",
            "moonshotai",
            "MiniMaxAI",
            "Qwen",
            "ZhipuAI",
            "deepseek-ai",
            "ByteDance-Seed",
            "BAAI",
            "THUDM",
            "internlm",
            "01-ai",
            "modelscope",
        ],
        "github_orgs": [
            "openai",
            "anthropic-ai",
            "google-deepmind",
            "mistralai",
            "xai-org",
            "MoonshotAI",
            "MiniMax-AI",
            "QwenLM",
            "THUDM",
            "deepseek-ai",
            "InternLM",
            "OpenBMB",
            "modelscope",
            "PaddlePaddle",
        ],
        "github_release_repos": [
            {"org": "openai", "repo": "openai-python"},
            {"org": "anthropic-ai", "repo": "anthropic-sdk-python"},
            {"org": "google-deepmind", "repo": "gemma"},
            {"org": "mistralai", "repo": "mistral-common"},
            {"org": "meta-llama", "repo": "llama-models"},
            {"org": "QwenLM", "repo": "Qwen3"},
            {"org": "deepseek-ai", "repo": "DeepSeek-V3"},
            {"org": "InternLM", "repo": "InternLM"},
            {"org": "OpenBMB", "repo": "MiniCPM"},
        ],
    },
    "live_sources": {
        "reddit": {
            "enabled": True,
            "description": "Reddit developer/community discussion collection through reddit-mcp-buddy with the legacy JSON scraper as fallback.",
            "scripts": ["reddit_mcp_buddy_collect.py"],
            "outputs": ["data/reddit_raw_standalone.json"],
        },
        "finance": {
            "enabled": True,
            "description": "Finance, market, macro, newsletter, and SEC signals scoped to AI market intelligence.",
            "scripts": ["finance_market_collector.py"],
            "outputs": ["data/finance_raw_standalone.json", "data/finance_signals.json"],
        },
        "startup_funding": {
            "enabled": True,
            "description": "AI startup fundraising and product-launch signals, with Series A/B/C extraction.",
            "scripts": ["startup_funding_collector.py"],
            "outputs": ["data/startup_funding_raw.json", "data/startup_funding_signals.json"],
        },
        "github": {
            "enabled": True,
            "description": "GitHub organization and repository release monitoring for AI/agent/model/tool artifacts.",
            "scripts": ["github_monitor_standalone.py", "github_releases_discovery.py"],
            "outputs": ["data/github_discoveries.json", "data/release_discoveries.json"],
        },
        "arxiv": {
            "enabled": True,
            "description": "arXiv research feed monitoring for AI, ML, language, vision, robotics, and technical benchmark papers.",
            "scripts": ["arxiv_sentinel_standalone.py"],
            "outputs": ["data/arxiv_raw_standalone.json"],
        },
        "huggingface": {
            "enabled": True,
            "description": "Hugging Face organization monitoring for global and Chinese model artifacts.",
            "scripts": ["hf_tracker_standalone.py"],
            "outputs": ["data/hf_discoveries.json"],
        },
        "model_market": {
            "enabled": True,
            "description": "OpenRouter model-market radar for new model listings, capability/pricing changes, free models, and tool-calling support.",
            "scripts": ["model_market_collector.py"],
            "outputs": ["data/model_market_raw.json", "data/model_market_signals.json"],
        },
        "startup_collections": {
            "enabled": True,
            "description": "Collection-style startup discovery with API/RSS/HTML fallback for TrustMRR, StartupHub, FundBat, Analytics India Deep Tech, Jiqizhixin, and related directories.",
            "scripts": ["startup_collections_collector.py"],
            "outputs": ["data/startup_collections_raw.json", "data/startup_collections_signals.json"],
        },
        "science_breakthroughs": {
            "enabled": True,
            "description": "Bio, biotech, science, and deep-tech breakthrough collection filtered for AI/tech/science commercialization signals.",
            "scripts": ["science_breakthrough_collector.py"],
            "outputs": ["data/science_breakthrough_raw.json", "data/science_breakthrough_signals.json"],
        },
        "developer_sentiment": {
            "enabled": True,
            "description": "Provider status, outage, latency, pricing, and developer pain/adoption signals for model platforms.",
            "scripts": ["developer_sentiment_collector.py"],
            "outputs": ["data/developer_sentiment_raw.json", "data/developer_sentiment_signals.json"],
        },
    },
    "collector_outputs": [
        "data/sitemap_discoveries.json",
        "data/hf_discoveries.json",
        "data/github_discoveries.json",
        "data/release_discoveries.json",
        "data/corporate_announcements.json",
        "data/hn_raw_standalone.json",
        "data/arxiv_raw_standalone.json",
        "data/finance_raw_standalone.json",
        "data/finance_signals.json",
        "data/startup_funding_raw.json",
        "data/startup_funding_signals.json",
        "data/x_radar_standalone.json",
        "data/reddit_raw_standalone.json",
        "data/new_videos_queue.json",
        "data/model_market_raw.json",
        "data/model_market_signals.json",
        "data/startup_collections_raw.json",
        "data/startup_collections_signals.json",
        "data/science_breakthrough_raw.json",
        "data/science_breakthrough_signals.json",
        "data/developer_sentiment_raw.json",
        "data/developer_sentiment_signals.json",
    ],
}


def load_registry() -> dict[str, Any]:
    if not REGISTRY_PATH.exists():
        merged = DEFAULT_REGISTRY.copy()
    else:
        with REGISTRY_PATH.open("r", encoding="utf-8") as file_handle:
            parsed = json.load(file_handle)
        merged = DEFAULT_REGISTRY | parsed
        merged["artifact_sources"] = (
            DEFAULT_REGISTRY["artifact_sources"] | parsed.get("artifact_sources", {})
        )
        merged["queue_policy"] = DEFAULT_REGISTRY["queue_policy"] | parsed.get("queue_policy", {})
        merged["youtube_discovery"] = (
            DEFAULT_REGISTRY["youtube_discovery"] | parsed.get("youtube_discovery", {})
        )
        merged["collection_runtime"] = (
            DEFAULT_REGISTRY["collection_runtime"] | parsed.get("collection_runtime", {})
        )
        merged["live_sources"] = DEFAULT_REGISTRY["live_sources"] | parsed.get("live_sources", {})

    parsed_runtime_paths = parsed.get("runtime_paths", {}) if REGISTRY_PATH.exists() else {}
    
    runtime_paths = {}
    if RUNTIME_PATHS_PATH.exists():
        try:
            with RUNTIME_PATHS_PATH.open("r", encoding="utf-8") as f:
                runtime_paths = json.load(f)
        except Exception:
            pass

    merged["runtime_paths"] = DEFAULT_REGISTRY["runtime_paths"] | parsed_runtime_paths | runtime_paths
    return merged


def artifact_sources() -> dict[str, Any]:
    return load_registry().get("artifact_sources", {})


def hugging_face_orgs() -> list[str]:
    return list(artifact_sources().get("hugging_face_orgs", []))


def github_orgs() -> list[str]:
    return list(artifact_sources().get("github_orgs", []))


def github_release_repos() -> list[tuple[str, str]]:
    repos = artifact_sources().get("github_release_repos", [])
    return [(entry["org"], entry["repo"]) for entry in repos if entry.get("org") and entry.get("repo")]


def collector_outputs() -> list[str]:
    return list(load_registry().get("collector_outputs", []))


def live_sources() -> dict[str, Any]:
    return load_registry().get("live_sources", {})


def enabled_live_source_scripts(*source_names: str) -> list[str]:
    selected = set(source_names)
    scripts: list[str] = []
    for name, source in live_sources().items():
        if selected and name not in selected:
            continue
        if source.get("enabled"):
            scripts.extend(source.get("scripts", []))
    return scripts


def live_source_outputs(*source_names: str) -> list[str]:
    selected = set(source_names)
    outputs: list[str] = []
    for name, source in live_sources().items():
        if selected and name not in selected:
            continue
        if source.get("enabled"):
            outputs.extend(source.get("outputs", []))
    return outputs


def queue_policy() -> dict[str, Any]:
    return load_registry().get("queue_policy", DEFAULT_REGISTRY["queue_policy"])


def youtube_discovery_policy() -> dict[str, Any]:
    return load_registry().get("youtube_discovery", DEFAULT_REGISTRY["youtube_discovery"])


def collection_runtime_policy() -> dict[str, Any]:
    return load_registry().get("collection_runtime", DEFAULT_REGISTRY["collection_runtime"])
