"""
Unit tests for Stage 1 & Stage 2 candidate discovery and scoring in src/search.py.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from search import (
    find_candidate_drugs,
    resolve_disease_nodes,
    score_candidate_pairs,
    get_full_explanations_for_top_k,
    _load_resources,
    _load_model_cached,
)


class TestCandidateSearchAndScoring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module, cls.heterodata, cls.device = _load_model_cached()
        _, cls.node_maps, cls.name_lookup, cls.id_lookup, cls.drug_targets = _load_resources(cls.heterodata)

    def test_resolve_disease_nodes(self):
        dis_names = self.name_lookup["disease"]

        # Exact match
        indices, names = resolve_disease_nodes("breast neoplasm", dis_names)
        self.assertGreater(len(indices), 0)
        self.assertTrue(any("breast neoplasm" in n.lower() for n in names))

        # Substring match
        indices, names = resolve_disease_nodes("glioblastoma", dis_names)
        self.assertGreater(len(indices), 0)
        self.assertTrue(any("glioblastoma" in n.lower() for n in names))

        # Synonym token match
        indices, names = resolve_disease_nodes("ovarian carcinoma", dis_names)
        self.assertGreater(len(indices), 0)

        # Nonexistent
        indices, names = resolve_disease_nodes("unknown_fake_disease_12345", dis_names)
        self.assertEqual(len(indices), 0)
        self.assertEqual(len(names), 0)

    def test_find_candidate_drugs_glioblastoma(self):
        candidates = find_candidate_drugs(
            "glioblastoma",
            heterodata=self.heterodata,
            node_maps=self.node_maps,
            max_candidates=10,
        )

        self.assertGreaterEqual(len(candidates), 5)
        match_types = {c["match_type"] for c in candidates}
        self.assertIn("direct", match_types)

        drug_names = {c["drug_name"] for c in candidates}
        self.assertTrue(
            any(d in drug_names for d in ["Temozolomide", "Carmustine", "Bevacizumab", "Procarbazine"])
        )

        # Assert no non-drug entities (e.g. keratinocytes, fibroblasts) exist in candidate pool
        for c in candidates:
            self.assertIn("drug_id", c)
            self.assertTrue(c["drug_id"].startswith("DB"))
            self.assertIn("drug_name", c)
            self.assertFalse(any(bad in c["drug_name"].lower() for bad in ["keratinocyte", "fibroblast", "cell line", "foreskin"]))
            self.assertIn(c["match_type"], ("direct", "target_overlap"))
            self.assertGreaterEqual(c["score"], 0.0)
            self.assertLessEqual(c["score"], 1.0)

    def test_find_candidate_drugs_unknown_disease(self):
        candidates = find_candidate_drugs(
            "completely_made_up_illness",
            heterodata=self.heterodata,
            node_maps=self.node_maps,
        )
        self.assertEqual(candidates, [])

    def test_score_candidate_pairs_invalid_cell_line(self):
        with self.assertRaises(ValueError) as ctx:
            score_candidate_pairs(
                "glioblastoma",
                "FAKE_CELL_LINE_999",
                heterodata=self.heterodata,
                module=self.module,
                device=self.device,
            )
        self.assertIn("not recognized", str(ctx.exception))

    def test_score_candidate_pairs_and_explain(self):
        # Score top 2 pairs from 5 candidates (10 pairs total)
        top_pairs = score_candidate_pairs(
            disease_name="glioblastoma",
            cell_line_name="T98G",
            heterodata=self.heterodata,
            module=self.module,
            device=self.device,
            max_candidate_drugs=5,
            top_k=2,
        )

        self.assertEqual(len(top_pairs), 2)
        for p in top_pairs:
            self.assertIn("drug_a", p)
            self.assertIn("drug_b", p)
            self.assertIn("pair_tier", p)
            self.assertIn("pair_tier_name", p)
            self.assertIn("p_synergy", p)
            self.assertIn("p_additive", p)
            self.assertIn("p_antagonism", p)
            self.assertIn("predicted_class", p)
            self.assertIn(p["predicted_class"], ("synergy", "additive", "antagonism"))

        # Verify sorted by tier ascending then p_synergy descending
        self.assertLessEqual(top_pairs[0]["pair_tier"], top_pairs[1]["pair_tier"])

        # Test full explanations on the top 1 pair
        explanations = get_full_explanations_for_top_k(
            top_k_pairs=top_pairs[:1],
            cell_line_name="T98G",
            module=self.module,
            heterodata=self.heterodata,
            device=self.device,
        )
        self.assertEqual(len(explanations), 1)
        expl = explanations[0]
        self.assertIn("explanation_text", expl)
        self.assertIn("necessity_delta_pct", expl)
        self.assertIn("sufficiency_retained_pct", expl)
        self.assertIn("supporting_literature", expl)


if __name__ == "__main__":
    unittest.main()
