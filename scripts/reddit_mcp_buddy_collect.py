"""Collect Reddit discussions through reddit-mcp-buddy, with local fallback.

The old Reddit collector uses public reddit.com JSON endpoints directly. Those
often return 403 from local automation. This adapter talks to the
reddit-mcp-buddy MCP server instead, then writes the same output shape expected
by the rest of the X Distribution pipeline.
"""

from __future__ import annotations

import json
import os
import platform
import queue
import subprocess
import sys
import threading
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import requests

from reddit_scraper_standalone import (
    CONFIG_PATH,
    OUTPUT_PATH,
    clean_text,
    discussion_score,
    has_topic_signal,
    load_config,
    load_existing_output,
    to_discovery,
)
from source_clis import python_script_command


ROOT = Path(__file__).resolve().parents[1]
BRIDGE_PATH = ROOT / "scripts" / "reddit_mcp_buddy_bridge.mjs"
DEFAULT_STARTUP_TIMEOUT_SECONDS = 45
DEFAULT_REQUEST_TIMEOUT_SECONDS = 60
DEFAULT_SEARCH_QUERIES_PER_SUBREDDIT = 2
DEFAULT_MAX_DETAIL_FETCH_ITEMS = 20
DEFAULT_RSS_TIMEOUT_SECONDS = 20
FALLBACK_SCRIPT = "reddit_scraper_standalone.py"
UTF8_ENV = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
RSS_HEADERS = {
    "User-Agent": "XDistributionCommunityDiscovery/2.0 (developer discussion monitor; local RSS fallback)"
}
MCP_FAILURES: list[str] = []
RSS_RATE_LIMITS: list[str] = []
RSS_FAILURES: list[str] = []


class MCPClientError(RuntimeError):
    pass


class RedditMCPBuddyClient:
    def __init__(
        self,
        command: list[str],
        startup_timeout: int = DEFAULT_STARTUP_TIMEOUT_SECONDS,
        request_timeout: int = DEFAULT_REQUEST_TIMEOUT_SECONDS,
    ) -> None:
        self.command = command
        self.startup_timeout = startup_timeout
        self.request_timeout = request_timeout
        self.proc: subprocess.Popen[bytes] | None = None
        self.next_id = 1
        self.responses: dict[int, dict[str, Any]] = {}
        self.response_queue: queue.Queue[dict[str, Any]] = queue.Queue()
        self.stderr_lines: list[str] = []
        self._stderr_lock = threading.Lock()

    def __enter__(self) -> "RedditMCPBuddyClient":
        self.start()
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def start(self) -> None:
        env = UTF8_ENV.copy()
        self.proc = subprocess.Popen(
            self.command,
            cwd=str(ROOT),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            bufsize=0,
        )
        threading.Thread(target=self._read_stdout, daemon=True).start()
        threading.Thread(target=self._read_stderr, daemon=True).start()
        self.initialize()

    def initialize(self) -> None:
        result = self.request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "x-distribution", "version": "0.1"},
            },
            timeout=self.startup_timeout,
        )
        if "serverInfo" not in result:
            raise MCPClientError("reddit-mcp-buddy initialize returned no serverInfo")
        self.notify("notifications/initialized", {})

    def notify(self, method: str, params: dict[str, Any]) -> None:
        self._send({"jsonrpc": "2.0", "method": method, "params": params})

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        result = self.request(
            "tools/call",
            {"name": name, "arguments": arguments},
            timeout=self.request_timeout,
        )
        content = result.get("content", [])
        if result.get("isError"):
            text = content[0].get("text", "") if content else ""
            raise MCPClientError(f"{name} failed: {text}")
        if not content:
            return {}
        text = content[0].get("text", "")
        if not text:
            return {}
        return json.loads(text)

    def request(self, method: str, params: dict[str, Any], timeout: int | None = None) -> dict[str, Any]:
        if not self.proc or self.proc.poll() is not None:
            raise MCPClientError(self._process_error("reddit-mcp-buddy process is not running"))
        request_id = self.next_id
        self.next_id += 1
        self._send({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
        deadline = time.monotonic() + (timeout or self.request_timeout)
        while time.monotonic() < deadline:
            if request_id in self.responses:
                response = self.responses.pop(request_id)
                if "error" in response:
                    raise MCPClientError(f"{method} failed: {response['error']}")
                return response.get("result", {})
            try:
                response = self.response_queue.get(timeout=0.25)
            except queue.Empty:
                if self.proc and self.proc.poll() is not None:
                    raise MCPClientError(self._process_error("reddit-mcp-buddy exited"))
                continue
            response_id = response.get("id")
            if response_id == request_id:
                if "error" in response:
                    raise MCPClientError(f"{method} failed: {response['error']}")
                return response.get("result", {})
            if isinstance(response_id, int):
                self.responses[response_id] = response
        raise MCPClientError(self._process_error(f"{method} timed out after {timeout or self.request_timeout}s"))

    def close(self) -> None:
        if not self.proc:
            return
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.proc = None

    def _send(self, payload: dict[str, Any]) -> None:
        if not self.proc or not self.proc.stdin:
            raise MCPClientError("reddit-mcp-buddy stdin is unavailable")
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        header = (
            f"Content-Length: {len(body)}\r\n"
            "Content-Type: application/vscode-jsonrpc; charset=utf-8\r\n\r\n"
        ).encode("ascii")
        self.proc.stdin.write(header + body)
        self.proc.stdin.flush()

    def _read_stdout(self) -> None:
        if not self.proc or not self.proc.stdout:
            return
        while True:
            header = self._read_until_header_end(self.proc.stdout)
            if not header:
                return
            content_length = self._content_length(header)
            if content_length <= 0:
                return
            body = self._read_exact(self.proc.stdout, content_length)
            if body is None:
                return
            try:
                self.response_queue.put(json.loads(body.decode("utf-8")))
            except json.JSONDecodeError:
                continue

    def _read_stderr(self) -> None:
        if not self.proc or not self.proc.stderr:
            return
        while True:
            line = self.proc.stderr.readline()
            if not line:
                return
            decoded = line.decode("utf-8", errors="replace").strip()
            if decoded:
                with self._stderr_lock:
                    self.stderr_lines.append(decoded)
                    self.stderr_lines = self.stderr_lines[-20:]

    def _process_error(self, message: str) -> str:
        with self._stderr_lock:
            stderr_tail = " | ".join(self.stderr_lines[-5:])
        if stderr_tail:
            safe_tail = stderr_tail.encode("ascii", errors="backslashreplace").decode("ascii")
            return f"{message}. stderr: {safe_tail}"
        return message

    @staticmethod
    def _read_until_header_end(stream: Any) -> bytes | None:
        data = b""
        while b"\r\n\r\n" not in data:
            chunk = stream.read(1)
            if not chunk:
                return None
            data += chunk
        return data

    @staticmethod
    def _read_exact(stream: Any, length: int) -> bytes | None:
        data = b""
        while len(data) < length:
            chunk = stream.read(length - len(data))
            if not chunk:
                return None
            data += chunk
        return data

    @staticmethod
    def _content_length(header: bytes) -> int:
        for line in header.decode("ascii", errors="ignore").split("\r\n"):
            if line.lower().startswith("content-length:"):
                return int(line.split(":", 1)[1].strip())
        return 0


def default_command() -> list[str]:
    return ["npx.cmd" if platform.system() == "Windows" else "npx", "-y", "reddit-mcp-buddy"]


def mcp_config(config: dict[str, Any]) -> dict[str, Any]:
    return config.get("reddit", {}).get("mcp_buddy", {})


def configured_command(config: dict[str, Any]) -> list[str]:
    configured = mcp_config(config).get("command")
    if isinstance(configured, list) and configured:
        return [str(part) for part in configured]
    return default_command()


def run_bridge_calls(calls: list[dict[str, Any]], timeout: int, config: dict[str, Any]) -> list[dict[str, Any]]:
    payload = json.dumps({"calls": calls}, ensure_ascii=False)
    env = UTF8_ENV.copy()
    package_root = mcp_config(config).get("package_root") or os.environ.get("REDDIT_MCP_BUDDY_PACKAGE_ROOT")
    if package_root:
        env["REDDIT_MCP_BUDDY_PACKAGE_ROOT"] = str(package_root)
    result = subprocess.run(
        ["node", str(BRIDGE_PATH)],
        input=payload,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(ROOT),
        env=env,
        timeout=timeout,
        check=False,
    )
    stdout = result.stdout.strip()
    if not stdout:
        stderr = result.stderr.encode("ascii", errors="backslashreplace").decode("ascii")
        raise MCPClientError(f"reddit-mcp-buddy bridge returned no output: {stderr[-1000:]}")
    try:
        parsed = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise MCPClientError(f"reddit-mcp-buddy bridge returned invalid JSON: {exc}: {stdout[:500]}") from exc
    if result.returncode != 0 or parsed.get("error"):
        stderr = result.stderr.encode("ascii", errors="backslashreplace").decode("ascii")
        raise MCPClientError(f"reddit-mcp-buddy bridge failed: {parsed.get('error') or stderr[-1000:]}")
    return list(parsed.get("results", []))


def reddit_permalink(url: str | None) -> str:
    if not url:
        return ""
    return url.replace("https://reddit.com", "https://www.reddit.com")


def normalize_mcp_post(
    post: dict[str, Any],
    subreddit_name: str,
    subreddit_role: str,
    surface: str,
) -> dict[str, Any] | None:
    post_id = post.get("id")
    if not post_id:
        return None
    created_utc = post.get("created_utc") or 0
    try:
        published_at = datetime.fromtimestamp(float(created_utc), tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OSError):
        published_at = None
    permalink = reddit_permalink(post.get("permalink"))
    external_url = post.get("url")
    if external_url == permalink:
        external_url = None
    return {
        "id": str(post_id),
        "title": clean_text(post.get("title")),
        "url": permalink or external_url or "",
        "external_url": external_url,
        "author": post.get("author"),
        "score": int(post.get("score") or 0),
        "upvote_ratio": post.get("upvote_ratio"),
        "num_comments": int(post.get("num_comments") or 0),
        "created_utc": created_utc,
        "published_at": published_at,
        "subreddit": post.get("subreddit") or subreddit_name,
        "subreddit_role": subreddit_role,
        "surface": surface,
        "text": clean_text(post.get("content", ""))[:1200],
    }


def merge_posts(seen: dict[str, dict[str, Any]], posts: list[dict[str, Any]], keywords: list[str]) -> None:
    for post in posts:
        post_id = post.get("id")
        if not post_id:
            continue
        existing = seen.get(post_id)
        if existing and discussion_score(existing, keywords) >= discussion_score(post, keywords):
            continue
        seen[post_id] = post


def collect_posts_via_mcp(config: dict[str, Any]) -> list[dict[str, Any]]:
    reddit_config = config.get("reddit", {})
    buddy_config = mcp_config(config)
    lookback = reddit_config.get("lookback", "day")
    limit = int(reddit_config.get("limit_per_listing", 25))
    query_limit = max(10, limit // 2)
    search_queries_per_subreddit = int(
        buddy_config.get("search_queries_per_subreddit", DEFAULT_SEARCH_QUERIES_PER_SUBREDDIT)
    )
    max_subreddits_per_run = int(buddy_config.get("max_subreddits_per_run", 0) or 0)
    keywords = config.get("discussion_keywords", [])
    seen: dict[str, dict[str, Any]] = {}

    subreddits = reddit_config.get("subreddits", [])
    if max_subreddits_per_run > 0:
        subreddits = subreddits[:max_subreddits_per_run]

    first_pass_calls: list[dict[str, Any]] = []
    for subreddit in subreddits:
        name = subreddit["name"]
        role = subreddit.get("role", "community")
        print(f"Reddit MCP Buddy: queueing r/{name}...")
        for sort, surface in [("top", f"mcp_top_{lookback}"), ("hot", "mcp_hot")]:
            browse_args = {"subreddit": name, "sort": sort, "limit": limit}
            if sort == "top":
                browse_args["time"] = lookback
            first_pass_calls.append(
                {
                    "name": "browse_subreddit",
                    "arguments": browse_args,
                    "meta": {"subreddit": name, "role": role, "surface": surface},
                }
            )
        for query_text in subreddit.get("queries", [])[:search_queries_per_subreddit]:
            first_pass_calls.append(
                {
                    "name": "search_reddit",
                    "arguments": {
                        "query": query_text,
                        "subreddits": [name],
                        "sort": "new",
                        "time": "week",
                        "limit": query_limit,
                    },
                    "meta": {"subreddit": name, "role": role, "surface": f"mcp_search:{query_text}"},
                }
            )

    per_call_timeout = int(buddy_config.get("request_timeout_seconds", DEFAULT_REQUEST_TIMEOUT_SECONDS))
    first_pass_timeout = int(buddy_config.get("startup_timeout_seconds", DEFAULT_STARTUP_TIMEOUT_SECONDS)) + (
        per_call_timeout * max(1, len(first_pass_calls))
    )
    for call, response in zip(first_pass_calls, run_bridge_calls(first_pass_calls, first_pass_timeout, config)):
        meta = call["meta"]
        if not response.get("ok"):
            error_text = response.get("error") or response.get("result", {}).get("text", "")
            MCP_FAILURES.append(f"r/{meta['subreddit']} {meta['surface']}: {error_text}")
            continue
        result = response.get("result", {})
        raw_posts = result.get("posts", []) if call["name"] == "browse_subreddit" else result.get("results", [])
        posts = [
            normalized
            for post in raw_posts
            if (normalized := normalize_mcp_post(post, meta["subreddit"], meta["role"], meta["surface"]))
        ]
        merge_posts(seen, posts, keywords)

    ranked_posts = sorted(seen.values(), key=lambda item: discussion_score(item, keywords), reverse=True)
    max_detail_items = int(buddy_config.get("max_detail_fetch_items", DEFAULT_MAX_DETAIL_FETCH_ITEMS))
    detail_calls = [
        {
            "name": "get_post_details",
            "arguments": {
                "post_id": post["id"],
                "subreddit": post.get("subreddit"),
                "comment_limit": reddit_config.get("comment_limit", 8),
                "comment_sort": "top",
                "comment_depth": 3,
                "max_top_comments": reddit_config.get("comment_limit", 8),
            },
            "meta": {"post_id": post["id"]},
        }
        for post in ranked_posts[:max_detail_items]
    ]
    if detail_calls:
        detail_timeout = int(buddy_config.get("startup_timeout_seconds", DEFAULT_STARTUP_TIMEOUT_SECONDS)) + (
            per_call_timeout * len(detail_calls)
        )
        for post, response in zip(ranked_posts[:max_detail_items], run_bridge_calls(detail_calls, detail_timeout, config)):
            if not response.get("ok"):
                print(
                    "Reddit MCP warning: comments for "
                    f"{post['id']} failed: {response.get('error') or response.get('result', {}).get('text', '')}"
                )
                continue
            details = response.get("result", {})
            post["top_comments"] = [
                {
                    "author": comment.get("author"),
                    "score": comment.get("score", 0),
                    "body": clean_text(comment.get("body", ""))[:700],
                    "url": reddit_permalink(comment.get("permalink")),
                }
                for comment in details.get("top_comments", [])
                if clean_text(comment.get("body", ""))
            ]
            post["discussion_score"] = discussion_score(post, keywords)

    return sorted(seen.values(), key=lambda item: discussion_score(item, keywords), reverse=True)


def parse_rss_datetime(value: str | None) -> str | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc).isoformat()
        except (TypeError, ValueError):
            return None


def atom_text(entry: ET.Element, name: str) -> str:
    node = entry.find(f"{{http://www.w3.org/2005/Atom}}{name}")
    return clean_text(node.text if node is not None else "")


def atom_link(entry: ET.Element) -> str:
    for node in entry.findall("{http://www.w3.org/2005/Atom}link"):
        href = node.attrib.get("href")
        if href:
            return href
    return ""


def atom_author(entry: ET.Element) -> str | None:
    author = entry.find("{http://www.w3.org/2005/Atom}author")
    if author is None:
        return None
    name = author.find("{http://www.w3.org/2005/Atom}name")
    return clean_text(name.text if name is not None else "") or None


def rss_post_id(entry_id: str, link: str) -> str:
    source = entry_id or link
    parts = [part for part in source.rstrip("/").split("/") if part]
    if "comments" in parts:
        index = parts.index("comments")
        if len(parts) > index + 1:
            return parts[index + 1]
    return str(abs(hash(source)))


def fetch_rss_posts(subreddit: dict[str, Any], config: dict[str, Any], surface: str, url: str) -> list[dict[str, Any]]:
    timeout = int(config.get("reddit", {}).get("rss_timeout_seconds", DEFAULT_RSS_TIMEOUT_SECONDS))
    name = subreddit["name"]
    role = subreddit.get("role", "community")
    try:
        response = requests.get(url, headers=RSS_HEADERS, timeout=timeout)
        response.raise_for_status()
    except Exception as exc:
        status_code = getattr(getattr(exc, "response", None), "status_code", None)
        if status_code == 429 or "429" in str(exc):
            RSS_RATE_LIMITS.append(f"r/{name} {surface}")
        else:
            RSS_FAILURES.append(f"r/{name} {surface}: {exc}")
        return []

    try:
        root = ET.fromstring(response.text)
    except ET.ParseError as exc:
        RSS_FAILURES.append(f"r/{name} {surface} parse failed: {exc}")
        return []

    posts: list[dict[str, Any]] = []
    for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
        title = atom_text(entry, "title")
        link = reddit_permalink(atom_link(entry))
        entry_id = atom_text(entry, "id")
        published_at = parse_rss_datetime(atom_text(entry, "published") or atom_text(entry, "updated"))
        if not title or not link:
            continue
        posts.append(
            {
                "id": rss_post_id(entry_id, link),
                "title": title,
                "url": link,
                "external_url": None,
                "author": atom_author(entry),
                "score": 0,
                "upvote_ratio": None,
                "num_comments": 0,
                "created_utc": None,
                "published_at": published_at,
                "subreddit": name,
                "subreddit_role": role,
                "surface": surface,
                "text": atom_text(entry, "content")[:1200],
                "top_comments": [],
            }
        )
    return posts


def collect_posts_via_rss(config: dict[str, Any]) -> list[dict[str, Any]]:
    reddit_config = config.get("reddit", {})
    keywords = config.get("discussion_keywords", [])
    lookback = reddit_config.get("lookback", "day")
    limit = int(reddit_config.get("limit_per_listing", 25))
    search_queries_per_subreddit = int(
        reddit_config.get("rss_search_queries_per_subreddit", DEFAULT_SEARCH_QUERIES_PER_SUBREDDIT)
    )
    seen: dict[str, dict[str, Any]] = {}

    for subreddit in reddit_config.get("subreddits", []):
        name = subreddit["name"]
        print(f"Reddit RSS: scraping r/{name}...")
        urls = [
            ("rss_hot", f"https://www.reddit.com/r/{name}/.rss?limit={limit}"),
            ("rss_top", f"https://www.reddit.com/r/{name}/top/.rss?t={lookback}&limit={limit}"),
        ]
        for query in subreddit.get("queries", [])[:search_queries_per_subreddit]:
            urls.append(
                (
                    f"rss_search:{query}",
                    f"https://www.reddit.com/r/{name}/search.rss?"
                    f"q={quote_plus(query)}&restrict_sr=on&sort=new&t=week&limit={max(10, limit // 2)}",
                )
            )
        for surface, url in urls:
            merge_posts(seen, fetch_rss_posts(subreddit, config, surface, url), keywords)
            time.sleep(float(reddit_config.get("rss_delay_seconds", 0.8)))

    if MCP_FAILURES:
        print(f"Reddit MCP had {len(MCP_FAILURES)} fallback-safe failure(s); RSS fallback remains active.")
    if RSS_RATE_LIMITS:
        print(f"Reddit RSS rate-limited {len(RSS_RATE_LIMITS)} surface(s); collected available surfaces and continued.")
    if RSS_FAILURES:
        print(f"Reddit RSS had {len(RSS_FAILURES)} non-rate-limit failure(s); collected available surfaces and continued.")

    return sorted(seen.values(), key=lambda item: discussion_score(item, keywords), reverse=True)


def write_output(posts: list[dict[str, Any]], discoveries: list[dict[str, Any]], status: str) -> None:
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as file_handle:
        json.dump(
            {
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "collection_status": status,
                "collector": "reddit_mcp_buddy",
                "posts": posts,
                "new_discoveries": discoveries,
            },
            file_handle,
            indent=2,
            ensure_ascii=False,
        )


def preserve_existing_output(existing_output: dict[str, Any], error: str) -> None:
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    existing_output["last_attempted"] = datetime.now(timezone.utc).isoformat()
    existing_output["collection_status"] = "mcp_failed_preserved_previous"
    existing_output["last_error"] = error
    existing_output["collector"] = existing_output.get("collector", "reddit_mcp_buddy")
    with open(OUTPUT_PATH, "w", encoding="utf-8") as file_handle:
        json.dump(existing_output, file_handle, indent=2, ensure_ascii=False)


def run_fallback() -> int:
    print(f"Running Reddit fallback collector: {FALLBACK_SCRIPT}")
    result = subprocess.run(
        python_script_command(FALLBACK_SCRIPT),
        cwd=str(ROOT),
        env=UTF8_ENV,
        check=False,
    )
    return result.returncode


def main() -> int:
    config = load_config()
    if not mcp_config(config).get("enabled", True):
        return run_fallback()

    existing_output = load_existing_output()
    try:
        posts = collect_posts_via_mcp(config)
    except Exception as exc:
        error = f"Reddit MCP Buddy failed: {exc}"
        print(error)
        posts = []
    else:
        error = ""

    rss_posts = collect_posts_via_rss(config)
    if rss_posts:
        merge_posts({post["id"]: post for post in posts}, [], config.get("discussion_keywords", []))
        merged_posts = {post["id"]: post for post in posts}
        merge_posts(merged_posts, rss_posts, config.get("discussion_keywords", []))
        posts = sorted(merged_posts.values(), key=lambda item: discussion_score(item, config.get("discussion_keywords", [])), reverse=True)

    topic_keywords = config.get("topic_keywords", [])
    discoveries = [
        to_discovery(post, config.get("discussion_keywords", []))
        for post in posts
        if has_topic_signal(post, topic_keywords)
    ]

    if not posts and not discoveries:
        posts = collect_posts_via_rss(config)
        if posts:
            discoveries = [
                to_discovery(post, config.get("discussion_keywords", []))
                for post in posts
                if has_topic_signal(post, topic_keywords)
            ]
            write_output(posts, discoveries, "rss_fallback_ok")
            print(f"Done. Reddit RSS fallback saved {len(posts)} posts and {len(discoveries)} discoveries to {OUTPUT_PATH}")
            return 0
        if run_fallback() == 0:
            return 0
        if existing_output:
            preserve_existing_output(existing_output, error or "Reddit MCP Buddy and RSS returned zero posts/discoveries.")
            return 0
        write_output([], [], "mcp_live_empty")
        return 0

    status = "mcp_rss_live_ok" if rss_posts else "mcp_live_ok"
    write_output(posts, discoveries, status)
    print(f"Done. Reddit collector saved {len(posts)} posts and {len(discoveries)} discoveries to {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
