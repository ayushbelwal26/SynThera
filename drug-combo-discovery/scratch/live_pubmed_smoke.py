"""
scratch/live_pubmed_smoke.py -- Manual live smoke test for NCBI PubMed RAG retrieval.
Run manually to verify live connectivity to NCBI E-utilities:
  python scratch/live_pubmed_smoke.py
"""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from literature import retrieve_literature_rag

print("=" * 70)
print("  SYNTHERA: LIVE NCBI PUBMED RAG SMOKE TEST")
print("=" * 70)

# Test pair: Procarbazine + Carmustine for Glioblastoma
drug_a = "Procarbazine"
drug_b = "Carmustine"
disease = "glioblastoma"
top_edges = [
    {"source": "Procarbazine", "target": "MGMT", "importance": 0.15},
    {"source": "Carmustine", "target": "MGMT", "importance": 0.15},
    {"source": "fibrillary astrocytoma", "target": "Carmustine", "importance": 0.12},
]
explanation_text = "Procarbazine and Carmustine are both alkylating agents with precedent in malignant glioma."

print(f"\nQuerying PubMed for combination: {drug_a} + {drug_b} in {disease}...")
result = retrieve_literature_rag(
    drug_a_name=drug_a,
    drug_b_name=drug_b,
    disease_context=disease,
    top_edges=top_edges,
    explanation_text=explanation_text,
    max_citations=3,
)

print("\n--- RAG RETRIEVAL RESULT ---")
print(f"Method: {result.get('retrieval_method')}")
print(f"Query Used: {result.get('query_used')}")
print(f"Error: {result.get('error')}")
print(f"No Literature Reason: {result.get('no_literature_reason')}")
print(f"Total Citations: {len(result.get('citations', []))}")

for i, c in enumerate(result.get("citations", []), 1):
    print(f"\n[Citation #{i}]")
    print(f"  PMID         : {c['pmid']}")
    print(f"  Title        : {c['title']}")
    print(f"  Year         : {c['year']}")
    print(f"  Journal      : {c.get('journal')}")
    print(f"  First Author : {c.get('first_author')}")
    print(f"  Evidence Type: {c.get('evidence_type')}")
    print(f"  Match Reason : {c.get('match_reason')}")
    print(f"  Snippet      : {c.get('snippet')}")
    print(f"  PubMed URL   : {c['url']}")

print("\n" + "=" * 70)
print("Smoke test complete.")
print("=" * 70)
