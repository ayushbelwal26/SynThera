"""
src/build_random_split.py — Random / Warm Observation-Level Split Builder
==========================================================================

PURPOSE
-------
Builds a 70/15/15 observation-level random split across all 151,264 rows
of labeled_pairs.csv for the Random/Warm benchmark.

In a random/warm split the SPLIT UNIT is the individual observation/row,
not the drug or drug-pair.  This means:
  - Individual drugs may appear in all three partitions.
  - Individual unordered drug pairs may appear in all three partitions.
  - Drug-cell-line combinations may appear in all three partitions.

This is intentionally different from the cold-drug splits used for the
headline SynThera benchmarks.  It exists purely so SynThera performance
can be compared with literature that uses random splits.

IMPORTANT LEAKAGE NOTE
----------------------
Because individual drugs, pairs, and cell lines overlap across partitions,
this benchmark is a WARM benchmark — it cannot be used to claim inductive
zero-shot generalisation.  Any model trained on this split and evaluated on
its test set benefits from having seen the same drugs (and often the same
pairs in other cell lines) during training.

This file documents the overlap statistics exhaustively in random_benchmark.json.

PROTECTED FILES — NEVER TOUCHED
--------------------------------
  models/synergy_gnn_pair_interaction.ckpt
  data/processed/pair_disjoint_benchmark.json
  data/processed/leave_drug_out_benchmark.json
  data/processed/strict_bilateral_benchmark.json
  data/processed/split_train.csv
  data/processed/split_val.csv
  data/processed/split_test.csv

OUTPUT
------
  data/processed/splits_random/random_train.csv   (row_index)
  data/processed/splits_random/random_val.csv     (row_index)
  data/processed/splits_random/random_test.csv    (row_index)
  data/processed/random_benchmark.json
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import datetime

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED  = os.path.join(ROOT_DIR, "data", "processed")
SPLITS_DIR = os.path.join(PROCESSED, "splits_random")

LABELS_CSV        = os.path.join(PROCESSED, "labeled_pairs.csv")
BENCHMARK_JSON    = os.path.join(PROCESSED, "random_benchmark.json")

# Output CSVs
RANDOM_TRAIN_CSV  = os.path.join(SPLITS_DIR, "random_train.csv")
RANDOM_VAL_CSV    = os.path.join(SPLITS_DIR, "random_val.csv")
RANDOM_TEST_CSV   = os.path.join(SPLITS_DIR, "random_test.csv")

# Protected files that must NEVER be overwritten
PROTECTED_FILES = [
    os.path.join(ROOT_DIR, "models", "synergy_gnn_pair_interaction.ckpt"),
    os.path.join(PROCESSED, "pair_disjoint_benchmark.json"),
    os.path.join(PROCESSED, "leave_drug_out_benchmark.json"),
    os.path.join(PROCESSED, "strict_bilateral_benchmark.json"),
    os.path.join(PROCESSED, "split_train.csv"),
    os.path.join(PROCESSED, "split_val.csv"),
    os.path.join(PROCESSED, "split_test.csv"),
]

# ---------------------------------------------------------------------------
# Split configuration
# ---------------------------------------------------------------------------
SEED       = 42
TRAIN_FRAC = 0.70
VAL_FRAC   = 0.15
TEST_FRAC  = 0.15

assert abs(TRAIN_FRAC + VAL_FRAC + TEST_FRAC - 1.0) < 1e-9


# ---------------------------------------------------------------------------
# Safety check
# ---------------------------------------------------------------------------

def _check_protected_files() -> None:
    """Abort if any protected file would be in our output paths."""
    output_paths = {
        os.path.abspath(p)
        for p in [RANDOM_TRAIN_CSV, RANDOM_VAL_CSV, RANDOM_TEST_CSV, BENCHMARK_JSON]
    }
    for pf in PROTECTED_FILES:
        abs_pf = os.path.abspath(pf)
        if abs_pf in output_paths:
            raise RuntimeError(
                f"SAFETY ABORT: output path collides with protected file: {pf}"
            )


def _sha256_short(path: str) -> str:
    if not os.path.exists(path):
        return "MISSING"
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Canonical pair helper
# ---------------------------------------------------------------------------

def canonical_pair(da: str, db: str) -> tuple[str, str]:
    return tuple(sorted([da, db]))


# ---------------------------------------------------------------------------
# Main build logic
# ---------------------------------------------------------------------------

def build_random_split(
    seed: int = SEED,
    train_frac: float = TRAIN_FRAC,
    val_frac: float = VAL_FRAC,
    test_frac: float = TEST_FRAC,
    labels_csv: str = LABELS_CSV,
    out_dir: str = SPLITS_DIR,
    benchmark_json: str = BENCHMARK_JSON,
    verbose: bool = True,
) -> dict:
    """
    Build and save the random/warm observation-level split.

    Parameters
    ----------
    seed : int
        Random seed for reproducibility (default 42).
    train_frac / val_frac / test_frac : float
        Fractional sizes (must sum to 1.0).
    labels_csv : str
        Path to labeled_pairs.csv.
    out_dir : str
        Directory where random_train/val/test.csv are saved.
    benchmark_json : str
        Path to write random_benchmark.json.
    verbose : bool
        Whether to print progress.

    Returns
    -------
    dict
        The benchmark metadata dictionary that was written to benchmark_json.
    """
    _check_protected_files()
    os.makedirs(out_dir, exist_ok=True)

    # ── 1. Load labels ────────────────────────────────────────────
    if verbose:
        print("=" * 72)
        print("  SynThera — Random / Warm Observation-Level Split Builder")
        print("=" * 72)
        print(f"\n  Loading: {labels_csv}")

    labels = pd.read_csv(labels_csv)
    n_total = len(labels)

    if verbose:
        print(f"  Total observations  : {n_total:,}")
        print(f"  Unique drugs        : {len(set(labels['drug_a_kg_id'].unique()) | set(labels['drug_b_kg_id'].unique())):,}")
        uniq_pairs = labels.apply(lambda r: canonical_pair(r['drug_a_kg_id'], r['drug_b_kg_id']), axis=1).nunique()
        print(f"  Unique unord. pairs : {uniq_pairs:,}")
        print(f"  Unique cell lines   : {labels['cell_line_name'].nunique():,}")
        print(f"\n  Split fractions     : train={train_frac:.0%}  val={val_frac:.0%}  test={test_frac:.0%}")
        print(f"  Seed                : {seed}")

    # ── 2. Deterministic row-level random shuffle ─────────────────
    rng = np.random.default_rng(seed)
    shuffled_row_indices = rng.permutation(n_total)  # [0..n_total-1] shuffled

    n_test  = max(1, round(n_total * test_frac))
    n_val   = max(1, round(n_total * val_frac))
    n_train = n_total - n_test - n_val

    # Assignment order: test first, then val, then train
    # (mirrors the drug-level split convention in the project)
    test_idx  = sorted(shuffled_row_indices[:n_test].tolist())
    val_idx   = sorted(shuffled_row_indices[n_test : n_test + n_val].tolist())
    train_idx = sorted(shuffled_row_indices[n_test + n_val :].tolist())

    # ── 3. Integrity assertions ───────────────────────────────────
    train_set = set(train_idx)
    val_set   = set(val_idx)
    test_set  = set(test_idx)

    assert len(train_set & test_set) == 0, "BUG: row overlap between train and test!"
    assert len(val_set   & test_set) == 0, "BUG: row overlap between val and test!"
    assert len(train_set & val_set)  == 0, "BUG: row overlap between train and val!"
    assert len(train_set | val_set | test_set) == n_total, "BUG: rows do not cover full dataset!"
    assert n_train + n_val + n_test == n_total, "BUG: partition counts do not sum to total!"

    if verbose:
        print(f"\n  Row counts:")
        print(f"    train : {n_train:>8,}  ({n_train/n_total:.1%})")
        print(f"    val   : {n_val:>8,}  ({n_val/n_total:.1%})")
        print(f"    test  : {n_test:>8,}  ({n_test/n_total:.1%})")
        print(f"  Row overlap assertions: PASS")

    # ── 4. Build partition dataframes ────────────────────────────
    train_df = labels.iloc[train_idx]
    val_df   = labels.iloc[val_idx]
    test_df  = labels.iloc[test_idx]

    # ── 5. Drug overlap statistics ────────────────────────────────
    train_drugs = set(train_df["drug_a_kg_id"]) | set(train_df["drug_b_kg_id"])
    val_drugs   = set(val_df["drug_a_kg_id"])   | set(val_df["drug_b_kg_id"])
    test_drugs  = set(test_df["drug_a_kg_id"])  | set(test_df["drug_b_kg_id"])

    drug_train_test_overlap = len(train_drugs & test_drugs)
    drug_val_test_overlap   = len(val_drugs   & test_drugs)

    if verbose:
        print(f"\n  Drug overlap (EXPECTED in warm split):")
        print(f"    Unique drugs in train : {len(train_drugs):,}")
        print(f"    Unique drugs in val   : {len(val_drugs):,}")
        print(f"    Unique drugs in test  : {len(test_drugs):,}")
        print(f"    Train/Test drug overlap : {drug_train_test_overlap:,}")
        print(f"    Val/Test   drug overlap : {drug_val_test_overlap:,}")

    # ── 6. Pair overlap statistics ────────────────────────────────
    def _pair_set(df: pd.DataFrame) -> set[tuple[str, str]]:
        return {canonical_pair(r.drug_a_kg_id, r.drug_b_kg_id) for _, r in df.iterrows()}

    if verbose:
        print(f"\n  Computing pair sets (this may take a moment)...")

    train_pairs = _pair_set(train_df)
    val_pairs   = _pair_set(val_df)
    test_pairs  = _pair_set(test_df)

    pair_train_test_overlap = len(train_pairs & test_pairs)
    pair_val_test_overlap   = len(val_pairs   & test_pairs)

    if verbose:
        print(f"\n  Pair overlap (EXPECTED in warm split):")
        print(f"    Unique pairs in train : {len(train_pairs):,}")
        print(f"    Unique pairs in val   : {len(val_pairs):,}")
        print(f"    Unique pairs in test  : {len(test_pairs):,}")
        print(f"    Train/Test pair overlap : {pair_train_test_overlap:,}")
        print(f"    Val/Test   pair overlap : {pair_val_test_overlap:,}")

    # ── 7. Observation-level leakage characterisation ─────────────
    # For test observations: how many involve pairs seen in train?
    test_pair_in_train_mask = test_df.apply(
        lambda r: canonical_pair(r.drug_a_kg_id, r.drug_b_kg_id) in train_pairs, axis=1
    )
    test_obs_with_train_pair = int(test_pair_in_train_mask.sum())

    test_drug_a_in_train = test_df["drug_a_kg_id"].isin(train_drugs)
    test_drug_b_in_train = test_df["drug_b_kg_id"].isin(train_drugs)
    test_obs_both_drugs_in_train = int((test_drug_a_in_train & test_drug_b_in_train).sum())
    test_obs_any_drug_in_train   = int((test_drug_a_in_train | test_drug_b_in_train).sum())

    test_cl_in_train = test_df["cell_line_name"].isin(set(train_df["cell_line_name"]))
    test_obs_cl_in_train = int(test_cl_in_train.sum())

    if verbose:
        print(f"\n  Test observation leakage characterisation:")
        print(f"    Test obs. with pair seen in train : {test_obs_with_train_pair:,} / {n_test:,}"
              f"  ({test_obs_with_train_pair/n_test:.1%})")
        print(f"    Test obs. any drug in train       : {test_obs_any_drug_in_train:,} / {n_test:,}"
              f"  ({test_obs_any_drug_in_train/n_test:.1%})")
        print(f"    Test obs. both drugs in train     : {test_obs_both_drugs_in_train:,} / {n_test:,}"
              f"  ({test_obs_both_drugs_in_train/n_test:.1%})")
        print(f"    Test obs. cell line in train      : {test_obs_cl_in_train:,} / {n_test:,}"
              f"  ({test_obs_cl_in_train/n_test:.1%})")

    # ── 8. Class distribution per split ──────────────────────────
    def _class_dist(df: pd.DataFrame) -> dict:
        vc = df["synergy_class"].value_counts()
        n  = len(df)
        return {
            cls: {"count": int(vc.get(cls, 0)), "pct": float(vc.get(cls, 0) / n * 100)}
            for cls in ["antagonism", "additive", "synergy"]
        }

    if verbose:
        print(f"\n  Class distribution:")
        for name, df_s in [("train", train_df), ("val", val_df), ("test", test_df)]:
            vc = df_s["synergy_class"].value_counts()
            print(f"    {name}  — antagonism={vc.get('antagonism',0):,}  "
                  f"additive={vc.get('additive',0):,}  synergy={vc.get('synergy',0):,}")

    # ── 9. Save CSVs ──────────────────────────────────────────────
    out_train = os.path.join(out_dir, "random_train.csv")
    out_val   = os.path.join(out_dir, "random_val.csv")
    out_test  = os.path.join(out_dir, "random_test.csv")

    pd.DataFrame({"row_index": train_idx}).to_csv(out_train, index=False)
    pd.DataFrame({"row_index": val_idx}).to_csv(out_val,   index=False)
    pd.DataFrame({"row_index": test_idx}).to_csv(out_test,  index=False)

    if verbose:
        print(f"\n  Saved:")
        print(f"    {out_train}")
        print(f"    {out_val}")
        print(f"    {out_test}")

    # ── 10. Hash protected files ──────────────────────────────────
    protected_hashes = {
        os.path.basename(pf): _sha256_short(pf)
        for pf in PROTECTED_FILES
    }

    # ── 11. Build benchmark JSON ──────────────────────────────────
    benchmark = {
        "split_type":       "random_observation",
        "description": (
            "Row/observation-level random 70/15/15 split of labeled_pairs.csv. "
            "Individual drugs, unordered pairs, and cell lines may appear in all "
            "three partitions by design (warm benchmark). "
            "Not comparable to cold-drug/LDO/strict-bilateral benchmarks."
        ),
        "seed":             seed,
        "train_fraction":   train_frac,
        "validation_fraction": val_frac,
        "test_fraction":    test_frac,
        "created_at":       datetime.datetime.utcnow().isoformat() + "Z",
        "labels_csv":       labels_csv,
        "output_dir":       out_dir,
        "row_counts": {
            "total":      n_total,
            "train":      n_train,
            "validation": n_val,
            "test":       n_test,
        },
        "drug_counts": {
            "train":          len(train_drugs),
            "validation":     len(val_drugs),
            "test":           len(test_drugs),
            "total_unique":   len(set(labels["drug_a_kg_id"]) | set(labels["drug_b_kg_id"])),
        },
        "pair_counts": {
            "train":      len(train_pairs),
            "validation": len(val_pairs),
            "test":       len(test_pairs),
            "total_unique": len(train_pairs | val_pairs | test_pairs),
        },
        "overlap_statistics": {
            "drug_train_test_overlap":        drug_train_test_overlap,
            "drug_val_test_overlap":          drug_val_test_overlap,
            "pair_train_test_overlap":        pair_train_test_overlap,
            "pair_val_test_overlap":          pair_val_test_overlap,
            "test_obs_with_train_pair":       test_obs_with_train_pair,
            "test_obs_with_train_pair_pct":   round(test_obs_with_train_pair / n_test * 100, 2),
            "test_obs_any_drug_in_train":     test_obs_any_drug_in_train,
            "test_obs_any_drug_in_train_pct": round(test_obs_any_drug_in_train / n_test * 100, 2),
            "test_obs_both_drugs_in_train":   test_obs_both_drugs_in_train,
            "test_obs_both_drugs_in_train_pct": round(test_obs_both_drugs_in_train / n_test * 100, 2),
            "test_obs_cell_line_in_train":    test_obs_cl_in_train,
            "test_obs_cell_line_in_train_pct": round(test_obs_cl_in_train / n_test * 100, 2),
        },
        "class_distribution": {
            "train":      _class_dist(train_df),
            "validation": _class_dist(val_df),
            "test":       _class_dist(test_df),
        },
        "cell_line_counts": {
            "train":      int(train_df["cell_line_name"].nunique()),
            "validation": int(val_df["cell_line_name"].nunique()),
            "test":       int(test_df["cell_line_name"].nunique()),
        },
        "integrity_verified": True,
        "protected_file_hashes": protected_hashes,
    }

    with open(benchmark_json, "w", encoding="utf-8") as fh:
        json.dump(benchmark, fh, indent=2)

    if verbose:
        print(f"  Saved: {benchmark_json}")
        print(f"\n  Protected file SHA-256 snapshots:")
        for k, v in protected_hashes.items():
            print(f"    {k}: {v}")
        print("\n  Random split build COMPLETE.")
        print("=" * 72)

    return benchmark


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Build deterministic random/warm observation-level split for SynThera."
    )
    parser.add_argument("--seed",        type=int,   default=SEED,       help="Random seed (default 42)")
    parser.add_argument("--train-frac",  type=float, default=TRAIN_FRAC, help="Train fraction (default 0.70)")
    parser.add_argument("--val-frac",    type=float, default=VAL_FRAC,   help="Validation fraction (default 0.15)")
    parser.add_argument("--test-frac",   type=float, default=TEST_FRAC,  help="Test fraction (default 0.15)")
    parser.add_argument("--labels-csv",  type=str,   default=LABELS_CSV, help="Path to labeled_pairs.csv")
    parser.add_argument("--out-dir",     type=str,   default=SPLITS_DIR, help="Output directory for split CSVs")
    parser.add_argument("--benchmark-json", type=str, default=BENCHMARK_JSON, help="Output path for benchmark JSON")
    args = parser.parse_args()

    build_random_split(
        seed=args.seed,
        train_frac=args.train_frac,
        val_frac=args.val_frac,
        test_frac=args.test_frac,
        labels_csv=args.labels_csv,
        out_dir=args.out_dir,
        benchmark_json=args.benchmark_json,
        verbose=True,
    )
