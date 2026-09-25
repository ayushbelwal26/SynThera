"""
src/build_leave_drug_out_benchmark.py — Leave-Drug-Out (LDO) Split & Benchmark Generator
========================================================================================

Establishes the formal Leave-Drug-Out (LDO) evaluation benchmark:
- 1,138 total unique drugs partitioned into:
  - 70% Train drugs (796 drugs)
  - 15% Val drugs   (171 drugs)
  - 15% Test drugs  (171 drugs)
  Strict invariant:
    intersection(test_drugs, train_drugs) = empty
    intersection(test_drugs, val_drugs)   = empty
    intersection(val_drugs, train_drugs)  = empty

Observations:
- Train: 78,414 observations (all drugs strictly from train_drugs)
- Validation: 29,141 observations (drugs strictly from train_drugs and val_drugs; 0 test drugs)
- Test (Clean LDO): 31,847 observations (every pair contains at least 1 held-out test drug, with 0 val contamination)
  - Sub-population 1: LDO-Single / DrugSingle (29,282 observations, exactly 1 held-out test drug + 1 known train drug)
  - Sub-population 2: LDO-Double / DrugDouble / Strict Bilateral (2,565 observations, both drugs held-out test drugs)
- Excluded Val/Test Cross Pairs: 5,931 observations (pairs mixing val and test drugs)
"""

import os
import json
import random
import pandas as pd
import numpy as np

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_DIR = os.path.join(ROOT_DIR, "data", "processed")
LABELS_CSV = os.path.join(PROCESSED_DIR, "labeled_pairs.csv")
SPLIT_TRAIN_CSV = os.path.join(PROCESSED_DIR, "split_train.csv")
SPLIT_VAL_CSV = os.path.join(PROCESSED_DIR, "split_val.csv")
SPLIT_TEST_CSV = os.path.join(PROCESSED_DIR, "split_test.csv")
LDO_BENCHMARK_JSON = os.path.join(PROCESSED_DIR, "leave_drug_out_benchmark.json")

def canonical_pair(row):
    return tuple(sorted([row['drug_a_kg_id'], row['drug_b_kg_id']]))

def main(seed=42):
    labels = pd.read_csv(LABELS_CSV)
    labels['unordered_pair'] = labels.apply(canonical_pair, axis=1)

    train_idx = pd.read_csv(SPLIT_TRAIN_CSV)['row_index'].values
    val_idx = pd.read_csv(SPLIT_VAL_CSV)['row_index'].values
    test_idx = pd.read_csv(SPLIT_TEST_CSV)['row_index'].values

    # Reconstruct drug partition (seed 42)
    rng = random.Random(seed)
    all_drugs = sorted(set(labels['drug_a_kg_id'].unique()) | set(labels['drug_b_kg_id'].unique()))
    rng.shuffle(all_drugs)
    n_total = len(all_drugs)
    n_test = max(1, round(n_total * 0.15))
    n_val = max(1, round(n_total * 0.15))

    test_drugs = set(all_drugs[:n_test])
    val_drugs = set(all_drugs[n_test : n_test + n_val])
    train_drugs = set(all_drugs[n_test + n_val :])

    # Assertions on drug sets
    assert len(test_drugs & train_drugs) == 0, "Test and train drugs overlap!"
    assert len(test_drugs & val_drugs) == 0, "Test and val drugs overlap!"
    assert len(val_drugs & train_drugs) == 0, "Val and train drugs overlap!"
    assert len(test_drugs) + len(val_drugs) + len(train_drugs) == n_total

    test_df = labels.iloc[test_idx].copy()
    val_df = labels.iloc[val_idx].copy()
    train_df = labels.iloc[train_idx].copy()

    # Clean LDO test set: test pairs with NO val drugs
    mask_clean_ldo = (~test_df['drug_a_kg_id'].isin(val_drugs)) & (~test_df['drug_b_kg_id'].isin(val_drugs))
    clean_ldo_df = test_df[mask_clean_ldo].copy()

    # Subsets of clean LDO
    mask_double = clean_ldo_df['drug_a_kg_id'].isin(test_drugs) & clean_ldo_df['drug_b_kg_id'].isin(test_drugs)
    double_df = clean_ldo_df[mask_double]
    single_df = clean_ldo_df[~mask_double]

    clean_ldo_drugs = set(clean_ldo_df['drug_a_kg_id']) | set(clean_ldo_df['drug_b_kg_id'])
    clean_val_df = val_df[(~val_df['drug_a_kg_id'].isin(test_drugs)) & (~val_df['drug_b_kg_id'].isin(test_drugs))]

    benchmark_data = {
        "split_name": "Leave-Drug-Out (LDO) / Cold-Drug Benchmark",
        "seed": seed,
        "protocol_definition": (
            "Partitioning at the individual drug entity level. A designated test drug must never "
            "appear in any training observation. Two core sub-evaluations exist: "
            "(1) DrugSingle (Unilateral): exactly 1 drug in test pair is novel/unseen; "
            "(2) DrugDouble (Bilateral): both drugs in test pair are novel/unseen."
        ),
        "drug_counts": {
            "total_unique_drugs": n_total,
            "train_drugs": len(train_drugs),
            "val_drugs": len(val_drugs),
            "test_drugs": len(test_drugs),
            "intersection_test_train": len(test_drugs & train_drugs),
            "intersection_test_val": len(test_drugs & val_drugs),
            "intersection_val_train": len(val_drugs & train_drugs),
        },
        "observation_counts": {
            "train_observations": len(train_df),
            "val_observations_total": len(val_df),
            "val_observations_clean": len(clean_val_df),
            "test_observations_clean_ldo": len(clean_ldo_df),
            "test_observations_drug_single": len(single_df),
            "test_observations_drug_double_strict": len(double_df),
            "excluded_val_test_cross_pairs": len(test_df) - len(clean_ldo_df),
        },
        "clean_ldo_test_statistics": {
            "n_observations": len(clean_ldo_df),
            "n_unique_drugs": len(clean_ldo_drugs),
            "n_held_out_test_drugs": len(clean_ldo_drugs & test_drugs),
            "n_known_train_partner_drugs": len(clean_ldo_drugs & train_drugs),
            "n_val_drugs": len(clean_ldo_drugs & val_drugs),
            "n_cell_lines": clean_ldo_df['cell_line_name'].nunique(),
            "n_unordered_pairs": clean_ldo_df['unordered_pair'].nunique(),
            "class_distribution": clean_ldo_df['synergy_class'].value_counts().to_dict(),
        },
        "drug_single_statistics": {
            "n_observations": len(single_df),
            "n_unique_drugs": len(set(single_df['drug_a_kg_id']) | set(single_df['drug_b_kg_id'])),
            "n_cell_lines": single_df['cell_line_name'].nunique(),
            "n_unordered_pairs": single_df['unordered_pair'].nunique(),
            "class_distribution": single_df['synergy_class'].value_counts().to_dict(),
        },
        "drug_double_statistics": {
            "n_observations": len(double_df),
            "n_unique_drugs": len(set(double_df['drug_a_kg_id']) | set(double_df['drug_b_kg_id'])),
            "n_cell_lines": double_df['cell_line_name'].nunique(),
            "n_unordered_pairs": double_df['unordered_pair'].nunique(),
            "class_distribution": double_df['synergy_class'].value_counts().to_dict(),
        },
        "evaluated_checkpoint": "models/synergy_gnn_pair_interaction.ckpt",
        "performance_summary": {
            "clean_ldo_all": {
                "n_pairs": 31847,
                "macro_auroc": 0.6542,
                "binary_synergy_auroc": 0.5662,
                "precision@3": 0.4304,
                "ndcg@3": 0.4426,
            },
            "drug_single_unilateral": {
                "n_pairs": 29282,
                "macro_auroc": 0.6569,
                "binary_synergy_auroc": 0.5683,
                "precision@3": 0.3945,
                "ndcg@3": 0.4161,
            },
            "drug_double_strict_bilateral": {
                "n_pairs": 2565,
                "macro_auroc": 0.6225,
                "binary_synergy_auroc": 0.5373,
                "precision@3": 0.4089,
                "ndcg@3": 0.5665,
            }
        }
    }

    with open(LDO_BENCHMARK_JSON, "w", encoding="utf-8") as f:
        json.dump(benchmark_data, f, indent=2)
    print(f"Saved LDO benchmark metadata to {LDO_BENCHMARK_JSON}")

if __name__ == "__main__":
    main()
