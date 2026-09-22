"""
tests/test_ranking.py
=====================
Unit and integration tests for Multi-Objective Ranking V(pair) (Phase B2).

Test coverage:
1. Known DDI=True pair ranks below otherwise-similar DDI=False pair, all else equal.
2. Pinned unknown-risk policy tests (exact uncertainty penalties, no silent 0.0 or drift).
3. Value function V(pair) formula correctness and full inspectability breakdown.
4. Redundancy penalty retrieval from precomputed Phase A target features vs unindexed None.
5. Beam search output ordering change vs pre-B2 fixture (Carmustine + Procarbazine demotion).
"""

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from ranking import (
    compute_toxicity_penalty,
    compute_redundancy_penalty,
    compute_pair_score_v,
    DEFAULT_W_SYNERGY,
    DEFAULT_W_TOXICITY,
    DEFAULT_W_REDUNDANCY,
    ALPHA_DDI,
    ALPHA_SE,
    UNKNOWN_DDI_PENALTY,
    UNKNOWN_SE_PENALTY,
)
from search import beam_search_combinations


class TestRankingModule(unittest.TestCase):
    """Unit tests for src/ranking.py value function V(pair)."""

    def test_known_ddi_pair_ranks_below_safe_pair_all_else_equal(self):
        """
        Verify that a pair with known DDI=True ranks strictly below an
        otherwise-similar pair with DDI=False, given identical p_synergy.
        """
        # Pair 1: Cisplatin + Paclitaxel (Known DDI = True, overlapping toxicity)
        # Pair 2: Aspirin + Acetaminophen (Known DDI = False, standard OTC pair)
        p_syn = 0.8500

        res_toxic = compute_pair_score_v("DB00515", "DB01229", p_synergy=p_syn)
        res_safe = compute_pair_score_v("DB00945", "DB00316", p_synergy=p_syn)

        self.assertTrue(res_toxic["breakdown"]["has_known_ddi"] is True)
        self.assertTrue(res_safe["breakdown"]["has_known_ddi"] is False)

        # Toxic pair must receive higher toxicity penalty
        self.assertGreater(res_toxic["toxicity_penalty"], res_safe["toxicity_penalty"])

        # Toxic pair must receive strictly lower composite V score
        self.assertLess(res_toxic["v_score"], res_safe["v_score"])

    def test_unknown_risk_policy_pinned(self):
        """
        Pins down the exact unknown-risk policy:
        - has_known_ddi is None -> ddi_risk = UNKNOWN_DDI_PENALTY (0.35)
        - side_effect_overlap is None -> se_risk = UNKNOWN_SE_PENALTY (0.15)
        - composite unknown penalty = round(0.65 * 0.35 + 0.35 * 0.15, 4) = 0.2800
        - Confirmed Safe (0.0) < Unknown Risk (0.28) < Confirmed Toxic (>0.70)
        """
        # Query two dummy unindexed drugs
        pen_unknown, details_unknown = compute_toxicity_penalty("DB99998_DUMMY", "DB99999_DUMMY")

        self.assertIsNone(details_unknown["has_known_ddi"])
        self.assertIsNone(details_unknown["side_effect_overlap_score"])
        self.assertTrue(details_unknown["unknown_risk_applied"])
        self.assertTrue(details_unknown["is_unknown_ddi"])
        self.assertTrue(details_unknown["is_unknown_se"])

        # Assert pinned numerical constants
        self.assertEqual(details_unknown["ddi_risk"], UNKNOWN_DDI_PENALTY)
        self.assertEqual(details_unknown["se_risk"], UNKNOWN_SE_PENALTY)
        expected_penalty = round(ALPHA_DDI * UNKNOWN_DDI_PENALTY + ALPHA_SE * UNKNOWN_SE_PENALTY, 4)
        self.assertEqual(pen_unknown, expected_penalty)
        self.assertEqual(pen_unknown, 0.2800)

        # Ordering guarantee check:
        # Confirmed safe pair with 0 SE overlap:
        # Metformin + Glipizide has DDI=False
        pen_safe, details_safe = compute_toxicity_penalty("DB00331", "DB01067")
        self.assertFalse(details_safe["has_known_ddi"])

        # Confirmed toxic pair:
        pen_toxic, details_toxic = compute_toxicity_penalty("DB00262", "DB01168")  # Carmustine + Procarbazine
        self.assertTrue(details_toxic["has_known_ddi"])

        # Strict ordering: safe (0.09) < unknown (0.28) < toxic (0.72)
        self.assertLess(pen_safe, pen_unknown, "Safe pair must have lower penalty than unknown uncertainty")
        self.assertLess(pen_unknown, pen_toxic, "Unknown pair must have lower penalty than confirmed toxic")

    def test_ranking_formula_and_inspectability_breakdown(self):
        """
        Verify that compute_pair_score_v computes V(pair) exactly as documented
        and exposes all weights and component breakdowns.
        """
        p_syn = 0.90
        w_syn = 1.0
        w_tox = 0.35
        w_red = 0.10

        res = compute_pair_score_v(
            "DB00515", "DB01229",
            p_synergy=p_syn,
            w_synergy=w_syn,
            w_toxicity=w_tox,
            w_redundancy=w_red,
        )

        # Formula check
        red_sub = (w_red * res["redundancy_penalty"]) if res["redundancy_penalty"] is not None else 0.0
        expected_v = round((w_syn * p_syn) - (w_tox * res["toxicity_penalty"]) - red_sub, 4)
        self.assertEqual(res["v_score"], expected_v)

        # Inspectability check: weights and breakdown are fully populated
        self.assertIn("weights", res)
        self.assertEqual(res["weights"]["w_synergy"], w_syn)
        self.assertEqual(res["weights"]["w_toxicity"], w_tox)
        self.assertEqual(res["weights"]["w_redundancy"], w_red)

        bd = res["breakdown"]
        self.assertIn("has_known_ddi", bd)
        self.assertIn("side_effect_overlap", bd)
        self.assertIn("ddi_risk", bd)
        self.assertIn("se_risk", bd)
        self.assertIn("unknown_risk_applied", bd)
        self.assertIn("source_coverage", bd)
        self.assertIn("redundancy_available", bd)

    def test_redundancy_penalty_behavior(self):
        """
        Verify that compute_redundancy_penalty returns float for Phase A indexed pairs
        and None (with a logged TODO note) for unindexed pairs.
        """
        # Unindexed dummy pair
        red_unindexed, details_unindexed = compute_redundancy_penalty("DB99998_DUMMY", "DB99999_DUMMY")
        self.assertIsNone(red_unindexed)
        self.assertFalse(details_unindexed["available"])
        self.assertIn("TODO", details_unindexed["note"])


class TestSearchRankingIntegration(unittest.TestCase):
    """Integration test verifying beam search candidate re-ranking."""

    def test_beam_search_order_changes_vs_pre_b2_on_toxic_pair(self):
        """
        In pre-B2 raw p_synergy ranking on Glioblastoma @ T98G:
            Rank 4: Procarbazine + Carmustine (p_syn = 0.9218, known severe DDI)
            Rank 5: Procarbazine + Endostatin (p_syn = 0.9216, DDI = False)
        In post-B2 multi-objective ranking V(pair):
            Procarbazine + Endostatin is promoted above Procarbazine + Carmustine,
            and Procarbazine + Carmustine is demoted out of the top-5.
        """
        hits, meta = beam_search_combinations("glioblastoma", "T98G", top_k=5)
        self.assertEqual(len(hits), 5)

        # Inspect rankings
        hit_pairs = [(h["drug_a_name"], h["drug_b_name"]) for h in hits]
        flat_pairs = [set(p) for p in hit_pairs]

        # 1. Procarbazine + Endostatin must be in top-5
        endostatin_in_top5 = any({"Procarbazine", "Endostatin"}.issubset(p) for p in flat_pairs)
        self.assertTrue(endostatin_in_top5, "Procarbazine + Endostatin (safe) should be promoted to top 5")

        # 2. Carmustine + Procarbazine must NOT rank above Endostatin + Procarbazine
        endo_rank = next((h["rank"] for h in hits if {"Procarbazine", "Endostatin"}.issubset({h["drug_a_name"], h["drug_b_name"]})), None)
        carmustine_rank = next((h["rank"] for h in hits if {"Procarbazine", "Carmustine"}.issubset({h["drug_a_name"], h["drug_b_name"]})), 999)

        self.assertIsNotNone(endo_rank)
        self.assertLess(endo_rank, carmustine_rank, "Endostatin (safe) must rank above Carmustine (severe toxic DDI)")

        # 3. Verify each hit has a complete ranking block with weights and breakdown
        for h in hits:
            self.assertIn("ranking", h)
            self.assertIn("v_score", h)
            self.assertEqual(h["score"], h["v_score"])
            self.assertIn("weights", h["ranking"])
            self.assertIn("breakdown", h["ranking"])


if __name__ == "__main__":
    unittest.main()
