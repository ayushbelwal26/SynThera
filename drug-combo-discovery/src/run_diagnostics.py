"""
run_diagnostics.py

Implements Tasks 2, 3, and 4:
- Task 2: Per-class OVR AUROC and AUPR for seeds 1, 2, 3, 42 and 4-seed ensemble.
- Task 3: Split composition and drug overlap statistics.
- Task 4: Paired drug-level bootstrap utility for AUROC difference (Run A vs 4-seed ensemble).
"""

import os
import sys
import torch
import torch.nn.functional as F
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, average_precision_score

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from train import (
    HETERODATA_PATH,
    LABELS_PATH,
    SPLIT_TRAIN_PATH,
    SPLIT_VAL_PATH,
    SPLIT_TEST_PATH,
    MODELS_DIR,
    build_loaders,
    compute_class_weights,
)
from model import SynergyModule, CLASS_NAMES

CLASS_MAP = {"antagonism": 0, "additive": 1, "synergy": 2}


# ─────────────────────────────────────────────────────────────────
# TASK 3: Split Composition Analysis
# ─────────────────────────────────────────────────────────────────

def analyze_split_composition():
    print("\n" + "=" * 80)
    print("  TASK 3: SPLIT COMPOSITION ANALYSIS")
    print("=" * 80)

    labels_df = pd.read_csv(LABELS_PATH)
    train_idx = pd.read_csv(SPLIT_TRAIN_PATH)["row_index"].values
    val_idx = pd.read_csv(SPLIT_VAL_PATH)["row_index"].values
    test_idx = pd.read_csv(SPLIT_TEST_PATH)["row_index"].values

    train_df = labels_df.iloc[train_idx].reset_index(drop=True)
    val_df = labels_df.iloc[val_idx].reset_index(drop=True)
    test_df = labels_df.iloc[test_idx].reset_index(drop=True)

    train_drugs = set(train_df["drug_a_kg_id"]) | set(train_df["drug_b_kg_id"])
    val_drugs = set(val_df["drug_a_kg_id"]) | set(val_df["drug_b_kg_id"])
    test_drugs = set(test_df["drug_a_kg_id"]) | set(test_df["drug_b_kg_id"])

    a_in_train = test_df["drug_a_kg_id"].isin(train_drugs).values
    b_in_train = test_df["drug_b_kg_id"].isin(train_drugs).values
    mask_bilateral = (~a_in_train) & (~b_in_train)
    mask_unilateral = (a_in_train & ~b_in_train) | (~a_in_train & b_in_train)

    bilat_df = test_df[mask_bilateral].reset_index(drop=True)
    unilat_df = test_df[mask_unilateral].reset_index(drop=True)

    bilat_drugs = set(bilat_df["drug_a_kg_id"]) | set(bilat_df["drug_b_kg_id"])
    unilat_drugs = set(unilat_df["drug_a_kg_id"]) | set(unilat_df["drug_b_kg_id"])

    print("1. Unique Drugs per Split:")
    print(f"   - Train Split            : {len(train_drugs):>6,} unique drugs")
    print(f"   - Val Split              : {len(val_drugs):>6,} unique drugs")
    print(f"   - Test Split (Full)      : {len(test_drugs):>6,} unique drugs")
    print(f"   - Bilateral Test Subset  : {len(bilat_drugs):>6,} unique drugs")
    print(f"   - Unilateral Test Subset : {len(unilat_drugs):>6,} unique drugs")

    # Overlaps
    print("\n   Overlap Checks:")
    print(f"   - |Train & Bilateral Test| : {len(train_drugs & bilat_drugs)} (must be 0)")
    print(f"   - |Train & Test|           : {len(train_drugs & test_drugs)}")

    # Validation split composition
    val_a_in_train = val_df["drug_a_kg_id"].isin(train_drugs).values
    val_b_in_train = val_df["drug_b_kg_id"].isin(train_drugs).values
    n_seen_in_train = val_a_in_train.astype(int) + val_b_in_train.astype(int)

    n_val_total = len(val_df)
    n_val_0 = int((n_seen_in_train == 0).sum())
    n_val_1 = int((n_seen_in_train == 1).sum())
    n_val_2 = int((n_seen_in_train == 2).sum())

    print("\n2. Validation Split Composition (Drugs seen in Train):")
    print(f"   Total Validation Pairs: {n_val_total:,}")
    print(f"   - 0 drugs seen in train (bilateral cold) : {n_val_0:>8,} pairs ({n_val_0 / n_val_total * 100:>6.2f}%)")
    print(f"   - 1 drug seen in train  (unilateral cold): {n_val_1:>8,} pairs ({n_val_1 / n_val_total * 100:>6.2f}%)")
    print(f"   - 2 drugs seen in train (warm/both seen) : {n_val_2:>8,} pairs ({n_val_2 / n_val_total * 100:>6.2f}%)")

    print("\n3. Early Stopping & Checkpoint Selection in src/train.py:")
    print("   - Monitored Metric : val_loss (CrossEntropyLoss with class weights)")
    print("   - Evaluation Split : Validation Split (built from data/processed/split_val.csv)")
    print("   - Selection Mode   : min (saves checkpoint with lowest val_loss)")
    print("=" * 80)

    return {
        "train_drugs": train_drugs,
        "val_drugs": val_drugs,
        "test_drugs": test_drugs,
        "bilat_drugs": bilat_drugs,
        "unilat_drugs": unilat_drugs,
        "val_counts": (n_val_0, n_val_1, n_val_2, n_val_total),
    }


# ─────────────────────────────────────────────────────────────────
# Inference Helper
# ─────────────────────────────────────────────────────────────────

def run_model_inference(ckpt_path: str, heterodata, test_loader, device="cuda"):
    device_obj = torch.device(device if torch.cuda.is_available() else "cpu")
    metadata = heterodata.metadata()
    num_nodes_dict = {nt: heterodata[nt].num_nodes for nt in heterodata.node_types}
    n_fallback = int((~heterodata["drug"].fp_mask).sum().item())
    class_weights = compute_class_weights(heterodata)

    model = SynergyModule.load_from_checkpoint(
        ckpt_path,
        metadata=metadata,
        num_nodes_dict=num_nodes_dict,
        num_fallback_drugs=n_fallback,
        num_cell_lines=heterodata.num_cell_lines,
        num_layers=2,
        class_weights=class_weights,
    )
    model.to(device_obj)
    model.eval()

    all_logits = []
    all_labels = []

    # Set seed for reproducible sampling if loader samples
    torch.manual_seed(42)
    with torch.no_grad():
        for batch in test_loader:
            batch = batch.to(device_obj)
            logits, labels = model(batch)
            if logits.shape[0] > 0:
                all_logits.append(logits.detach().cpu())
                all_labels.append(labels.detach().cpu())

    all_logits = torch.cat(all_logits, dim=0)
    all_labels = torch.cat(all_labels, dim=0)
    probs = F.softmax(all_logits, dim=-1).numpy()
    labels_np = all_labels.numpy()
    return probs, labels_np


# ─────────────────────────────────────────────────────────────────
# TASK 2: Per-Class Metrics
# ─────────────────────────────────────────────────────────────────

def compute_per_class_metrics(labels_np: np.ndarray, probs: np.ndarray):
    """
    Computes per-class one-vs-rest AUROC, AUPR, and prevalence for:
    - antagonism (class 0)
    - additive (class 1)
    - synergy (class 2)
    """
    metrics = {}
    class_names = ["antagonism", "additive", "synergy"]
    for c_idx, c_name in enumerate(class_names):
        y_c = (labels_np == c_idx).astype(int)
        score_c = probs[:, c_idx]
        prev = float(np.mean(y_c))

        if len(np.unique(y_c)) < 2:
            auroc, aupr = float("nan"), float("nan")
        else:
            try:
                auroc = float(roc_auc_score(y_c, score_c))
            except ValueError:
                auroc = float("nan")
            try:
                aupr = float(average_precision_score(y_c, score_c))
            except ValueError:
                aupr = float("nan")

        metrics[c_name] = {"prev": prev, "auroc": auroc, "aupr": aupr}
    return metrics


def run_per_class_evaluation(all_probs_dict, labels_np, masks):
    print("\n" + "=" * 90)
    print("  TASK 2: PER-CLASS METRICS (OVR AUROC / AUPR / PREVALENCE)")
    print("=" * 90)

    classes = ["antagonism", "additive", "synergy"]
    subsets = ["Full", "Bilateral", "Unilateral"]

    # Prevalences
    print("Subset Prevalences:")
    for sub in subsets:
        mask = masks[sub]
        sub_y = labels_np[mask]
        counts = {c: int((sub_y == idx).sum()) for idx, c in enumerate(classes)}
        prevs = {c: float((sub_y == idx).mean()) for idx, c in enumerate(classes)}
        print(f"  {sub:<10} (N={len(sub_y):>6,}): Antagonism={prevs['antagonism']:.4f} ({counts['antagonism']:,}), "
              f"Additive={prevs['additive']:.4f} ({counts['additive']:,}), "
              f"Synergy={prevs['synergy']:.4f} ({counts['synergy']:,})")
    print("-" * 90)

    tables_by_subset = {}
    for sub in subsets:
        mask = masks[sub]
        sub_y = labels_np[mask]
        print(f"\n--- SUBSET: {sub} Test Pairs (N={len(sub_y):,}) ---")
        print(f"{'Model':<20} | {'Ant AUROC':<9} | {'Ant AUPR':<9} | {'Add AUROC':<9} | {'Add AUPR':<9} | {'Syn AUROC':<9} | {'Syn AUPR':<9} | {'Macro AUROC':<11} | {'Macro AUPR':<10}")
        print("-" * 105)

        rows = []
        for model_name, probs in all_probs_dict.items():
            sub_p = probs[mask]
            pcm = compute_per_class_metrics(sub_y, sub_p)

            # Macro
            macro_auroc = np.nanmean([pcm[c]["auroc"] for c in classes])
            macro_aupr = np.nanmean([pcm[c]["aupr"] for c in classes])

            rows.append({
                "model": model_name,
                "ant_auroc": pcm["antagonism"]["auroc"],
                "ant_aupr": pcm["antagonism"]["aupr"],
                "add_auroc": pcm["additive"]["auroc"],
                "add_aupr": pcm["additive"]["aupr"],
                "syn_auroc": pcm["synergy"]["auroc"],
                "syn_aupr": pcm["synergy"]["aupr"],
                "macro_auroc": macro_auroc,
                "macro_aupr": macro_aupr,
            })

            print(f"{model_name:<20} | {pcm['antagonism']['auroc']:>9.4f} | {pcm['antagonism']['aupr']:>9.4f} | "
                  f"{pcm['additive']['auroc']:>9.4f} | {pcm['additive']['aupr']:>9.4f} | "
                  f"{pcm['synergy']['auroc']:>9.4f} | {pcm['synergy']['aupr']:>9.4f} | "
                  f"{macro_auroc:>11.4f} | {macro_aupr:>10.4f}")
        tables_by_subset[sub] = pd.DataFrame(rows)
    print("=" * 90)
    return tables_by_subset


# ─────────────────────────────────────────────────────────────────
# TASK 4: Paired Drug-Level Bootstrap Utility
# ─────────────────────────────────────────────────────────────────

def paired_drug_bootstrap_difference(
    test_df: pd.DataFrame,
    labels_np: np.ndarray,
    probs_A: np.ndarray,
    probs_B: np.ndarray,
    metric_type: str = "macro_ovr",
    n_bootstraps: int = 1000,
    seed: int = 42,
) -> tuple[float, float, float, int]:
    """
    Takes two prediction arrays (probs_A and probs_B) on the same pairs of test_df.
    Resamples unique DRUGS with replacement over n_bootstraps iterations.
    Evaluates metric(A) - metric(B) on each sampled subset of pairs where both drugs are sampled.
    Returns:
      (mean_diff, ci_lower, ci_upper, n_valid_iterations)
    """
    rng = np.random.RandomState(seed)

    unique_drugs = np.array(sorted(
        list(set(test_df["drug_a_kg_id"]) | set(test_df["drug_b_kg_id"]))
    ))
    n_unique_drugs = len(unique_drugs)

    a_drugs = test_df["drug_a_kg_id"].values
    b_drugs = test_df["drug_b_kg_id"].values

    diffs = []
    skipped = 0

    for _ in range(n_bootstraps):
        sampled_drugs = set(rng.choice(unique_drugs, size=n_unique_drugs, replace=True))
        pair_mask = np.isin(a_drugs, list(sampled_drugs)) & np.isin(b_drugs, list(sampled_drugs))

        if pair_mask.sum() < 10:
            skipped += 1
            continue

        sub_y = labels_np[pair_mask]

        if metric_type == "macro_ovr":
            if len(np.unique(sub_y)) < 3:
                skipped += 1
                continue
            try:
                auc_A = roc_auc_score(sub_y, probs_A[pair_mask], multi_class="ovr", average="macro")
                auc_B = roc_auc_score(sub_y, probs_B[pair_mask], multi_class="ovr", average="macro")
                diffs.append(auc_A - auc_B)
            except ValueError:
                skipped += 1
        elif metric_type == "binary_synergy":
            # Binary synergy (class 2) vs non-synergy (classes 0 and 1)
            sub_y_bin = (sub_y == 2).astype(int)
            if len(np.unique(sub_y_bin)) < 2:
                skipped += 1
                continue
            try:
                auc_A = roc_auc_score(sub_y_bin, probs_A[pair_mask, 2])
                auc_B = roc_auc_score(sub_y_bin, probs_B[pair_mask, 2])
                diffs.append(auc_A - auc_B)
            except ValueError:
                skipped += 1
        else:
            raise ValueError(f"Unknown metric_type: {metric_type}")

    diff_arr = np.array(diffs)
    ci_lower = float(np.percentile(diff_arr, 2.5))
    ci_upper = float(np.percentile(diff_arr, 97.5))
    mean_diff = float(np.mean(diff_arr))

    return mean_diff, ci_lower, ci_upper, len(diffs)


def run_all():
    # 1. Task 3 Analysis
    analyze_split_composition()

    # 2. Data & Model inference
    print("\nLoading HeteroData and Building Test Loader...")
    heterodata = torch.load(HETERODATA_PATH, weights_only=False)
    _, _, test_loader = build_loaders(heterodata, [], [], [])

    labels_df = pd.read_csv(LABELS_PATH)
    train_idx = pd.read_csv(SPLIT_TRAIN_PATH)["row_index"].values
    test_idx = pd.read_csv(SPLIT_TEST_PATH)["row_index"].values

    train_drugs = set(labels_df.iloc[train_idx]["drug_a_kg_id"]) | set(labels_df.iloc[train_idx]["drug_b_kg_id"])
    test_df = labels_df.iloc[test_idx].reset_index(drop=True)

    a_in_train = test_df["drug_a_kg_id"].isin(train_drugs).values
    b_in_train = test_df["drug_b_kg_id"].isin(train_drugs).values
    mask_bilat = (~a_in_train) & (~b_in_train)
    mask_unilat = (a_in_train & ~b_in_train) | (~a_in_train & b_in_train)
    mask_full = np.ones(len(test_df), dtype=bool)

    masks = {
        "Full": mask_full,
        "Bilateral": mask_bilat,
        "Unilateral": mask_unilat,
    }

    checkpoints = {
        "Seed 1": os.path.join(MODELS_DIR, "baseline_seed1.ckpt"),
        "Seed 2": os.path.join(MODELS_DIR, "baseline_seed2.ckpt"),
        "Seed 3": os.path.join(MODELS_DIR, "baseline_seed3.ckpt"),
        "Seed 42": os.path.join(MODELS_DIR, "synergy_gnn_final.ckpt"),
        "Run A": os.path.join(MODELS_DIR, "synergy_gnn_runA.ckpt"),
    }

    all_probs = {}
    ground_truth = None

    for name, path in checkpoints.items():
        print(f"Running inference for {name} ({os.path.basename(path)})...")
        p, y = run_model_inference(path, heterodata, test_loader)
        all_probs[name] = p
        if ground_truth is None:
            ground_truth = y

    # 4-seed ensemble
    ensemble_probs = (
        all_probs["Seed 1"] +
        all_probs["Seed 2"] +
        all_probs["Seed 3"] +
        all_probs["Seed 42"]
    ) / 4.0
    all_probs["4-Seed Ensemble"] = ensemble_probs

    # Task 2 Evaluation (seeds 1, 2, 3, 42, and 4-seed ensemble)
    task2_models = {
        "Seed 1": all_probs["Seed 1"],
        "Seed 2": all_probs["Seed 2"],
        "Seed 3": all_probs["Seed 3"],
        "Seed 42": all_probs["Seed 42"],
        "4-Seed Ensemble": all_probs["4-Seed Ensemble"],
    }
    run_per_class_evaluation(task2_models, ground_truth, masks)

    # Task 4: Paired bootstrap utility on bilateral cold subset
    print("\n" + "=" * 90)
    print("  TASK 4: PAIRED DRUG-LEVEL BOOTSTRAP UTILITY")
    print("  Comparison: Run A (models/synergy_gnn_runA.ckpt) minus 4-Seed Ensemble")
    print("  Subset    : Bilateral cold test pairs (neither drug seen in train)")
    print("  Iterations: 1,000 resamples of unique bilateral test drugs with replacement")
    print("=" * 90)

    bilat_df = test_df[mask_bilat].reset_index(drop=True)
    bilat_y = ground_truth[mask_bilat]
    bilat_p_runA = all_probs["Run A"][mask_bilat]
    bilat_p_ens = all_probs["4-Seed Ensemble"][mask_bilat]

    # 1. Macro AUROC
    mean_diff_m, ci_lo_m, ci_hi_m, n_val_m = paired_drug_bootstrap_difference(
        test_df=bilat_df,
        labels_np=bilat_y,
        probs_A=bilat_p_runA,
        probs_B=bilat_p_ens,
        metric_type="macro_ovr",
        n_bootstraps=1000,
        seed=42,
    )
    print(f"Macro AUROC (OVR) Difference [Run A - 4-Seed Ensemble]:")
    print(f"  Mean Difference : {mean_diff_m:+.4f}")
    print(f"  95% Bootstrap CI: [{ci_lo_m:+.4f}, {ci_hi_m:+.4f}]")
    print(f"  Valid Iterations: {n_val_m}/1000")
    if ci_lo_m > 0:
        print("  Statistical Conclusion: Run A is significantly BETTER than 4-seed ensemble (CI excludes 0).")
    elif ci_hi_m < 0:
        print("  Statistical Conclusion: Run A is significantly WORSE than 4-seed ensemble (CI excludes 0).")
    else:
        print("  Statistical Conclusion: Difference is not statistically significant at 95% confidence (CI spans 0).")

    # 2. Binary Synergy AUROC
    print("-" * 90)
    mean_diff_b, ci_lo_b, ci_hi_b, n_val_b = paired_drug_bootstrap_difference(
        test_df=bilat_df,
        labels_np=bilat_y,
        probs_A=bilat_p_runA,
        probs_B=bilat_p_ens,
        metric_type="binary_synergy",
        n_bootstraps=1000,
        seed=42,
    )
    print(f"Binary Synergy AUROC Difference [Run A - 4-Seed Ensemble]:")
    print(f"  Mean Difference : {mean_diff_b:+.4f}")
    print(f"  95% Bootstrap CI: [{ci_lo_b:+.4f}, {ci_hi_b:+.4f}]")
    print(f"  Valid Iterations: {n_val_b}/1000")
    if ci_lo_b > 0:
        print("  Statistical Conclusion: Run A is significantly BETTER than 4-seed ensemble (CI excludes 0).")
    elif ci_hi_b < 0:
        print("  Statistical Conclusion: Run A is significantly WORSE than 4-seed ensemble (CI excludes 0).")
    else:
        print("  Statistical Conclusion: Difference is not statistically significant at 95% confidence (CI spans 0).")
    print("=" * 90)


if __name__ == "__main__":
    run_all()
