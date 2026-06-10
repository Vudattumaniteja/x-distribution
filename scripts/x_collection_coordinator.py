"""Shared read-only X collection coordinator with notified degradation."""

from __future__ import annotations

import json
import os
import shutil
from collections import deque
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
LOCK_PATH = CACHE_DIR / "x_collection.lock"
NOTIFICATION_PATH = WORKSPACE_ROOT / "logs" / "x_collection_notifications.jsonl"
HOME_CACHE_MAX_HOURS = 24
WATCHLIST_CACHE_MAX_HOURS = 48
FALLBACK_THRESHOLD = 3
MAX_NOTIFICATION_BYTES = 5 * 1024 * 1024


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


def pid_is_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


class XNotifier:
    def __init__(
        self,
        run_id: str,
        *,
        path: str | Path = NOTIFICATION_PATH,
        now: Callable[[], datetime] = utc_now,
        max_bytes: int = MAX_NOTIFICATION_BYTES,
    ):
        self.run_id = run_id
        self.path = Path(path)
        self.previous_path = self.path.with_name("x_collection_notifications.previous.jsonl")
        self.now = now
        self.max_bytes = max_bytes
        self.records: list[dict] = []

    def _rotate(self) -> None:
        if not self.path.exists() or self.path.stat().st_size < self.max_bytes:
            return
        self.previous_path.parent.mkdir(parents=True, exist_ok=True)
        if self.previous_path.exists():
            self.previous_path.unlink()
        shutil.move(str(self.path), str(self.previous_path))

    def notify(self, severity: str, notification_type: str, reason: str, **state) -> dict:
        record = {
            "timestamp": self.now().isoformat(),
            "run_id": self.run_id,
            "severity": severity,
            "type": notification_type,
            "reason": reason,
            **state,
        }
        print(f"[X NOTIFY] {severity} {notification_type}: {reason}")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._rotate()
        with self.path.open("a", encoding="utf-8") as file_handle:
            file_handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        self.records.append(record)
        return record


class XCollectionCoordinator:
    def __init__(
        self,
        *,
        home_collector: Callable = collect_home_tweets,
        timeline_collector: Callable = collect_timeline_tweets,
        slot_releaser: Callable[[], bool] = release_read_only_slots,
        status_path: str | Path = STATUS_PATH,
        cache_dir: str | Path = CACHE_DIR,
        lock_path: str | Path | None = None,
        notification_path: str | Path = NOTIFICATION_PATH,
        now: Callable[[], datetime] = utc_now,
        pid_checker: Callable[[int], bool] = pid_is_running,
        pid: int | None = None,
        notification_max_bytes: int = MAX_NOTIFICATION_BYTES,
    ):
        self.home_collector = home_collector
        self.timeline_collector = timeline_collector
        self.slot_releaser = slot_releaser
        self.status_path = Path(status_path)
        self.cache_dir = Path(cache_dir)
        self.lock_path = Path(lock_path) if lock_path else self.cache_dir / "x_collection.lock"
        self.notification_path = Path(notification_path)
        self.now = now
        self.pid_checker = pid_checker
        self.pid = pid if pid is not None else os.getpid()
        self.notification_max_bytes = notification_max_bytes

    def _timeline_output_path(self, handle: str) -> Path:
        return self.cache_dir / f"xcli_timeline_{handle}.json"

    def _home_output_path(self) -> Path:
        return self.cache_dir / "xcli_home.json"

    @staticmethod
    def _tag_tweets(tweets: Iterable[dict], *, source: str, scope: str) -> list[dict]:
        return [
            {
                **tweet,
                "_x_collection_source": source,
                "_x_collection_scope": scope,
            }
            for tweet in tweets
        ]

    def _fresh_cache(self, path: Path, max_hours: float, allow_stale: bool = False) -> tuple[list[dict], dict]:
        if not path.exists():
            return [], {"cache_status": "MISSING", "cache_path": str(path)}
        age_hours = max(0.0, (self.now().timestamp() - path.stat().st_mtime) / 3600)
        cache_meta = {
            "cache_path": str(path),
            "cache_timestamp": datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat(),
            "cache_age_hours": age_hours,
        }
        if age_hours > max_hours and not allow_stale:
            return [], {**cache_meta, "cache_status": "STALE"}
        try:
            with path.open("r", encoding="utf-8") as file_handle:
                payload = json.load(file_handle)
        except (OSError, json.JSONDecodeError):
            return [], {**cache_meta, "cache_status": "INVALID"}
        if not isinstance(payload, list) or not payload:
            return [], {**cache_meta, "cache_status": "EMPTY"}
        
        if age_hours > max_hours:
            return payload, {**cache_meta, "cache_status": "STALE_FALLBACK"}
        return payload, {**cache_meta, "cache_status": "FRESH"}

    def _attempt_home_live(self, count: int) -> tuple[list[dict], str | None]:
        try:
            tweets = self.home_collector(
                count,
                self._home_output_path(),
                slot="home",
                allow_cache_fallback=False,
                raise_on_error=True,
            )
        except Exception as exc:
            return [], str(exc)
        if not tweets:
            return [], "live home feed returned no tweets"
        return self._tag_tweets(tweets, source="live", scope="home"), None

    def _attempt_timeline(self, handle: str, slot: str) -> dict:
        output_path = self._timeline_output_path(handle)
        try:
            tweets = self.timeline_collector(
                handle,
                days=self.timeline_days,
                output_path=output_path,
                slot=slot,
                allow_cache_fallback=False,
                raise_on_error=True,
            )
        except Exception as exc:
            error = str(exc)
        else:
            if tweets:
                return {
                    "handle": handle,
                    "slot": slot,
                    "live_ok": True,
                    "tweets": self._tag_tweets(tweets, source="live", scope=f"watchlist:{handle}"),
                }
            error = "live timeline returned no tweets"

        cached, cache_meta = self._fresh_cache(output_path, WATCHLIST_CACHE_MAX_HOURS)
        if not cached and cache_meta.get("cache_status") == "STALE":
            cached, cache_meta = self._fresh_cache(output_path, WATCHLIST_CACHE_MAX_HOURS, allow_stale=True)
        return {
            "handle": handle,
            "slot": slot,
            "live_ok": False,
            "error": error,
            "tweets": self._tag_tweets(cached, source="cache", scope=f"watchlist:{handle}"),
            **cache_meta,
        }

    def _acquire_lock(self, run_id: str, notifier: XNotifier) -> tuple[bool, dict | None]:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"run_id": run_id, "pid": self.pid, "created_at": self.now().isoformat()}
        while True:
            try:
                with self.lock_path.open("x", encoding="utf-8") as file_handle:
                    json.dump(payload, file_handle, indent=2)
                return True, payload
            except FileExistsError:
                try:
                    with self.lock_path.open("r", encoding="utf-8") as file_handle:
                        existing = json.load(file_handle)
                except (OSError, json.JSONDecodeError):
                    existing = {}
                existing_pid = int(existing.get("pid") or 0)
                if existing_pid and self.pid_checker(existing_pid):
                    notifier.notify(
                        "ERROR",
                        "active_lock_rejected",
                        "another X collection run is active",
                        active_run_id=existing.get("run_id"),
                        active_pid=existing_pid,
                    )
                    return False, existing
                notifier.notify(
                    "INFO",
                    "stale_lock_replaced",
                    "replacing X collection lock because its owning PID is not running",
                    stale_run_id=existing.get("run_id"),
                    stale_pid=existing_pid,
                )
                try:
                    self.lock_path.unlink()
                except FileNotFoundError:
                    pass

    def _release_lock(self, run_id: str) -> None:
        try:
            with self.lock_path.open("r", encoding="utf-8") as file_handle:
                existing = json.load(file_handle)
        except (OSError, json.JSONDecodeError):
            return
        if existing.get("run_id") == run_id:
            self.lock_path.unlink(missing_ok=True)

    def _record_failed_attempt(self, attempt: dict, notifier: XNotifier) -> None:
        if attempt.get("tweets"):
            if attempt.get("cache_status") == "STALE_FALLBACK":
                notifier.notify(
                    "WARN",
                    "stale_cache_fallback",
                    f"live timeline failed for @{attempt['handle']}; using stale cache fallback",
                    handle=attempt["handle"],
                    slot=attempt["slot"],
                    live_error=attempt.get("error"),
                    cache_timestamp=attempt.get("cache_timestamp"),
                    cache_age_hours=attempt.get("cache_age_hours"),
                )
            else:
                notifier.notify(
                    "WARN",
                    "watchlist_cache_used",
                    f"live timeline failed for @{attempt['handle']}; using fresh cache",
                    handle=attempt["handle"],
                    slot=attempt["slot"],
                    live_error=attempt.get("error"),
                    cache_timestamp=attempt.get("cache_timestamp"),
                    cache_age_hours=attempt.get("cache_age_hours"),
                )
        else:
            notifier.notify(
                "ERROR",
                "watchlist_missing",
                f"live timeline failed for @{attempt['handle']} and no fresh cache is usable",
                handle=attempt["handle"],
                slot=attempt["slot"],
                live_error=attempt.get("error"),
                cache_status=attempt.get("cache_status"),
                cache_age_hours=attempt.get("cache_age_hours"),
            )

    def _collect_watchlist(self, handles: list[str], workers: int, notifier: XNotifier) -> tuple[list[dict], dict]:
        tweets: list[dict] = []
        best_by_handle: dict[str, dict] = {}
        failed_parallel: list[str] = []
        attempts: list[dict] = []
        remaining = deque(handles)
        consecutive_failures = 0
        fallback_activated = False
        requested_workers = max(1, int(workers))
        slot_count = min(requested_workers, len(handles)) if handles else 0

        def remember(attempt: dict) -> None:
            current = best_by_handle.get(attempt["handle"])
            if current is None or (attempt["live_ok"] and not current["live_ok"]):
                best_by_handle[attempt["handle"]] = attempt
            attempts.append(attempt)
            tweets.extend(attempt.get("tweets", []))

        if slot_count:
            with ThreadPoolExecutor(max_workers=slot_count) as executor:
                active = {}

                def submit(handle: str, slot: str) -> None:
                    future = executor.submit(self._attempt_timeline, handle, slot)
                    active[future] = (handle, slot, len(attempts) + len(active))

                for index in range(slot_count):
                    submit(remaining.popleft(), f"watch-{index + 1}")

                while active:
                    completed, _ = wait(active, return_when=FIRST_COMPLETED)
                    ordered = sorted(completed, key=lambda future: active[future][2])
                    for future in ordered:
                        handle, slot, _ = active.pop(future)
                        attempt = future.result()
                        remember(attempt)
                        if attempt["live_ok"]:
                            consecutive_failures = 0
                        else:
                            consecutive_failures += 1
                            failed_parallel.append(handle)
                            self._record_failed_attempt(attempt, notifier)
                            if consecutive_failures >= FALLBACK_THRESHOLD and not fallback_activated:
                                fallback_activated = True
                                notifier.notify(
                                    "WARN",
                                    "serialized_fallback_activated",
                                    "three consecutive live watchlist failures; draining active workers before serialized recovery",
                                    requested_workers=requested_workers,
                                    fallback_workers=1,
                                    failed_handles=list(failed_parallel),
                                )
                        if remaining and not fallback_activated:
                            submit(remaining.popleft(), slot)

        if fallback_activated:
            retry_queue = list(dict.fromkeys([*failed_parallel, *remaining]))
            for handle in retry_queue:
                attempt = self._attempt_timeline(handle, "watch-1")
                remember(attempt)
                if not attempt["live_ok"]:
                    self._record_failed_attempt(attempt, notifier)
            notifier.notify(
                "INFO",
                "serialized_fallback_completed",
                "serialized watchlist recovery completed",
                retried_handles=retry_queue,
            )

        summary = {
            "requested_workers": requested_workers,
            "effective_workers": 1 if fallback_activated else slot_count,
            "serialized_fallback_activated": fallback_activated,
            "watchlist_attempts": attempts,
            "watchlist_live_successes": sorted(handle for handle, attempt in best_by_handle.items() if attempt["live_ok"]),
            "watchlist_cached_accounts": sorted(
                handle for handle, attempt in best_by_handle.items() if not attempt["live_ok"] and attempt.get("tweets")
            ),
            "watchlist_missing_accounts": sorted(
                handle for handle in handles if not best_by_handle.get(handle, {}).get("tweets")
            ),
            "failed_parallel_accounts": failed_parallel,
        }
        return tweets, summary

    def _write_status(self, result: dict) -> None:
        self.status_path.parent.mkdir(parents=True, exist_ok=True)
        compact = {key: value for key, value in result.items() if key not in {"tweets", "watchlist_attempts"}}
        with self.status_path.open("w", encoding="utf-8") as file_handle:
            json.dump(compact, file_handle, indent=2, ensure_ascii=False)

    def _blocked_result(self, run_id: str, started: datetime, notifier: XNotifier, existing_lock: dict | None) -> dict:
        result = {
            "run_id": run_id,
            "status": "FAILED",
            "blocked_by_active_lock": True,
            "active_lock": existing_lock,
            "started_at": started.isoformat(),
            "finished_at": self.now().isoformat(),
            "notification_count": len(notifier.records),
            "tweet_count": 0,
            "tweets": [],
        }
        self._write_status(result)
        return result

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
        notifier = XNotifier(
            run_id,
            path=self.notification_path,
            now=self.now,
            max_bytes=self.notification_max_bytes,
        )
        normalized_handles = list(dict.fromkeys(filter(None, (normalize_handle(handle) for handle in handles))))
        self.timeline_days = days
        acquired, existing_lock = self._acquire_lock(run_id, notifier)
        if not acquired:
            return self._blocked_result(run_id, started, notifier, existing_lock)

        all_tweets: list[dict] = []
        home_status = "SKIPPED" if skip_home else "LIVE_OK"
        home_error = None
        home_cache_meta = {}
        degraded = False

        try:
            if not skip_home:
                home_tweets, home_error = self._attempt_home_live(home_count)
                if home_error:
                    degraded = True
                    home_status = "LIVE_FAILED"
                    notifier.notify(
                        "WARN",
                        "home_failed",
                        "live home-feed collection failed; continuing with watchlist collection",
                        live_error=home_error,
                    )
                else:
                    all_tweets.extend(home_tweets)

            watchlist_tweets, watchlist = self._collect_watchlist(normalized_handles, workers, notifier)
            all_tweets.extend(watchlist_tweets)
            degraded = degraded or watchlist["serialized_fallback_activated"] or bool(watchlist["watchlist_cached_accounts"])

            if home_status == "LIVE_FAILED":
                retry_tweets, retry_error = self._attempt_home_live(home_count)
                if retry_error:
                    home_error = retry_error
                    cached, home_cache_meta = self._fresh_cache(self._home_output_path(), HOME_CACHE_MAX_HOURS)
                    is_stale_fallback = False
                    if not cached and home_cache_meta.get("cache_status") == "STALE":
                        cached, home_cache_meta = self._fresh_cache(self._home_output_path(), HOME_CACHE_MAX_HOURS, allow_stale=True)
                        if cached:
                            is_stale_fallback = True
                    if cached:
                        home_status = "CACHE"
                        all_tweets.extend(self._tag_tweets(cached, source="cache", scope="home"))
                        if is_stale_fallback:
                            notifier.notify(
                                "WARN",
                                "stale_cache_fallback",
                                "live home-feed retry failed; using stale cache fallback",
                                live_error=retry_error,
                                cache_timestamp=home_cache_meta.get("cache_timestamp"),
                                cache_age_hours=home_cache_meta.get("cache_age_hours"),
                            )
                        else:
                            notifier.notify(
                                "WARN",
                                "home_cache_used",
                                "live home-feed retry failed; using fresh cache",
                                live_error=retry_error,
                                cache_timestamp=home_cache_meta.get("cache_timestamp"),
                                cache_age_hours=home_cache_meta.get("cache_age_hours"),
                            )
                    else:
                        home_status = "MISSING"
                        notifier.notify(
                            "ERROR",
                            "home_missing",
                            "live home-feed retry failed and no fresh cache is usable",
                            live_error=retry_error,
                            cache_status=home_cache_meta.get("cache_status"),
                            cache_age_hours=home_cache_meta.get("cache_age_hours"),
                        )
                else:
                    home_status = "LIVE_RECOVERED"
                    all_tweets.extend(retry_tweets)
                    notifier.notify("INFO", "home_recovered", "live home-feed retry succeeded")
        finally:
            try:
                if not self.slot_releaser():
                    notifier.notify("WARN", "slot_release_failed", "tagged automation tabs could not be released")
            except Exception as exc:
                notifier.notify("WARN", "slot_release_failed", f"tagged automation tab release failed: {exc}")
            self._release_lock(run_id)

        tweets = dedupe_tweets(all_tweets)
        missing_sources = list(watchlist["watchlist_missing_accounts"])
        if home_status == "MISSING":
            missing_sources.insert(0, "home")
        if missing_sources:
            status = "PARTIAL" if tweets else "FAILED"
        elif degraded:
            status = "DEGRADED_OK"
        else:
            status = "LIVE_OK"
        if status == "FAILED":
            notifier.notify("FATAL", "x_collection_failed", "X collection produced no usable data")

        finished = self.now()
        result = {
            "run_id": run_id,
            "status": status,
            "started_at": started.isoformat(),
            "finished_at": finished.isoformat(),
            "requested_workers": watchlist["requested_workers"],
            "effective_workers": watchlist["effective_workers"],
            "serialized_fallback_activated": watchlist["serialized_fallback_activated"],
            "home_feed_skipped": skip_home,
            "home_feed_status": home_status,
            "home_feed_error": home_error,
            "home_cache": home_cache_meta,
            "watchlist_requested": normalized_handles,
            "watchlist_live_successes": watchlist["watchlist_live_successes"],
            "watchlist_cached_accounts": watchlist["watchlist_cached_accounts"],
            "watchlist_missing_accounts": watchlist["watchlist_missing_accounts"],
            "failed_parallel_accounts": watchlist["failed_parallel_accounts"],
            "watchlist_attempts": watchlist["watchlist_attempts"],
            "missing_sources": missing_sources,
            "notification_count": len(notifier.records),
            "tweet_count": len(tweets),
            "tweets": tweets,
        }
        self._write_status(result)
        return result


def collect_x_read_only(handles: Iterable[str], **kwargs) -> dict:
    return XCollectionCoordinator().collect(handles, **kwargs)
