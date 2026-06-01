"""Shared read-only X collection coordinator."""

from __future__ import annotations

import json
import os
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable

from source_clis import WORKSPACE_ROOT
from xcli_utils import (
    collect_home_tweets,
    collect_timeline_tweets,
    normalize_handle,
    release_read_only_slots,
)


STATUS_PATH = WORKSPACE_ROOT / "data" / "x_collection_status.json"
CACHE_DIR = WORKSPACE_ROOT / "cache"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def make_run_id(now: datetime) -> str:
    return f"x-{now.strftime('%Y%m%dT%H%M%S.%fZ')}-{os.getpid()}"


def dedupe_tweets(tweets: Iterable[dict]) -> list[dict]:
    """Deduplicate by URL while preferring live evidence over cache."""
    selected: dict[str, dict] = {}
    unkeyed: list[dict] = []
    source_rank = {"cache": 0, "live": 1}
    for tweet in tweets:
        item = dict(tweet)
        url = item.get("url")
        if not url:
            unkeyed.append(item)
            continue
        existing = selected.get(url)
        if existing is None:
            selected[url] = item
            continue
        old_rank = source_rank.get(existing.get("_x_collection_source"), 0)
        new_rank = source_rank.get(item.get("_x_collection_source"), 0)
        if new_rank > old_rank:
            selected[url] = item
    return [*selected.values(), *unkeyed]


class XCollectionCoordinator:
    def __init__(
        self,
        *,
        home_collector: Callable = collect_home_tweets,
        timeline_collector: Callable = collect_timeline_tweets,
        slot_releaser: Callable[[], bool] = release_read_only_slots,
        status_path: str | Path = STATUS_PATH,
        cache_dir: str | Path = CACHE_DIR,
        now: Callable[[], datetime] = utc_now,
    ):
        self.home_collector = home_collector
        self.timeline_collector = timeline_collector
        self.slot_releaser = slot_releaser
        self.status_path = Path(status_path)
        self.cache_dir = Path(cache_dir)
        self.now = now

    def _timeline_output_path(self, handle: str) -> Path:
        return self.cache_dir / f"xcli_timeline_{handle}.json"

    @staticmethod
    def _live_tweets(tweets: Iterable[dict], *, scope: str) -> list[dict]:
        return [
            {
                **tweet,
                "_x_collection_source": "live",
                "_x_collection_scope": scope,
            }
            for tweet in tweets
        ]

    def _collect_watchlist(self, handles: list[str], workers: int, days: float) -> tuple[list[dict], list[str], list[str]]:
        tweets: list[dict] = []
        successful: list[str] = []
        failed: list[str] = []
        if not handles:
            return tweets, successful, failed

        slot_count = min(max(1, int(workers)), len(handles))
        remaining = iter(handles)
        with ThreadPoolExecutor(max_workers=slot_count) as executor:
            active = {}
            for index in range(slot_count):
                handle = next(remaining, None)
                if handle is None:
                    break
                slot = f"watch-{index + 1}"
                future = executor.submit(
                    self.timeline_collector,
                    handle,
                    days=days,
                    output_path=self._timeline_output_path(handle),
                    slot=slot,
                )
                active[future] = (handle, slot)

            while active:
                completed, _ = wait(active, return_when=FIRST_COMPLETED)
                for future in completed:
                    handle, slot = active.pop(future)
                    try:
                        account_tweets = future.result()
                    except Exception:
                        failed.append(handle)
                    else:
                        successful.append(handle)
                        tweets.extend(self._live_tweets(account_tweets, scope=f"watchlist:{handle}"))

                    next_handle = next(remaining, None)
                    if next_handle is not None:
                        next_future = executor.submit(
                            self.timeline_collector,
                            next_handle,
                            days=days,
                            output_path=self._timeline_output_path(next_handle),
                            slot=slot,
                        )
                        active[next_future] = (next_handle, slot)

        return tweets, successful, failed

    def _write_status(self, result: dict) -> None:
        self.status_path.parent.mkdir(parents=True, exist_ok=True)
        compact = {key: value for key, value in result.items() if key != "tweets"}
        with self.status_path.open("w", encoding="utf-8") as file_handle:
            json.dump(compact, file_handle, indent=2, ensure_ascii=False)

    def collect(
        self,
        handles: Iterable[str],
        *,
        workers: int = 3,
        days: float = 7.0,
        home_count: int = 30,
        skip_home: bool = False,
    ) -> dict:
        started = self.now()
        run_id = make_run_id(started)
        normalized_handles = list(dict.fromkeys(filter(None, (normalize_handle(handle) for handle in handles))))
        all_tweets: list[dict] = []
        home_state = "SKIPPED" if skip_home else "LIVE_OK"
        home_error = None

        try:
            if not skip_home:
                try:
                    home_tweets = self.home_collector(
                        home_count,
                        self.cache_dir / "xcli_home.json",
                        slot="home",
                    )
                except Exception as exc:
                    home_state = "FAILED"
                    home_error = str(exc)
                else:
                    all_tweets.extend(self._live_tweets(home_tweets, scope="home"))

            watchlist_tweets, successful, failed = self._collect_watchlist(normalized_handles, workers, days)
            all_tweets.extend(watchlist_tweets)
        finally:
            self.slot_releaser()

        tweets = dedupe_tweets(all_tweets)
        missing = list(failed)
        if home_state == "FAILED" and not skip_home:
            missing.insert(0, "home")
        status = "LIVE_OK"
        if missing:
            status = "PARTIAL" if tweets else "FAILED"

        finished = self.now()
        result = {
            "run_id": run_id,
            "status": status,
            "started_at": started.isoformat(),
            "finished_at": finished.isoformat(),
            "requested_workers": max(1, int(workers)),
            "effective_workers": min(max(1, int(workers)), len(normalized_handles)) if normalized_handles else 0,
            "home_feed_skipped": skip_home,
            "home_feed_status": home_state,
            "home_feed_error": home_error,
            "watchlist_requested": normalized_handles,
            "watchlist_live_successes": successful,
            "watchlist_failures": failed,
            "missing_sources": missing,
            "tweet_count": len(tweets),
            "tweets": tweets,
        }
        self._write_status(result)
        return result


def collect_x_read_only(handles: Iterable[str], **kwargs) -> dict:
    return XCollectionCoordinator().collect(handles, **kwargs)
