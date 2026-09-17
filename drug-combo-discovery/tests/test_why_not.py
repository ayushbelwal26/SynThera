"""
Unit tests for the grounded "Why Not Drug X?" diagnostic agent in src/why_not.py.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from why_not import analyze_why_not, parse_why_not_intent
from search import _load_model_cached
from predict import _get_node_maps
from explain import _build_name_lookups


class TestWhyNotAgent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module, cls.heterodata, cls.device = _load_model_cached()
        name_lookup, id_lookup = _build_name_lookups(cls.heterodata)
        drug_id2idx = _get_node_maps(cls.heterodata).get("drug", {})

        cls.drug_list = []
        cls.drug_alias_map = {}
        seen = set()
        for idx, db_id in id_lookup.get("drug", {}).items():
            name = name_lookup.get("drug", {}).get(idx, db_id)
            if db_id in drug_id2idx and db_id not in seen:
                seen.add(db_id)
                cls.drug_list.append({"id": db_id, "name": name})
                cls.drug_alias_map[db_id.lower()] = db_id
                cls.drug_alias_map[name.lower()] = db_id

    def test_parse_intent_rules(self):
        """Test rule-based intent parsing for supported patterns and fallback."""
        # why_not patterns
        intent, ext = parse_why_not_intent("Why not Temozolomide?")
        self.assertEqual(intent, "why_not")
        self.assertEqual(ext.get("drug_x"), "Temozolomide")

        intent, ext = parse_why_not_intent("why isn't DB00853 ranked?")
        self.assertEqual(intent, "why_not")
        self.assertEqual(ext.get("drug_x"), "DB00853")

        intent, ext = parse_why_not_intent("Why was Zinc chloride excluded from search?")
        self.assertEqual(intent, "why_not")
        self.assertEqual(ext.get("drug_x"), "Zinc chloride")

        # compare pattern
        intent, ext = parse_why_not_intent("Compare Temozolomide vs Procarbazine")
        self.assertEqual(intent, "compare")
        self.assertEqual(ext.get("drug_a"), "Temozolomide")
        self.assertEqual(ext.get("drug_b"), "Procarbazine")

        # ranked_below pattern
        intent, ext = parse_why_not_intent("Why is Temozolomide ranked below Procarbazine?")
        self.assertEqual(intent, "ranked_below")
        self.assertEqual(ext.get("drug_a"), "Temozolomide")
        self.assertEqual(ext.get("drug_b"), "Procarbazine")

        # unsupported questions
        intent, _ = parse_why_not_intent("What's the weather?")
        self.assertEqual(intent, "unsupported_question")

        intent, _ = parse_why_not_intent("Hello")
        self.assertEqual(intent, "unsupported_question")

    def test_why_not_unsupported_question(self):
        """Unsupported questions return structured error object with helpful hint."""
        res = analyze_why_not(
            disease_name="glioblastoma",
            cell_line_name="T98G",
            question="Hello",
            drug_alias_map=self.drug_alias_map,
            drug_list=self.drug_list,
            heterodata=self.heterodata,
            module=self.module,
            device=self.device,
        )
        self.assertEqual(res.get("error"), "unsupported_question")
        self.assertIn("hint", res)
        self.assertIn("Ask why not <drug>", res["hint"])

    def test_why_not_zinc_filtered(self):
        """Zinc chloride is classified as filtered without GNN scoring or hallucination."""
        res = analyze_why_not(
            disease_name="glioblastoma",
            cell_line_name="T98G",
            question="Why not Zinc chloride?",
            drug_alias_map=self.drug_alias_map,
            drug_list=self.drug_list,
            heterodata=self.heterodata,
            module=self.module,
            device=self.device,
        )
        self.assertEqual(res.get("intent"), "why_not")
        self.assertEqual(res.get("status"), "filtered")
        self.assertEqual(res.get("verdict"), "filtered")
        self.assertEqual(res.get("drug_x", {}).get("id"), "DB14533")
        self.assertIsNone(res.get("best_pair"))
        self.assertIsNone(res.get("reference_top"))
        self.assertIsNone(res.get("faithfulness"))
        self.assertIn("therapeutic candidate filter", res.get("explanation_text", ""))

    def test_why_not_unknown_drug(self):
        """Unrecognized drug returns unknown_drug status and not_in_graph verdict."""
        res = analyze_why_not(
            disease_name="glioblastoma",
            cell_line_name="T98G",
            question="Why not ImaginaryDrug999?",
            drug_alias_map=self.drug_alias_map,
            drug_list=self.drug_list,
            heterodata=self.heterodata,
            module=self.module,
            device=self.device,
        )
        self.assertEqual(res.get("status"), "unknown_drug")
        self.assertEqual(res.get("verdict"), "not_in_graph")
        self.assertIsNone(res.get("best_pair"))
        self.assertIn("could not be resolved", res.get("explanation_text", ""))

    def test_why_not_temozolomide_scored(self):
        """Temozolomide is scored against disease candidate pool with real IDs and p_synergy."""
        res = analyze_why_not(
            disease_name="glioblastoma",
            cell_line_name="T98G",
            question="Why not Temozolomide?",
            drug_alias_map=self.drug_alias_map,
            drug_list=self.drug_list,
            heterodata=self.heterodata,
            module=self.module,
            device=self.device,
            run_literature=False,
        )
        self.assertEqual(res.get("status"), "scored")
        self.assertIn(res.get("verdict"), ("competitive", "weaker"))
        self.assertEqual(res.get("drug_x", {}).get("id"), "DB00853")
        self.assertEqual(res.get("drug_x", {}).get("name"), "Temozolomide")

        best_pair = res.get("best_pair")
        self.assertIsNotNone(best_pair)
        self.assertIn("p_synergy", best_pair)
        self.assertGreater(best_pair["p_synergy"], 0.0)
        self.assertEqual(best_pair["cell_line"], "T98G")

        ref_top = res.get("reference_top")
        self.assertIsNotNone(ref_top)
        self.assertIn("p_synergy", ref_top)

        self.assertIsNone(res.get("faithfulness"))
        self.assertIn("DB00853", res.get("explanation_text", ""))
        self.assertIn("Inspect", res.get("explanation_text", ""))

    def test_why_not_cisplatin_allowed_and_scored(self):
        """Cisplatin (DB00515) is allowed as an approved oncology therapeutic and scored."""
        res = analyze_why_not(
            disease_name="glioblastoma",
            cell_line_name="T98G",
            question="Why not Cisplatin?",
            drug_alias_map=self.drug_alias_map,
            drug_list=self.drug_list,
            heterodata=self.heterodata,
            module=self.module,
            device=self.device,
            run_literature=False,
        )
        self.assertEqual(res.get("status"), "scored")
        self.assertNotEqual(res.get("status"), "filtered")
        self.assertEqual(res.get("drug_x", {}).get("id"), "DB00515")
        self.assertIsNotNone(res.get("best_pair"))


if __name__ == "__main__":
    unittest.main()
