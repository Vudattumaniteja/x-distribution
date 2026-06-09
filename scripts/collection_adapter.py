"""Programmatic collection lane adapters."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Callable

import requests

SCRIPTS_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = SCRIPTS_DIR.parent

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.append(str(SCRIPTS_DIR))


class CollectionAdapter:
    """Base programmatic adapter interface for workspace collection lanes."""

    def collect(self) -> list[dict[str, Any]]:
        """Run collection and return a list of normalized signal records."""
        raise NotImplementedError("Subclasses must implement collect()")


@dataclass
class LaneRunResult:
    """Normalized Phase 1 lane result plus health metadata."""

    lane: str
    records: list[dict[str, Any]]
    status: str = "OK"
    health: dict[str, Any] = field(default_factory=dict)

    def health_entry(self) -> dict[str, Any]:
        entry = {"lane": self.lane, "status": self.status, "items": len(self.records)}
        entry.update(self.health)
        return entry


class CollectionLaneAdapter:
    """Base Phase 1 lane adapter returning records and health."""

    lane_name: str

    def run(self) -> LaneRunResult:
        raise NotImplementedError("Subclasses must implement run()")


class FunctionLaneAdapter(CollectionLaneAdapter):
    """Wrap existing collection functions during incremental lane migration."""

    def __init__(
        self,
        lane_name: str,
        collect_fn: Callable[[], Any],
        *,
        x_metadata: bool = False,
    ) -> None:
        self.lane_name = lane_name
        self.collect_fn = collect_fn
        self.x_metadata = x_metadata

    def run(self) -> LaneRunResult:
        value = self.collect_fn()
        if self.x_metadata:
            records, metadata = value
            status = metadata["status"]
            return LaneRunResult(
                lane=self.lane_name,
                records=records,
                status=status,
                health={
                    "x_status": status,
                    "x_run_id": metadata["run_id"],
                },
            )
        return LaneRunResult(self.lane_name, value or [])


class ScriptOutputLaneAdapter(CollectionLaneAdapter):
    """Run configured scripts, read compatibility outputs, and normalize records."""

    def __init__(
        self,
        lane_name: str,
        source_names: tuple[str, ...],
        output_loader: Callable[[Path], list[dict[str, Any]]],
        normalizer: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> None:
        self.lane_name = lane_name
        self.source_names = source_names
        self.output_loader = output_loader
        self.normalizer = normalizer

    def run(self) -> LaneRunResult:
        from source_clis import python_script_command
        from source_registry import enabled_live_source_scripts, live_source_outputs

        env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
        failures = []
        for script in enabled_live_source_scripts(*self.source_names):
            completed = subprocess.run(python_script_command(script), check=False, env=env)
            if completed.returncode != 0:
                failures.append({"script": script, "returncode": completed.returncode})

        records = []
        for output in live_source_outputs(*self.source_names):
            output_path = WORKSPACE_ROOT / output
            if not output_path.exists():
                continue
            for item in self.output_loader(output_path):
                records.append(self.normalizer(item))

        status = "ERROR" if failures and not records else "PARTIAL" if failures else "OK"
        health = {"script_failures": failures} if failures else {}
        return LaneRunResult(self.lane_name, records, status, health)


def load_discovery_items(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    if isinstance(payload, list):
        return payload
    return payload.get("new_discoveries", [])


def normalize_artifact_research_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "headline": (
            item.get("title")
            or item.get("repo_name")
            or item.get("model_id")
            or item.get("release_name")
            or "Artifact/research discovery"
        ),
        "summary": item.get("summary") or item.get("description") or "",
        "source": item.get("source", "GitHub/arXiv"),
        "url": item.get("url") or item.get("html_url") or item.get("source_url") or "",
        "signal_type": "Artifact/Research Source",
        "notes": "Collected through configured GitHub/Hugging Face/arXiv source lane",
        "published_at": item.get("published_at") or item.get("created_at") or item.get("updated_at"),
    }


class ArtifactResearchLaneAdapter(ScriptOutputLaneAdapter):
    """Lane E adapter for GitHub, Hugging Face, and arXiv outputs."""

    def __init__(self) -> None:
        super().__init__(
            "artifact_research",
            ("github", "huggingface", "arxiv"),
            load_discovery_items,
            normalize_artifact_research_item,
        )


class RSSCollectionAdapter(CollectionAdapter):
    """In-process adapter for Lane B: Corporate RSS (Ground Truth)."""

    def collect(self) -> list[dict[str, Any]]:
        import corporate_rss_discovery

        config_path = WORKSPACE_ROOT / corporate_rss_discovery.CONFIG_PATH
        if not config_path.exists():
            print(f"RSS Config not found: {config_path}")
            return []

        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        default_cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        all_announcements = []
        session = requests.Session()

        for blog in config["blogs"]:
            mode = blog.get("discovery_type", "rss")
            lookback_hours = blog.get("lookback_hours")
            cutoff = (
                datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
                if lookback_hours
                else default_cutoff
            )

            try:
                if mode == "rss":
                    items, _ = corporate_rss_discovery.collect_rss(session, blog, cutoff)
                elif mode == "health_only":
                    items, _ = corporate_rss_discovery.collect_health_only(session, blog)
                elif mode == "hacker_news_algolia":
                    items, _ = corporate_rss_discovery.collect_hacker_news(session, blog, cutoff)
                else:
                    items, _ = corporate_rss_discovery.collect_official_pages(session, blog, cutoff)
                all_announcements.extend(items)
            except Exception as e:
                print(f"Error collecting corporate blog {blog.get('name')}: {e}")

        # Normalize the announcements for news_queue.json
        normalized = []
        for a in all_announcements:
            normalized.append(
                {
                    "headline": a["title"],
                    "summary": a.get("summary", ""),
                    "source": a["source"],
                    "url": a["url"],
                    "signal_type": "Verified",
                    "notes": "Official Corporate Announcement",
                    "published_at": a.get("published_at"),
                }
            )

        # Write cache to match legacy side-effect file behavior if downstream readers rely on it
        output_path = WORKSPACE_ROOT / corporate_rss_discovery.OUTPUT_PATH
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                    "announcements": all_announcements,
                },
                f,
                indent=2,
                ensure_ascii=False,
            )

        return normalized


class HNCollectionAdapter(CollectionAdapter):
    """In-process adapter for Hacker News community signals."""

    def collect(self) -> list[dict[str, Any]]:
        import hn_scraper_standalone

        config = hn_scraper_standalone.load_config()
        discoveries, _ = hn_scraper_standalone.fetch_hn_discussions(config)

        # Save side-effect output cache to match legacy behavior
        output_path = WORKSPACE_ROOT / hn_scraper_standalone.OUTPUT_PATH
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                    "new_discoveries": discoveries,
                },
                f,
                indent=2,
                ensure_ascii=False,
            )

        normalized = []
        for item in discoveries:
            normalized.append(
                {
                    "headline": item.get("title", "Community discussion"),
                    "summary": item.get("summary", ""),
                    "source": item.get("source", "Hacker News"),
                    "url": item.get("url", ""),
                    "signal_type": "Community Reality Check",
                    "notes": item.get("discussion_signal", "real_developer_talk"),
                    "published_at": item.get("published_at"),
                    "score": item.get("points"),
                    "num_comments": item.get("num_comments"),
                    "top_comments": item.get("top_comments", []),
                }
            )
        return normalized


class RedditCollectionAdapter(CollectionAdapter):
    """In-process adapter for Reddit community signals."""

    def collect(self) -> list[dict[str, Any]]:
        import reddit_mcp_buddy_collect

        config = reddit_mcp_buddy_collect.load_config()

        posts = []
        if reddit_mcp_buddy_collect.mcp_config(config).get("enabled", True):
            try:
                posts = reddit_mcp_buddy_collect.collect_posts_via_mcp(config)
            except Exception as exc:
                print(f"Reddit MCP Buddy failed in-process: {exc}")

        rss_posts = reddit_mcp_buddy_collect.collect_posts_via_rss(config)
        if rss_posts:
            merged_posts = {post["id"]: post for post in posts}
            reddit_mcp_buddy_collect.merge_posts(
                merged_posts, rss_posts, config.get("discussion_keywords", [])
            )
            posts = sorted(
                merged_posts.values(),
                key=lambda item: reddit_mcp_buddy_collect.discussion_score(
                    item, config.get("discussion_keywords", [])
                ),
                reverse=True,
            )

        topic_keywords = config.get("topic_keywords", [])
        discoveries = [
            reddit_mcp_buddy_collect.to_discovery(post, config.get("discussion_keywords", []))
            for post in posts
            if reddit_mcp_buddy_collect.has_topic_signal(post, topic_keywords)
        ]

        # Save side-effect cache to match legacy behavior
        output_path = WORKSPACE_ROOT / reddit_mcp_buddy_collect.OUTPUT_PATH
        output_path.parent.mkdir(parents=True, exist_ok=True)
        status = "mcp_rss_live_ok" if rss_posts else "mcp_live_ok"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                    "collection_status": status,
                    "collector": "reddit_mcp_buddy",
                    "posts": posts,
                    "new_discoveries": discoveries,
                },
                f,
                indent=2,
                ensure_ascii=False,
            )

        normalized = []
        for item in discoveries:
            normalized.append(
                {
                    "headline": item.get("title", "Community discussion"),
                    "summary": item.get("summary", ""),
                    "source": item.get("source", "Reddit"),
                    "url": item.get("url", ""),
                    "signal_type": "Community Reality Check",
                    "notes": item.get("discussion_signal", "real_developer_talk"),
                    "published_at": item.get("published_at"),
                    "score": item.get("score"),
                    "num_comments": item.get("num_comments"),
                    "top_comments": item.get("top_comments", []),
                }
            )
        return normalized
