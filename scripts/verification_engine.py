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

    def fetch_polymarket_corroboration(
        self,
        keywords: str,
    ) -> dict[str, Any] | None:
        """Fetch closest active Polymarket question, URL, and YES odds for keywords (Check 2)."""
        if not keywords:
            return None
        return self.oracle.fetch_polymarket_corroboration(keywords)

    def calculate_confidence_score(
        self,
        base_score: int = 50,
        confirming_sources: int = 0,
        is_top_tier: bool = False,
        has_verifiable_numbers: bool = False,
        has_official_statement: bool = False,
        is_contradicted: bool = False,
        is_single_source: bool = False,
        has_bias_or_coi: bool = False,
        context_gaps: int = 0,
        has_corrections: bool = False,
        date_ambiguous: bool = False,
        yes_odds: float | None = None,
    ) -> int:
        """Calculate the fact-checking confidence score (0-100) based on source and claim signals."""
        score = base_score

        # Bonuses
        score += min(confirming_sources, 3) * 15
        if is_top_tier:
            score += 10
        if has_verifiable_numbers:
            score += 5
        if has_official_statement:
            score += 5

        # Penalties
        if is_contradicted:
            score -= 15
        if is_single_source:
            score -= 10
        if has_bias_or_coi:
            score -= 10
        score -= context_gaps * 5
        if has_corrections:
            score -= 5
        if date_ambiguous:
            score -= 5

        # Prediction Market Adjustments
        if yes_odds is not None:
            prob = yes_odds / 100.0 if yes_odds > 1.0 else yes_odds
            if prob > 0.70:
                score += 10
            elif prob < 0.15:
                score -= 15

        return max(0, min(100, score))


if __name__ == "__main__":
    engine = VerificationEngine()
    print("--- Polymarket Corroboration Test ---")
    print(engine.fetch_polymarket_corroboration("OpenAI"))
    
    print("\n--- Confidence Score Calculator Tests ---")
    # Base case: 50
    score = engine.calculate_confidence_score()
    print(f"Base score (expected 50): {score}")
    assert score == 50

    # Test >70% Polymarket YES odds (+10 bonus)
    score = engine.calculate_confidence_score(yes_odds=0.75)
    print(f"YES odds 75% (expected 60): {score}")
    assert score == 60

    # Test <15% Polymarket YES odds (-15 penalty)
    score = engine.calculate_confidence_score(yes_odds=0.10)
    print(f"YES odds 10% (expected 35): {score}")
    assert score == 35

    # Test complex combination
    # Base: 50
    # +15 (1 confirming source)
    # +10 (top tier)
    # -10 (known bias)
    # +10 (YES odds 80%)
    # Total = 50 + 15 + 10 - 10 + 10 = 75
    score = engine.calculate_confidence_score(
        confirming_sources=1,
        is_top_tier=True,
        has_bias_or_coi=True,
        yes_odds=0.80
    )
    print(f"Complex score (expected 75): {score}")
    assert score == 75

    print("\nAll VerificationEngine tests passed successfully!")

