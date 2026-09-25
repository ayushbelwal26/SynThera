"""
tests/test_predict_triple.py - Test Suite for Targeted Three-Drug Analysis (POST /predict-triple)

Verifies:
1. Consistency:
   - Procarbazine + Carmustine + Vincristine @ T98G returns identical aggregate_min,
     bottleneck_pair, and toxicity union numbers as manual computation through the
     existing /predict path and compose_triple_result().
   - Resolving by name ('Procarbazine', 'Carmustine', 'Vincristine') yields identical
     results to DrugBank IDs ('DB01168', 'DB00262', 'DB00541').
2. Error handling:
   - Unknown drug name returns clear HTTP 404 with identifier in message.
   - Duplicate drugs (e.g. A == B) return HTTP 400.
   - Unknown cell line returns HTTP 404.
3. Schema parity:
   - Response shape matches a /search-triple single result item field-for-field.
   - Includes mechanistic explanation_text in pair_ab, pair_ac, and pair_bc.
"""

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
APP = os.path.join(ROOT, "app")
for path in [SRC, APP]:
    if path not in sys.path:
        sys.path.insert(0, path)

from fastapi.testclient import TestClient
from main import app
from ranking import compute_pair_score_v
from triple_search import compose_triple_result, COMPOSITION_CAPTION


class TestPredictTripleEndpoint(unittest.TestCase):
    """Integration tests for POST /predict-triple."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_predict_triple_consistency_and_parity(self):
        """
        Verify that POST /predict-triple returns identical scores to manual pair computation
        and matches /search-triple item schema field-for-field.
        """
        payload = {
            "drug_a": "DB01168",  # Procarbazine
            "drug_b": "DB00262",  # Carmustine
            "drug_c": "DB00541",  # Vincristine
            "cell_line": "T98G",
        }
        resp = self.client.post("/predict-triple", json=payload)
        self.assertEqual(resp.status_code, 200, f"Failed: {resp.text}")
        data = resp.json()

        # 1. Verify schema parity field-for-field with /search-triple result items
        expected_fields = {
            "drug_a",
            "drug_a_name",
            "drug_b",
            "drug_b_name",
            "drug_c",
            "drug_c_name",
            "aggregate_min",
            "aggregate_mean",
            "score",
            "v_score",
            "triple_toxicity_penalty",
            "has_known_ddi",
            "bottleneck_pair",
            "pair_ab",
            "pair_ac",
            "pair_bc",
            "literature_all_three",
            "composition_caption",
        }
        self.assertTrue(expected_fields.issubset(data.keys()), f"Missing fields: {expected_fields - set(data.keys())}")

        # 2. Mandatory disclaimer check
        self.assertEqual(data["composition_caption"], COMPOSITION_CAPTION)

        # 3. Known toxic interaction check
        # Procarbazine + Carmustine has known myelosuppressive interaction in PrimeKG DDI
        self.assertTrue(data["has_known_ddi"])
        self.assertGreaterEqual(data["triple_toxicity_penalty"], 0.70)

        # 4. Bottleneck check
        # Procarbazine + Vincristine has lowest V-score (0.4044 post-fix symmetric) and is identified as bottleneck
        bottleneck = data["bottleneck_pair"]
        self.assertEqual(bottleneck["pair_key"], "pair_ac")
        self.assertEqual(data["aggregate_min"], bottleneck["v_score"])

        # 5. Explanations included in constituent pairs
        self.assertIn("explanation_text", data["pair_ab"])
        self.assertIn("explanation_text", data["pair_ac"])
        self.assertIn("explanation_text", data["pair_bc"])

        # 6. Manual computation parity check
        resp_ab = self.client.post("/predict", json={"drug_a": "DB01168", "drug_b": "DB00262", "cell_line": "T98G"}).json()
        resp_ac = self.client.post("/predict", json={"drug_a": "DB01168", "drug_b": "DB00541", "cell_line": "T98G"}).json()
        resp_bc = self.client.post("/predict", json={"drug_a": "DB00262", "drug_b": "DB00541", "cell_line": "T98G"}).json()

        manual_composed = compose_triple_result(
            drug_a={"drug_id": "DB01168", "drug_name": "Procarbazine"},
            drug_b={"drug_id": "DB00262", "drug_name": "Carmustine"},
            drug_c={"drug_id": "DB00541", "drug_name": "Vincristine"},
            pair_ab=resp_ab["ranking"],
            pair_ac=resp_ac["ranking"],
            pair_bc=resp_bc["ranking"],
        )

        self.assertAlmostEqual(data["aggregate_min"], manual_composed["aggregate_min"], places=4)
        self.assertAlmostEqual(data["aggregate_mean"], manual_composed["aggregate_mean"], places=4)
        self.assertAlmostEqual(data["triple_toxicity_penalty"], manual_composed["triple_toxicity_penalty"], places=4)
        self.assertEqual(data["has_known_ddi"], manual_composed["has_known_ddi"])
        self.assertEqual(data["bottleneck_pair"]["pair_key"], manual_composed["bottleneck_pair"]["pair_key"])

        # 7. Bottleneck inspection payload check
        self.assertIn("bottleneck_inspect", data)
        btn_insp = data["bottleneck_inspect"]
        self.assertIn("top_edges", btn_insp)
        self.assertIsInstance(btn_insp["top_edges"], list)
        self.assertGreater(len(btn_insp["top_edges"]), 0)
        self.assertIn("explanation_text", btn_insp)
        self.assertIn("supporting_literature", btn_insp)
        self.assertEqual(btn_insp["drug_a"], "DB01168")
        self.assertEqual(btn_insp["drug_b"], "DB00541")
        self.assertEqual(btn_insp["drug_a_name"], "Procarbazine")
        self.assertEqual(btn_insp["drug_b_name"], "Vincristine")

    def test_bottleneck_only_literature_requested(self):
        """
        Verify that PubMed literature retrieval is ONLY executed for the bottleneck pair,
        and never batch-requested for the other two constituent pairs.
        """
        from unittest.mock import patch

        payload = {
            "drug_a": "DB01168",
            "drug_b": "DB00262",
            "drug_c": "DB00541",
            "cell_line": "T98G",
            "disease": "glioblastoma",
        }

        # Clear prediction cache for bottleneck pair to force a fresh run
        from main import PREDICTION_CACHE
        key_ac = (tuple(sorted(["DB01168", "DB00541"])), "T98G", "glioblastoma")
        PREDICTION_CACHE.pop(key_ac, None)

        with patch("literature.retrieve_literature_rag") as mock_rag:
            mock_rag.return_value = {
                "citations": [
                    {
                        "pmid": "12345678",
                        "title": "Procarbazine and Vincristine in Brain Tumors",
                        "abstract": "Synergy test abstract.",
                        "journal": "Neuro-Oncol",
                        "year": 2024,
                    }
                ],
                "count": 1,
                "query_used": "mock query",
                "retrieval_method": "mock",
            }
            resp = self.client.post("/predict-triple", json=payload)
            self.assertEqual(resp.status_code, 200)
            data = resp.json()

            # Ensure bottleneck_inspect is returned
            self.assertIn("bottleneck_inspect", data)
            btn_insp = data["bottleneck_inspect"]
            self.assertEqual(btn_insp["drug_a"], "DB01168")
            self.assertEqual(btn_insp["drug_b"], "DB00541")

            # Literature RAG must be invoked at most once, and ONLY for the bottleneck pair
            self.assertLessEqual(mock_rag.call_count, 1)
            if mock_rag.call_count == 1:
                call_kwargs = mock_rag.call_args.kwargs
                called_drugs = {call_kwargs.get("drug_a_name"), call_kwargs.get("drug_b_name")}
                self.assertEqual(called_drugs, {"Procarbazine", "Vincristine"})

    def test_predict_triple_by_drug_names(self):
        """
        Verify resolving compounds by common names yields identical results to DrugBank IDs.
        """
        payload_names = {
            "drug_a": "procarbazine",
            "drug_b": "carmustine",
            "drug_c": "vincristine",
            "cell_line": "t98g",
        }
        resp_names = self.client.post("/predict-triple", json=payload_names)
        self.assertEqual(resp_names.status_code, 200)
        data_names = resp_names.json()

        self.assertEqual(data_names["drug_a"], "DB01168")
        self.assertEqual(data_names["drug_b"], "DB00262")
        self.assertEqual(data_names["drug_c"], "DB00541")
        self.assertTrue(data_names["has_known_ddi"])
        self.assertEqual(data_names["bottleneck_pair"]["pair_key"], "pair_ac")
        self.assertIn("bottleneck_inspect", data_names)

    def test_unknown_drug_returns_404(self):
        """
        Verify invalid drug name returns HTTP 404 with failing identifier mentioned.
        """
        payload = {
            "drug_a": "NonExistentDrugXYZ123",
            "drug_b": "Carmustine",
            "drug_c": "Vincristine",
            "cell_line": "T98G",
        }
        resp = self.client.post("/predict-triple", json=payload)
        self.assertEqual(resp.status_code, 404)
        self.assertIn("NonExistentDrugXYZ123", resp.json()["detail"])

    def test_duplicate_drugs_return_400(self):
        """
        Verify passing identical drugs returns HTTP 400.
        """
        payload = {
            "drug_a": "Procarbazine",
            "drug_b": "Procarbazine",
            "drug_c": "Vincristine",
            "cell_line": "T98G",
        }
        resp = self.client.post("/predict-triple", json=payload)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("three distinct drugs", resp.json()["detail"])

    def test_unknown_cell_line_returns_404(self):
        """
        Verify invalid cell line returns HTTP 404.
        """
        payload = {
            "drug_a": "Procarbazine",
            "drug_b": "Carmustine",
            "drug_c": "Vincristine",
            "cell_line": "NonExistentCellLine999",
        }
        resp = self.client.post("/predict-triple", json=payload)
        self.assertEqual(resp.status_code, 404)
        self.assertIn("NonExistentCellLine999", resp.json()["detail"])


if __name__ == "__main__":
    unittest.main()
