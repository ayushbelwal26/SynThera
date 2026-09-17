import sys
import os
sys.path.insert(0, "src")
from search import score_candidate_pairs

print("Running score_candidate_pairs for glioblastoma @ T98G...")
top_pairs = score_candidate_pairs("glioblastoma", "T98G", top_k=5)
for i, p in enumerate(top_pairs, 1):
    print(f"{i}. {p['drug_a_name']} ({p['drug_a']}) + {p['drug_b_name']} ({p['drug_b']}) | p_syn={p['p_synergy']:.4f} tier={p['pair_tier_name']}")
