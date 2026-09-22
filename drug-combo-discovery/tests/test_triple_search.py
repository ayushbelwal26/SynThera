"""
tests/test_triple_search.py - Test Suite for Phase C1 Composed Three-Drug Scoring

Verifies:
1. Pairwise V scores: A known triple produces three constituent pairwise V scores
   matching what compute_pair_score_v returns independently.
2. aggregate_min: Correctly identifies the worst constituent pair (weak-link framing).
3. Toxicity demotion: A triple containing a known-toxic pair (e.g. Procarbazine + Carmustine)
   inherits max toxicity penalty (triple_toxicity_penalty >= 0.70) and is demoted.
4. Mandatory disclaimer: "We compose pair scores; we do not have DrugComb 3-way synergy labels."
   appears on every returned triple and top-level response.
5. Candidate pool hard cap: Large candidate requests (e.g. max_candidates=100) are capped at 20.
6. API endpoint: POST /search-triple returns valid schema with required fields.
"""

import unittest
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from ranking import compute_pair_score_v
from triple_search import (
    COMPOSITION_CAPTION,
    CANDIDATE_POOL_HARD_CAP,
    score_triple_combination,
    search_triple_combinations,
)


class TestTripleSearchComposition(unittest.TestCase):
    """Unit tests for Phase C1 three-drug composed pair scoring logic."""

    def setUp(self):
        # Known compounds from glioblastoma candidate pool
        self.procarbazine = {"drug_id": "DB01168", "drug_name": "Procarbazine"}
        self.carmustine = {"drug_id": "DB00262", "drug_name": "Carmustine"}
        self.vincristine = {"drug_id": "DB00541", "drug_name": "Vincristine"}
        self.alvocidib = {"drug_id": "DB03496", "drug_name": "Alvocidib"}
        self.fostamatinib = {"drug_id": "DB12010", "drug_name": "Fostamatinib"}

    def test_pairwise_v_scores_match(self):
        """
        Verify that score_triple_combination produces three constituent pairwise
        V scores matching independent calls to compute_pair_score_v.
        """
        p_ab, p_ac, p_bc = 0.90, 0.85, 0.75
        pair_rankings = {
            (min("DB01168", "DB00262"), max("DB01168", "DB00262")): compute_pair_score_v(
                "DB01168", "DB00262", p_synergy=p_ab
            ),
            (min("DB01168", "DB00541"), max("DB01168", "DB00541")): compute_pair_score_v(
                "DB01168", "DB00541", p_synergy=p_ac
            ),
            (min("DB00262", "DB00541"), max("DB00262", "DB00541")): compute_pair_score_v(
                "DB00262", "DB00541", p_synergy=p_bc
            ),
        }

        triple = score_triple_combination(
            drug_a=self.procarbazine,
            drug_b=self.carmustine,
            drug_c=self.vincristine,
            pair_rankings=pair_rankings,
        )

        # Check constituent rankings match independent computations
        expected_ab = compute_pair_score_v("DB01168", "DB00262", p_synergy=p_ab)
        expected_ac = compute_pair_score_v("DB01168", "DB00541", p_synergy=p_ac)
        expected_bc = compute_pair_score_v("DB00262", "DB00541", p_synergy=p_bc)

        self.assertEqual(triple["pair_ab"]["v_score"], expected_ab["v_score"])
        self.assertEqual(triple["pair_ac"]["v_score"], expected_ac["v_score"])
        self.assertEqual(triple["pair_bc"]["v_score"], expected_bc["v_score"])

        self.assertEqual(triple["pair_ab"]["toxicity_penalty"], expected_ab["toxicity_penalty"])
        self.assertEqual(triple["pair_ac"]["toxicity_penalty"], expected_ac["toxicity_penalty"])
        self.assertEqual(triple["pair_bc"]["toxicity_penalty"], expected_bc["toxicity_penalty"])

    def test_aggregate_min_identifies_worst_pair(self):
        """
        Verify that aggregate_min strictly computes the minimum of the 3 pairs
        and that bottleneck_pair accurately points to the weak link.
        """
        # Assign asymmetric synthetic synergy probabilities
        # Pair AB: strong synergy (0.95), Pair AC: moderate (0.80), Pair BC: weak (0.30)
        p_ab, p_ac, p_bc = 0.95, 0.80, 0.30
        pair_rankings = {
            (min("DB01168", "DB03496"), max("DB01168", "DB03496")): compute_pair_score_v(
                "DB01168", "DB03496", p_synergy=p_ab
            ),
            (min("DB01168", "DB12010"), max("DB01168", "DB12010")): compute_pair_score_v(
                "DB01168", "DB12010", p_synergy=p_ac
            ),
            (min("DB03496", "DB12010"), max("DB03496", "DB12010")): compute_pair_score_v(
                "DB03496", "DB12010", p_synergy=p_bc
            ),
        }

        triple = score_triple_combination(
            drug_a=self.procarbazine,
            drug_b=self.alvocidib,
            drug_c=self.fostamatinib,
            pair_rankings=pair_rankings,
        )

        v_ab = triple["pair_ab"]["v_score"]
        v_ac = triple["pair_ac"]["v_score"]
        v_bc = triple["pair_bc"]["v_score"]

        expected_min = min(v_ab, v_ac, v_bc)
        expected_mean = round((v_ab + v_ac + v_bc) / 3.0, 4)

        self.assertEqual(triple["aggregate_min"], expected_min)
        self.assertEqual(triple["aggregate_mean"], expected_mean)

        # Bottleneck pair must identify BC (Alvocidib x Fostamatinib)
        self.assertEqual(triple["bottleneck_pair"]["pair_key"], "pair_bc")
        self.assertEqual(triple["bottleneck_pair"]["v_score"], expected_min)

    def test_known_toxic_pair_demotes_triple(self):
        """
        Verify that a triple containing the known-bad Procarbazine + Carmustine pair
        (which has ddi_risk=1.0 and severe myelosuppression) inherits triple_toxicity_penalty >= 0.70
        and has_known_ddi=True.
        """
        # Triple 1 (Toxic constituent): Procarbazine + Carmustine + Vincristine
        p_syn = 0.90
        pair_rankings_toxic = {
            (min("DB01168", "DB00262"), max("DB01168", "DB00262")): compute_pair_score_v(
                "DB01168", "DB00262", p_synergy=p_syn
            ),
            (min("DB01168", "DB00541"), max("DB01168", "DB00541")): compute_pair_score_v(
                "DB01168", "DB00541", p_synergy=p_syn
            ),
            (min("DB00262", "DB00541"), max("DB00262", "DB00541")): compute_pair_score_v(
                "DB00262", "DB00541", p_synergy=p_syn
            ),
        }
        triple_toxic = score_triple_combination(
            drug_a=self.procarbazine,
            drug_b=self.carmustine,
            drug_c=self.vincristine,
            pair_rankings=pair_rankings_toxic,
        )

        # Procarbazine + Carmustine has known DDI
        self.assertTrue(triple_toxic["has_known_ddi"])
        self.assertGreaterEqual(triple_toxic["triple_toxicity_penalty"], 0.70)

        # Triple 2 (Safe constituents): Procarbazine + Alvocidib + Fostamatinib
        pair_rankings_safe = {
            (min("DB01168", "DB03496"), max("DB01168", "DB03496")): compute_pair_score_v(
                "DB01168", "DB03496", p_synergy=p_syn
            ),
            (min("DB01168", "DB12010"), max("DB01168", "DB12010")): compute_pair_score_v(
                "DB01168", "DB12010", p_synergy=p_syn
            ),
            (min("DB03496", "DB12010"), max("DB03496", "DB12010")): compute_pair_score_v(
                "DB03496", "DB12010", p_synergy=p_syn
            ),
        }
        triple_safe = score_triple_combination(
            drug_a=self.procarbazine,
            drug_b=self.alvocidib,
            drug_c=self.fostamatinib,
            pair_rankings=pair_rankings_safe,
        )

        # Safe triple toxicity should be vastly lower than the toxic triple
        self.assertLess(triple_safe["triple_toxicity_penalty"], triple_toxic["triple_toxicity_penalty"])
        # Safe triple aggregate_min must be higher due to lack of DDI penalty
        self.assertGreater(triple_safe["aggregate_min"], triple_toxic["aggregate_min"])

    def test_composition_caption_present(self):
        """
        Verify that the mandatory composition caption:
        'We compose pair scores; we do not have DrugComb 3-way synergy labels.'
        is present in every scored triple result dictionary.
        """
        pair_rankings = {
            (min("DB01168", "DB03496"), max("DB01168", "DB03496")): compute_pair_score_v("DB01168", "DB03496", 0.8),
            (min("DB01168", "DB12010"), max("DB01168", "DB12010")): compute_pair_score_v("DB01168", "DB12010", 0.8),
            (min("DB03496", "DB12010"), max("DB03496", "DB12010")): compute_pair_score_v("DB03496", "DB12010", 0.8),
        }
        triple = score_triple_combination(
            drug_a=self.procarbazine,
            drug_b=self.alvocidib,
            drug_c=self.fostamatinib,
            pair_rankings=pair_rankings,
        )
        self.assertIn("composition_caption", triple)
        self.assertEqual(
            triple["composition_caption"],
            "We compose pair scores; we do not have DrugComb 3-way synergy labels.",
        )

    def test_candidate_pool_hard_capped(self):
        """
        Verify that passing a huge candidate pool request (e.g. max_candidates=100)
        is capped at CANDIDATE_POOL_HARD_CAP (20) to prevent combinatorial explosion.
        """
        self.assertEqual(CANDIDATE_POOL_HARD_CAP, 20)
        # Test search with max_candidates=100
        results, meta = search_triple_combinations(
            disease_name="glioblastoma",
            cell_line_name="T98G",
            max_candidates=100,
            top_k=3,
            time_budget_sec=10.0,
        )
        self.assertLessEqual(meta["candidate_pool_size"], CANDIDATE_POOL_HARD_CAP)
        self.assertEqual(
            meta["composition_caption"],
            "We compose pair scores; we do not have DrugComb 3-way synergy labels.",
        )
        for hit in results:
            self.assertEqual(
                hit["composition_caption"],
                "We compose pair scores; we do not have DrugComb 3-way synergy labels.",
            )


class TestTripleSearchEndpoint(unittest.TestCase):
    """Integration test verifying FastAPI POST /search-triple endpoint."""

    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        app_path = os.path.join(ROOT, "app")
        if app_path not in sys.path:
            sys.path.insert(0, app_path)
        from main import app
        cls.client = TestClient(app)

    def test_search_triple_api_endpoint(self):
        """Verify POST /search-triple returns valid response with composition caption."""
        resp = self.client.post(
            "/search-triple",
            json={
                "disease": "glioblastoma",
                "cell_line": "T98G",
                "max_candidates": 6,
                "top_k": 3,
                "time_budget_sec": 10.0,
            },
        )
        self.assertEqual(resp.status_code, 200, f"Expected 200, got: {resp.text}")
        data = resp.json()

        # Top-level assertions
        self.assertEqual(data["disease"], "glioblastoma")
        self.assertEqual(data["cell_line"], "T98G")
        self.assertIn("results", data)
        self.assertIn("composition_caption", data)
        self.assertEqual(
            data["composition_caption"],
            "We compose pair scores; we do not have DrugComb 3-way synergy labels.",
        )
        self.assertLessEqual(len(data["results"]), 3)

        # Check each triple in results
        for item in data["results"]:
            self.assertIn("drug_a", item)
            self.assertIn("drug_b", item)
            self.assertIn("drug_c", item)
            self.assertIn("aggregate_min", item)
            self.assertIn("aggregate_mean", item)
            self.assertIn("triple_toxicity_penalty", item)
            self.assertIn("bottleneck_pair", item)
            self.assertIn("pair_ab", item)
            self.assertIn("pair_ac", item)
            self.assertIn("pair_bc", item)
            self.assertIn("composition_caption", item)
            self.assertEqual(
                item["composition_caption"],
                "We compose pair scores; we do not have DrugComb 3-way synergy labels.",
            )
            # Bottleneck pair check
            self.assertEqual(
                item["bottleneck_pair"]["v_score"],
                item["aggregate_min"],
            )


if __name__ == "__main__":
    unittest.main()
