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
    beam_search_combinations,
    get_full_explanations_for_top_k,
    is_valid_therapeutic_candidate,
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

    def test_therapeutic_candidate_filter_rules(self):
        """Verify allow/deny classification rules for therapeutic candidates."""
        # Denied: inorganics, metal salts, elemental minerals, excipients, solvents, diagnostics
        denied_samples = [
            ("Zinc chloride", "DB14533"),
            ("Zinc sulfate", "DB14534"),
            ("Zinc oxide", "DB09321"),
            ("Zinc", "DB01593"),
            ("Zinc cation", "DB01593"),
            ("Magnesium sulfate", "DB00653"),
            ("Magnesium oxide", "DB01377"),
            ("Calcium chloride", "DB01164"),
            ("Sodium chloride", "DB09158"),
            ("Potassium chloride", "DB00761"),
            ("Dimethyl sulfoxide", "DB01093"),
            ("Water", "DB09145"),
            ("Fluorescein", "DB00693"),
            ("Iohexol", "DB01362"),
            ("Platinum", "DB09146"),  # Pure elemental metal
            ("human foreskin fibroblast", "DB99999"),
        ]
        for name, db_id in denied_samples:
            self.assertFalse(
                is_valid_therapeutic_candidate(name, db_id),
                f"Expected '{name}' ({db_id}) to be denied as non-therapeutic"
            )

        # Allowed: real therapeutics, platinum-coordination chemotherapies, oncology inorganics
        allowed_samples = [
            ("Cisplatin", "DB00515"),
            ("Carboplatin", "DB00958"),
            ("Oxaliplatin", "DB00526"),
            ("Nedaplatin", "DB06653"),
            ("Arsenic trioxide", "DB01169"),
            ("Porfimer sodium", "DB00707"),
            ("Bleomycin", "DB00252"),
            ("Temozolomide", "DB00853"),
            ("Carmustine", "DB00262"),
            ("Irinotecan", "DB00762"),
            ("Procarbazine", "DB01168"),
            ("Fostamatinib", "DB12010"),
            ("Alvocidib", "DB03496"),
            ("Doxorubicin hydrochloride", "DB00997"),
        ]
        for name, db_id in allowed_samples:
            self.assertTrue(
                is_valid_therapeutic_candidate(name, db_id),
                f"Expected '{name}' ({db_id}) to be allowed as legitimate therapeutic"
            )

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

        # Assert Zinc and Zinc chloride are NOT in candidate pool
        self.assertNotIn("Zinc chloride", drug_names)
        self.assertNotIn("Zinc", drug_names)
        candidate_ids = {c["drug_id"] for c in candidates}
        self.assertNotIn("DB14533", candidate_ids)
        self.assertNotIn("DB01593", candidate_ids)

        # Assert all candidates satisfy therapeutic eligibility
        for c in candidates:
            self.assertIn("drug_id", c)
            self.assertTrue(c["drug_id"].startswith("DB"))
            self.assertIn("drug_name", c)
            self.assertTrue(
                is_valid_therapeutic_candidate(c["drug_name"], c["drug_id"]),
                f"Candidate '{c['drug_name']}' failed therapeutic validation"
            )
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

    def test_beam_search_combinations_ranking(self):
        top_pairs, search_meta = beam_search_combinations(
            disease_name="glioblastoma",
            cell_line_name="T98G",
            heterodata=self.heterodata,
            module=self.module,
            device=self.device,
            max_candidate_drugs=6,
            beam_width=3,
            top_k=3,
            search_method="beam",
        )

        self.assertEqual(len(top_pairs), 3)
        self.assertEqual(search_meta["search_method"], "beam")
        self.assertEqual(search_meta["beam_width"], 3)
        self.assertEqual(search_meta["candidate_pool_size"], 6)
        self.assertGreater(search_meta["max_candidates_scored"], 0)

        for p in top_pairs:
            self.assertIn("drug_a", p)
            self.assertIn("drug_b", p)
            self.assertTrue(p["drug_a"].startswith("DB"))
            self.assertTrue(p["drug_b"].startswith("DB"))
            self.assertIn("p_synergy", p)
            self.assertIn("predicted_class", p)
            self.assertIn(p["predicted_class"], ("synergy", "additive", "antagonism"))
            # Assert no non-therapeutic zinc or inorganic salts in scored pairs
            self.assertNotIn(p["drug_a"], {"DB14533", "DB01593"})
            self.assertNotIn(p["drug_b"], {"DB14533", "DB01593"})
            self.assertNotIn("zinc", p["drug_a_name"].lower())
            self.assertNotIn("zinc", p["drug_b_name"].lower())

        # Strictly sorted by p_synergy descending
        for i in range(len(top_pairs) - 1):
            self.assertGreaterEqual(
                top_pairs[i]["p_synergy"],
                top_pairs[i + 1]["p_synergy"] - 1e-6,
                f"Rank {i+1} score {top_pairs[i]['p_synergy']} should be >= Rank {i+2} score {top_pairs[i+1]['p_synergy']}"
            )

    def test_greedy_search_combinations(self):
        top_pairs, search_meta = beam_search_combinations(
            disease_name="glioblastoma",
            cell_line_name="T98G",
            heterodata=self.heterodata,
            module=self.module,
            device=self.device,
            max_candidate_drugs=6,
            beam_width=1,
            top_k=2,
            search_method="greedy",
        )
        self.assertEqual(len(top_pairs), 2)
        self.assertEqual(search_meta["search_method"], "greedy")
        self.assertEqual(search_meta["beam_width"], 1)

    def test_stable_tie_breaking(self):
        run1, _ = beam_search_combinations(
            disease_name="glioblastoma",
            cell_line_name="T98G",
            heterodata=self.heterodata,
            module=self.module,
            device=self.device,
            max_candidate_drugs=5,
            beam_width=3,
            top_k=3,
            search_method="beam",
        )
        run2, _ = beam_search_combinations(
            disease_name="glioblastoma",
            cell_line_name="T98G",
            heterodata=self.heterodata,
            module=self.module,
            device=self.device,
            max_candidate_drugs=5,
            beam_width=3,
            top_k=3,
            search_method="beam",
        )
        pairs1 = [(p["drug_a"], p["drug_b"]) for p in run1]
        pairs2 = [(p["drug_a"], p["drug_b"]) for p in run2]
        self.assertEqual(pairs1, pairs2)

    def test_batch_search_faithfulness_is_none(self):
        top_pairs, _ = beam_search_combinations(
            disease_name="glioblastoma",
            cell_line_name="T98G",
            heterodata=self.heterodata,
            module=self.module,
            device=self.device,
            max_candidate_drugs=5,
            beam_width=2,
            top_k=2,
            search_method="beam",
        )
        explanations = get_full_explanations_for_top_k(
            top_k_pairs=top_pairs,
            cell_line_name="T98G",
            module=self.module,
            heterodata=self.heterodata,
            device=self.device,
            inspect_top_k=0,
        )
        self.assertEqual(len(explanations), 2)
        for expl in explanations:
            self.assertIsNone(expl.get("faithfulness"))
            self.assertIsNone(expl.get("literature"))
            self.assertEqual(expl.get("supporting_literature"), [])
            self.assertIn("explanation_text", expl)
            self.assertIn("rank", expl)
            self.assertEqual(expl.get("search_method"), "beam")

    from unittest.mock import patch

    @patch("literature.retrieve_literature_rag")
    def test_batch_search_does_not_call_ncbi(self, mock_rag):
        """Confirm batch search never invokes literature retrieval for hits when inspect_top_k=0."""
        top_pairs, _ = beam_search_combinations(
            disease_name="glioblastoma",
            cell_line_name="T98G",
            heterodata=self.heterodata,
            module=self.module,
            device=self.device,
            max_candidate_drugs=5,
            beam_width=2,
            top_k=3,
            search_method="beam",
        )
        explanations = get_full_explanations_for_top_k(
            top_k_pairs=top_pairs,
            cell_line_name="T98G",
            module=self.module,
            heterodata=self.heterodata,
            device=self.device,
            inspect_top_k=0,
        )
        self.assertEqual(len(explanations), 3)
        # NCBI RAG must NOT be called for any candidate in batch search
        mock_rag.assert_not_called()
        for expl in explanations:
            self.assertIsNone(expl.get("literature"))
            self.assertEqual(expl.get("supporting_literature"), [])

    @patch("literature.retrieve_literature_rag")
    def test_inspect_top_k_faithfulness(self, mock_rag):
        mock_rag.return_value = {
            "citations": [{
                "pmid": "12345678",
                "title": "Mock study",
                "year": "2024",
                "journal": "Mock J",
                "first_author": "Smith J",
                "snippet": "Snippet text.",
                "url": "https://pubmed.ncbi.nlm.nih.gov/12345678/",
                "match_reason": "both drugs",
                "evidence_type": "combination",
            }],
            "query_used": "mock query",
            "retrieval_method": "ncbi_eutilities_keyword_overlap",
            "error": None,
        }
        top_pairs, _ = beam_search_combinations(
            disease_name="glioblastoma",
            cell_line_name="T98G",
            heterodata=self.heterodata,
            module=self.module,
            device=self.device,
            max_candidate_drugs=5,
            beam_width=2,
            top_k=2,
            search_method="beam",
        )
        explanations = get_full_explanations_for_top_k(
            top_k_pairs=top_pairs,
            cell_line_name="T98G",
            module=self.module,
            heterodata=self.heterodata,
            device=self.device,
            inspect_top_k=1,
        )
        self.assertEqual(len(explanations), 2)
        self.assertIsNotNone(explanations[0].get("faithfulness"))
        self.assertIsNotNone(explanations[0].get("literature"))
        self.assertEqual(len(explanations[0]["supporting_literature"]), 1)
        self.assertIsNone(explanations[1].get("faithfulness"))
        self.assertIsNone(explanations[1].get("literature"))
        self.assertEqual(explanations[1]["supporting_literature"], [])
        self.assertEqual(mock_rag.call_count, 1)

    def test_cisplatin_eligible_in_pool(self):
        """Verify cisplatin and platinum-complex antineoplastics remain eligible for candidate search."""
        self.assertTrue(is_valid_therapeutic_candidate("Cisplatin", "DB00515"))
        self.assertTrue(is_valid_therapeutic_candidate("Carboplatin", "DB00958"))
        self.assertTrue(is_valid_therapeutic_candidate("Oxaliplatin", "DB00526"))
        self.assertFalse(is_valid_therapeutic_candidate("Platinum", "DB09146"))

        # Seed search with Cisplatin (DB00515) to confirm GNN scoring executes normally
        top_pairs, search_meta = beam_search_combinations(
            disease_name="glioblastoma",
            cell_line_name="T98G",
            heterodata=self.heterodata,
            module=self.module,
            device=self.device,
            seed_drug_id="DB00515",
            max_candidate_drugs=5,
            beam_width=2,
            top_k=2,
            search_method="beam",
        )
        self.assertGreaterEqual(len(top_pairs), 1)
        self.assertTrue(any(p["drug_a"] == "DB00515" or p["drug_b"] == "DB00515" for p in top_pairs))

    def test_mcts_search_combinations(self):
        """Test MCTS combination search: metadata, faithfulness null, no zinc, ranking, and budget caching."""
        top_pairs, search_meta = beam_search_combinations(
            disease_name="glioblastoma",
            cell_line_name="T98G",
            heterodata=self.heterodata,
            module=self.module,
            device=self.device,
            max_candidate_drugs=8,
            top_k=3,
            search_method="mcts",
            n_simulations=30,
            mcts_c=1.414,
            time_budget_sec=15.0,
        )

        self.assertEqual(len(top_pairs), 3)
        self.assertEqual(search_meta["search_method"], "mcts")
        self.assertLessEqual(search_meta["n_simulations"], 30)
        self.assertLessEqual(search_meta["n_pairs_scored"], search_meta["n_simulations"])
        self.assertGreaterEqual(search_meta["cache_hits"], 0)
        self.assertIn("truncated", search_meta)

        for p in top_pairs:
            self.assertEqual(p["search_method"], "mcts")
            self.assertIsNone(p["faithfulness"])
            self.assertIn("mcts_visits", p)
            self.assertGreaterEqual(p["mcts_visits"], 1)
            # Zinc absent
            self.assertNotIn(p["drug_a"], {"DB14533", "DB01593"})
            self.assertNotIn(p["drug_b"], {"DB14533", "DB01593"})
            self.assertNotIn("zinc", p["drug_a_name"].lower())
            self.assertNotIn("zinc", p["drug_b_name"].lower())

        # Strictly sorted by p_synergy descending
        for i in range(len(top_pairs) - 1):
            self.assertGreaterEqual(
                top_pairs[i]["p_synergy"],
                top_pairs[i + 1]["p_synergy"] - 1e-6,
                f"MCTS Rank {i+1} score {top_pairs[i]['p_synergy']} should be >= Rank {i+2} score {top_pairs[i+1]['p_synergy']}"
            )

        # Confirm full explanation retains faithfulness null and passes mcts_visits
        explanations = get_full_explanations_for_top_k(
            top_k_pairs=top_pairs,
            cell_line_name="T98G",
            module=self.module,
            heterodata=self.heterodata,
            device=self.device,
            inspect_top_k=0,
        )
        self.assertEqual(len(explanations), 3)
        for expl in explanations:
            self.assertIsNone(expl.get("faithfulness"))
            self.assertIsNone(expl.get("literature"))
            self.assertEqual(expl.get("search_method"), "mcts")
            self.assertIn("mcts_visits", expl)

    def test_mcts_diverse_first_drugs(self):
        """Test that UCT exploration allows MCTS to return combinations with more than one distinct anchor drug."""
        top_pairs, _ = beam_search_combinations(
            disease_name="glioblastoma",
            cell_line_name="T98G",
            heterodata=self.heterodata,
            module=self.module,
            device=self.device,
            max_candidate_drugs=10,
            top_k=4,
            search_method="mcts",
            n_simulations=35,
            mcts_c=1.414,
            time_budget_sec=15.0,
        )
        first_drugs = {p["drug_a"] for p in top_pairs}
        # In glioblastoma with UCT c=1.414, top 4 hits span multiple distinct anchor drugs
        self.assertGreater(len(first_drugs), 1, f"Expected >1 distinct first drug in top-4 MCTS hits, got {first_drugs}")


if __name__ == "__main__":
    unittest.main()
