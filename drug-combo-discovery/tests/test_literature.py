"""
Unit tests for literature RAG retrieval via NCBI E-utilities in src/literature.py.
Uses mocked NCBI responses to guarantee hermetic, offline testing without hitting live NCBI.
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from literature import (
    retrieve_literature_rag,
    _extract_best_snippet,
    _rank_and_format_citations,
    _LITERATURE_CACHE,
)


class TestLiteratureRAG(unittest.TestCase):
    def setUp(self):
        _LITERATURE_CACHE.clear()

    @patch("literature._esearch")
    @patch("literature._efetch_xml")
    def test_mocked_ncbi_retrieval_success(self, mock_efetch, mock_esearch):
        """Verify parsing of real-format PubMed articles and structure of citations."""
        mock_esearch.return_value = ["12345678", "87654321"]
        mock_efetch.return_value = [
            {
                "pmid": "12345678",
                "title": "Combined Procarbazine and Carmustine in glioblastoma therapy.",
                "year": "2023",
                "journal": "Neuro-Oncology Advances",
                "first_author": "Smith AB",
                "abstract": "BACKGROUND: Glioblastoma patients face poor prognosis. RESULTS: Procarbazine combined with Carmustine demonstrated synergistic cytotoxicity in glioma models. CONCLUSION: Dual alkylating therapy warrants further investigation.",
                "url": "https://pubmed.ncbi.nlm.nih.gov/12345678/",
            },
            {
                "pmid": "87654321",
                "title": "Carmustine mechanisms in recurrent brain tumors.",
                "year": "2021",
                "journal": "Journal of Neuro-Oncology",
                "first_author": "Doe CD",
                "abstract": "Carmustine remains an essential alkylating agent in high-grade glioma. We analyzed cell cycle arrest.",
                "url": "https://pubmed.ncbi.nlm.nih.gov/87654321/",
            },
        ]

        result = retrieve_literature_rag(
            drug_a_name="Procarbazine",
            drug_b_name="Carmustine",
            disease_context="glioblastoma",
            top_edges=[{"source": "Procarbazine", "target": "MGMT", "importance": 0.1}],
            explanation_text="Procarbazine and Carmustine demonstrate synergistic potential.",
            max_citations=3,
        )

        self.assertEqual(result["retrieval_method"], "ncbi_eutilities_rag")
        self.assertIsNone(result["error"])
        self.assertGreaterEqual(len(result["citations"]), 1)

        # Assert every citation has a valid non-empty pmid
        for cite in result["citations"]:
            self.assertIn("pmid", cite)
            self.assertTrue(bool(cite["pmid"]))
            self.assertIn("title", cite)
            self.assertIn("url", cite)
            self.assertTrue(cite["url"].startswith("https://pubmed.ncbi.nlm.nih.gov/"))
            self.assertIn("snippet", cite)
            self.assertTrue(len(cite["snippet"]) > 10)
            self.assertIn("match_reason", cite)

        # First citation mentions both drugs -> combination evidence
        top_cite = result["citations"][0]
        self.assertEqual(top_cite["pmid"], "12345678")
        self.assertEqual(top_cite["evidence_type"], "combination")
        self.assertIn("both Procarbazine and Carmustine", top_cite["match_reason"])

    @patch("literature._esearch")
    def test_empty_ncbi_returns_empty_citations_with_reason(self, mock_esearch):
        """Verify 0 hits from NCBI results in citations=[] and clear no_literature_reason."""
        mock_esearch.return_value = []

        result = retrieve_literature_rag(
            drug_a_name="UnknownDrugA",
            drug_b_name="UnknownDrugB",
            disease_context="rare_syndrome",
            top_edges=[],
            max_citations=3,
        )

        self.assertEqual(result["citations"], [])
        self.assertIsNotNone(result["no_literature_reason"])
        self.assertIn("No matching PubMed records found", result["no_literature_reason"])
        self.assertIsNone(result["error"])

    @patch("literature._esearch")
    @patch("literature._efetch_xml")
    def test_single_drug_support_labeling(self, mock_efetch, mock_esearch):
        """Verify that papers mentioning only one drug are correctly labeled as single-drug support."""
        mock_esearch.return_value = ["99999999"]
        mock_efetch.return_value = [
            {
                "pmid": "99999999",
                "title": "Temozolomide in glioblastoma targeting MGMT pathway.",
                "year": "2020",
                "journal": "Cancer Research",
                "first_author": "Lee K",
                "abstract": "Temozolomide induces DNA methylation and targets MGMT in glioblastoma cell models.",
                "url": "https://pubmed.ncbi.nlm.nih.gov/99999999/",
            }
        ]

        result = retrieve_literature_rag(
            drug_a_name="Temozolomide",
            drug_b_name="Irinotecan",
            disease_context="glioblastoma",
            top_edges=[{"source": "Temozolomide", "target": "MGMT", "importance": 0.2}],
            max_citations=1,
        )

        self.assertEqual(len(result["citations"]), 1)
        cite = result["citations"][0]
        self.assertEqual(cite["evidence_type"], "single_drug")
        self.assertIn("Single-drug support", cite["match_reason"])

    def test_snippet_extraction(self):
        """Verify extraction of relevant snippet from raw abstract text."""
        abstract = (
            "Glioblastoma is an aggressive brain tumor with high recurrence rates. "
            "In this study, we evaluated the combination of Carmustine and Procarbazine in glioblastoma cells. "
            "The combination produced a 75% reduction in clonogenic survival compared to single agents. "
            "These findings demonstrate potent synergistic activity in preclinical models."
        )
        snippet = _extract_best_snippet(abstract, ["Carmustine", "Procarbazine", "glioblastoma"])
        self.assertIn("Carmustine and Procarbazine", snippet)

    @patch("literature._esearch")
    @patch("literature._efetch_xml")
    def test_query_excludes_unrelated_subgraph_diseases(self, mock_efetch, mock_esearch):
        """
        Verify building a query with subgraph diseases [glioblastoma, breast carcinoma, pyoureter]
        and user disease glioblastoma MUST NOT include breast carcinoma or pyoureter.
        """
        mock_esearch.return_value = ["11111111"]
        mock_efetch.return_value = [{
            "pmid": "11111111",
            "title": "Study of Temozolomide and Cyclophosphamide in glioblastoma",
            "year": "2022",
            "journal": "Neuro-Oncology",
            "first_author": "Clark D",
            "abstract": "We evaluated Temozolomide and Cyclophosphamide combination in glioblastoma models.",
            "url": "https://pubmed.ncbi.nlm.nih.gov/11111111/",
        }]

        subgraph_edges = [
            {"source": "glioblastoma", "source_type": "disease", "target": "Temozolomide", "target_type": "drug", "relation": "indication"},
            {"source": "breast carcinoma", "source_type": "disease", "target": "Cyclophosphamide", "target_type": "drug", "relation": "indication"},
            {"source": "pyoureter", "source_type": "disease", "target": "Cyclophosphamide", "target_type": "drug", "relation": "contraindication"},
        ]

        result = retrieve_literature_rag(
            drug_a_name="Temozolomide",
            drug_b_name="Cyclophosphamide",
            disease_context="glioblastoma",
            top_edges=subgraph_edges,
            explanation_text="Temozolomide and Cyclophosphamide co-treatment.",
            max_citations=1,
        )

        query_used = result["query_used"].lower()
        self.assertNotIn("breast carcinoma", query_used)
        self.assertNotIn("pyoureter", query_used)
        self.assertIn("glioblastoma", query_used)
        self.assertIn("temozolomide", query_used)
        self.assertIn("cyclophosphamide", query_used)

    @patch("literature._esearch")
    @patch("literature._efetch_xml")
    def test_mocked_abstract_one_drug_not_combination(self, mock_efetch, mock_esearch):
        """
        Verify a mocked abstract that contains cyclophosphamide but not temozolomide
        MUST NOT get evidence_type combination (must be single_drug).
        """
        mock_esearch.return_value = ["22222222"]
        mock_efetch.return_value = [{
            "pmid": "22222222",
            "title": "Adjuvant alternating electric fields with chemotherapy in cancer cell lines",
            "year": "2009",
            "journal": "BMC Medical Physics",
            "first_author": "Kirson ED",
            "abstract": (
                "Cell proliferation was studied in breast carcinoma and glioma cell lines exposed to TTFields, "
                "paclitaxel, doxorubicin, and cyclophosphamide separately and in combinations."
            ),
            "url": "https://pubmed.ncbi.nlm.nih.gov/22222222/",
        }]

        result = retrieve_literature_rag(
            drug_a_name="Temozolomide",
            drug_b_name="Cyclophosphamide",
            disease_context="glioblastoma",
            top_edges=[],
            max_citations=1,
        )

        self.assertEqual(len(result["citations"]), 1)
        cite = result["citations"][0]
        # Must NOT be combination because temozolomide does not appear in abstract or title
        self.assertNotEqual(cite["evidence_type"], "combination")
        self.assertEqual(cite["evidence_type"], "single_drug")
        self.assertIn("Single-drug support", cite["match_reason"])
        self.assertNotIn("both Temozolomide and Cyclophosphamide", cite["match_reason"])

    @patch("literature._esearch")
    @patch("literature._efetch_xml")
    def test_mocked_abstract_both_drugs_gets_combination(self, mock_efetch, mock_esearch):
        """
        Verify a mocked abstract containing both procarbazine and carmustine MAY get combination.
        """
        mock_esearch.return_value = ["33333333"]
        mock_efetch.return_value = [{
            "pmid": "33333333",
            "title": "Combination of Procarbazine, Carmustine, and Vincristine in recurrent glioblastoma",
            "year": "2012",
            "journal": "Journal of Neuro-Oncology",
            "first_author": "Kuhnhenn J",
            "abstract": (
                "In this observational study we recorded the efficacy and toxicity of a combination of "
                "procarbazine, carmustine, and vincristine (PBV) for 69 patients with recurrent glioblastoma."
            ),
            "url": "https://pubmed.ncbi.nlm.nih.gov/33333333/",
        }]

        result = retrieve_literature_rag(
            drug_a_name="Procarbazine",
            drug_b_name="Carmustine",
            disease_context="glioblastoma",
            top_edges=[],
            max_citations=1,
        )

        self.assertEqual(len(result["citations"]), 1)
        cite = result["citations"][0]
        self.assertEqual(cite["evidence_type"], "combination")
        self.assertIn("Combination evidence", cite["match_reason"])
        self.assertIn("both Procarbazine and Carmustine", cite["match_reason"])


if __name__ == "__main__":
    unittest.main()

