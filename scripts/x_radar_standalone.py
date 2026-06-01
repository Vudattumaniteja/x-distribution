import json
import argparse
import sys
from datetime import datetime, timezone

from source_clis import WORKSPACE_ROOT
from source_registry import collection_runtime_policy
from x_collection_coordinator import collect_x_read_only

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
    parser.add_argument("--workers", type=int, help="Concurrent watchlist timeline workers; default: registry x_workers")
    parser.add_argument(
        "--tiers",
        nargs="*",
        default=["must_follow"],
        help="Account tiers to scan; default: must_follow",
    )
    parser.add_argument("--skip-home", action="store_true", help="Skip the flaky algorithmic home feed route")
    args = parser.parse_args()
    workers = max(1, args.workers or int(collection_runtime_policy().get("x_workers", 3)))

    print("Scanning X for 'X-ray' discoveries...")
    all_discoveries = []
    print("Step 1: Running shared home + watchlist coordinator...")
    try:
        with CONFIG_PATH.open('r', encoding="utf-8") as f:
            config = json.load(f)
            accounts = config.get('accounts', [])
            
        selected = selected_accounts(accounts, args.tiers, args.max_accounts)
        accounts_by_handle = {
            acc['handle'].replace('@', '').lower(): acc
            for acc in selected
        }
        result = collect_x_read_only(
            accounts_by_handle,
            workers=workers,
            days=args.days,
            home_count=args.home_count,
            skip_home=args.skip_home,
        )
        per_account_counts = {}
        for t in result["tweets"]:
            scope = t.get("_x_collection_scope", "")
            if scope == "home":
                t["signal_source"] = "home_feed"
            else:
                handle = scope.partition(":")[2]
                count = per_account_counts.get(handle, 0)
                if count >= args.per_account:
                    continue
                per_account_counts[handle] = count + 1
                acc = accounts_by_handle.get(handle, {})
                t["signal_source"] = f"watchlist_{handle}"
                t['account_category'] = acc.get('category', 'unknown')
                t['account_tier'] = acc.get('tier', 'unknown')
            all_discoveries.append(t)
    except Exception as e:
        print(f"Error reading followed accounts: {e}")
        return 1
            
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open('w', encoding='utf-8') as f:
        json.dump({
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "run_id": result["run_id"],
            "status": result["status"],
            "collection_policy": {
                "days": args.days,
                "home_count": args.home_count,
                "per_account": args.per_account,
                "max_accounts": args.max_accounts,
                "tiers": args.tiers,
                "skip_home": args.skip_home,
                "watchlist_workers": workers,
            },
            "total_discoveries": len(all_discoveries),
            "new_discoveries": all_discoveries
        }, f, indent=2)
    
    print(f"Done. Saved {len(all_discoveries)} total X-Radar discoveries to {OUTPUT_PATH}")
    return 1 if result["status"] == "FAILED" else 0

if __name__ == "__main__":
    sys.exit(main())
