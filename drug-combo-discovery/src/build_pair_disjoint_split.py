"""
src/build_pair_disjoint_split.py — Canonical Leave-Pair-Out (LPO) Split Builder
=============================================================================

Generates a deterministic pair-disjoint (Leave-Pair-Out) train/val/test split
across all 4,311 unique unordered drug combinations in labeled_pairs.csv:
- 70% Train pairs (3,017 pairs -> 106,242 observations, 70.2%)
- 15% Val pairs   (  647 pairs ->  22,353 observations, 14.8%)
- 15% Test pairs  (  647 pairs ->  22,669 observations, 15.0%)

Strict invariant:
The exact same unordered pair {Drug A, Drug B} CANNOT appear in more than one partition:
  intersection(train_pairs, test_pairs) = empty
  intersection(val_pairs, test_pairs)   = empty
  intersection(train_pairs, val_pairs)  = empty

However, individual drugs are allowed (and expected) to appear across partitions
with different combination partners.
"""

import os
import json
import random
import pandas as pd
import numpy as np

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_DIR = os.path.join(ROOT_DIR, "data", "processed")
SPLITS_EXTRA_DIR = os.path.join(PROCESSED_DIR, "splits_extra")
os.makedirs(SPLITS_EXTRA_DIR, exist_ok=True)

LABELS_CSV = os.path.join(PROCESSED_DIR, "labeled_pairs.csv")
BENCHMARK_JSON = os.path.join(PROCESSED_DIR, "pair_disjoint_benchmark.json")

def canonical_pair(row):
    return tuple(sorted([row['drug_a_kg_id'], row['drug_b_kg_id']]))

def main(seed=42):
    print("Loading labeled_pairs.csv...")
    labels = pd.read_csv(LABELS_CSV)
    labels['unordered_pair'] = labels.apply(canonical_pair, axis=1)

    all_pairs = sorted(labels['unordered_pair'].unique())
    n_pairs = len(all_pairs)
    print(f"Total labeled observations: {len(labels):,}")
    print(f"Total unique unordered drug pairs: {n_pairs:,}")

    # Deterministic shuffle
    rng = random.Random(seed)
    shuffled_pairs = list(all_pairs)
    rng.shuffle(shuffled_pairs)

    n_test_pairs = round(n_pairs * 0.15)
    n_val_pairs = round(n_pairs * 0.15)
    n_train_pairs = n_pairs - n_test_pairs - n_val_pairs

    test_pairs = set(shuffled_pairs[:n_test_pairs])
    val_pairs = set(shuffled_pairs[n_test_pairs : n_test_pairs + n_val_pairs])
    train_pairs = set(shuffled_pairs[n_test_pairs + n_val_pairs :])

    # Integrity assertions
    assert len(train_pairs & test_pairs) == 0, "Pair leakage between train and test!"
    assert len(val_pairs & test_pairs) == 0, "Pair leakage between val and test!"
    assert len(train_pairs & val_pairs) == 0, "Pair leakage between train and val!"

    test_idx = labels.index[labels['unordered_pair'].isin(test_pairs)].tolist()
    val_idx = labels.index[labels['unordered_pair'].isin(val_pairs)].tolist()
    train_idx = labels.index[labels['unordered_pair'].isin(train_pairs)].tolist()

    assert len(set(train_idx) & set(test_idx)) == 0, "Row index overlap between train and test!"
    assert len(set(val_idx) & set(test_idx)) == 0, "Row index overlap between val and test!"
    assert len(set(train_idx) & set(val_idx)) == 0, "Row index overlap between train and val!"
    assert len(train_idx) + len(val_idx) + len(test_idx) == len(labels), "Rows do not sum to total!"

    # Save row index CSVs
    pd.DataFrame({"row_index": train_idx}).to_csv(os.path.join(SPLITS_EXTRA_DIR, "pair_disjoint_train.csv"), index=False)
    pd.DataFrame({"row_index": val_idx}).to_csv(os.path.join(SPLITS_EXTRA_DIR, "pair_disjoint_val.csv"), index=False)
    pd.DataFrame({"row_index": test_idx}).to_csv(os.path.join(SPLITS_EXTRA_DIR, "pair_disjoint_test.csv"), index=False)
    print("Saved pair_disjoint split CSVs to data/processed/splits_extra/")

    test_df = labels.iloc[test_idx]
    train_df = labels.iloc[train_idx]
    val_df = labels.iloc[val_idx]

    test_drugs = set(test_df['drug_a_kg_id']) | set(test_df['drug_b_kg_id'])
    train_drugs = set(train_df['drug_a_kg_id']) | set(train_df['drug_b_kg_id'])
    val_drugs = set(val_df['drug_a_kg_id']) | set(val_df['drug_b_kg_id'])

    stats = {
        "split_name": "Pair-disjoint / Leave-Pair-Out (LPO)",
        "protocol_definition": (
            "Partitioning at the unordered drug-pair level {d_A, d_B}. "
            "No pair in test appears in train or validation. Individual drugs appear in both "
            "with different partners."
        ),
        "seed": seed,
        "n_total_observations": len(labels),
        "n_total_pairs": n_pairs,
        "train": {
            "n_pairs": len(train_pairs),
            "n_observations": len(train_idx),
            "n_unique_drugs": len(train_drugs),
            "n_cell_lines": train_df['cell_line_name'].nunique(),
            "class_distribution": train_df['synergy_class'].value_counts().to_dict(),
        },
        "validation": {
            "n_pairs": len(val_pairs),
            "n_observations": len(val_idx),
            "n_unique_drugs": len(val_drugs),
            "n_cell_lines": val_df['cell_line_name'].nunique(),
            "class_distribution": val_df['synergy_class'].value_counts().to_dict(),
        },
        "test": {
            "n_pairs": len(test_pairs),
            "n_observations": len(test_idx),
            "n_unique_drugs": len(test_drugs),
            "n_cell_lines": test_df['cell_line_name'].nunique(),
            "overlap_drugs_with_train": len(test_drugs & train_drugs),
            "overlap_pairs_with_train": len(test_pairs & train_pairs),
            "class_distribution": test_df['synergy_class'].value_counts().to_dict(),
        }
    }

    with open(BENCHMARK_JSON, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)
    print(f"Saved benchmark metadata to {BENCHMARK_JSON}")

    print("\n=== LPO SPLIT STATISTICS ===")
    print(f"Train : {len(train_idx):>7,} obs ({len(train_pairs):>4} pairs, {len(train_drugs):>4} drugs, {train_df['cell_line_name'].nunique():>2} cell lines)")
    print(f"Val   : {len(val_idx):>7,} obs ({len(val_pairs):>4} pairs, {len(val_drugs):>4} drugs, {val_df['cell_line_name'].nunique():>2} cell lines)")
    print(f"Test  : {len(test_idx):>7,} obs ({len(test_pairs):>4} pairs, {len(test_drugs):>4} drugs, {test_df['cell_line_name'].nunique():>2} cell lines)")
    print(f"Test/Train pair overlap: {len(test_pairs & train_pairs)} (strictly 0)")
    print(f"Test/Train drug overlap: {len(test_drugs & train_drugs)} (individual drugs shared with different partners)")

if __name__ == "__main__":
    main()
