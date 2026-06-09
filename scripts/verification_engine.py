"""Verification engine seam for temporal and source integrity checks.

This module decouples raw third-party date parsing (TruthOracle) from the
core decision-tree verification logic (TemporalSentinel).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from scripts.truth_oracle import TruthOracle


SUPPORTS = "supports"
CONTRADICTS = "contradicts"
NEUTRAL = "neutral"


@dataclass
class SourceEvidence:
    """Normalized evidence attached to one atomic claim."""

    source: str
    url: str | None = None
    title: str | None = None
    excerpt: str | None = None
    timestamp: str | None = None
    observed_at: str | None = None
    support: str = NEUTRAL
    adapter: str | None = None
    weight: float = 1.0
    corroboration_hints: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class AtomicClaim:
    """Claim-shaped verification input with source evidence and optional market context."""

    claim: str
    source_evidence: list[SourceEvidence | dict[str, Any]] = field(default_factory=list)
    timestamp: str | None = None
    corroboration_hints: list[dict[str, Any] | str] = field(default_factory=list)
    market_context: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class VerificationResult:
    """Reasoned verdict returned by atomic claim verification."""

    verdict: str
    confidence: int
    rationale: list[str]
    evidence: list[dict[str, Any]]
    market_context: dict[str, Any] | None
    checked_at: str


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

    def normalize_source_evidence(
        self,
        evidence: SourceEvidence | dict[str, Any],
    ) -> SourceEvidence:
        """Normalize source-shaped dictionaries into the atomic evidence contract."""
        if isinstance(evidence, SourceEvidence):
            return evidence
        if not isinstance(evidence, dict):
            raise TypeError("source evidence must be a SourceEvidence or dict")

        support = self._normalize_support(
            evidence.get("support")
            or evidence.get("stance")
            or evidence.get("verdict")
            or evidence.get("relationship")
        )
        timestamp = (
            evidence.get("timestamp")
            or evidence.get("published_at")
            or evidence.get("created_at")
            or evidence.get("date")
        )
        observed_at = evidence.get("observed_at") or evidence.get("fetched_at")
        hints = evidence.get("corroboration_hints") or evidence.get("hints") or []
        if isinstance(hints, str):
            hints = [hints]

        return SourceEvidence(
            source=str(evidence.get("source") or evidence.get("source_name") or "unknown"),
            url=evidence.get("url") or evidence.get("source_url"),
            title=evidence.get("title") or evidence.get("headline") or evidence.get("question"),
            excerpt=evidence.get("excerpt") or evidence.get("summary") or evidence.get("body"),
            timestamp=str(timestamp) if timestamp else None,
            observed_at=str(observed_at) if observed_at else None,
            support=support,
            adapter=evidence.get("adapter"),
            weight=self._normalize_weight(evidence.get("weight")),
            corroboration_hints=[str(hint) for hint in hints],
            raw=dict(evidence),
        )

    def verify_atomic_claim(
        self,
        claim: AtomicClaim | dict[str, Any],
        *,
        use_adapters: bool = False,
    ) -> VerificationResult:
        """Verify one atomic claim and return a closed, reasoned verdict object."""
        atomic_claim = self._normalize_claim(claim)
        evidence = [
            self.normalize_source_evidence(item)
            for item in atomic_claim.source_evidence
        ]
        if use_adapters:
            evidence.extend(self._fetch_adapter_evidence(atomic_claim))

        supporting = [item for item in evidence if item.support == SUPPORTS]
        contradictory = [item for item in evidence if item.support == CONTRADICTS]
        neutral = [item for item in evidence if item.support == NEUTRAL]
        market_context = self._resolve_market_context(atomic_claim, use_adapters)
        yes_odds = self._extract_yes_odds(market_context)

        confidence = self.calculate_confidence_score(
            base_score=50,
            confirming_sources=len(supporting),
            has_verifiable_numbers=any(self._has_number(item) for item in evidence),
            has_official_statement=any(self._is_official(item) for item in supporting),
            is_contradicted=bool(contradictory),
            is_single_source=len([item for item in evidence if item.support != NEUTRAL]) == 1,
            context_gaps=0 if supporting else 1,
            yes_odds=yes_odds,
        )
        verdict = self._verdict_from_signals(confidence, supporting, contradictory)
        rationale = self._build_rationale(
            supporting=supporting,
            contradictory=contradictory,
            neutral=neutral,
            market_context=market_context,
            yes_odds=yes_odds,
            confidence=confidence,
            verdict=verdict,
        )

        return VerificationResult(
            verdict=verdict,
            confidence=confidence,
            rationale=rationale,
            evidence=[asdict(item) for item in evidence],
            market_context=market_context,
            checked_at=datetime.now(timezone.utc).isoformat(),
        )

    def fetch_github_release_evidence(
        self,
        org: str,
        repo: str,
        tag: str | None = None,
    ) -> SourceEvidence | None:
        """Adapter wrapper for GitHub release timestamps."""
        entry = self.oracle.fetch_github_release(org, repo, tag)
        if not entry:
            return None
        return self.normalize_source_evidence({
            **entry,
            "source": entry.get("source", "github_release"),
            "adapter": "github_release",
            "support": SUPPORTS,
            "url": f"https://github.com/{org}/{repo}/releases"
            + (f"/tag/{tag}" if tag else "/latest"),
        })

    def fetch_huggingface_model_evidence(self, model_id: str) -> SourceEvidence | None:
        """Adapter wrapper for Hugging Face model timestamps."""
        entry = self.oracle.fetch_hf_lastmodified(model_id)
        if not entry:
            return None
        return self.normalize_source_evidence({
            **entry,
            "source": entry.get("source", "huggingface_lastmodified"),
            "adapter": "huggingface_model",
            "support": SUPPORTS,
            "url": f"https://huggingface.co/{model_id}",
        })

    def fetch_wayback_evidence(self, url: str) -> SourceEvidence | None:
        """Adapter wrapper for Wayback first-seen timestamps."""
        entry = self.oracle.fetch_wayback_first_seen(url)
        if not entry:
            return None
        return self.normalize_source_evidence({
            **entry,
            "source": entry.get("source", "wayback_cdx"),
            "adapter": "wayback_first_seen",
            "support": SUPPORTS,
            "url": url,
        })

    def fetch_polymarket_evidence(self, keywords: str) -> SourceEvidence | None:
        """Adapter wrapper for Polymarket corroboration."""
        entry = self.fetch_polymarket_corroboration(keywords)
        if not entry:
            return None
        yes_odds = self._extract_yes_odds(entry)
        support = SUPPORTS if yes_odds is not None and yes_odds > 0.70 else NEUTRAL
        if yes_odds is not None and yes_odds < 0.15:
            support = CONTRADICTS
        return self.normalize_source_evidence({
            **entry,
            "source": "polymarket",
            "adapter": "polymarket",
            "support": support,
            "title": entry.get("question"),
        })

    def _normalize_claim(self, claim: AtomicClaim | dict[str, Any]) -> AtomicClaim:
        if isinstance(claim, AtomicClaim):
            return claim
        if not isinstance(claim, dict):
            raise TypeError("atomic claim must be an AtomicClaim or dict")
        evidence = claim.get("source_evidence") or claim.get("evidence") or []
        return AtomicClaim(
            claim=str(claim.get("claim") or claim.get("text") or claim.get("headline") or ""),
            source_evidence=list(evidence),
            timestamp=claim.get("timestamp") or claim.get("claimed_at"),
            corroboration_hints=list(claim.get("corroboration_hints") or []),
            market_context=claim.get("market_context"),
            metadata=dict(claim.get("metadata") or {}),
        )

    def _fetch_adapter_evidence(self, claim: AtomicClaim) -> list[SourceEvidence]:
        fetched: list[SourceEvidence] = []
        for hint in claim.corroboration_hints:
            if not isinstance(hint, dict):
                continue
            adapter = hint.get("adapter") or hint.get("type")
            evidence: SourceEvidence | None = None
            if adapter == "github_release":
                evidence = self.fetch_github_release_evidence(
                    str(hint.get("org") or ""),
                    str(hint.get("repo") or ""),
                    hint.get("tag"),
                )
            elif adapter == "huggingface_model":
                evidence = self.fetch_huggingface_model_evidence(str(hint.get("model_id") or ""))
            elif adapter == "wayback_first_seen":
                evidence = self.fetch_wayback_evidence(str(hint.get("url") or ""))
            elif adapter == "polymarket":
                evidence = self.fetch_polymarket_evidence(str(hint.get("keywords") or claim.claim))
            if evidence:
                fetched.append(evidence)
        return fetched

    def _resolve_market_context(
        self,
        claim: AtomicClaim,
        use_adapters: bool,
    ) -> dict[str, Any] | None:
        if claim.market_context:
            return dict(claim.market_context)
        if not use_adapters:
            return None
        for hint in claim.corroboration_hints:
            if isinstance(hint, dict) and (hint.get("adapter") or hint.get("type")) == "polymarket":
                return self.fetch_polymarket_corroboration(str(hint.get("keywords") or claim.claim))
        return None

    def _build_rationale(
        self,
        *,
        supporting: list[SourceEvidence],
        contradictory: list[SourceEvidence],
        neutral: list[SourceEvidence],
        market_context: dict[str, Any] | None,
        yes_odds: float | None,
        confidence: int,
        verdict: str,
    ) -> list[str]:
        rationale = [
            f"Verdict {verdict} with confidence {confidence}.",
            f"{len(supporting)} supporting, {len(contradictory)} contradictory, and {len(neutral)} neutral evidence item(s).",
        ]
        if contradictory:
            sources = ", ".join(sorted({item.source for item in contradictory}))
            rationale.append(f"Contradictory evidence from {sources} prevents a publishable verified verdict.")
        if not supporting:
            rationale.append("No supporting source evidence was supplied, so the claim remains fail-closed.")
        if yes_odds is not None:
            percent = yes_odds * 100 if yes_odds <= 1.0 else yes_odds
            if yes_odds > 0.70:
                rationale.append(f"Polymarket YES odds at {percent:.1f}% add confidence.")
            elif yes_odds < 0.15:
                rationale.append(f"Polymarket YES odds at {percent:.1f}% penalize confidence.")
            else:
                rationale.append(f"Polymarket YES odds at {percent:.1f}% are neutral.")
        elif market_context:
            rationale.append("Market context was present but did not include usable YES odds.")
        return rationale

    def _verdict_from_signals(
        self,
        confidence: int,
        supporting: list[SourceEvidence],
        contradictory: list[SourceEvidence],
    ) -> str:
        if contradictory:
            return "DISPUTED" if supporting else "LIKELY_FALSE"
        if not supporting:
            return "UNVERIFIED"
        if confidence >= 85 and len(supporting) >= 2:
            return "VERIFIED"
        if confidence >= 70:
            return "LIKELY_TRUE"
        return "UNVERIFIED"

    def _normalize_support(self, support: Any) -> str:
        normalized = str(support or "").strip().lower()
        if normalized in {"support", "supports", "supporting", "confirmed", "true", "yes"}:
            return SUPPORTS
        if normalized in {"contradict", "contradicts", "contradictory", "false", "refutes", "no"}:
            return CONTRADICTS
        return NEUTRAL

    def _normalize_weight(self, weight: Any) -> float:
        try:
            value = float(weight)
        except (TypeError, ValueError):
            return 1.0
        return max(0.0, min(5.0, value))

    def _extract_yes_odds(self, market_context: dict[str, Any] | None) -> float | None:
        if not market_context:
            return None
        for key in ("yes_odds", "yes_probability", "yes_price"):
            if key in market_context:
                try:
                    odds = float(market_context[key])
                except (TypeError, ValueError):
                    return None
                return odds / 100.0 if odds > 1.0 else odds
        return None

    def _has_number(self, evidence: SourceEvidence) -> bool:
        text = " ".join(
            str(part)
            for part in [evidence.title, evidence.excerpt, evidence.raw.get("raw")]
            if part
        )
        return any(char.isdigit() for char in text)

    def _is_official(self, evidence: SourceEvidence) -> bool:
        source = evidence.source.lower()
        adapter = (evidence.adapter or "").lower()
        return any(
            marker in source or marker in adapter
            for marker in ("github", "huggingface", "official", "sec")
        )


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

