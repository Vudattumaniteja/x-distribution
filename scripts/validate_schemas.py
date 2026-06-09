"""Practical schema checks for X Distribution config and data files."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


class Validator:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, path: str, message: str) -> None:
        self.errors.append(f"{path}: {message}")

    def warn(self, path: str, message: str) -> None:
        self.warnings.append(f"{path}: {message}")

    def load_json(self, rel_path: str) -> Any | None:
        path = ROOT / rel_path
        if not path.exists():
            self.error(rel_path, "missing")
            return None
        try:
            with path.open("r", encoding="utf-8") as file_handle:
                return json.load(file_handle)
        except json.JSONDecodeError as exc:
            self.error(rel_path, f"invalid JSON: {exc}")
            return None

    def require_keys(self, rel_path: str, obj: dict[str, Any], keys: list[str]) -> None:
        for key in keys:
            if key not in obj:
                self.error(rel_path, f"missing key `{key}`")

    def validate_source_registry(self) -> None:
        rel_path = "config/source_registry.json"
        registry = self.load_json(rel_path)
        if not isinstance(registry, dict):
            self.error(rel_path, "must be a JSON object")
            return

        self.require_keys(rel_path, registry, ["queue_policy", "collector_outputs"])
        queue_policy = registry.get("queue_policy", {})
        if not isinstance(queue_policy.get("active_queue_max_items"), int):
            self.error(rel_path, "queue_policy.active_queue_max_items must be an integer")
        if not isinstance(queue_policy.get("dedupe_url_fields"), list) or not queue_policy.get("dedupe_url_fields"):
            self.error(rel_path, "queue_policy.dedupe_url_fields must be a non-empty list")

        youtube_discovery = registry.get("youtube_discovery", {})
        if youtube_discovery:
            if youtube_discovery.get("method") != "yt-transcript-latest":
                self.error(rel_path, "youtube_discovery.method must be yt-transcript-latest")
            for key in ["lookback_days", "max_scan_per_channel", "transcript_timeout_seconds"]:
                if not isinstance(youtube_discovery.get(key), int) or youtube_discovery.get(key) <= 0:
                    self.error(rel_path, f"youtube_discovery.{key} must be a positive integer")
            transcript_count = youtube_discovery.get("transcript_count_per_channel")
            if transcript_count is not None and (
                not isinstance(transcript_count, int) or transcript_count <= 0
            ):
                self.error(
                    rel_path,
                    "youtube_discovery.transcript_count_per_channel must be null or a positive integer",
                )

        # Validate runtime_paths from the decoupled runtime_paths layer
        try:
            sys.path.append(str(ROOT / "scripts"))
            from source_registry import load_registry
            merged_registry = load_registry()
            runtime_paths = merged_registry.get("runtime_paths", {})
        except Exception as exc:
            self.error(rel_path, f"failed to load runtime paths registry: {exc}")
            runtime_paths = {}

        for key in [
            "python_exe_env",
            "xcli_script_env",
            "yt_transcript_cli_env",
            "yt_transcript_py_script_env",
            "default_xcli_script",
            "default_yt_transcript_cli",
            "default_yt_transcript_py_script",
        ]:
            if key not in runtime_paths:
                self.error("config/runtime_paths.json", f"runtime_paths.{key} missing")

        collector_outputs = registry.get("collector_outputs", [])
        if not isinstance(collector_outputs, list) or not collector_outputs:
            self.error(rel_path, "collector_outputs must be a non-empty list")

        live_sources = registry.get("live_sources", {})
        if not isinstance(live_sources, dict) or not live_sources:
            self.error(rel_path, "live_sources must define enabled source lanes")
        for name, source in live_sources.items():
            if not isinstance(source, dict):
                self.error(rel_path, f"live_sources.{name} must be an object")
                continue
            for key in ["enabled", "scripts", "outputs"]:
                if key not in source:
                    self.error(rel_path, f"live_sources.{name}.{key} missing")
            for script in source.get("scripts", []):
                if not (ROOT / "scripts" / script).exists():
                    self.error(rel_path, f"live_sources.{name} script not found: {script}")

    def validate_followed_accounts(self) -> None:
        rel_path = "config/followed_accounts.json"
        data = self.load_json(rel_path)
        if not isinstance(data, dict):
            self.error(rel_path, "must be a JSON object")
            return
        accounts = data.get("accounts")
        if not isinstance(accounts, list) or not accounts:
            self.error(rel_path, "accounts must be a non-empty list")
            return
        allowed_tiers = {"must_follow", "high_priority", "standard", "low_priority"}
        for index, account in enumerate(accounts):
            if not isinstance(account, dict):
                self.error(rel_path, f"accounts[{index}] must be an object")
                continue
            self.require_keys(rel_path, account, ["id", "handle", "name", "category", "tier"])
            if not str(account.get("handle", "")).startswith("@"):
                self.warn(rel_path, f"accounts[{index}].handle should start with @")
            if account.get("tier") not in allowed_tiers:
                self.error(rel_path, f"accounts[{index}].tier invalid: {account.get('tier')}")

    def validate_youtube_channels(self) -> None:
        rel_path = "config/youtube_channels.json"
        data = self.load_json(rel_path)
        if not isinstance(data, dict) or not data:
            self.error(rel_path, "must be a non-empty object")
            return
        for name, channel in data.items():
            if not isinstance(channel, dict):
                self.error(rel_path, f"{name} must be an object")
                continue
            if not channel.get("channel_id"):
                self.error(rel_path, f"{name}.channel_id missing")

    def validate_youtube_channel_profiles(self) -> None:
        channels_path = "config/youtube_channels.json"
        profiles_path = "config/youtube_channel_profiles.json"
        channels = self.load_json(channels_path)
        profiles = self.load_json(profiles_path)
        if profiles is None:
            return
        if not isinstance(channels, dict) or not isinstance(profiles, dict):
            return
        profile_channels = profiles.get("channels")
        if not isinstance(profile_channels, dict) or not profile_channels:
            self.error(profiles_path, "channels must be a non-empty object")
            return
        allowed = {"P-2", "P-1", "P0", "P1", "P2", "P3"}
        channel_names = set(channels)
        profile_names = set(profile_channels)
        missing_profiles = sorted(channel_names - profile_names)
        stale_profiles = sorted(profile_names - channel_names)
        if missing_profiles:
            self.warn(profiles_path, f"missing profile(s): {', '.join(missing_profiles)}")
        if stale_profiles:
            self.error(profiles_path, f"profile(s) without channel config: {', '.join(stale_profiles)}")
        for name, profile in profile_channels.items():
            if not isinstance(profile, dict):
                self.error(profiles_path, f"channels.{name} must be an object")
                continue
            priority = profile.get("priority")
            if priority not in allowed:
                self.error(profiles_path, f"channels.{name}.priority invalid: {priority}")

    def validate_corporate_blogs(self) -> None:
        rel_path = "config/corporate_blogs.json"
        data = self.load_json(rel_path)
        if not isinstance(data, dict):
            self.error(rel_path, "must be a JSON object")
            return
        blogs = data.get("blogs")
        if not isinstance(blogs, list) or not blogs:
            self.error(rel_path, "blogs must be a non-empty list")
            return
        source_keys = {"rss_url", "sitemap_url", "algolia_url", "url", "discovery_type"}
        for index, blog in enumerate(blogs):
            if not isinstance(blog, dict):
                self.error(rel_path, f"blogs[{index}] must be an object")
                continue
            self.require_keys(rel_path, blog, ["name", "tier"])
            if not any(blog.get(key) for key in source_keys):
                self.error(rel_path, f"blogs[{index}] has no discoverable URL/source field")

    def validate_community_sources(self) -> None:
        rel_path = "config/community_sources.json"
        data = self.load_json(rel_path)
        if not isinstance(data, dict):
            self.error(rel_path, "must be a JSON object")
            return
        reddit = data.get("reddit", {})
        hacker_news = data.get("hacker_news", {})
        if not isinstance(reddit.get("subreddits"), list) or not reddit.get("subreddits"):
            self.error(rel_path, "reddit.subreddits must be a non-empty list")
        mcp_buddy = reddit.get("mcp_buddy", {})
        if mcp_buddy:
            if not isinstance(mcp_buddy, dict):
                self.error(rel_path, "reddit.mcp_buddy must be an object")
            elif mcp_buddy.get("enabled", True):
                command = mcp_buddy.get("command")
                if not isinstance(command, list) or not command:
                    self.error(rel_path, "reddit.mcp_buddy.command must be a non-empty list")
        if not isinstance(hacker_news.get("queries"), list) or not hacker_news.get("queries"):
            self.error(rel_path, "hacker_news.queries must be a non-empty list")

    def validate_finance_sources(self) -> None:
        rel_path = "config/finance_sources.json"
        data = self.load_json(rel_path)
        if not isinstance(data, dict):
            self.error(rel_path, "must be a JSON object")
            return
        rss_sources = data.get("rss_sources")
        if not isinstance(rss_sources, list) or not rss_sources:
            self.error(rel_path, "rss_sources must be a non-empty list")
        else:
            for index, source in enumerate(rss_sources):
                if not isinstance(source, dict):
                    self.error(rel_path, f"rss_sources[{index}] must be an object")
                    continue
                self.require_keys(rel_path, source, ["name", "rss_url", "tier", "source_type"])
        sec_companies = data.get("sec_companies", [])
        if sec_companies and not isinstance(sec_companies, list):
            self.error(rel_path, "sec_companies must be a list")
        for index, company in enumerate(sec_companies if isinstance(sec_companies, list) else []):
            if not isinstance(company, dict):
                self.error(rel_path, f"sec_companies[{index}] must be an object")
                continue
            self.require_keys(rel_path, company, ["name", "ticker", "cik"])
        if not isinstance(data.get("ai_keywords"), list) or not data.get("ai_keywords"):
            self.error(rel_path, "ai_keywords must be a non-empty list")
        if not isinstance(data.get("finance_keywords"), list) or not data.get("finance_keywords"):
            self.error(rel_path, "finance_keywords must be a non-empty list")

    def validate_startup_sources(self) -> None:
        rel_path = "config/startup_sources.json"
        data = self.load_json(rel_path)
        if not isinstance(data, dict):
            self.error(rel_path, "must be a JSON object")
            return
        rss_sources = data.get("rss_sources")
        if not isinstance(rss_sources, list) or not rss_sources:
            self.error(rel_path, "rss_sources must be a non-empty list")
        else:
            for index, source in enumerate(rss_sources):
                if not isinstance(source, dict):
                    self.error(rel_path, f"rss_sources[{index}] must be an object")
                    continue
                self.require_keys(rel_path, source, ["name", "rss_url", "tier", "source_type"])
        for key in ["ai_keywords", "startup_keywords", "funding_keywords", "product_keywords"]:
            if not isinstance(data.get(key), list) or not data.get(key):
                self.error(rel_path, f"{key} must be a non-empty list")
        round_patterns = data.get("round_patterns")
        if not isinstance(round_patterns, dict) or not round_patterns:
            self.error(rel_path, "round_patterns must be a non-empty object")

    def validate_model_market_sources(self) -> None:
        rel_path = "config/model_market_sources.json"
        data = self.load_json(rel_path)
        if not isinstance(data, dict):
            self.error(rel_path, "must be a JSON object")
            return
        openrouter = data.get("openrouter")
        if not isinstance(openrouter, dict):
            self.error(rel_path, "openrouter must be an object")
            return
        for key in ["models_url", "tool_models_url", "tier"]:
            if not openrouter.get(key):
                self.error(rel_path, f"openrouter.{key} missing")
        if not isinstance(data.get("tracked_change_fields"), list) or not data.get("tracked_change_fields"):
            self.error(rel_path, "tracked_change_fields must be a non-empty list")
        catalog_sources = data.get("catalog_sources", [])
        if catalog_sources and not isinstance(catalog_sources, list):
            self.error(rel_path, "catalog_sources must be a list")
        for index, source in enumerate(catalog_sources if isinstance(catalog_sources, list) else []):
            if not isinstance(source, dict):
                self.error(rel_path, f"catalog_sources[{index}] must be an object")
                continue
            self.require_keys(rel_path, source, ["name", "mode", "url", "tier", "source_type"])

    def validate_startup_collection_sources(self) -> None:
        rel_path = "config/startup_collection_sources.json"
        data = self.load_json(rel_path)
        if not isinstance(data, dict):
            self.error(rel_path, "must be a JSON object")
            return
        sources = data.get("sources")
        if not isinstance(sources, list) or not sources:
            self.error(rel_path, "sources must be a non-empty list")
            return
        allowed_modes = {"rss", "html_index", "api_or_html", "sitemap"}
        for index, source in enumerate(sources):
            if not isinstance(source, dict):
                self.error(rel_path, f"sources[{index}] must be an object")
                continue
            self.require_keys(rel_path, source, ["name", "mode", "url", "tier", "source_type"])
            if source.get("mode") not in allowed_modes:
                self.error(rel_path, f"sources[{index}].mode invalid: {source.get('mode')}")
            if source.get("mode") == "rss" and not source.get("rss_url"):
                self.error(rel_path, f"sources[{index}].rss_url missing for rss mode")
            if source.get("mode") == "api_or_html" and not source.get("fallback_urls"):
                self.error(rel_path, f"sources[{index}].fallback_urls missing for api_or_html mode")
            if source.get("mode") == "sitemap" and not source.get("sitemap_url"):
                self.error(rel_path, f"sources[{index}].sitemap_url missing for sitemap mode")
        for key in ["topic_keywords", "funding_keywords"]:
            if not isinstance(data.get(key), list) or not data.get(key):
                self.error(rel_path, f"{key} must be a non-empty list")

    def validate_science_sources(self) -> None:
        rel_path = "config/science_sources.json"
        data = self.load_json(rel_path)
        if not isinstance(data, dict):
            self.error(rel_path, "must be a JSON object")
            return
        rss_sources = data.get("rss_sources")
        if not isinstance(rss_sources, list) or not rss_sources:
            self.error(rel_path, "rss_sources must be a non-empty list")
        else:
            for index, source in enumerate(rss_sources):
                if not isinstance(source, dict):
                    self.error(rel_path, f"rss_sources[{index}] must be an object")
                    continue
                self.require_keys(rel_path, source, ["name", "rss_url", "tier", "source_type"])
        for key in ["science_keywords", "breakthrough_keywords"]:
            if not isinstance(data.get(key), list) or not data.get(key):
                self.error(rel_path, f"{key} must be a non-empty list")
        html_sources = data.get("html_sources", [])
        if html_sources and not isinstance(html_sources, list):
            self.error(rel_path, "html_sources must be a list")
        for index, source in enumerate(html_sources if isinstance(html_sources, list) else []):
            if not isinstance(source, dict):
                self.error(rel_path, f"html_sources[{index}] must be an object")
                continue
            self.require_keys(rel_path, source, ["name", "url", "tier", "source_type"])

    def validate_developer_sentiment_sources(self) -> None:
        rel_path = "config/developer_sentiment_sources.json"
        data = self.load_json(rel_path)
        if not isinstance(data, dict):
            self.error(rel_path, "must be a JSON object")
            return
        sources = data.get("status_sources")
        if not isinstance(sources, list) or not sources:
            self.error(rel_path, "status_sources must be a non-empty list")
            return
        for index, source in enumerate(sources):
            if not isinstance(source, dict):
                self.error(rel_path, f"status_sources[{index}] must be an object")
                continue
            self.require_keys(rel_path, source, ["name", "mode", "url", "tier", "source_type"])
            if source.get("mode") == "rss" and not source.get("rss_url"):
                self.error(rel_path, f"status_sources[{index}].rss_url missing for rss mode")
        if not isinstance(data.get("pain_keywords"), list) or not data.get("pain_keywords"):
            self.error(rel_path, "pain_keywords must be a non-empty list")

    def validate_prediction_market_sources(self) -> None:
        rel_path = "config/prediction_market_sources.json"
        data = self.load_json(rel_path)
        if not isinstance(data, dict):
            self.error(rel_path, "must be a JSON object")
            return
        self.require_keys(
            rel_path,
            data,
            ["watchlist_queries", "min_volume", "min_price_change_24h", "max_creation_age_hours"]
        )
        queries = data.get("watchlist_queries", [])
        if not isinstance(queries, list) or not queries:
            self.error(rel_path, "watchlist_queries must be a non-empty list")
        else:
            for index, query in enumerate(queries):
                if not isinstance(query, str):
                    self.error(rel_path, f"watchlist_queries[{index}] must be a string")
        for key in ["min_volume", "min_price_change_24h", "max_creation_age_hours"]:
            val = data.get(key)
            if not isinstance(val, (int, float)) or val < 0:
                self.error(rel_path, f"{key} must be a non-negative number")

    def validate_news_queue(self) -> None:
        rel_path = "data/news_queue.json"
        if not (ROOT / rel_path).exists():
            self.warn(rel_path, "active queue missing; create it with collection or queue maintenance")
            return
        data = self.load_json(rel_path)
        if isinstance(data, list):
            self.warn(rel_path, "legacy list format; prefer object with items[]")
            items = data
        elif isinstance(data, dict):
            items = data.get("items")
            if not isinstance(items, list):
                self.error(rel_path, "items must be a list")
                return
            if "total_items" in data and data["total_items"] != len(items):
                self.error(rel_path, f"total_items {data['total_items']} != len(items) {len(items)}")
        else:
            self.error(rel_path, "must be an object or legacy list")
            return

        if not items:
            self.warn(rel_path, "queue has no items")
            return
        url_fields = {"source_url", "url", "resolved_url", "hn_discussion_url"}
        missing_headline = 0
        missing_url = 0
        missing_source = 0
        for item in items:
            if not isinstance(item, dict):
                continue
            if not item.get("headline") and not item.get("title"):
                missing_headline += 1
            if not any(item.get(field) for field in url_fields):
                missing_url += 1
            if not item.get("source_name") and not item.get("source"):
                missing_source += 1
        if missing_headline:
            self.warn(rel_path, f"{missing_headline} item(s) missing headline/title")
        if missing_url:
            self.warn(rel_path, f"{missing_url} item(s) missing URL field")
        if missing_source:
            self.warn(rel_path, f"{missing_source} item(s) missing source/source_name")

    def validate_collector_outputs(self) -> None:
        registry = self.load_json("config/source_registry.json")
        if not isinstance(registry, dict):
            return
        for rel_path in registry.get("collector_outputs", []):
            path = ROOT / rel_path
            if not path.exists():
                self.warn(rel_path, "collector output missing; may be created by next collection run")
                continue
            payload = self.load_json(rel_path)
            if payload is None:
                continue
            if isinstance(payload, list):
                continue
            if isinstance(payload, dict):
                known_keys = {"new_discoveries", "announcements", "posts", "items", "discoveries", "signals"}
                if not any(key in payload for key in known_keys):
                    self.warn(rel_path, "collector output has no recognized item list key")
                continue
            self.warn(rel_path, "collector output should be object or list")

    def run(self) -> int:
        self.validate_source_registry()
        self.validate_followed_accounts()
        self.validate_youtube_channels()
        self.validate_youtube_channel_profiles()
        self.validate_corporate_blogs()
        self.validate_community_sources()
        self.validate_finance_sources()
        self.validate_startup_sources()
        self.validate_model_market_sources()
        self.validate_startup_collection_sources()
        self.validate_science_sources()
        self.validate_developer_sentiment_sources()
        self.validate_prediction_market_sources()
        self.validate_news_queue()
        self.validate_collector_outputs()

        for warning in self.warnings:
            print(f"WARN {warning}")
        for error in self.errors:
            print(f"ERROR {error}")
        print(f"Schema validation: {len(self.errors)} error(s), {len(self.warnings)} warning(s)")
        return 1 if self.errors else 0


if __name__ == "__main__":
    sys.exit(Validator().run())
