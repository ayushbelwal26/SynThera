import os
import torch
import numpy as np
import pandas as pd
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED = os.path.join(ROOT, "data", "processed")

heterodata = torch.load(os.path.join(PROCESSED, "heterodata.pt"), weights_only=False)

train_a = heterodata.label_train_drug_a.numpy()
train_b = heterodata.label_train_drug_b.numpy()
test_a = heterodata.label_test_drug_a.numpy()
test_b = heterodata.label_test_drug_b.numpy()

train_drugs = set(train_a) | set(train_b)
test_drugs = set(test_a) | set(test_b)
cold_test_drugs = test_drugs - train_drugs

print(f"Unique train drugs: {len(train_drugs)}")
print(f"Unique full test drugs: {len(test_drugs)}")
print(f"Unique cold test drugs: {len(cold_test_drugs)}")

# Drug-target edges in heterodata
dp_edge_index = heterodata["drug", "drug_protein", "gene/protein"].edge_index
drug_targets = Counter(dp_edge_index[0].numpy())

def analyze_drug_set(name, drug_set):
    counts = [drug_targets.get(d, 0) for d in drug_set]
    counts = np.array(counts)
    nonzero_mask = counts > 0
    pct_nonzero = float(np.mean(nonzero_mask)) * 100
    n_total = len(counts)
    n_nonzero = int(np.sum(nonzero_mask))
    
    min_c = int(np.min(counts)) if n_total > 0 else 0
    med_c = float(np.median(counts)) if n_total > 0 else 0
    mean_c = float(np.mean(counts)) if n_total > 0 else 0
    max_c = int(np.max(counts)) if n_total > 0 else 0
    
    # Also distribution among nonzero only:
    med_c_nonzero = float(np.median(counts[nonzero_mask])) if n_nonzero > 0 else 0
    mean_c_nonzero = float(np.mean(counts[nonzero_mask])) if n_nonzero > 0 else 0
    
    print(f"\n=======================================================")
    print(f"  SET: {name}")
    print(f"=======================================================")
    print(f"  Total unique drugs            : {n_total}")
    print(f"  Drugs with >= 1 target edge   : {n_nonzero} ({pct_nonzero:.2f}%)")
    print(f"  Drugs with 0 target edges     : {n_total - n_nonzero} ({100 - pct_nonzero:.2f}%)")
    print(f"  All drugs target count dist   : min={min_c}, median={med_c:.1f}, mean={mean_c:.2f}, max={max_c}")
    print(f"  Nonzero drugs target count    : median={med_c_nonzero:.1f}, mean={mean_c_nonzero:.2f}")
    
    return {
        "name": name,
        "n_total": n_total,
        "n_nonzero": n_nonzero,
        "pct_nonzero": pct_nonzero,
        "min": min_c,
        "median": med_c,
        "mean": mean_c,
        "max": max_c,
        "med_nonzero": med_c_nonzero,
        "mean_nonzero": mean_c_nonzero,
    }

res_train = analyze_drug_set("Train Drugs", train_drugs)
res_test = analyze_drug_set("Full Test Drugs", test_drugs)
res_cold = analyze_drug_set("Cold Test Drugs (184 drugs)", cold_test_drugs)

# Pair-level target coverage
# Both drugs have >= 1 target:
test_df_a = test_a
test_df_b = test_b
pair_both_nonzero = np.array([drug_targets.get(a, 0) > 0 and drug_targets.get(b, 0) > 0 for a, b in zip(test_df_a, test_df_b)])
print(f"\nFull Test Pairs Total         : {len(test_a)}")
print(f"Full Test Pairs Both Nonzero  : {pair_both_nonzero.sum()} ({pair_both_nonzero.mean()*100:.2f}%)")
