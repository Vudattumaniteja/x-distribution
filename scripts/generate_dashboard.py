"""Dashboard generator for X Distribution updates."""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
QUEUE_PATH = WORKSPACE_ROOT / "data" / "news_queue.json"
HEALTH_PATH = WORKSPACE_ROOT / "data" / "phase1_lane_health.json"
OUTPUT_PATH = WORKSPACE_ROOT / "dashboard.html"

# Default fallback values if files don't exist
DEFAULT_HEALTH = {
    "last_updated": datetime.now(timezone.utc).isoformat(),
    "lane_workers": 5,
    "lanes": []
}
DEFAULT_QUEUE = {
    "last_updated": datetime.now(timezone.utc).isoformat(),
    "total_items": 0,
    "items": []
}

def load_data():
    # Load health stats
    if HEALTH_PATH.exists():
        try:
            with HEALTH_PATH.open("r", encoding="utf-8") as f:
                health = json.load(f)
        except Exception as e:
            print(f"Error loading health data: {e}", file=sys.stderr)
            health = DEFAULT_HEALTH
    else:
        print("Warning: phase1_lane_health.json not found, using default.", file=sys.stderr)
        health = DEFAULT_HEALTH

    # Load news queue
    if QUEUE_PATH.exists():
        try:
            with QUEUE_PATH.open("r", encoding="utf-8") as f:
                queue = json.load(f)
        except Exception as e:
            print(f"Error loading news queue data: {e}", file=sys.stderr)
            queue = DEFAULT_QUEUE
    else:
        print("Warning: news_queue.json not found, using default.", file=sys.stderr)
        queue = DEFAULT_QUEUE

    return health, queue

def format_timestamp(ts_str):
    if not ts_str:
        return "Unknown Date"
    try:
        # Strip Z or +00:00 and parse
        ts_clean = ts_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(ts_clean)
        # Format as e.g., "Jun 1, 2026, 11:46 AM"
        return dt.strftime("%b %d, %Y, %I:%M %p")
    except Exception:
        return ts_str

def main():
    health, queue = load_data()
    
    # Process items to ensure safety and clean up keys
    processed_items = []
    for item in queue.get("items", []):
        processed_items.append({
            "url": item.get("url") or "#",
            "headline": item.get("headline") or "Untitled Signal",
            "summary": item.get("summary") or item.get("primary_text") or "",
            "source": item.get("source") or "Unknown Source",
            "signal_type": item.get("signal_type") or "System Alert",
            "notes": item.get("notes") or "",
            "published_at": format_timestamp(item.get("published_at")),
            "published_at_raw": item.get("published_at") or "",
            "score": item.get("score"),
            "region": item.get("source_region") or item.get("region") or "",
        })

    # Sort processed items by published_at_raw (descending)
    processed_items.sort(key=lambda x: x["published_at_raw"], reverse=True)

    # HTML template incorporating Sandoz color palette, /impeccable, /design-taste-frontend
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>X Distribution - Intelligence Dashboard</title>
    <!-- Premium Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700&family=Geist:wght@300;400;500;600&family=Geist+Mono:wght@400;500&display=swap" rel="stylesheet">
    <!-- Phosphor Icons -->
    <link rel="stylesheet" type="text/css" href="https://unpkg.com/@phosphor-icons/web@2.1.1/src/regular/style.css" />
    <link rel="stylesheet" type="text/css" href="https://unpkg.com/@phosphor-icons/web@2.1.1/src/bold/style.css" />
    
    <style>
        /* Design Read: 
           Reading this as: Intelligence Operations Dashboard for technical content creators, 
           using a clean Sandoz Light Theme, leaning toward Outfit Display, Geist Body, and 
           strict CSS Grid Bento-box layout.
           
           Three Dials Configuration:
           DESIGN_VARIANCE: 6 (Clean asymmetric grid)
           MOTION_INTENSITY: 4 (Tactile interactive micro-motion)
           VISUAL_DENSITY: 5 (Readable information density with monospace numbers)
        */

        :root {{
            /* Color Palette: Sandoz Corporate (Light Theme) */
            --sandoz-prussian-blue: #001C4A;
            --sandoz-yellow-orange: #FCB13B;
            --bg-page: #F4F7FC; /* Cool light ice background */
            --bg-card: #FFFFFF; /* Crisp white cards */
            --border-color: rgba(0, 28, 74, 0.1); /* Subtle prussian blue border tint */
            --border-hover: rgba(0, 28, 74, 0.25);
            --text-primary: #001C4A; /* Prussian blue headers */
            --text-body: #1E293B; /* High-contrast slate body copy */
            --text-muted: #64748B; /* Secondary label text */
            
            /* Typography */
            --font-display: 'Outfit', -apple-system, BlinkMacSystemFont, sans-serif;
            --font-body: 'Geist', -apple-system, BlinkMacSystemFont, sans-serif;
            --font-mono: 'Geist Mono', monospace;
            
            /* Spacing & Transitions */
            --radius-card: 16px;
            --radius-pill: 9999px;
            --transition-smooth: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: var(--font-body);
            background-color: var(--bg-page);
            color: var(--text-body);
            line-height: 1.6;
            min-height: 100dvh;
            padding-bottom: 5rem;
            -webkit-font-smoothing: antialiased;
        }}

        /* Navigation Header */
        header.dashboard-header {{
            background: var(--bg-card);
            border-bottom: 1px solid var(--border-color);
            padding: 1.25rem 2rem;
            position: sticky;
            top: 0;
            z-index: 100;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}

        .brand-section {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }}

        .brand-logo {{
            width: 2.25rem;
            height: 2.25rem;
            background: var(--sandoz-prussian-blue);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--sandoz-yellow-orange);
            font-weight: 700;
            font-size: 1.2rem;
            font-family: var(--font-display);
        }}

        .brand-title {{
            font-family: var(--font-display);
            font-size: 1.25rem;
            font-weight: 700;
            color: var(--sandoz-prussian-blue);
            letter-spacing: -0.02em;
        }}

        .header-meta {{
            display: flex;
            align-items: center;
            gap: 1.5rem;
        }}

        .status-badge-wrapper {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.85rem;
            font-weight: 500;
            color: var(--text-muted);
        }}

        .status-indicator {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: #22C55E;
            animation: pulse-glow 2s infinite ease-in-out;
        }}

        @keyframes pulse-glow {{
            0%, 100% {{
                transform: scale(1);
                opacity: 0.8;
                box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.4);
            }}
            50% {{
                transform: scale(1.2);
                opacity: 1;
                box-shadow: 0 0 0 4px rgba(34, 197, 94, 0.2);
            }}
        }}

        .timestamp-box {{
            font-family: var(--font-mono);
            font-size: 0.8rem;
            background: rgba(0, 28, 74, 0.05);
            padding: 0.35rem 0.75rem;
            border-radius: var(--radius-pill);
            color: var(--sandoz-prussian-blue);
            font-weight: 500;
        }}

        /* Main Layout Wrapper */
        main.dashboard-container {{
            max-w: 1400px;
            margin: 2rem auto;
            padding: 0 1.5rem;
            display: flex;
            flex-direction: column;
            gap: 2rem;
        }}

        /* Split-screen Hero and Filters Section */
        .hero-split {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 2rem;
            align-items: stretch;
        }}

        @media (max-width: 900px) {{
            .hero-split {{
                grid-template-columns: 1fr;
            }}
        }}

        .hero-left {{
            display: flex;
            flex-direction: column;
            justify-content: center;
        }}

        .hero-title {{
            font-family: var(--font-display);
            font-size: 3rem;
            line-height: 1.1;
            font-weight: 700;
            color: var(--sandoz-prussian-blue);
            letter-spacing: -0.03em;
            margin-bottom: 0.75rem;
        }}

        .hero-description {{
            font-size: 1.05rem;
            color: var(--text-body);
            max-width: 55ch;
            margin-bottom: 1.5rem;
        }}

        .hero-right {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-card);
            padding: 2rem;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            gap: 1.5rem;
            box-shadow: 0 10px 30px -10px rgba(0, 28, 74, 0.04);
        }}

        .search-container {{
            position: relative;
        }}

        .search-input {{
            width: 100%;
            padding: 1rem 1rem 1rem 3rem;
            border: 1px solid var(--border-color);
            border-radius: var(--radius-card);
            background: var(--bg-page);
            color: var(--text-primary);
            font-family: var(--font-body);
            font-size: 1rem;
            outline: none;
            transition: var(--transition-smooth);
        }}

        .search-input:focus {{
            border-color: var(--sandoz-prussian-blue);
            background: var(--bg-card);
            box-shadow: 0 0 0 3px rgba(0, 28, 74, 0.08);
        }}

        .search-icon-inside {{
            position: absolute;
            left: 1.1rem;
            top: 50%;
            transform: translateY(-50%);
            color: var(--sandoz-prussian-blue);
            font-size: 1.25rem;
            pointer-events: none;
        }}

        /* Lanes Health Board */
        .health-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
            gap: 0.75rem;
            width: 100%;
        }}

        .health-chip {{
            background: var(--bg-page);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 0.75rem;
            display: flex;
            flex-direction: column;
            gap: 0.25rem;
            transition: var(--transition-smooth);
            cursor: pointer;
        }}

        .health-chip:hover {{
            border-color: var(--sandoz-prussian-blue);
            transform: translateY(-2px);
        }}

        .health-chip.active-filter {{
            background: var(--sandoz-prussian-blue);
            border-color: var(--sandoz-prussian-blue);
            color: #FFFFFF;
        }}

        .health-chip.active-filter .lane-name {{
            color: #FFFFFF;
        }}

        .health-chip.active-filter .lane-meta {{
            color: var(--sandoz-yellow-orange);
        }}

        .lane-name {{
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-primary);
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}

        .lane-meta {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-family: var(--font-mono);
            font-size: 0.85rem;
            font-weight: 500;
            color: var(--text-muted);
        }}

        .lane-indicator {{
            width: 6px;
            height: 6px;
            border-radius: 50%;
        }}

        .indicator-ok {{ background-color: #22C55E; }}
        .indicator-partial {{ background-color: #FCB13B; }}
        .indicator-error {{ background-color: #EF4444; }}

        /* Statistics Bento Panel */
        .stats-bento {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1.5rem;
        }}

        @media (max-width: 768px) {{
            .stats-bento {{
                grid-template-columns: 1fr;
            }}
        }}

        .stat-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-card);
            padding: 1.5rem;
            display: flex;
            align-items: center;
            gap: 1.25rem;
            box-shadow: 0 8px 24px -8px rgba(0, 28, 74, 0.03);
        }}

        .stat-icon {{
            width: 3rem;
            height: 3rem;
            background: rgba(0, 28, 74, 0.05);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--sandoz-prussian-blue);
            font-size: 1.5rem;
        }}

        .stat-data {{
            display: flex;
            flex-direction: column;
        }}

        .stat-value {{
            font-family: var(--font-mono);
            font-size: 1.75rem;
            font-weight: 600;
            color: var(--text-primary);
            line-height: 1.1;
        }}

        .stat-label {{
            font-size: 0.85rem;
            color: var(--text-muted);
            font-weight: 500;
        }}

        /* Feed Columns / Asymmetric Grid */
        .feed-layout {{
            display: grid;
            grid-template-columns: 3fr 1.25fr;
            gap: 2rem;
            align-items: start;
        }}

        @media (max-width: 1024px) {{
            .feed-layout {{
                grid-template-columns: 1fr;
            }}
        }}

        /* Filter Controls */
        .filter-toolbar {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-card);
            padding: 0.75rem;
            margin-bottom: 1.5rem;
            align-items: center;
            box-shadow: 0 4px 12px -4px rgba(0, 28, 74, 0.02);
        }}

        .filter-label-text {{
            font-size: 0.85rem;
            font-weight: 600;
            color: var(--sandoz-prussian-blue);
            margin-left: 0.5rem;
            margin-right: 0.5rem;
        }}

        .filter-btn {{
            background: transparent;
            border: 1px solid transparent;
            padding: 0.4rem 1rem;
            border-radius: 10px;
            font-family: var(--font-body);
            font-size: 0.85rem;
            font-weight: 500;
            cursor: pointer;
            color: var(--text-muted);
            transition: var(--transition-smooth);
        }}

        .filter-btn:hover {{
            background: rgba(0, 28, 74, 0.04);
            color: var(--sandoz-prussian-blue);
        }}

        .filter-btn:active {{
            transform: scale(0.97);
        }}

        .filter-btn.active-filter {{
            background: rgba(0, 28, 74, 0.08);
            border-color: rgba(0, 28, 74, 0.15);
            color: var(--sandoz-prussian-blue);
            font-weight: 600;
        }}

        /* Signal Items Stream */
        .stream-container {{
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }}

        .signal-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-card);
            padding: 1.5rem;
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
            transition: var(--transition-smooth);
            position: relative;
            box-shadow: 0 4px 12px -6px rgba(0, 28, 74, 0.02);
        }}

        .signal-card:hover {{
            border-color: var(--sandoz-prussian-blue);
            box-shadow: 0 8px 24px -10px rgba(0, 28, 74, 0.06);
            transform: translateY(-1px);
        }}

        .signal-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 1rem;
        }}

        .signal-source-badge {{
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            font-size: 0.8rem;
            font-weight: 600;
            color: var(--sandoz-prussian-blue);
            background: rgba(0, 28, 74, 0.05);
            padding: 0.25rem 0.75rem;
            border-radius: var(--radius-pill);
            text-transform: capitalize;
        }}

        .signal-type-tag {{
            font-family: var(--font-mono);
            font-size: 0.7rem;
            font-weight: 600;
            color: #FFFFFF;
            background: var(--sandoz-prussian-blue);
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            letter-spacing: 0.02em;
        }}

        /* Color Coding based on signal types */
        .type-verified {{ background-color: var(--sandoz-prussian-blue); }}
        .type-deep-signal {{ background-color: #7C3AED; }}
        .type-rumor {{ background-color: #D97706; }}
        .type-market {{ background-color: #059669; }}
        .type-research {{ background-color: #2563EB; }}
        .type-community {{ background-color: #DB2777; }}

        .signal-meta-right {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
            font-size: 0.8rem;
            color: var(--text-muted);
        }}

        .signal-score-badge {{
            font-family: var(--font-mono);
            font-weight: 600;
            color: var(--sandoz-yellow-orange);
            background: rgba(252, 177, 59, 0.1);
            border: 1px solid rgba(252, 177, 59, 0.3);
            padding: 0.15rem 0.4rem;
            border-radius: 4px;
        }}

        .signal-headline {{
            font-family: var(--font-display);
            font-size: 1.25rem;
            font-weight: 700;
            color: var(--sandoz-prussian-blue);
            line-height: 1.3;
            letter-spacing: -0.01em;
            text-decoration: none;
            transition: var(--transition-smooth);
        }}

        .signal-headline:hover {{
            color: var(--sandoz-yellow-orange);
        }}

        .signal-summary {{
            font-size: 0.95rem;
            color: var(--text-body);
            white-space: pre-wrap;
            max-width: 75ch; /* strict line-length limit for legibility */
        }}

        .signal-footer {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-top: 1px solid rgba(0, 28, 74, 0.04);
            padding-top: 0.75rem;
            margin-top: 0.25rem;
            font-size: 0.8rem;
            color: var(--text-muted);
        }}

        .signal-author {{
            display: flex;
            align-items: center;
            gap: 0.4rem;
            font-weight: 500;
            color: var(--text-body);
        }}

        .signal-action-btn {{
            display: inline-flex;
            align-items: center;
            gap: 0.3rem;
            color: var(--sandoz-prussian-blue);
            text-decoration: none;
            font-weight: 600;
            transition: var(--transition-smooth);
        }}

        .signal-action-btn:hover {{
            color: var(--sandoz-yellow-orange);
            transform: translateX(2px);
        }}

        /* Sidebar: Radar, announcements, settings */
        .sidebar-container {{
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
            position: sticky;
            top: 6rem;
        }}

        .sidebar-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-card);
            padding: 1.5rem;
            box-shadow: 0 4px 12px -4px rgba(0, 28, 74, 0.02);
        }}

        .sidebar-title {{
            font-family: var(--font-display);
            font-size: 1.1rem;
            font-weight: 700;
            color: var(--sandoz-prussian-blue);
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 0.5rem;
        }}

        /* Watchlist list items */
        .watchlist-item-list {{
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
        }}

        .watchlist-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.85rem;
        }}

        .watchlist-handle {{
            font-weight: 500;
            color: var(--text-body);
            text-decoration: none;
        }}

        .watchlist-handle:hover {{
            color: var(--sandoz-yellow-orange);
        }}

        .watchlist-status-pill {{
            font-size: 0.75rem;
            font-family: var(--font-mono);
            padding: 0.15rem 0.5rem;
            border-radius: 4px;
            font-weight: 500;
        }}

        .badge-live-ok {{
            background: rgba(34, 197, 94, 0.1);
            color: #16A34A;
        }}

        .badge-cached {{
            background: rgba(252, 177, 59, 0.1);
            color: #D97706;
        }}

        .badge-missing {{
            background: rgba(239, 68, 68, 0.1);
            color: #DC2626;
        }}

        /* Empty states / Loader */
        .empty-state {{
            background: var(--bg-card);
            border: 2px dashed var(--border-color);
            border-radius: var(--radius-card);
            padding: 3rem;
            text-align: center;
            color: var(--text-muted);
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 1rem;
        }}

        .empty-icon {{
            font-size: 2.5rem;
            color: var(--sandoz-prussian-blue);
            opacity: 0.5;
        }}

        /* Pagination & Utility */
        .load-more-btn {{
            display: block;
            width: 100%;
            padding: 1rem;
            background: var(--sandoz-prussian-blue);
            color: #FFFFFF;
            border: none;
            border-radius: var(--radius-card);
            font-family: var(--font-body);
            font-weight: 600;
            cursor: pointer;
            transition: var(--transition-smooth);
            text-align: center;
            box-shadow: 0 4px 12px rgba(0, 28, 74, 0.1);
        }}

        .load-more-btn:hover {{
            background: #002B73;
            box-shadow: 0 6px 16px rgba(0, 28, 74, 0.15);
        }}

        .load-more-btn:active {{
            transform: scale(0.98);
        }}
    </style>
</head>
<body>

    <!-- Header Navigation -->
    <header class="dashboard-header">
        <div class="brand-section">
            <div class="brand-logo">X</div>
            <div class="brand-title">X Distribution Operations</div>
        </div>
        <div class="header-meta">
            <div class="status-badge-wrapper">
                <div class="status-indicator"></div>
                System Active
            </div>
            <div class="timestamp-box" id="system-time">
                Last collection: {format_timestamp(health.get("last_updated"))}
            </div>
        </div>
    </header>

    <main class="dashboard-container">
        
        <!-- Asymmetric Hero Section -->
        <section class="hero-split">
            <div class="hero-left">
                <h1 class="hero-title">Aggregated Intelligence Feed</h1>
                <p class="hero-description">
                    Real-time technical alerts, verified macro updates, and startup discoveries aggregated across our active multi-worker operations.
                </p>
                <div class="stats-bento">
                    <div class="stat-card">
                        <div class="stat-icon"><i class="ph ph-database-bold"></i></div>
                        <div class="stat-data">
                            <span class="stat-value">{queue.get("total_items", 0)}</span>
                            <span class="stat-label">Active Queue Items</span>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon"><i class="ph ph-activity-bold"></i></div>
                        <div class="stat-data">
                            <span class="stat-value">{len([l for l in health.get("lanes", []) if l.get("status") == "OK" or l.get("status") == "PARTIAL"])}</span>
                            <span class="stat-label">Active Signal Lanes</span>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon"><i class="ph ph-browsers-bold"></i></div>
                        <div class="stat-data">
                            <span class="stat-value">{health.get("lane_workers", 5)}</span>
                            <span class="stat-label">Concurrency Slots</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="hero-right">
                <div class="search-container">
                    <i class="ph ph-magnifying-glass search-icon-inside"></i>
                    <input type="text" class="search-input" id="search-box" placeholder="Search signals, technologies, funding rounds..." oninput="handleSearch()">
                </div>
                
                <div>
                    <h3 style="font-family: var(--font-display); font-size: 0.9rem; font-weight: 700; color: var(--sandoz-prussian-blue); margin-bottom: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em;">Lanes Control</h3>
                    <div class="health-grid" id="health-grid-target">
                        <!-- Filled dynamically -->
                    </div>
                </div>
            </div>
        </section>

        <!-- Feed Toolbar and Items Stream -->
        <section class="feed-layout">
            <div>
                <!-- Category Toolbar -->
                <div class="filter-toolbar">
                    <span class="filter-label-text">Filter Signals:</span>
                    <button class="filter-btn active-filter" onclick="filterCategory('all', this)">All Signals</button>
                    <button class="filter-btn" onclick="filterCategory('verified', this)">Announcements</button>
                    <button class="filter-btn" onclick="filterCategory('finance', this)">Finance/Macro</button>
                    <button class="filter-btn" onclick="filterCategory('startup', this)">Startups</button>
                    <button class="filter-btn" onclick="filterCategory('research', this)">Research/Papers</button>
                    <button class="filter-btn" onclick="filterCategory('model', this)">OpenRouter/Models</button>
                    <button class="filter-btn" onclick="filterCategory('community', this)">Community</button>
                    <button class="filter-btn" onclick="filterCategory('x', this)">X watchlists</button>
                </div>

                <!-- Main Updates Stream -->
                <div class="stream-container" id="updates-stream">
                    <!-- Cards will be populated here -->
                </div>
                
                <div style="margin-top: 2rem;">
                    <button class="load-more-btn" id="load-more" onclick="loadMore()">Load More Updates</button>
                </div>
            </div>

            <!-- Sidebar: X watchlists, stats, system metadata -->
            <div class="sidebar-container">
                
                <!-- X Watchlist Status -->
                <div class="sidebar-card">
                    <h3 class="sidebar-title"><i class="ph ph-twitter-logo-bold"></i> X Watchlist status</h3>
                    <div class="watchlist-item-list" id="watchlist-status-list">
                        <!-- Populated dynamically -->
                    </div>
                </div>

                <!-- Technical Details -->
                <div class="sidebar-card">
                    <h3 class="sidebar-title"><i class="ph ph-cpu-bold"></i> Runner parameters</h3>
                    <div style="display: flex; flex-direction: column; gap: 0.5rem; font-size: 0.85rem;">
                        <div style="display: flex; justify-content: space-between;"><span style="color: var(--text-muted);">Operation:</span><span style="font-weight:500;">Phase 1 Collect</span></div>
                        <div style="display: flex; justify-content: space-between;"><span style="color: var(--text-muted);">Cache Duration (X):</span><span style="font-family: var(--font-mono);">48 Hours</span></div>
                        <div style="display: flex; justify-content: space-between;"><span style="color: var(--text-muted);">Lookback (YouTube):</span><span style="font-family: var(--font-mono);">2 Days</span></div>
                        <div style="display: flex; justify-content: space-between;"><span style="color: var(--text-muted);">Protected Queue:</span><span style="font-family: var(--font-mono);">data/news_queue.json</span></div>
                    </div>
                </div>
            </div>
        </section>

    </main>

    <!-- Embedded Data Payload -->
    <script>
        const healthData = {json.dumps(health, ensure_ascii=False)};
        const streamItems = {json.dumps(processed_items, ensure_ascii=False)};
        
        let currentFilter = 'all';
        let searchQuery = '';
        let itemsLimit = 20;

        function populateHealthGrid() {{
            const grid = document.getElementById('health-grid-target');
            grid.innerHTML = '';
            
            healthData.lanes.forEach(lane => {{
                const card = document.createElement('div');
                card.className = 'health-chip';
                card.onclick = () => {{
                    // Quick filter based on clicking health chips
                    const buttons = document.querySelectorAll('.filter-btn');
                    let targetCategory = 'all';
                    if (lane.lane === 'x') targetCategory = 'x';
                    else if (lane.lane === 'rss') targetCategory = 'verified';
                    else if (lane.lane === 'community') targetCategory = 'community';
                    else if (lane.lane === 'artifact_research') targetCategory = 'research';
                    else if (lane.lane === 'finance') targetCategory = 'finance';
                    else if (lane.lane === 'startup_funding' || lane.lane === 'startup_collections') targetCategory = 'startup';
                    else if (lane.lane === 'model_market') targetCategory = 'model';
                    
                    // Click the matching category button
                    for (let btn of buttons) {{
                        if (btn.getAttribute('onclick').includes(targetCategory)) {{
                            btn.click();
                            break;
                        }}
                    }}
                }};
                
                let indicatorClass = 'indicator-ok';
                if (lane.status === 'PARTIAL') indicatorClass = 'indicator-partial';
                else if (lane.status === 'FAILED' || lane.status === 'ERROR') indicatorClass = 'indicator-error';
                
                card.innerHTML = `
                    <div class="lane-name" title="${{lane.lane}}">${{lane.lane}}</div>
                    <div class="lane-meta">
                        <span>${{lane.items}}</span>
                        <div class="lane-indicator ${{indicatorClass}}"></div>
                    </div>
                `;
                grid.appendChild(card);
            }});
        }}

        function populateWatchlistStatus() {{
            const list = document.getElementById('watchlist-status-list');
            list.innerHTML = '';
            
            const xLane = healthData.lanes.find(l => l.lane === 'x');
            if (!xLane) {{
                list.innerHTML = '<div style="color: var(--text-muted); font-size: 0.85rem;">No X Watchlist data available.</div>';
                return;
            }}
            
            // Map statuses
            const successes = xLane.watchlist_live_successes || [];
            const cached = xLane.watchlist_cached_accounts || [];
            const missing = xLane.watchlist_missing_accounts || [];
            
            const allHandles = [...successes.map(h => ({{ handle: h, status: 'LIVE_OK' }})), 
                                ...cached.map(h => ({{ handle: h, status: 'CACHED' }})), 
                                ...missing.map(h => ({{ handle: h, status: 'MISSING' }}))];
                                
            if (allHandles.length === 0) {{
                list.innerHTML = '<div style="color: var(--text-muted); font-size: 0.85rem;">No watchlist accounts scanned.</div>';
                return;
            }}

            // Sort alphabetically
            allHandles.sort((a, b) => a.handle.localeCompare(b.handle));

            allHandles.forEach(acc => {{
                const row = document.createElement('div');
                row.className = 'watchlist-item';
                
                let badgeClass = 'badge-live-ok';
                let label = 'Live';
                if (acc.status === 'CACHED') {{
                    badgeClass = 'badge-cached';
                    label = 'Cache';
                }} else if (acc.status === 'MISSING') {{
                    badgeClass = 'badge-missing';
                    label = 'Offline';
                }}
                
                row.innerHTML = `
                    <a href="https://x.com/${{acc.handle}}" target="_blank" class="watchlist-handle">@${{acc.handle}}</a>
                    <span class="watchlist-status-pill ${{badgeClass}}">${{label}}</span>
                `;
                list.appendChild(row);
            }});
        }}

        function getSignalColorClass(type) {{
            const t = type.toLowerCase();
            if (t.includes('verified')) return 'type-verified';
            if (t.includes('deep') || t.includes('youtube')) return 'type-deep-signal';
            if (t.includes('rumor') || t.includes('trend')) return 'type-rumor';
            if (t.includes('market') || t.includes('model')) return 'type-market';
            if (t.includes('research') || t.includes('arxiv') || t.includes('github') || t.includes('paper')) return 'type-research';
            if (t.includes('community') || t.includes('reddit') || t.includes('hacker')) return 'type-community';
            return '';
        }}

        function renderStream() {{
            const stream = document.getElementById('updates-stream');
            
            // Filter logic
            let filtered = streamItems.filter(item => {{
                // Category Filter
                let matchesCategory = true;
                if (currentFilter !== 'all') {{
                    const st = item.signal_type.toLowerCase();
                    const note = item.notes.toLowerCase();
                    const src = item.source.toLowerCase();
                    
                    if (currentFilter === 'verified') {{
                        matchesCategory = st.includes('verified') && note.includes('corporate');
                    }} else if (currentFilter === 'finance') {{
                        matchesCategory = st.includes('market') || st.includes('finance');
                    }} else if (currentFilter === 'startup') {{
                        matchesCategory = st.includes('startup') || note.includes('funding');
                    }} else if (currentFilter === 'research') {{
                        matchesCategory = st.includes('research') || note.includes('github') || note.includes('arxiv');
                    }} else if (currentFilter === 'model') {{
                        matchesCategory = st.includes('model');
                    }} else if (currentFilter === 'community') {{
                        matchesCategory = note.includes('reddit') || note.includes('hacker') || note.includes('community');
                    }} else if (currentFilter === 'x') {{
                        matchesCategory = note.includes('watchlist');
                    }}
                }}
                
                // Search query filter
                let matchesSearch = true;
                if (searchQuery) {{
                    const term = searchQuery.toLowerCase();
                    matchesSearch = (
                        item.headline.toLowerCase().includes(term) ||
                        item.summary.toLowerCase().includes(term) ||
                        item.source.toLowerCase().includes(term) ||
                        item.signal_type.toLowerCase().includes(term) ||
                        item.notes.toLowerCase().includes(term)
                    );
                }}
                
                return matchesCategory && matchesSearch;
            }});

            if (filtered.length === 0) {{
                stream.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-icon"><i class="ph ph-magnifying-glass-bold"></i></div>
                        <h3 style="font-family: var(--font-display); font-weight:700; color: var(--sandoz-prussian-blue);">No matching signals</h3>
                        <p>Try refining your search terms or selecting another lane category.</p>
                    </div>
                `;
                document.getElementById('load-more').style.display = 'none';
                return;
            }}

            // Pagination slice
            const paginated = filtered.slice(0, itemsLimit);
            
            stream.innerHTML = '';
            paginated.forEach(item => {{
                const card = document.createElement('div');
                card.className = 'signal-card';
                
                let scoreBadge = '';
                if (item.score !== null && item.score !== undefined) {{
                    scoreBadge = `<span class="signal-score-badge">Relevance: ${{item.score}}</span>`;
                }}
                
                let regionBadge = '';
                if (item.region) {{
                    regionBadge = `<span style="font-family: var(--font-mono); font-size: 0.75rem; background: rgba(0, 28, 74, 0.04); padding: 0.15rem 0.5rem; border-radius: 4px;">${{item.region}}</span>`;
                }}

                card.innerHTML = `
                    <div class="signal-header">
                        <div style="display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center;">
                            <span class="signal-source-badge">${{item.notes || 'Signal'}}</span>
                            <span class="signal-type-tag ${{getSignalColorClass(item.signal_type)}}">${{item.signal_type}}</span>
                            ${{regionBadge}}
                        </div>
                        <div class="signal-meta-right">
                            ${{scoreBadge}}
                            <span>${{item.published_at}}</span>
                        </div>
                    </div>
                    <a href="${{item.url}}" target="_blank" class="signal-headline">${{item.headline}}</a>
                    <p class="signal-summary">${{item.summary}}</p>
                    <div class="signal-footer">
                        <div class="signal-author">
                            <i class="ph ph-user-circle-bold"></i>
                            <span>${{item.source}}</span>
                        </div>
                        <a href="${{item.url}}" target="_blank" class="signal-action-btn">
                            View Source <i class="ph ph-arrow-up-right-bold"></i>
                        </a>
                    </div>
                `;
                stream.appendChild(card);
            }});

            // Toggle show/hide for load more button
            if (filtered.length > itemsLimit) {{
                document.getElementById('load-more').style.display = 'block';
            }} else {{
                document.getElementById('load-more').style.display = 'none';
            }}
        }}

        function filterCategory(category, buttonEl) {{
            // Toggle active filter button style
            document.querySelectorAll('.filter-btn').forEach(btn => {{
                btn.classList.remove('active-filter');
            }});
            buttonEl.classList.add('active-filter');
            
            currentFilter = category;
            itemsLimit = 20; // reset pagination
            renderStream();
        }}

        function handleSearch() {{
            searchQuery = document.getElementById('search-box').value;
            itemsLimit = 20; // reset pagination
            renderStream();
        }}

        function loadMore() {{
            itemsLimit += 20;
            renderStream();
        }}

        // Run Initializers
        populateHealthGrid();
        populateWatchlistStatus();
        renderStream();
    </script>
</body>
</html>
"""

    OUTPUT_PATH.write_text(html_content, encoding="utf-8")
    print(f"Successfully compiled dashboard. html data into {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
