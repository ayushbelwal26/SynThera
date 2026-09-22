"""
Generate extra generalization splits:
  (a) Warm/random split: standard pair-level random split stratified by synergy_class
  (b) Leave-cell-line-out: hold out ~20% of cell lines entirely for test
  (c) Leave-tissue-out: hold out 1-2 entire tissues for test

Saves to data/processed/splits_extra/
Does NOT modify data/processed/split_{train,val,test}.csv or heterodata.pt.
"""

import os
import random
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")
SPLITS_EXTRA_DIR = os.path.join(PROCESSED_DIR, "splits_extra")
os.makedirs(SPLITS_EXTRA_DIR, exist_ok=True)

LABELS_CSV = os.path.join(PROCESSED_DIR, "labeled_pairs.csv")
CELL_META_CSV = os.path.join(PROCESSED_DIR, "cell_line_metadata.csv")


def get_unique_drugs(df: pd.DataFrame) -> set:
    return set(df["drug_a_kg_id"].unique()) | set(df["drug_b_kg_id"].unique())


def summarize_split(split_name: str, train_df: pd.DataFrame, val_df: pd.DataFrame, test_df: pd.DataFrame):
    total = len(train_df) + len(val_df) + len(test_df)
    print(f"\n{'=' * 80}")
    print(f"  SPLIT: {split_name.upper()} (Total pairs: {total:,})")
    print(f"{'=' * 80}")
    
    for name, df in [("Train", train_df), ("Val", val_df), ("Test", test_df)]:
        n_pairs = len(df)
        pct = n_pairs / total * 100
        n_drugs = len(get_unique_drugs(df))
        n_cls = df["cell_line_name"].nunique()
        syn_cnt = (df["synergy_class"] == "synergy").sum()
        add_cnt = (df["synergy_class"] == "additive").sum()
        ant_cnt = (df["synergy_class"] == "antagonism").sum()
        print(f"  {name:<6}: {n_pairs:>7,} pairs ({pct:>5.1f}%) | {n_drugs:>4} drugs | {n_cls:>2} cell lines | "
              f"Classes: syn={syn_cnt:>6,} ({syn_cnt/n_pairs*100:4.1f}%), "
              f"add={add_cnt:>6,} ({add_cnt/n_pairs*100:4.1f}%), "
              f"ant={ant_cnt:>6,} ({ant_cnt/n_pairs*100:4.1f}%)")


def build_warm_random(labels: pd.DataFrame):
    """
    (a) Warm/random split at the pair level.
    Stratify by synergy_class to maintain label balance across splits.
    Proportions match existing split: Train ~51.8%, Val ~23.2%, Test ~25.0%.
    """
    indices = np.arange(len(labels))
    classes = labels["synergy_class"].values

    # Step 1: Hold out 24.9747% for test (exact match: 37,778 pairs)
    train_val_idx, test_idx = train_test_split(
        indices,
        test_size=37778,
        stratify=classes,
        random_state=42,
    )

    # Step 2: From remaining (113,486 pairs), hold out 35,072 for val
    train_val_classes = classes[train_val_idx]
    train_idx, val_idx = train_test_split(
        train_val_idx,
        test_size=35072,
        stratify=train_val_classes,
        random_state=42,
    )

    train_df = labels.iloc[train_idx]
    val_df = labels.iloc[val_idx]
    test_df = labels.iloc[test_idx]

    summarize_split("Warm / Random", train_df, val_df, test_df)

    # Save
    pd.DataFrame({"row_index": train_idx}).to_csv(os.path.join(SPLITS_EXTRA_DIR, "warm_random_train.csv"), index=False)
    pd.DataFrame({"row_index": val_idx}).to_csv(os.path.join(SPLITS_EXTRA_DIR, "warm_random_val.csv"), index=False)
    pd.DataFrame({"row_index": test_idx}).to_csv(os.path.join(SPLITS_EXTRA_DIR, "warm_random_test.csv"), index=False)

    return train_idx, val_idx, test_idx


def build_leave_cell_line(labels: pd.DataFrame):
    """
    (b) Leave-cell-line-out:
    Hold out ~20% of cell lines entirely for test (16 / 80 cell lines).
    Hold out ~15% for val (12 / 80 cell lines).
    Remaining 52 cell lines (65%) for train.
    Strict isolation: test cell lines strictly absent from train and val.
    """
    rng = random.Random(42)
    all_cell_lines = sorted(labels["cell_line_name"].unique())
    assert len(all_cell_lines) == 80, f"Expected 80 cell lines, found {len(all_cell_lines)}"

    shuffled = list(all_cell_lines)
    rng.shuffle(shuffled)

    test_cls = set(shuffled[:16])     # 16 cell lines (20.0%)
    val_cls = set(shuffled[16:28])    # 12 cell lines (15.0%)
    train_cls = set(shuffled[28:])    # 52 cell lines (65.0%)

    # Assertions on cell line sets
    assert len(test_cls & train_cls) == 0, "Test cell lines leak into train!"
    assert len(val_cls & train_cls) == 0, "Val cell lines leak into train!"
    assert len(test_cls & val_cls) == 0, "Test cell lines leak into val!"

    test_idx = labels.index[labels["cell_line_name"].isin(test_cls)].tolist()
    val_idx = labels.index[labels["cell_line_name"].isin(val_cls)].tolist()
    train_idx = labels.index[labels["cell_line_name"].isin(train_cls)].tolist()

    assert len(train_idx) + len(val_idx) + len(test_idx) == len(labels)

    train_df = labels.iloc[train_idx]
    val_df = labels.iloc[val_idx]
    test_df = labels.iloc[test_idx]

    # Confirm held-out entities strictly absent from train
    assert len(set(test_df["cell_line_name"]) & set(train_df["cell_line_name"])) == 0
    print(f"\n  [Integrity Check] Held-out cell lines in test ({len(test_cls)}) are strictly absent from train: CONFIRMED")

    summarize_split("Leave-Cell-Line-Out", train_df, val_df, test_df)
    print(f"  Test Cell Lines ({len(test_cls)}): {sorted(list(test_cls))}")
    print(f"  Val Cell Lines  ({len(val_cls)}): {sorted(list(val_cls))}")

    # Save
    pd.DataFrame({"row_index": train_idx}).to_csv(os.path.join(SPLITS_EXTRA_DIR, "leave_cell_line_train.csv"), index=False)
    pd.DataFrame({"row_index": val_idx}).to_csv(os.path.join(SPLITS_EXTRA_DIR, "leave_cell_line_val.csv"), index=False)
    pd.DataFrame({"row_index": test_idx}).to_csv(os.path.join(SPLITS_EXTRA_DIR, "leave_cell_line_test.csv"), index=False)

    return train_idx, val_idx, test_idx


def build_leave_tissue(labels: pd.DataFrame, meta: pd.DataFrame):
    """
    (c) Leave-tissue-out:
    Hold out 1-2 entire tissues for test (Breast: 8 cell lines, Ovary: 11 cell lines = 19 cell lines, 33,931 pairs, 22.4%).
    Hold out 1 tissue for val (CNS / Brain: 6 cell lines, 14,583 pairs, 9.6%).
    Remaining 8 tissues for train (55 cell lines, 102,750 pairs, 67.9%).
    Strict isolation: test tissues and cell lines strictly absent from train and val.
    """
    merged = labels.merge(meta[["cell_line_name", "tissue"]], on="cell_line_name", how="left")
    assert merged["tissue"].isna().sum() == 0, "Missing tissue in pairs!"

    test_tissues = {"Breast", "Ovary"}
    val_tissues = {"CNS / Brain"}
    train_tissues = set(meta["tissue"].unique()) - test_tissues - val_tissues

    assert len(test_tissues & train_tissues) == 0
    assert len(val_tissues & train_tissues) == 0
    assert len(test_tissues & val_tissues) == 0

    test_idx = merged.index[merged["tissue"].isin(test_tissues)].tolist()
    val_idx = merged.index[merged["tissue"].isin(val_tissues)].tolist()
    train_idx = merged.index[merged["tissue"].isin(train_tissues)].tolist()

    assert len(train_idx) + len(val_idx) + len(test_idx) == len(labels)

    train_df = merged.iloc[train_idx]
    val_df = merged.iloc[val_idx]
    test_df = merged.iloc[test_idx]

    # Confirm held out entities strictly absent from train
    assert len(set(test_df["tissue"]) & set(train_df["tissue"])) == 0
    assert len(set(test_df["cell_line_name"]) & set(train_df["cell_line_name"])) == 0
    print(f"\n  [Integrity Check] Held-out test tissues {test_tissues} and their cell lines are strictly absent from train: CONFIRMED")

    summarize_split("Leave-Tissue-Out", train_df, val_df, test_df)
    print(f"  Test Tissues ({len(test_tissues)}): {test_tissues} | Cell lines: {test_df['cell_line_name'].nunique()}")
    print(f"  Val Tissues  ({len(val_tissues)}): {val_tissues} | Cell lines: {val_df['cell_line_name'].nunique()}")
    print(f"  Train Tissues ({len(train_tissues)}): {train_tissues} | Cell lines: {train_df['cell_line_name'].nunique()}")

    # Save
    pd.DataFrame({"row_index": train_idx}).to_csv(os.path.join(SPLITS_EXTRA_DIR, "leave_tissue_train.csv"), index=False)
    pd.DataFrame({"row_index": val_idx}).to_csv(os.path.join(SPLITS_EXTRA_DIR, "leave_tissue_val.csv"), index=False)
    pd.DataFrame({"row_index": test_idx}).to_csv(os.path.join(SPLITS_EXTRA_DIR, "leave_tissue_test.csv"), index=False)

    return train_idx, val_idx, test_idx


def main():
    print("Loading labeled pairs and cell metadata...")
    labels = pd.read_csv(LABELS_CSV)
    meta = pd.read_csv(CELL_META_CSV)
    print(f"Total labeled pairs: {len(labels):,}")
    print(f"Total cell lines in metadata: {len(meta):,}")

    build_warm_random(labels)
    build_leave_cell_line(labels)
    build_leave_tissue(labels, meta)

    print("\nAll extra splits generated successfully in:", SPLITS_EXTRA_DIR)


if __name__ == "__main__":
    main()
