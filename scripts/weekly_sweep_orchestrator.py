import subprocess
from datetime import datetime, timezone, timedelta
from source_clis import python_script_command
from xcli_utils import collect_home_tweets

def run_weekly_sweep():
    # 7-day lookback window
    DAYS = 7
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=DAYS)
    print(f"--- Weekly Deep Dive Initiated (Cutoff: {cutoff_date.strftime('%Y-%m-%d')}) ---")

    # 1. Lane A: X Feed (Home + Watchlist)
    print("\n[Layer 1/2] Scraping X (50 Home Tweets + Watchlist)...")
    home_tweets = collect_home_tweets(50, "data/weekly_x_home.json")
    print(f"  -> collected {len(home_tweets)} home-feed tweets via XCLI")
    
    # 2. Lane B: Corporate RSS (7-day window)
    print("\n[Layer 3] Polling Corporate RSS & Sitemaps...")
    subprocess.run(python_script_command('corporate_rss_discovery.py'), check=False)

    # 3. Lane C: YouTube (Full 7-day sweep for 24 channels)
    print("\n[Layer 2] Executing YT Transcript latest discovery...")
    subprocess.run(python_script_command('orchestrate_videos.py'), check=False)
    subprocess.run(python_script_command('orchestrate_all_latest.py'), check=False)

    # 4. Final Aggregation
    print("\n[Aggregation] Building Weekly Intelligence Pool...")
    # Trigger the Phase 1 script but with the 7-day data already staged
    # We modify phase1_collect.py briefly to handle the pool merge
    subprocess.run(python_script_command('phase1_collect.py'), check=False)

if __name__ == "__main__":
    run_weekly_sweep()
