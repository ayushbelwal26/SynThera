"""
diagnostic_baselines.py

Implements:
1. Cell-line-only baseline:
   - Predicts the training-set synergy rate of each cell line (or global rate if unseen).
   - Evaluates AUROC and AUPR across Validation, Full cold-drug test, Bilateral cold, and Unilateral cold.
2. Drug-only baseline:
   - Predicts each drug's training-set synergy rate (or global rate if unseen).
   - For each pair, uses the mean rate of the two drugs.
   - Evaluates AUROC and AUPR across the same four subsets.
3. Drug-level bootstrap confidence intervals (Task 3):
   - Resamples unique drugs with replacement over 1,000 iterations on the bilateral cold subset.
   - Computes 95% bootstrap CI for AUROC.
"""

import os
import sys
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, average_precision_score

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED = os.path.join(ROOT, "data", "processed")
LABELS_PATH = os.path.join(PROCESSED, "labeled_pairs.csv")
SPLIT_TRAIN_PATH = os.path.join(PROCESSED, "split_train.csv")
SPLIT_VAL_PATH = os.path.join(PROCESSED, "split_val.csv")
SPLIT_TEST_PATH = os.path.join(PROCESSED, "split_test.csv")

CLASS_MAP = {"antagonism": 0, "additive": 1, "synergy": 2}


def load_data_and_subsets():
    labels = pd.read_csv(LABELS_PATH)
    train_idx = pd.read_csv(SPLIT_TRAIN_PATH)["row_index"].values
    val_idx = pd.read_csv(SPLIT_VAL_PATH)["row_index"].values
    test_idx = pd.read_csv(SPLIT_TEST_PATH)["row_index"].values

    train_df = labels.iloc[train_idx].reset_index(drop=True)
    val_df = labels.iloc[val_idx].reset_index(drop=True)
    test_df = labels.iloc[test_idx].reset_index(drop=True)

    train_drugs = set(train_df["drug_a_kg_id"]) | set(train_df["drug_b_kg_id"])

    a_in_train = test_df["drug_a_kg_id"].isin(train_drugs).values
    b_in_train = test_df["drug_b_kg_id"].isin(train_drugs).values

    mask_bilateral = (~a_in_train) & (~b_in_train)
    mask_unilateral = (a_in_train & ~b_in_train) | (~a_in_train & b_in_train)

    subsets = {
        "Validation Split": val_df,
        "Full cold-drug test": test_df,
        "Bilateral cold-drug": test_df[mask_bilateral].reset_index(drop=True),
        "Unilateral cold-drug": test_df[mask_unilateral].reset_index(drop=True),
    }

    return train_df, subsets, train_drugs


def compute_binary_metrics(y_true_binary: np.ndarray, scores: np.ndarray) -> tuple[float, float]:
    """Computes binary AUROC and AUPR for synergy detection."""
    # Check if more than one class is present
    if len(np.unique(y_true_binary)) < 2:
        return float("nan"), float("nan")
    try:
        auroc = float(roc_auc_score(y_true_binary, scores))
    except ValueError:
        auroc = float("nan")
    try:
        aupr = float(average_precision_score(y_true_binary, scores))
    except ValueError:
        aupr = float("nan")
    return auroc, aupr


def run_cell_line_baseline(train_df: pd.DataFrame, subsets: dict[str, pd.DataFrame]):
    """Task 2: Cell-line-only baseline."""
    # Global training synergy rate
    train_syn_mask = (train_df["synergy_class"] == "synergy")
    global_rate = float(train_syn_mask.mean())

    # Per cell-line training synergy rate
    cl_rates = train_df.groupby("cell_line_name")["synergy_class"].apply(
        lambda s: (s == "synergy").mean()
    ).to_dict()

    print("\n" + "=" * 78)
    print("  TASK 2: CELL-LINE-ONLY BASELINE (Synergy Detection: AUROC / AUPR)")
    print("=" * 78)
    print(f"  Global training synergy rate: {global_rate:.4f} ({global_rate*100:.2f}%)")
    print(f"  Training cell lines: {len(cl_rates)}")
    print("-" * 78)
    print(f"{'Split / Subset':<35} | {'Pairs':>8} | {'Prevalence':>10} | {'AUROC':>7} | {'AUPR':>7}")
    print("-" * 78)

    results = {}
    for name, df in subsets.items():
        y_true = (df["synergy_class"] == "synergy").astype(int).values
        prev = float(y_true.mean())
        preds = np.array([cl_rates.get(cl, global_rate) for cl in df["cell_line_name"].values])

        auroc, aupr = compute_binary_metrics(y_true, preds)
        results[name] = {"n_pairs": len(df), "prevalence": prev, "auroc": auroc, "aupr": aupr}
        print(f"{name:<35} | {len(df):>8,} | {prev:>9.4f} | {auroc:>7.4f} | {aupr:>7.4f}")
    print("=" * 78)
    return results


def run_drug_only_baseline(train_df: pd.DataFrame, subsets: dict[str, pd.DataFrame]):
    """Task 2: Drug-only baseline."""
    train_syn_mask = (train_df["synergy_class"] == "synergy")
    global_rate = float(train_syn_mask.mean())

    # Compute per-drug synergy count and pair count in training set
    drug_syn_counts = {}
    drug_total_counts = {}

    for _, row in train_df.iterrows():
        da, db, is_syn = row["drug_a_kg_id"], row["drug_b_kg_id"], (row["synergy_class"] == "synergy")
        for d in (da, db):
            drug_total_counts[d] = drug_total_counts.get(d, 0) + 1
            if is_syn:
                drug_syn_counts[d] = drug_syn_counts.get(d, 0) + 1

    drug_rates = {
        d: drug_syn_counts.get(d, 0) / drug_total_counts[d]
        for d in drug_total_counts
    }

    print("\n" + "=" * 78)
    print("  TASK 2: DRUG-ONLY BASELINE (Mean Drug Synergy Rate: AUROC / AUPR)")
    print("=" * 78)
    print(f"  Global training synergy rate: {global_rate:.4f} ({global_rate*100:.2f}%)")
    print(f"  Training drugs observed: {len(drug_rates)}")
    print("-" * 78)
    print(f"{'Split / Subset':<35} | {'Pairs':>8} | {'Prevalence':>10} | {'AUROC':>7} | {'AUPR':>7}")
    print("-" * 78)

    results = {}
    for name, df in subsets.items():
        y_true = (df["synergy_class"] == "synergy").astype(int).values
        prev = float(y_true.mean())

        ra = np.array([drug_rates.get(d, global_rate) for d in df["drug_a_kg_id"].values])
        rb = np.array([drug_rates.get(d, global_rate) for d in df["drug_b_kg_id"].values])
        preds = (ra + rb) / 2.0

        auroc, aupr = compute_binary_metrics(y_true, preds)
        results[name] = {"n_pairs": len(df), "prevalence": prev, "auroc": auroc, "aupr": aupr}
        print(f"{name:<35} | {len(df):>8,} | {prev:>9.4f} | {auroc:>7.4f} | {aupr:>7.4f}")
    print("=" * 78)
    return results


def run_drug_level_bootstrap_ci(
    bilateral_df: pd.DataFrame,
    scores: np.ndarray,
    n_bootstraps: int = 1000,
    seed: int = 42,
    metric_type: str = "macro_ovr",
    labels_np: np.ndarray | None = None,
    probs_np: np.ndarray | None = None,
) -> tuple[float, float, float, int]:
    """
    Task 3: Drug-level bootstrap confidence interval for AUROC on bilateral cold subset.
    Resamples unique DRUGS (not pairs) with replacement over n_bootstraps iterations.
    """
    rng = np.random.RandomState(seed)

    # Unique drugs appearing in bilateral subset
    unique_drugs = np.array(sorted(
        list(set(bilateral_df["drug_a_kg_id"]) | set(bilateral_df["drug_b_kg_id"]))
    ))
    n_unique_drugs = len(unique_drugs)

    a_drugs = bilateral_df["drug_a_kg_id"].values
    b_drugs = bilateral_df["drug_b_kg_id"].values

    bootstrap_aurocs = []
    skipped = 0

    for i in range(n_bootstraps):
        sampled_drugs = set(rng.choice(unique_drugs, size=n_unique_drugs, replace=True))

        # Keep pairs where BOTH drugs are in sampled_drugs
        pair_mask = np.isin(a_drugs, list(sampled_drugs)) & np.isin(b_drugs, list(sampled_drugs))
        n_sampled_pairs = pair_mask.sum()

        if n_sampled_pairs < 10:
            skipped += 1
            continue

        if metric_type == "macro_ovr" and labels_np is not None and probs_np is not None:
            sub_y = labels_np[pair_mask]
            sub_p = probs_np[pair_mask]
            if len(np.unique(sub_y)) < 3:
                skipped += 1
                continue
            try:
                score = roc_auc_score(sub_y, sub_p, multi_class="ovr", average="macro")
                bootstrap_aurocs.append(score)
            except ValueError:
                skipped += 1
        else:
            sub_y = (bilateral_df.loc[pair_mask, "synergy_class"] == "synergy").astype(int).values
            sub_scores = scores[pair_mask]
            if len(np.unique(sub_y)) < 2:
                skipped += 1
                continue
            try:
                score = roc_auc_score(sub_y, sub_scores)
                bootstrap_aurocs.append(score)
            except ValueError:
                skipped += 1

    boot_arr = np.array(bootstrap_aurocs)
    ci_lower = float(np.percentile(boot_arr, 2.5))
    ci_upper = float(np.percentile(boot_arr, 97.5))
    mean_auc = float(np.mean(boot_arr))

    return mean_auc, ci_lower, ci_upper, len(bootstrap_aurocs)


if __name__ == "__main__":
    train_df, subsets, train_drugs = load_data_and_subsets()
    run_cell_line_baseline(train_df, subsets)
    run_drug_only_baseline(train_df, subsets)
