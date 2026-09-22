"""
eval_all_seeds.py

Orchestrates multi-seed evaluation (Task 1) and drug-level bootstrap CIs (Task 3).
Evaluates seeds 1, 2, 3 and seed 42 (final.ckpt).
Computes mean and std across the four seeds.
Computes 95% drug-level bootstrap CI on bilateral cold test pairs.
"""

import os
import sys
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, average_precision_score

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from eval_splits import evaluate_cold_split_subsets, compute_macro_metrics
from diagnostic_baselines import run_drug_level_bootstrap_ci

MODELS_DIR = os.path.join(ROOT, "models")

SEEDS_CONFIG = [
    ("Seed 1", os.path.join(MODELS_DIR, "baseline_seed1.ckpt"), 1),
    ("Seed 2", os.path.join(MODELS_DIR, "baseline_seed2.ckpt"), 2),
    ("Seed 3", os.path.join(MODELS_DIR, "baseline_seed3.ckpt"), 3),
    ("Seed 42 (Baseline final)", os.path.join(MODELS_DIR, "synergy_gnn_final.ckpt"), 42),
]


def evaluate_all():
    table_rows = []
    bilateral_probs_dict = {}
    bilateral_y = None
    bilateral_df = None

    for label, ckpt_path, seed_num in SEEDS_CONFIG:
        print(f"\n{'='*70}\n  Evaluating {label} ({ckpt_path})\n{'='*70}")
        res, probs, labels_np, mask_bilateral, mask_unilateral, test_pairs = evaluate_cold_split_subsets(
            ckpt_path=ckpt_path,
            eval_val=True,
            return_details=True,
        )

        val_auroc = res["Validation Split"]["auroc"]
        full_auroc = res["Full cold-drug test (headline)"]["auroc"]
        full_aupr = res["Full cold-drug test (headline)"]["aupr"]
        bilat_auroc = res["Bilateral cold-drug (neither in train)"]["auroc"]
        bilat_aupr = res["Bilateral cold-drug (neither in train)"]["aupr"]
        unilat_auroc = res["Unilateral cold-drug (exactly one in train)"]["auroc"]

        table_rows.append({
            "seed": seed_num,
            "label": label,
            "val_auroc": val_auroc,
            "full_auroc": full_auroc,
            "full_aupr": full_aupr,
            "bilat_auroc": bilat_auroc,
            "bilat_aupr": bilat_aupr,
            "unilat_auroc": unilat_auroc,
        })

        bilateral_probs_dict[seed_num] = probs[mask_bilateral]
        if bilateral_y is None:
            bilateral_y = labels_np[mask_bilateral]
            bilateral_df = test_pairs[mask_bilateral].reset_index(drop=True)

    df_results = pd.DataFrame(table_rows)

    print("\n" + "=" * 95)
    print("  TASK 1: MULTI-SEED BASELINE EVALUATION TABLE")
    print("=" * 95)
    header = f"{'Seed':<6} | {'Val AUROC':<10} | {'Full AUROC':<11} | {'Full AUPR':<10} | {'Bilateral AUROC':<16} | {'Bilateral AUPR':<15} | {'Unilateral AUROC':<16}"
    print(header)
    print("-" * 95)
    for _, r in df_results.iterrows():
        print(f"{int(r['seed']):<6} | {r['val_auroc']:<10.4f} | {r['full_auroc']:<11.4f} | {r['full_aupr']:<10.4f} | {r['bilat_auroc']:<16.4f} | {r['bilat_aupr']:<15.4f} | {r['unilat_auroc']:<16.4f}")

    print("-" * 95)
    means = df_results[["val_auroc", "full_auroc", "full_aupr", "bilat_auroc", "bilat_aupr", "unilat_auroc"]].mean()
    stds = df_results[["val_auroc", "full_auroc", "full_aupr", "bilat_auroc", "bilat_aupr", "unilat_auroc"]].std()

    mean_line = f"{'Mean':<6} | {means['val_auroc']:<10.4f} | {means['full_auroc']:<11.4f} | {means['full_aupr']:<10.4f} | {means['bilat_auroc']:<16.4f} | {means['bilat_aupr']:<15.4f} | {means['unilat_auroc']:<16.4f}"
    std_line  = f"{'Std':<6}  | {stds['val_auroc']:<10.4f} | {stds['full_auroc']:<11.4f} | {stds['full_aupr']:<10.4f} | {stds['bilat_auroc']:<16.4f} | {stds['bilat_aupr']:<15.4f} | {stds['unilat_auroc']:<16.4f}"
    print(mean_line)
    print(std_line)
    print("=" * 95)

    # ── Task 3: Drug-level Bootstrap CIs on Bilateral Cold Subset ──
    print("\n" + "=" * 95)
    print("  TASK 3: DRUG-LEVEL BOOTSTRAP CONFIDENCE INTERVALS (Bilateral Cold Test Subset)")
    print("=" * 95)
    print("  Method: Resample unique test drugs with replacement (1,000 iterations).")
    print("          Keep pairs where BOTH drugs are in the bootstrap sample.")
    print("          Compute AUROC per iteration, reporting 2.5th and 97.5th percentiles (95% CI).")
    print("-" * 95)

    # 1. Seed 42
    p42 = bilateral_probs_dict[42]
    # Macro AUROC
    mean_m42, ci_lo_m42, ci_hi_m42, n_eval_m42 = run_drug_level_bootstrap_ci(
        bilateral_df=bilateral_df,
        scores=p42[:, 2],
        n_bootstraps=1000,
        seed=42,
        metric_type="macro_ovr",
        labels_np=bilateral_y,
        probs_np=p42,
    )
    # Binary Synergy AUROC
    mean_b42, ci_lo_b42, ci_hi_b42, n_eval_b42 = run_drug_level_bootstrap_ci(
        bilateral_df=bilateral_df,
        scores=p42[:, 2],
        n_bootstraps=1000,
        seed=42,
        metric_type="binary",
        labels_np=bilateral_y,
        probs_np=p42,
    )

    print(f"Seed 42 Baseline:")
    print(f"  Macro AUROC (OVR)        : Mean = {mean_m42:.4f}, 95% CI = [{ci_lo_m42:.4f}, {ci_hi_m42:.4f}] (valid iterations: {n_eval_m42}/1000)")
    print(f"  Binary Synergy AUROC     : Mean = {mean_b42:.4f}, 95% CI = [{ci_lo_b42:.4f}, {ci_hi_b42:.4f}] (valid iterations: {n_eval_b42}/1000)")

    # 2. Ensemble Mean Prediction across 4 seeds
    probs_ensemble = (
        bilateral_probs_dict[1] +
        bilateral_probs_dict[2] +
        bilateral_probs_dict[3] +
        bilateral_probs_dict[42]
    ) / 4.0

    mean_m_ens, ci_lo_m_ens, ci_hi_m_ens, n_eval_m_ens = run_drug_level_bootstrap_ci(
        bilateral_df=bilateral_df,
        scores=probs_ensemble[:, 2],
        n_bootstraps=1000,
        seed=42,
        metric_type="macro_ovr",
        labels_np=bilateral_y,
        probs_np=probs_ensemble,
    )
    mean_b_ens, ci_lo_b_ens, ci_hi_b_ens, n_eval_b_ens = run_drug_level_bootstrap_ci(
        bilateral_df=bilateral_df,
        scores=probs_ensemble[:, 2],
        n_bootstraps=1000,
        seed=42,
        metric_type="binary",
        labels_np=bilateral_y,
        probs_np=probs_ensemble,
    )

    print(f"\n4-Seed Mean Prediction (Ensemble of Seeds 1, 2, 3, 42):")
    print(f"  Macro AUROC (OVR)        : Mean = {mean_m_ens:.4f}, 95% CI = [{ci_lo_m_ens:.4f}, {ci_hi_m_ens:.4f}] (valid iterations: {n_eval_m_ens}/1000)")
    print(f"  Binary Synergy AUROC     : Mean = {mean_b_ens:.4f}, 95% CI = [{ci_lo_b_ens:.4f}, {ci_hi_b_ens:.4f}] (valid iterations: {n_eval_b_ens}/1000)")
    print("=" * 95)


if __name__ == "__main__":
    evaluate_all()
