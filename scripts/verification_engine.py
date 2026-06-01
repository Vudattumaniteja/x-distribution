"""Verification engine seam for temporal and source integrity checks.

This module decouples raw third-party date parsing (TruthOracle) from the
core decision-tree verification logic (TemporalSentinel).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from scripts.truth_oracle import TruthOracle


class VerificationEngine:
    """Interface and implementation coordinating raw third-party adapters and date parsing."""

    def __init__(self, oracle: TruthOracle | None = None) -> None:
        self.oracle = oracle or TruthOracle()

    def get_hash(self, text: str) -> str:
        """Calculate normalized SHA-256 hash for a given text."""
        return self.oracle.get_hash(text)

    def extract_event_date_from_system(
        self,
        event_date_source: str,
        event_date_str: str | None,
    ) -> tuple[datetime | None, dict[str, Any] | None]:
        """Extract, parse, and normalize system-level timestamps (Tier 1)."""
        if not event_date_str:
            return None, None
        try:
            dt = datetime.fromisoformat(event_date_str.replace("Z", "+00:00"))
            evidence = {
                "source": "system_timestamp",
                "type": event_date_source,
                "timestamp": event_date_str,
            }
            return dt, evidence
        except (ValueError, TypeError):
            return None, None

    def fetch_wayback_event_date(
        self,
        url: str,
    ) -> tuple[datetime | None, dict[str, Any] | None]:
        """Fetch first-seen Wayback timestamp and parse into standard format (Tier 2)."""
        if not url:
            return None, None
        wayback = self.oracle.fetch_wayback_first_seen(url)
        if wayback and wayback.get("timestamp"):
            try:
                dt = datetime.fromisoformat(wayback["timestamp"].replace("Z", "+00:00"))
                return dt, wayback
            except (ValueError, TypeError):
                pass
        return None, None
