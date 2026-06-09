"""No-network tests for atomic claim verification."""

from __future__ import annotations

import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.verification_engine import AtomicClaim, VerificationEngine


class FakeOracle:
    def get_hash(self, text: str) -> str:
        return f"hash:{text}"

    def fetch_polymarket_corroboration(self, keywords: str) -> dict[str, object]:
        return {
            "question": f"Will {keywords} happen?",
            "url": "https://polymarket.com/event/test",
            "yes_odds": 0.82,
            "fetched_at": "2026-06-09T00:00:00+00:00",
        }


class AtomicClaimVerificationTests(unittest.TestCase):
    def test_source_evidence_normalization(self) -> None:
        engine = VerificationEngine()

        evidence = engine.normalize_source_evidence(
            {
                "source_name": "GitHub",
                "source_url": "https://github.com/example/project/releases/tag/v1",
                "headline": "Example v1 released",
                "published_at": "2026-06-09T01:02:03Z",
                "fetched_at": "2026-06-09T01:05:00Z",
                "stance": "confirmed",
                "hints": "release_timestamp",
                "weight": "2",
            }
        )

        self.assertEqual(evidence.source, "GitHub")
        self.assertEqual(evidence.url, "https://github.com/example/project/releases/tag/v1")
        self.assertEqual(evidence.title, "Example v1 released")
        self.assertEqual(evidence.timestamp, "2026-06-09T01:02:03Z")
        self.assertEqual(evidence.observed_at, "2026-06-09T01:05:00Z")
        self.assertEqual(evidence.support, "supports")
        self.assertEqual(evidence.corroboration_hints, ["release_timestamp"])
        self.assertEqual(evidence.weight, 2.0)

    def test_market_corroboration_preserves_yes_odds_bonus_and_penalty(self) -> None:
        engine = VerificationEngine()

        high_yes = engine.verify_atomic_claim(
            AtomicClaim(
                claim="Example AI model launches this week",
                source_evidence=[
                    {"source": "official_blog", "support": "supports", "excerpt": "Launch confirmed"}
                ],
                market_context={"question": "Will it launch?", "yes_odds": 0.80},
            )
        )
        low_yes = engine.verify_atomic_claim(
            AtomicClaim(
                claim="Example AI model launches this week",
                source_evidence=[
                    {"source": "official_blog", "support": "supports", "excerpt": "Launch confirmed"}
                ],
                market_context={"question": "Will it launch?", "yes_odds": 0.10},
            )
        )

        self.assertEqual(high_yes.confidence, 70)
        self.assertEqual(high_yes.verdict, "LIKELY_TRUE")
        self.assertIn("add confidence", " ".join(high_yes.rationale))
        self.assertEqual(low_yes.confidence, 45)
        self.assertEqual(low_yes.verdict, "UNVERIFIED")
        self.assertIn("penalize confidence", " ".join(low_yes.rationale))

    def test_contradictory_evidence_blocks_publishable_verdict(self) -> None:
        engine = VerificationEngine()

        result = engine.verify_atomic_claim(
            {
                "claim": "Company shipped model weights",
                "source_evidence": [
                    {"source": "GitHub", "support": "supports", "excerpt": "Release v1 includes weights."},
                    {"source": "Hugging Face", "support": "contradicts", "excerpt": "Repository is gated and empty."},
                ],
                "market_context": {"yes_odds": 0.90},
            }
        )

        self.assertEqual(result.verdict, "DISPUTED")
        self.assertNotIn(result.verdict, {"VERIFIED", "LIKELY_TRUE"})
        self.assertIn("Contradictory evidence", " ".join(result.rationale))

    def test_score_and_rationale_output_shape(self) -> None:
        engine = VerificationEngine()

        result = engine.verify_atomic_claim(
            AtomicClaim(
                claim="Project released v2",
                source_evidence=[
                    {"source": "GitHub", "support": "supports", "excerpt": "v2 released with 3 artifacts."},
                    {"source": "official_blog", "support": "supports", "excerpt": "v2 is generally available."},
                ],
                market_context={"yes_odds": 75},
            )
        )

        self.assertEqual(result.verdict, "VERIFIED")
        self.assertGreaterEqual(result.confidence, 85)
        self.assertIsInstance(result.rationale, list)
        self.assertTrue(result.rationale[0].startswith("Verdict VERIFIED"))
        self.assertEqual(len(result.evidence), 2)
        self.assertEqual(result.evidence[0]["support"], "supports")

    def test_polymarket_adapter_stays_behind_claim_interface(self) -> None:
        engine = VerificationEngine(oracle=FakeOracle())  # type: ignore[arg-type]

        result = engine.verify_atomic_claim(
            AtomicClaim(
                claim="test event",
                corroboration_hints=[{"adapter": "polymarket", "keywords": "test event"}],
            ),
            use_adapters=True,
        )

        self.assertEqual(result.market_context["yes_odds"], 0.82)  # type: ignore[index]
        self.assertEqual(result.evidence[0]["adapter"], "polymarket")
        self.assertEqual(result.evidence[0]["support"], "supports")


if __name__ == "__main__":
    unittest.main()
