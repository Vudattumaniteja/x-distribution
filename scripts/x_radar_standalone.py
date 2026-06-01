import json
import argparse
from datetime import datetime, timezone

from source_clis import WORKSPACE_ROOT
from xcli_utils import collect_home_tweets, collect_timeline_tweets

# The high-signal technical keywords we search for across all of X
# min_faves:100 filters out spam and guarantees algorithmic validation
QUERIES = [
    '"new SOTA" OR "state of the art" min_faves:100',
    '"beats GPT-4" OR "beats Claude 3" min_faves:100',
    '"million context" OR "12M context" min_faves:100',
    '"new architecture" OR "linear attention" min_faves:100',
    '"open weights" OR "open source model" min_faves:200'
]

CONFIG_PATH = WORKSPACE_ROOT / "config" / "followed_accounts.json"
OUTPUT_PATH = WORKSPACE_ROOT / "data" / "x_radar_standalone.json"
CACHE_DIR = WORKSPACE_ROOT / "cache"


def run_xcli_scrape(handle, count=30, days=7):
    """
    Invokes the pinned local XCLI for home-feed or timeline scraping.
    """
    print(f"  Executing XCLI scrape for: @{handle}")
    try:
        if handle.lower() == "home":
            return collect_home_tweets(count, CACHE_DIR / "xcli_radar_home.json")
        return collect_timeline_tweets(
            handle,
            days=days,
            output_path=CACHE_DIR / f"xcli_radar_{handle}.json",
        )[:count]
    except Exception as e:
        print(f"    -> Scrape failed for {handle}: {e}")
        return []


def selected_accounts(accounts, tiers, max_accounts):
    allowed_tiers = set(tiers or [])
    selected = [
        account
        for account in accounts
        if not allowed_tiers or account.get("tier") in allowed_tiers
    ]
    if max_accounts:
        return selected[:max_accounts]
    return selected


def main():
    parser = argparse.ArgumentParser(description="Collect X radar signals through the pinned local XCLI.")
    parser.add_argument("--days", type=float, default=7.0, help="Timeline lookback window in days")
    parser.add_argument("--home-count", type=int, default=30, help="Home-feed tweet count")
    parser.add_argument("--per-account", type=int, default=10, help="Maximum tweets per account")
    parser.add_argument("--max-accounts", type=int, help="Safety cap on watchlist accounts")
    parser.add_argument(
        "--tiers",
        nargs="*",
        default=["must_follow"],
        help="Account tiers to scan; default: must_follow",
    )
    parser.add_argument("--skip-home", action="store_true", help="Skip the flaky algorithmic home feed route")
    args = parser.parse_args()

    print("Scanning X for 'X-ray' discoveries...")
    all_discoveries = []
    
    # 1. Algorithmic Home Feed (The Pulse)
    if not args.skip_home:
        print("Step 1: Scraping Home Feed...")
        home_discoveries = run_xcli_scrape("home", count=args.home_count)
        for d in home_discoveries:
            d['signal_source'] = "home_feed"
            all_discoveries.append(d)
    else:
        print("Step 1: Home Feed skipped.")
        
    # 2. Followed Accounts (The Experts)
    print("Step 2: Scraping Followed Accounts...")
    try:
        with CONFIG_PATH.open('r', encoding="utf-8") as f:
            config = json.load(f)
            accounts = config.get('accounts', [])
            
        for acc in selected_accounts(accounts, args.tiers, args.max_accounts):
            handle = acc['handle'].replace('@', '')
            print(f"  -> Processing @{handle}...")
            account_tweets = run_xcli_scrape(handle, count=args.per_account, days=args.days)
            for t in account_tweets:
                t['signal_source'] = f"watchlist_{handle}"
                t['account_category'] = acc.get('category', 'unknown')
                t['account_tier'] = acc.get('tier', 'unknown')
                all_discoveries.append(t)
    except Exception as e:
        print(f"Error reading followed accounts: {e}")
            
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open('w', encoding='utf-8') as f:
        json.dump({
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "collection_policy": {
                "days": args.days,
                "home_count": args.home_count,
                "per_account": args.per_account,
                "max_accounts": args.max_accounts,
                "tiers": args.tiers,
                "skip_home": args.skip_home,
            },
            "total_discoveries": len(all_discoveries),
            "new_discoveries": all_discoveries
        }, f, indent=2)
    
    print(f"Done. Saved {len(all_discoveries)} total X-Radar discoveries to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
