"""
tests/test_familiarity.py
=========================
Regression & unit tests for Applicability-Domain / Prediction-Familiarity Indicator.
Phase B2 / Group 2 Item 5 Verification.
"""

import os
import sys
import unittest
from fastapi.testclient import TestClient

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from familiarity import (
    get_drug_familiarity,
    get_pair_familiarity,
    THRESHOLD_HIGH,
    THRESHOLD_LIMITED,
)
from app.main import app, _initialize_app_state


class TestDrugFamiliarityUnit(unittest.TestCase):
    def test_well_represented_training_drug_returns_high(self):
        """
        DB00853 (Temozolomide) appears in 3,699 training combinations and should
        be classified as 'high' familiarity.
        """
        res = get_drug_familiarity("DB00853")
        self.assertEqual(res["level"], "high")
        self.assertGreaterEqual(res["raw_score"], THRESHOLD_HIGH)
        self.assertIn("Seen in", res["basis"])
        self.assertIn("anchor compound", res["basis"])

    def test_bilateral_cold_drug_returns_novel(self):
        """
        DB00947 is in the bilateral cold-drug test set (0 appearances in training split)
        and must return 'novel' with raw_score == 0.0.
        """
        res = get_drug_familiarity("DB00947")
        self.assertEqual(res["level"], "novel")
        self.assertEqual(res["raw_score"], 0.0)
        self.assertIn("Unseen in training set", res["basis"])
        self.assertIn("inductive", res["basis"])

    def test_another_cold_drug_returns_novel(self):
        """
        DB00317 is another bilateral cold-drug test set compound.
        """
        res = get_drug_familiarity("DB00317")
        self.assertEqual(res["level"], "novel")
        self.assertEqual(res["raw_score"], 0.0)

    def test_discriminative_signal_not_constant(self):
        """
        Ensure familiarity actually discriminates between well-represented and unseen
        compounds rather than returning a constant or uniform value.
        """
        scores = [
            get_drug_familiarity("DB00853"),  # Temozolomide (high)
            get_drug_familiarity("DB00947"),  # Cold (novel)
            get_drug_familiarity("DB08881"),  # High anchor
            get_drug_familiarity("DB00530"),  # Cold (novel)
        ]
        levels = set(s["level"] for s in scores)
        raw_scores = set(s["raw_score"] for s in scores)
        self.assertGreaterEqual(len(levels), 2, f"Expected distinct levels, got {levels}")
        self.assertGreaterEqual(len(raw_scores), 2, f"Expected distinct raw scores, got {raw_scores}")

    def test_pair_familiarity_combinations(self):
        """
        Test joint pair familiarity under various combination regimes:
        - high x novel -> moderate
        - novel x novel -> novel
        - high x high -> high
        """
        # high x novel
        mod_pair = get_pair_familiarity("DB00853", "DB00947")
        self.assertEqual(mod_pair["pair_level"], "moderate")
        self.assertEqual(mod_pair["drug_a"]["level"], "high")
        self.assertEqual(mod_pair["drug_b"]["level"], "novel")
        self.assertIn("anchored by a high-frequency compound", mod_pair["summary"])

        # novel x novel (bilateral cold)
        cold_pair = get_pair_familiarity("DB00317", "DB00947")
        self.assertEqual(cold_pair["pair_level"], "novel")
        self.assertIn("Bilateral cold prediction", cold_pair["summary"])

        # high x high
        high_pair = get_pair_familiarity("DB00853", "DB08881")
        self.assertEqual(high_pair["pair_level"], "high")
        self.assertIn("High confidence domain", high_pair["summary"])


class TestAPIFamiliarityEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _initialize_app_state()
        cls.client = TestClient(app)

    def test_predict_endpoint_contains_familiarity(self):
        """
        Verify /predict returns drug_a_familiarity, drug_b_familiarity, and pair_familiarity.
        """
        resp = self.client.post(
            "/predict",
            json={"drug_a": "DB00853", "drug_b": "DB00531", "cell_line": "A549"},
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        data = resp.json()

        self.assertIn("drug_a_familiarity", data)
        self.assertIn("drug_b_familiarity", data)
        self.assertIn("pair_familiarity", data)

        fam_a = data["drug_a_familiarity"]
        self.assertIn(fam_a["level"], {"high", "limited", "novel"})
        self.assertIsInstance(fam_a["raw_score"], (int, float))
        self.assertIsInstance(fam_a["basis"], str)

        fam_pair = data["pair_familiarity"]
        self.assertIn(fam_pair["pair_level"], {"high", "moderate", "limited", "novel"})
        self.assertIsInstance(fam_pair["summary"], str)

    def test_predict_triple_endpoint_contains_familiarity(self):
        """
        Verify /predict-triple returns drug_a_familiarity, drug_b_familiarity,
        drug_c_familiarity, and bottleneck pair familiarity.
        """
        resp = self.client.post(
            "/predict-triple",
            json={
                "drug_a": "DB00853",
                "drug_b": "DB00531",
                "drug_c": "DB00947",
                "cell_line": "A549",
            },
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        data = resp.json()

        self.assertIn("drug_a_familiarity", data)
        self.assertIn("drug_b_familiarity", data)
        self.assertIn("drug_c_familiarity", data)

        btn = data.get("bottleneck_inspect", {})
        self.assertIn("drug_a_familiarity", btn)
        self.assertIn("drug_b_familiarity", btn)
        self.assertIn("pair_familiarity", btn)


if __name__ == "__main__":
    unittest.main()
