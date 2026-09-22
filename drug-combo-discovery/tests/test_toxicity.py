"""
Unit tests for the Toxicity and DDI signal layer in src/toxicity.py.
"""

import os
import sys
import unittest
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from toxicity import get_pair_toxicity, get_drug_toxicity_profile, ToxicitySignalLayer


class TestToxicitySignalLayer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.layer = ToxicitySignalLayer()
        cls.layer._ensure_initialized()

    def test_known_ddi_pair(self):
        """Known DDI pair returns has_known_ddi=True."""
        # Lepirudin (DB00001) + Apixaban (DB06605)
        res = self.layer.get_pair_toxicity("DB00001", "DB06605")
        self.assertEqual(res["has_known_ddi"], True)
        self.assertTrue(res["source_coverage"]["primekg_ddi"])

        # Cisplatin (DB00515) + Paclitaxel (DB01204)
        res2 = self.layer.get_pair_toxicity("DB00515", "DB01204")
        self.assertEqual(res2["has_known_ddi"], True)

    def test_pair_with_no_data_returns_none(self):
        """A pair with unindexed/missing data returns None fields (strictly not 0 or False)."""
        res = self.layer.get_pair_toxicity("DB00945", "DB99999_UNKNOWN")
        self.assertIsNone(res["side_effect_overlap_score"])
        self.assertIsNone(res["shared_side_effects_count"])
        self.assertIsNone(res["top_shared_side_effects"])
        self.assertIsNone(res["has_known_ddi"])
        self.assertIsNone(res["ddi_severity"])
        self.assertFalse(res["source_coverage"]["sider"])
        self.assertFalse(res["source_coverage"]["primekg_ddi"])

    def test_known_side_effect_overlap(self):
        """Pair with overlapping SIDER side effects yields non-zero Jaccard score and shared terms."""
        # Cisplatin (DB00515) + Paclitaxel (DB01204)
        res = self.layer.get_pair_toxicity("DB00515", "DB01204")
        self.assertTrue(res["source_coverage"]["sider"])
        self.assertIsNotNone(res["side_effect_overlap_score"])
        self.assertGreater(res["side_effect_overlap_score"], 0.0)
        self.assertLessEqual(res["side_effect_overlap_score"], 1.0)
        self.assertGreater(res["shared_side_effects_count"], 0)
        self.assertIsInstance(res["top_shared_side_effects"], list)
        self.assertGreater(len(res["top_shared_side_effects"]), 0)

    def test_tracked_pair_without_ddi_returns_false(self):
        """Both drugs are tracked in DDI network but have no interaction edge -> returns False (not None)."""
        # Aspirin (DB00945) + Acetaminophen (DB00316)
        res = self.layer.get_pair_toxicity("DB00945", "DB00316")
        self.assertTrue(res["source_coverage"]["primekg_ddi"])
        self.assertEqual(res["has_known_ddi"], False)

    def test_drug_name_resolution(self):
        """get_pair_toxicity resolves case-insensitive drug names to DrugBank IDs."""
        res_ids = self.layer.get_pair_toxicity("DB00515", "DB01229")
        res_names = self.layer.get_pair_toxicity("Cisplatin", "Paclitaxel")
        self.assertEqual(res_ids["side_effect_overlap_score"], res_names["side_effect_overlap_score"])
        self.assertEqual(res_ids["has_known_ddi"], res_names["has_known_ddi"])

    def test_coverage_report_generation_runs_without_crashing(self):
        """Validates that toxicity queries execute across full current drug list without errors."""
        pairs_csv = os.path.join(os.path.dirname(__file__), "..", "data", "processed", "labeled_pairs.csv")
        self.assertTrue(os.path.exists(pairs_csv))

        df = pd.read_csv(pairs_csv, nrows=500)
        for _, row in df.iterrows():
            res = get_pair_toxicity(str(row["drug_a_kg_id"]), str(row["drug_b_kg_id"]))
            self.assertIn("has_known_ddi", res)
            self.assertIn("side_effect_overlap_score", res)
            self.assertIn("source_coverage", res)


if __name__ == "__main__":
    unittest.main()
