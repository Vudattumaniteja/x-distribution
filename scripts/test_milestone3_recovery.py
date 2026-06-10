"""Unit tests verifying Milestone 3 (R2) Robust Recovery loops for X and YouTube."""

import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

from x_collection_coordinator import XCollectionCoordinator, XNotifier
from orchestrate_videos import scan_channel, YouTubeNotifier, parse_youtube_rss

NOW = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)

def tweet(url: str, **extra) -> dict:
    return {"url": url, "text": url, **extra}

class TestXStaleCacheFallback(unittest.TestCase):
    def test_watchlist_stale_cache_fallback(self):
        # Create temp dir for paths
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            status_path = root / "status.json"
            cache_dir = root / "cache"
            lock_path = cache_dir / "x_collection.lock"
            notification_path = root / "notifications.jsonl"
            
            # Setup stale cache file (50 hours old, limit is 48)
            cache_dir.mkdir(parents=True, exist_ok=True)
            handle = "elonmusk"
            cache_file = cache_dir / f"xcli_timeline_{handle}.json"
            cached_tweets = [tweet(f"https://x.com/{handle}/status/123", text="stale tweet data")]
            cache_file.write_text(json.dumps(cached_tweets), encoding="utf-8")
            
            # Set mtime to 50 hours ago
            mtime = (NOW - timedelta(hours=50)).timestamp()
            os.utime(cache_file, (mtime, mtime))
            
            # timeline_collector raises exception (live fetch fail)
            def failing_timeline_collector(*args, **opts):
                raise RuntimeError("Timeout or connection failed")
                
            coordinator = XCollectionCoordinator(
                home_collector=lambda *args, **opts: [],
                timeline_collector=failing_timeline_collector,
                slot_releaser=lambda: True,
                status_path=status_path,
                cache_dir=cache_dir,
                lock_path=lock_path,
                notification_path=notification_path,
                now=lambda: NOW,
            )
            
            # Run collection for the handle
            result = coordinator.collect([handle], skip_home=True)
            
            # Verify result status and fallback usage
            self.assertEqual(result["status"], "DEGRADED_OK")
            self.assertEqual(len(result["tweets"]), 1)
            self.assertEqual(result["tweets"][0]["text"], "stale tweet data")
            self.assertEqual(result["tweets"][0]["_x_collection_source"], "cache")
            self.assertEqual(result["watchlist_cached_accounts"], [handle])
            self.assertEqual(result["watchlist_missing_accounts"], [])
            
            # Verify notification log contains stale_cache_fallback
            self.assertTrue(notification_path.exists())
            notifications = [json.loads(line) for line in notification_path.read_text(encoding="utf-8").splitlines()]
            self.assertTrue(any(n["type"] == "stale_cache_fallback" for n in notifications))
            
            stale_notif = next(n for n in notifications if n["type"] == "stale_cache_fallback")
            self.assertEqual(stale_notif["severity"], "WARN")
            self.assertEqual(stale_notif["handle"], handle)
            self.assertGreater(stale_notif["cache_age_hours"], 48.0)

    def test_home_stale_cache_fallback(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            status_path = root / "status.json"
            cache_dir = root / "cache"
            lock_path = cache_dir / "x_collection.lock"
            notification_path = root / "notifications.jsonl"
            
            # Setup stale home cache file (30 hours old, limit is 24)
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file = cache_dir / "xcli_home.json"
            cached_tweets = [tweet("https://x.com/home/status/456", text="stale home data")]
            cache_file.write_text(json.dumps(cached_tweets), encoding="utf-8")
            mtime = (NOW - timedelta(hours=30)).timestamp()
            os.utime(cache_file, (mtime, mtime))
            
            # home_collector raises exception (live fetch fail)
            def failing_home_collector(*args, **opts):
                raise RuntimeError("Live home scrape timeout")
                
            coordinator = XCollectionCoordinator(
                home_collector=failing_home_collector,
                timeline_collector=lambda *args, **opts: [],
                slot_releaser=lambda: True,
                status_path=status_path,
                cache_dir=cache_dir,
                lock_path=lock_path,
                notification_path=notification_path,
                now=lambda: NOW,
            )
            
            # Run collection
            result = coordinator.collect([], skip_home=False)
            
            # Verify result status and fallback usage
            self.assertEqual(result["status"], "DEGRADED_OK")
            self.assertEqual(result["home_feed_status"], "CACHE")
            self.assertEqual(len(result["tweets"]), 1)
            self.assertEqual(result["tweets"][0]["text"], "stale home data")
            
            # Verify notification log contains stale_cache_fallback for home
            self.assertTrue(notification_path.exists())
            notifications = [json.loads(line) for line in notification_path.read_text(encoding="utf-8").splitlines()]
            self.assertTrue(any(n["type"] == "stale_cache_fallback" for n in notifications))
            
            stale_notif = next(n for n in notifications if n["type"] == "stale_cache_fallback")
            self.assertEqual(stale_notif["severity"], "WARN")
            self.assertIn("home-feed", stale_notif["reason"])


class TestYouTubeResilientScanning(unittest.TestCase):
    @patch("urllib.request.urlopen")
    def test_youtube_resilient_stages(self, mock_urlopen):
        # Set up a mock XML response for RSS Option B
        mock_rss_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns:yt="http://www.youtube.com/xml/schemas/2015" xmlns="http://www.w3.org/2005/Atom">
            <entry>
                <yt:videoId>rss_vid_123</yt:videoId>
                <title>RSS Fallback Title</title>
                <published>2026-06-01T10:00:00+00:00</published>
                <link rel="alternate" href="https://www.youtube.com/watch?v=rss_vid_123"/>
            </entry>
        </feed>
        """
        mock_response = MagicMock()
        mock_response.read.return_value = mock_rss_xml.encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Mock yt_cli that fails
        mock_yt_cli = MagicMock()
        mock_yt_cli.get_latest_videos.side_effect = RuntimeError("yt-dlp command timed out")

        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup notification file path in temp dir
            log_path = Path(temp_dir) / "youtube_channel_notifications.jsonl"
            notifier = YouTubeNotifier("test-run-123", path=log_path, now=lambda: NOW)
            
            name = "TestChannel"
            config = {"channel_id": "UCtest123"}
            profiles = {name: {"priority": "P0"}}
            
            # Call scan_channel (Option A fails, Option B RSS succeeds)
            videos, health = scan_channel(
                mock_yt_cli, name, config, profiles, days=2, max_scan_per_channel=500, notifier=notifier
            )
            
            # Verify RSS fallback results
            if health["status"] != "OK":
                print("\nHEALTH DICT FOR DEBUGGING:", health)
            self.assertEqual(health["status"], "OK")
            self.assertEqual(health["fallback_used"], "rss")
            self.assertEqual(len(videos), 1)
            self.assertEqual(videos[0]["video_id"], "rss_vid_123")
            self.assertEqual(videos[0]["title"], "RSS Fallback Title")
            
            # Verify warning notification logged
            self.assertTrue(log_path.exists())
            notifications = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
            self.assertTrue(any(n["type"] == "youtube_rss_fallback" for n in notifications))
            
            rss_notif = next(n for n in notifications if n["type"] == "youtube_rss_fallback")
            self.assertEqual(rss_notif["severity"], "WARN")
            self.assertEqual(rss_notif["channel"], name)
            self.assertEqual(rss_notif["channel_id"], "UCtest123")
            self.assertIn("yt-dlp failed", rss_notif["reason"])

    @patch("urllib.request.urlopen")
    @patch("orchestrate_videos.WORKSPACE_ROOT")
    def test_youtube_cache_fallback_as_last_resort(self, mock_workspace, mock_urlopen):
        # Option A (yt-dlp) and Option B (RSS) both fail
        mock_yt_cli = MagicMock()
        mock_yt_cli.get_latest_videos.side_effect = RuntimeError("yt-dlp connection failed")
        mock_urlopen.side_effect = RuntimeError("RSS request failed")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            mock_workspace.resolve.return_value = temp_root
            # Override WORKSPACE_ROOT properties
            from orchestrate_videos import WORKSPACE_ROOT
            
            # Setup local cache file (Option C)
            channel_id = "UCcache123"
            cache_file = temp_root / "cache" / f"youtube_channel_{channel_id}.json"
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cached_videos = [
                {
                    "video_id": "cached_vid_999",
                    "title": "Cached Old Video",
                    "published_at": "2026-05-15T00:00:00+00:00", # very old, past 2 days lookback
                    "url": "https://www.youtube.com/watch?v=cached_vid_999"
                }
            ]
            cache_file.write_text(json.dumps(cached_videos), encoding="utf-8")
            
            log_path = temp_root / "logs" / "youtube_channel_notifications.jsonl"
            notifier = YouTubeNotifier("test-run-456", path=log_path, now=lambda: NOW)
            
            name = "CacheChannel"
            config = {"channel_id": channel_id}
            profiles = {name: {"priority": "P1"}}
            
            # Set mocked workspace root in orchestrate_videos
            with patch("orchestrate_videos.WORKSPACE_ROOT", temp_root):
                videos, health = scan_channel(
                    mock_yt_cli, name, config, profiles, days=2, max_scan_per_channel=500, notifier=notifier
                )
            
            # Verify cache fallback results
            self.assertEqual(health["status"], "DEGRADED")
            self.assertEqual(health["fallback_used"], "cache")
            self.assertEqual(len(videos), 1)
            self.assertEqual(videos[0]["video_id"], "cached_vid_999")
            
            # Verify warning notification logged
            self.assertTrue(log_path.exists())
            notifications = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
            self.assertTrue(any(n["type"] == "youtube_cache_fallback" for n in notifications))
            
            cache_notif = next(n for n in notifications if n["type"] == "youtube_cache_fallback")
            self.assertEqual(cache_notif["severity"], "WARN")
            self.assertEqual(cache_notif["channel"], name)
            self.assertTrue(cache_notif["stale"]) # Should indicate stale was used

if __name__ == "__main__":
    unittest.main()
