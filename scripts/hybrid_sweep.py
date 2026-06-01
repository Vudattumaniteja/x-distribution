import subprocess
import sys
import os
from datetime import datetime, timezone

SCRIPTS = [
    "scripts/github_releases_discovery.py",
    "scripts/corporate_rss_discovery.py",
    "scripts/reddit_scraper_standalone.py",
    "scripts/sitemap_sentinel_standalone.py",
    "scripts/hf_tracker_standalone.py",
    "scripts/github_monitor_standalone.py",
    "scripts/hn_scraper_standalone.py",
    "scripts/arxiv_sentinel_standalone.py",
    "scripts/x_radar_standalone.py",
    "scripts/aggregate_deep_discovery.py"
]

def run_script(script_path):
    print(f"Executing {script_path}...")
    try:
        result = subprocess.run([sys.executable, script_path], capture_output=True, text=True, check=True)
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR executing {script_path}:")
        print(e.stderr)
        return False

def main():
    print(f"Starting Hardened Hybrid Discovery Sweep at {datetime.now(timezone.utc).isoformat()}")
    print("-" * 50)
    
    success_count = 0
    failures = []
    
    for script in SCRIPTS:
        if run_script(script):
            success_count += 1
        else:
            failures.append(script)
            
    print("-" * 50)
    print(f"Sweep complete. Success: {success_count}/{len(SCRIPTS)}")
    if failures:
        print(f"Failures encountered in: {', '.join(failures)}")
        sys.exit(1)
    else:
        print("All Phase 1 discovery scripts completed successfully.")

if __name__ == "__main__":
    main()
