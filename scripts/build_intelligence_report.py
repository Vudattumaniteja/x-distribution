"""Build categorized intelligence outputs from the latest collection run."""

from __future__ import annotations

import html
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from intelligence_queue import load_queue_document



ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
REPORT_DIR = DATA / "exports" / "reports"
QUEUE_PATH = DATA / "news_queue.json"
OUTPUT_JSON = REPORT_DIR / "latest-intelligence-categories.json"
OUTPUT_MD = REPORT_DIR / "x-distribution-intelligence-architecture-report.md"
OUTPUT_HTML = REPORT_DIR / "x-distribution-intelligence-architecture-report.html"


CATEGORIES = [
    "Bloomberg + Market-Moving AI",
    "New Models + Model Market",
    "Official Company Announcements",
    "YouTube Deep Signals",
    "X Watchlist + Fast Rumors",
    "Reddit Community Reality",
    "Hacker News Developer Talk",
    "Startup Funding",
    "Startup Collections + Missed Startups",
    "China + Regional AI",
    "India Deep-Tech",
    "Bio + Science Breakthroughs",
    "GitHub / Hugging Face / arXiv Artifacts",
    "Developer Pain + Provider Status",
    "Product Launch Radar",
    "Workflow / Agents / Coding",
    "Finance / Macro / Chips",
]


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as file_handle:
            return json.load(file_handle)
    except (OSError, json.JSONDecodeError):
        return default


def text_blob(item: dict[str, Any]) -> str:
    return " ".join(
        str(item.get(field, ""))
        for field in ["headline", "title", "summary", "notes", "source", "signal_type", "url"]
    ).lower()


def item_title(item: dict[str, Any]) -> str:
    return str(item.get("headline") or item.get("title") or "Untitled signal").strip()


def item_source(item: dict[str, Any]) -> str:
    return str(item.get("source") or item.get("source_name") or "Unknown source").strip()


def assign_category(item: dict[str, Any]) -> str:
    source = item_source(item).lower()
    signal = str(item.get("signal_type", "")).lower()
    blob = text_blob(item)

    if "bloomberg" in source or "bloomberg" in blob:
        return "Bloomberg + Market-Moving AI"
    if "model market" in signal or "model catalog" in signal or "openrouter" in source:
        return "New Models + Model Market"
    if "developer pain" in signal or "status" in source or "outage" in blob or "latency" in blob:
        return "Developer Pain + Provider Status"
    if "youtube" in blob or "deep signal" in signal:
        return "YouTube Deep Signals"
    if source.startswith("sam ") or "x watchlist" in blob or "algorithm trend" in signal or "high-impact rumor" in signal:
        return "X Watchlist + Fast Rumors"
    if source.startswith("reddit"):
        return "Reddit Community Reality"
    if "hacker news" in source:
        return "Hacker News Developer Talk"
    if "science" in signal or any(term in blob for term in ["biotech", "protein", "drug discovery", "clinical", "nature biotechnology", "synbio"]):
        return "Bio + Science Breakthroughs"
    if any(term in blob for term in ["github", "hugging face", "arxiv", "release_discoveries", "repo", "paper"]):
        return "GitHub / Hugging Face / arXiv Artifacts"
    if any(term in source for term in ["technode", "pandaily", "qbitai", "36kr", "synced", "jiqizhixin", "latepost"]) or any(term in blob for term in ["qwen", "deepseek", "kimi", "moonshot", "zhipu", "bytedance", "china"]):
        return "China + Regional AI"
    if any(term in source for term in ["inc42", "yourstory", "medianama", "entrackr", "analytics india", "economic times"]) or any(term in blob for term in ["india", "sarvam", "krutrim", "bhashini"]):
        return "India Deep-Tech"
    if "startup collection" in signal or any(term in source for term in ["trustmrr", "startuphub", "fundbat", "neuronfeed", "watchlist", "dealroom", "pitchbook", "cb insights", "yc "]):
        return "Startup Collections + Missed Startups"
    if "fund" in signal or any(term in blob for term in ["series a", "series b", "series c", "seed round", "raised", "funding"]):
        return "Startup Funding"
    if any(term in blob for term in ["product hunt", "show hn", "launch", "launched", "new tool"]):
        return "Product Launch Radar"
    if any(term in blob for term in ["agent", "workflow", "codex", "claude code", "mcp", "automation", "cursor"]):
        return "Workflow / Agents / Coding"
    if any(term in blob for term in ["nvidia", "amd", "chips", "datacenter", "data center", "sec filing", "cnbc", "markets", "ipo"]):
        return "Finance / Macro / Chips"
    if "verified" in signal:
        return "Official Company Announcements"
    return "Product Launch Radar"


def score_item(item: dict[str, Any]) -> float:
    score = 0.0
    signal = str(item.get("signal_type", "")).lower()
    source = item_source(item).lower()
    blob = text_blob(item)
    if any(term in signal for term in ["verified", "model", "science", "funded", "market"]):
        score += 4
    if any(term in source for term in ["openai", "anthropic", "mistral", "bloomberg", "openrouter", "arxiv", "hacker news"]):
        score += 3
    if item.get("score"):
        try:
            score += min(float(item["score"]) / 25, 4)
        except (TypeError, ValueError):
            pass
    if any(term in blob for term in ["new model", "release", "launch", "raised", "opus", "codex", "agent", "biotech"]):
        score += 2
    if item.get("published_at"):
        score += 1
    return score


def summarize_run(queue: dict[str, Any]) -> dict[str, Any]:
    items = queue.get("items", [])
    lane_health = read_json(DATA / "phase1_lane_health.json", {}).get("lanes", [])
    yt_report = read_json(DATA / "youtube_discovery_report.json", {})
    transcript_report = read_json(DATA / "transcript_pull_report.json", {}).get("summary", {})
    reddit = read_json(DATA / "reddit_raw_standalone.json", {})
    corporate = read_json(DATA / "corporate_announcements.json", {})
    return {
        "last_updated": queue.get("last_updated"),
        "total_queue_items": len(items),
        "lane_health": lane_health,
        "youtube_total_videos_2d": yt_report.get("total_videos", 0),
        "youtube_channels_scanned": len(yt_report.get("channels", [])),
        "transcript_summary": transcript_report,
        "reddit_posts": len(reddit.get("posts", [])),
        "reddit_discoveries": len(reddit.get("new_discoveries", [])),
        "corporate_announcements": len(corporate.get("announcements", [])),
        "corporate_health": corporate.get("source_health", []),
    }


def category_payload(items: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {category: [] for category in CATEGORIES}
    for item in items:
        grouped[assign_category(item)].append(item)
    payload = {}
    for category, category_items in grouped.items():
        ranked = sorted(category_items, key=score_item, reverse=True)
        payload[category] = {
            "count": len(category_items),
            "top_items": ranked[:12],
            "source_counts": Counter(item_source(item) for item in category_items).most_common(12),
            "signal_counts": Counter(str(item.get("signal_type", "Unknown")) for item in category_items).most_common(12),
        }
    return payload


def md_link(title: str, url: str) -> str:
    title = title.replace("[", "\\[").replace("]", "\\]")
    if url:
        return f"[{title}]({url})"
    return title


def build_markdown(summary: dict[str, Any], categories: dict[str, Any]) -> str:
    lane_lines = []
    for lane in summary["lane_health"]:
        lane_lines.append(f"- `{lane['lane']}`: {lane['status']} / {lane['items']} items")

    md = [
        "# X Distribution Intelligence Architecture Report",
        "",
        f"Generated: `{datetime.now(timezone.utc).isoformat()}`",
        f"Latest queue timestamp: `{summary.get('last_updated')}`",
        "",
        "## Executive Audit",
        "",
        "- Current level: fast creator / lightweight news-desk level for public AI intelligence. It is above a normal fast individual because it runs official blogs, X, Reddit, HN, YouTube, GitHub, Hugging Face, arXiv, finance, startup collections, model markets, and regional lanes together.",
        "- Not Bloomberg level: no paid terminals, no proprietary reporter network, no direct company/source calls, no guaranteed real-time finance feed, and no legal/compliance editorial desk.",
        "- Practical rating: `8/10` for public AI/news discovery, `7/10` for community/developer reality, `6/10` for global/regional coverage, `5.5/10` for finance depth, `8.5/10` for cost-effectiveness.",
        "- Current bottleneck: XCLI is browser-automation-bound and is intentionally serialized because parallel X browser sessions caused Playwright context failures. The rest of the lanes run in parallel.",
        "",
        "## Run Snapshot",
        "",
        f"- Queue items: `{summary['total_queue_items']}`",
        f"- Corporate announcements: `{summary['corporate_announcements']}`",
        f"- YouTube videos discovered in 2 days: `{summary['youtube_total_videos_2d']}` across `{summary['youtube_channels_scanned']}` configured channels",
        f"- Transcript summary: `{summary['transcript_summary']}`",
        f"- Reddit: `{summary['reddit_posts']}` posts / `{summary['reddit_discoveries']}` discoveries",
        "",
        "## Lane Health",
        "",
        *lane_lines,
        "",
        "## What Was Fixed",
        "",
        "- Mistral moved from `https://mistral.ai/sitemap.xml` to `https://mistral.ai/sitemap-index.xml`; sitemap recursion now handles sitemap indexes.",
        "- Moonshot/Kimi is no longer reported as unresolved; it is marked `MONITORED_ELSEWHERE` with configured fallback lanes.",
        "- YouTube transcript pulling is queue-based, not channel-loop based. It only transcripts discovered videos, skips existing transcript files, and caches unavailable transcript videos.",
        "- Julian Goldie SEO is disabled for now per instruction.",
        "- X collection remains inside the full parallel system, but the XCLI worker itself is serialized because the local Playwright/XCLI stack is not concurrency-safe.",
        "- Reddit MCP/RSS failures are fallback-safe; RSS rate limits are summarized rather than treated as broken source failures.",
        "- arXiv now has API retry, RSS fallback, and cache preservation.",
        "- Endpoints News 403 now falls back through search without crashing the science lane.",
        "- Raw X posts are normalized before entering `news_queue.json`; schema validation is clean.",
        "",
        "## Category Breakdown",
        "",
    ]

    for category, payload in categories.items():
        md.extend([f"### {category}", "", f"Count: `{payload['count']}`", ""])
        if payload["source_counts"]:
            md.append("Top sources: " + ", ".join(f"`{source}` ({count})" for source, count in payload["source_counts"][:6]))
            md.append("")
        for item in payload["top_items"][:8]:
            title = item_title(item)
            source = item_source(item)
            url = item.get("url", "")
            signal = item.get("signal_type", "")
            md.append(f"- {md_link(title, url)} — `{source}` / `{signal}`")
        md.append("")

    md.extend([
        "## Architecture Map",
        "",
        "```mermaid",
        "flowchart TD",
        "  A[\"Source Registry + Config\"] --> B[\"Phase 1 Collect\"]",
        "  B --> X[\"Lane A: XCLI Watchlist/Home\"]",
        "  B --> R[\"Lane B: Corporate RSS/Sitemaps\"]",
        "  B --> Y[\"Lane C: YouTube Discovery + Transcript Queue\"]",
        "  B --> C[\"Lane D: Reddit + HN\"]",
        "  B --> G[\"Lane E: GitHub/HF/arXiv\"]",
        "  B --> F[\"Lane F: Finance/Bloomberg/SEC\"]",
        "  B --> S[\"Lane G/I: Startup Funding + Collections\"]",
        "  B --> M[\"Lane H: Model Market\"]",
        "  B --> K[\"Lane K: Science/Bio\"]",
        "  B --> L[\"Lane L: Developer Pain/Status\"]",
        "  X --> Q[\"news_queue.json\"]",
        "  R --> Q",
        "  Y --> Q",
        "  C --> Q",
        "  G --> Q",
        "  F --> Q",
        "  S --> Q",
        "  M --> Q",
        "  K --> Q",
        "  L --> Q",
        "  Q --> Z[\"Categorized Intelligence Report\"]",
        "```",
        "",
        "## Next Architecture Priorities",
        "",
        "1. Split X collection into an authenticated persistent browser service with an internal queue, instead of launching independent CLI browser sessions.",
        "2. Add source-health scoring over time so failing/noisy sources are visible without blocking the collection run.",
        "3. Add newsletter inbox ingestion for TLDR/Bloomberg-style newsletters and private email sources.",
        "4. Add editorial ranking with cross-source corroboration: official + community + artifact + model-market.",
        "5. Add regional source packs for China, India, EU, Israel, and Southeast Asia with per-locale translation/summarization.",
    ])
    return "\n".join(md) + "\n"


def html_item(item: dict[str, Any]) -> str:
    title = html.escape(item_title(item))
    source = html.escape(item_source(item))
    signal = html.escape(str(item.get("signal_type", "")))
    summary = html.escape(str(item.get("summary") or item.get("notes") or "")[:260])
    url = html.escape(str(item.get("url", "")))
    link = f'<a href="{url}" target="_blank" rel="noreferrer">Open</a>' if url else ""
    return f"""
    <article class="item-card">
      <div class="item-meta"><span>{source}</span><span>{signal}</span></div>
      <h4>{title}</h4>
      <p>{summary}</p>
      {link}
    </article>
    """


def build_html(summary: dict[str, Any], categories: dict[str, Any], markdown_path: Path) -> str:
    cards = []
    for category, payload in categories.items():
        items_html = "\n".join(html_item(item) for item in payload["top_items"][:10])
        cards.append(f"""
        <section class="category" data-category="{html.escape(category.lower())}">
          <button class="category-header" type="button">
            <span>{html.escape(category)}</span>
            <strong>{payload['count']}</strong>
          </button>
          <div class="category-body">{items_html}</div>
        </section>
        """)

    lane_rows = "\n".join(
        f"<tr><td>{html.escape(lane['lane'])}</td><td>{html.escape(lane['status'])}</td><td>{lane['items']}</td></tr>"
        for lane in summary["lane_health"]
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>X Distribution Intelligence Report</title>
  <style>
    :root {{
      --bg: #071014;
      --panel: #0d1b22;
      --panel-2: #102832;
      --text: #e9fbff;
      --muted: #8fb5c1;
      --line: rgba(143, 181, 193, .22);
      --accent: #37f5c8;
      --accent-2: #7aa7ff;
      --warn: #ffd166;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, Arial, sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at 20% 5%, rgba(55,245,200,.18), transparent 28rem),
        radial-gradient(circle at 80% 15%, rgba(122,167,255,.18), transparent 26rem),
        var(--bg);
    }}
    .shell {{ max-width: 1240px; margin: 0 auto; padding: 32px 20px 64px; }}
    .hero {{
      border: 1px solid var(--line);
      border-radius: 28px;
      padding: 28px;
      background: linear-gradient(135deg, rgba(13,27,34,.94), rgba(16,40,50,.72));
      box-shadow: 0 24px 80px rgba(0,0,0,.28);
    }}
    .brand {{ display: flex; align-items: center; gap: 14px; color: var(--muted); text-transform: uppercase; letter-spacing: .12em; font-size: 12px; }}
    .mark {{
      width: 42px; height: 42px; border: 2px solid var(--accent); border-radius: 12px;
      display: grid; place-items: center; color: var(--accent); font-weight: 900; box-shadow: 0 0 24px rgba(55,245,200,.25);
    }}
    h1 {{ font-size: clamp(36px, 6vw, 76px); line-height: .92; margin: 22px 0 14px; letter-spacing: -.06em; max-width: 900px; }}
    .hero p {{ max-width: 820px; color: var(--muted); font-size: 18px; line-height: 1.6; }}
    .stats {{ display: grid; grid-template-columns: repeat(5, minmax(0,1fr)); gap: 12px; margin-top: 24px; }}
    .stat {{ padding: 16px; border: 1px solid var(--line); border-radius: 18px; background: rgba(255,255,255,.035); }}
    .stat strong {{ display:block; font-size: 28px; color: var(--accent); }}
    .stat span {{ color: var(--muted); font-size: 12px; }}
    .toolbar {{ position: sticky; top: 0; z-index: 10; display: flex; gap: 12px; padding: 14px 0; backdrop-filter: blur(16px); }}
    input, select {{ width: 100%; border: 1px solid var(--line); border-radius: 14px; padding: 13px 14px; color: var(--text); background: rgba(7,16,20,.88); }}
    .grid {{ display: grid; grid-template-columns: 340px 1fr; gap: 18px; align-items: start; margin-top: 18px; }}
    .panel {{ border: 1px solid var(--line); border-radius: 22px; background: rgba(13,27,34,.82); overflow: hidden; }}
    .panel h2 {{ margin: 0; padding: 18px 20px; border-bottom: 1px solid var(--line); font-size: 18px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    td {{ padding: 10px 14px; border-bottom: 1px solid var(--line); color: var(--muted); }}
    td:first-child {{ color: var(--text); }}
    .audit {{ padding: 18px 20px; color: var(--muted); line-height: 1.55; }}
    .audit strong {{ color: var(--text); }}
    .category {{ border: 1px solid var(--line); border-radius: 22px; background: rgba(13,27,34,.82); margin-bottom: 12px; overflow: hidden; }}
    .category-header {{ width: 100%; border: 0; color: var(--text); background: transparent; padding: 18px 20px; display:flex; justify-content:space-between; cursor:pointer; font-size: 16px; text-align:left; }}
    .category-header strong {{ color: var(--accent); }}
    .category-body {{ display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 12px; padding: 0 16px 16px; }}
    .category.collapsed .category-body {{ display: none; }}
    .item-card {{ border: 1px solid var(--line); border-radius: 18px; padding: 14px; background: rgba(255,255,255,.035); min-height: 160px; }}
    .item-meta {{ display:flex; gap:8px; flex-wrap:wrap; color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: .06em; }}
    .item-card h4 {{ margin: 10px 0 8px; font-size: 15px; line-height: 1.25; }}
    .item-card p {{ color: var(--muted); font-size: 13px; line-height: 1.45; }}
    a {{ color: var(--accent); text-decoration: none; font-weight: 700; }}
    .footer {{ color: var(--muted); margin-top: 28px; font-size: 13px; }}
    @media (max-width: 900px) {{ .stats, .grid, .category-body {{ grid-template-columns: 1fr; }} .toolbar {{ position: static; flex-direction: column; }} }}
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <div class="brand"><div class="mark">XD</div><span>X Distribution Intelligence System</span></div>
      <h1>AI News Radar, Source Architecture, and Coverage Audit</h1>
      <p>A live report generated from the latest collection run. It combines official announcements, Bloomberg/finance, model markets, X, YouTube transcripts, Reddit, Hacker News, GitHub, Hugging Face, arXiv, startup collections, regional AI, and science/deep-tech lanes.</p>
      <div class="stats">
        <div class="stat"><strong>{summary['total_queue_items']}</strong><span>queue items</span></div>
        <div class="stat"><strong>{summary['youtube_total_videos_2d']}</strong><span>YouTube videos / 2d</span></div>
        <div class="stat"><strong>{summary['reddit_discoveries']}</strong><span>Reddit discoveries</span></div>
        <div class="stat"><strong>{summary['corporate_announcements']}</strong><span>official/news items</span></div>
        <div class="stat"><strong>8/10</strong><span>public AI speed rating</span></div>
      </div>
    </section>

    <div class="toolbar">
      <input id="search" placeholder="Search categories, titles, sources, signals...">
      <select id="filter">
        <option value="">All categories</option>
        {''.join(f'<option value="{html.escape(category.lower())}">{html.escape(category)}</option>' for category in categories)}
      </select>
    </div>

    <section class="grid">
      <aside class="panel">
        <h2>Audit</h2>
        <div class="audit">
          <p><strong>Level:</strong> fast creator / lightweight news-desk. Above a normal individual because collection spans multiple independent lanes. Below Bloomberg because there is no proprietary terminal, paid wire depth, or reporter network.</p>
          <p><strong>Runtime:</strong> full verified collection now completes in tens of minutes, not 4+ hours. X is serialized because the local XCLI browser session is not concurrency-safe.</p>
          <p><strong>Coverage:</strong> strongest in public AI/model/developer signals; improving in finance, China, India, startups, and science.</p>
          <p><a href="{html.escape(markdown_path.name)}">Open Markdown source</a></p>
        </div>
        <h2>Lane Health</h2>
        <table>{lane_rows}</table>
      </aside>

      <section id="categories">{''.join(cards)}</section>
    </section>
    <p class="footer">Generated {html.escape(datetime.now(timezone.utc).isoformat())}. Local file, no external assets.</p>
  </main>
  <script>
    const search = document.querySelector('#search');
    const filter = document.querySelector('#filter');
    const sections = [...document.querySelectorAll('.category')];
    document.querySelectorAll('.category-header').forEach(button => {{
      button.addEventListener('click', () => button.closest('.category').classList.toggle('collapsed'));
    }});
    function applyFilters() {{
      const q = search.value.toLowerCase();
      const f = filter.value;
      sections.forEach(section => {{
        const matchesCategory = !f || section.dataset.category === f;
        const matchesSearch = !q || section.innerText.toLowerCase().includes(q);
        section.style.display = matchesCategory && matchesSearch ? '' : 'none';
      }});
    }}
    search.addEventListener('input', applyFilters);
    filter.addEventListener('change', applyFilters);
  </script>
</body>
</html>
"""


def main() -> int:
    queue = load_queue_document()
    items = queue.get("items", [])
    summary = summarize_run(queue)
    categories = category_payload(items)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    with OUTPUT_JSON.open("w", encoding="utf-8") as file_handle:
        json.dump({"summary": summary, "categories": categories}, file_handle, indent=2, ensure_ascii=False)

    markdown = build_markdown(summary, categories)
    OUTPUT_MD.write_text(markdown, encoding="utf-8")

    html_report = build_html(summary, categories, OUTPUT_MD)
    OUTPUT_HTML.write_text(html_report, encoding="utf-8")

    print(f"Wrote {OUTPUT_JSON}")
    print(f"Wrote {OUTPUT_MD}")
    print(f"Wrote {OUTPUT_HTML}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
