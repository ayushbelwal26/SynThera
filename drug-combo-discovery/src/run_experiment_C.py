"""
src/run_experiment_C.py
======================
Executes Experiment Run C: Target-complementarity features for cold-drug synergy prediction.

Steps:
0. Target coverage check (Step 0).
1. Precomputed features loaded via model.py buffers.
2. Train seeds 1, 2, 3, 42 with target features enabled. Save to models/runC_seed{N}.ckpt.
3. Deterministic 5-pass evaluation (eval_splits.py) on Full Test and Bilateral Cold Test.
4. 184-drug paired cold-drug bootstrap comparing Run C mean prediction vs baseline Mean A prediction.
5. Secondary paired bootstrap restricted to pairs where BOTH drugs have nonzero target coverage.
6. Evaluation against pre-declared success criterion.
"""

import os
import sys
import time
import numpy as np
import pandas as pd
import torch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
sys.path.insert(0, SRC)

from train import main as train_main
from model import SynergyModule
from run_tasks_3_4_5 import (
    load_environment,
    evaluate_model_on_test_5pass,
    paired_cold_drug_bootstrap_full_test,
)

MODELS_DIR = os.path.join(ROOT, "models")
B0_DIR = os.path.join(MODELS_DIR, "b0")

BASELINE_RULE_A_CKPTS = {
    1: os.path.join(B0_DIR, "seed1_epoch0.ckpt"),
    2: os.path.join(B0_DIR, "seed2_epoch5.ckpt"),
    3: os.path.join(B0_DIR, "seed3_epoch0.ckpt"),
    42: os.path.join(B0_DIR, "seed42_epoch1.ckpt"),
}

SEEDS = [1, 2, 3, 42]


def train_runC():
    wall_clocks = {}
    saved_ckpts = {}

    print("=" * 90)
    print("  RUN C: TRAINING 4 SEEDS WITH TARGET-COMPLEMENTARITY FEATURES")
    print("=" * 90)

    for s in SEEDS:
        run_name = f"runC_seed{s}"
        ckpt_path = os.path.join(MODELS_DIR, f"{run_name}.ckpt")

        print(f"\n>>> Starting training for Seed {s} ({run_name})...")
        t0 = time.time()
        saved_path, elapsed = train_main(
            run_name=run_name,
            seed=s,
            save_all_epochs=False,
            checkpoint_dir=MODELS_DIR,
            use_regularization=False,
            use_target_features=True,
        )
        wall_clocks[s] = elapsed
        saved_ckpts[s] = ckpt_path
        print(f">>> Seed {s} finished in {elapsed:.1f}s ({elapsed/60:.2f} min). Checkpoint: {ckpt_path}")

    return wall_clocks, saved_ckpts


def evaluate_runC(wall_clocks, runC_ckpts):
    print("\n" + "=" * 90)
    print("  RUN C: EVALUATION & PAIRED BOOTSTRAP")
    print("=" * 90)

    (
        heterodata,
        val_loader,
        test_loader,
        val_df,
        test_df,
        train_drugs,
        cold_test_drugs,
        mask_bilat_val,
        masks_test,
        class_weights,
    ) = load_environment()

    metadata = heterodata.metadata()
    num_nodes_dict = {nt: heterodata[nt].num_nodes for nt in heterodata.node_types}
    n_fallback = int((~heterodata["drug"].fp_mask).sum().item())
    device_obj = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # 1. Evaluate Run C models (5-pass deterministic)
    runC_results = {}
    runC_probs = {}
    test_labels_np = None

    print("\n--- Evaluating Run C Checkpoints (5-pass deterministic) ---")
    for s in SEEDS:
        ckpt = runC_ckpts[s]
        print(f"Loading {ckpt}...")
        model = SynergyModule.load_from_checkpoint(
            ckpt,
            metadata=metadata,
            num_nodes_dict=num_nodes_dict,
            num_fallback_drugs=n_fallback,
            num_cell_lines=heterodata.num_cell_lines,
            num_layers=2,
            class_weights=class_weights,
        )
        model.to(device_obj)
        model.eval()

        res_dict, mean_p, lbls = evaluate_model_on_test_5pass(model, test_loader, masks_test)
        runC_results[s] = res_dict
        runC_probs[s] = mean_p
        if test_labels_np is None:
            test_labels_np = lbls

    # 2. Evaluate Baseline Rule A models (5-pass deterministic)
    base_results = {}
    base_probs = {}
    print("\n--- Evaluating Baseline Rule A Checkpoints (5-pass deterministic) ---")
    for s in SEEDS:
        ckpt = BASELINE_RULE_A_CKPTS[s]
        print(f"Loading baseline {ckpt}...")
        model = SynergyModule.load_from_checkpoint(
            ckpt,
            metadata=metadata,
            num_nodes_dict=num_nodes_dict,
            num_fallback_drugs=n_fallback,
            num_cell_lines=heterodata.num_cell_lines,
            num_layers=2,
            class_weights=class_weights,
        )
        model.to(device_obj)
        model.eval()

        res_dict, mean_p, _ = evaluate_model_on_test_5pass(model, test_loader, masks_test)
        base_results[s] = res_dict
        base_probs[s] = mean_p

    # Compute Mean Predictions across the 4 seeds
    mean_prob_runC = np.mean([runC_probs[s] for s in SEEDS], axis=0)
    mean_prob_base = np.mean([base_probs[s] for s in SEEDS], axis=0)

    # ── Report Test Metrics ──
    print("\n" + "=" * 100)
    print("  RUN C TEST METRICS (5-Pass Deterministic Evaluation)")
    print("=" * 100)

    subsets = ["Full", "Bilateral"]
    for sub in subsets:
        print(f"\n--- SUBSET: {sub} Test Set ---")
        print(f"{'Model / Seed':<20} | {'Macro AUROC':<16} | {'Syn AUROC':<16} | {'Syn AUPR':<16} | {'Lift':<12}")
        print("-" * 88)
        for s in SEEDS:
            m = runC_results[s][sub]
            print(f"Run C Seed {s:<9} | {m['macro_auroc_mean']:.4f} (+/-{m['macro_auroc_sd']:.4f}) | "
                  f"{m['syn_auroc_mean']:.4f} (+/-{m['syn_auroc_sd']:.4f}) | "
                  f"{m['syn_aupr_mean']:.4f} (+/-{m['syn_aupr_sd']:.4f}) | "
                  f"{m['lift_mean']:.2f} (+/-{m['lift_sd']:.2f})")

        # Mean and SD across seeds
        m_aucs = [runC_results[s][sub]["macro_auroc_mean"] for s in SEEDS]
        s_aucs = [runC_results[s][sub]["syn_auroc_mean"] for s in SEEDS]
        s_auprs = [runC_results[s][sub]["syn_aupr_mean"] for s in SEEDS]
        lifts = [runC_results[s][sub]["lift_mean"] for s in SEEDS]
        print("-" * 88)
        print(f"{'Run C Mean (All)':<20} | {np.mean(m_aucs):.4f} (+/-{np.std(m_aucs):.4f}) | "
              f"{np.mean(s_aucs):.4f} (+/-{np.std(s_aucs):.4f}) | "
              f"{np.mean(s_auprs):.4f} (+/-{np.std(s_auprs):.4f}) | "
              f"{np.mean(lifts):.2f} (+/-{np.std(lifts):.2f})")

        # Baseline Mean comparison
        b_m_aucs = [base_results[s][sub]["macro_auroc_mean"] for s in SEEDS]
        b_s_aucs = [base_results[s][sub]["syn_auroc_mean"] for s in SEEDS]
        b_s_auprs = [base_results[s][sub]["syn_aupr_mean"] for s in SEEDS]
        b_lifts = [base_results[s][sub]["lift_mean"] for s in SEEDS]
        print(f"{'Baseline Mean A':<20} | {np.mean(b_m_aucs):.4f} (+/-{np.std(b_m_aucs):.4f}) | "
              f"{np.mean(b_s_aucs):.4f} (+/-{np.std(b_s_aucs):.4f}) | "
              f"{np.mean(b_s_auprs):.4f} (+/-{np.std(b_s_auprs):.4f}) | "
              f"{np.mean(b_lifts):.2f} (+/-{np.std(b_lifts):.2f})")
        print("-" * 88)

    # ── 184-Drug Paired Cold-Drug Bootstrap on Full Test Set ──
    print("\n" + "=" * 100)
    print("  184-DRUG PAIRED COLD-DRUG BOOTSTRAP (Full Test Set)")
    print("=" * 100)

    # 1. Run C Mean Prediction vs Baseline Mean Prediction (All 37,778 pairs)
    diff_macro, lo_macro, hi_macro, _, n_c = paired_cold_drug_bootstrap_full_test(
        test_df, test_labels_np, mean_prob_runC, mean_prob_base, cold_test_drugs, metric_type="macro_ovr", seed=42
    )
    diff_syn, lo_syn, hi_syn, _, _ = paired_cold_drug_bootstrap_full_test(
        test_df, test_labels_np, mean_prob_runC, mean_prob_base, cold_test_drugs, metric_type="binary_synergy", seed=42
    )

    print(f"\n>>> Run C Mean Prediction minus Baseline Mean Prediction (Cold test drugs: {n_c}, Pairs: {len(test_df):,}):")
    print(f"    Macro AUROC (OVR)    : Mean Diff = {diff_macro:+.4f}, 95% CI = [{lo_macro:+.4f}, {hi_macro:+.4f}]")
    print(f"    Binary Synergy AUROC : Mean Diff = {diff_syn:+.4f}, 95% CI = [{lo_syn:+.4f}, {hi_syn:+.4f}]")

    # 2. Per-seed paired comparisons (All pairs)
    print("\n>>> Per-Seed Paired Comparisons (Run C Seed s minus Baseline Seed s):")
    for s in SEEDS:
        d_m, l_m, h_m, _, _ = paired_cold_drug_bootstrap_full_test(
            test_df, test_labels_np, runC_probs[s], base_probs[s], cold_test_drugs, metric_type="macro_ovr", seed=42
        )
        d_s, l_s, h_s, _, _ = paired_cold_drug_bootstrap_full_test(
            test_df, test_labels_np, runC_probs[s], base_probs[s], cold_test_drugs, metric_type="binary_synergy", seed=42
        )
        print(f"    Seed {s:>2} Macro AUROC  : Mean Diff = {d_m:+.4f}, 95% CI = [{l_m:+.4f}, {h_m:+.4f}]")
        print(f"    Seed {s:>2} Synergy AUROC: Mean Diff = {d_s:+.4f}, 95% CI = [{l_s:+.4f}, {h_s:+.4f}]")

    # 3. Secondary Bootstrap Restricted to Pairs Where BOTH Drugs Have >= 1 Target
    print("\n" + "=" * 100)
    print("  PAIRED BOOTSTRAP RESTRICTED TO PAIRS WITH NONZERO TARGET COVERAGE ON BOTH DRUGS")
    print("=" * 100)

    dt_edges = heterodata["drug", "drug_protein", "gene/protein"].edge_index.numpy()
    target_drugs_set = set(dt_edges[0])

    test_a_global = heterodata.label_test_drug_a.numpy()
    test_b_global = heterodata.label_test_drug_b.numpy()
    both_nonzero_mask = np.array([a in target_drugs_set and b in target_drugs_set for a, b in zip(test_a_global, test_b_global)])

    test_df_sub = test_df[both_nonzero_mask].reset_index(drop=True)
    labels_np_sub = test_labels_np[both_nonzero_mask]
    probs_runC_sub = mean_prob_runC[both_nonzero_mask]
    probs_base_sub = mean_prob_base[both_nonzero_mask]

    diff_macro_sub, lo_macro_sub, hi_macro_sub, _, n_c_sub = paired_cold_drug_bootstrap_full_test(
        test_df_sub, labels_np_sub, probs_runC_sub, probs_base_sub, cold_test_drugs, metric_type="macro_ovr", seed=42
    )
    diff_syn_sub, lo_syn_sub, hi_syn_sub, _, _ = paired_cold_drug_bootstrap_full_test(
        test_df_sub, labels_np_sub, probs_runC_sub, probs_base_sub, cold_test_drugs, metric_type="binary_synergy", seed=42
    )

    print(f"\n>>> Both-Nonzero Pairs Only ({both_nonzero_mask.sum():,} / {len(test_df):,} pairs, {both_nonzero_mask.mean()*100:.1f}%):")
    print(f"    Macro AUROC (OVR)    : Mean Diff = {diff_macro_sub:+.4f}, 95% CI = [{lo_macro_sub:+.4f}, {hi_macro_sub:+.4f}]")
    print(f"    Binary Synergy AUROC : Mean Diff = {diff_syn_sub:+.4f}, 95% CI = [{lo_syn_sub:+.4f}, {hi_syn_sub:+.4f}]")

    # ── Pre-Declared Success Criterion Evaluation ──
    print("\n" + "=" * 100)
    print("  PRE-DECLARED SUCCESS CRITERION EVALUATION")
    print("=" * 100)

    runC_full_syn_mean = float(np.mean([runC_results[s]["Full"]["syn_auroc_mean"] for s in SEEDS]))
    base_full_syn_mean = 0.5673
    delta_full_syn = runC_full_syn_mean - base_full_syn_mean

    ci_excludes_zero = (lo_syn > 0) or (hi_syn < 0)

    runC_bilat_syn_mean = float(np.mean([runC_results[s]["Bilateral"]["syn_auroc_mean"] for s in SEEDS]))
    base_bilat_syn_mean = 0.5070
    bilat_drop = base_bilat_syn_mean - runC_bilat_syn_mean
    bilat_ok = bilat_drop <= 0.0100

    cond1 = delta_full_syn >= 0.0300
    cond2 = ci_excludes_zero
    cond3 = bilat_ok

    is_met = cond1 and cond2 and cond3

    print(f"1. Full-test synergy AUROC improvement >= +0.03 versus baseline Mean A (0.5673):")
    print(f"   Run C Mean: {runC_full_syn_mean:.4f} vs Baseline: {base_full_syn_mean:.4f}")
    print(f"   Delta: {delta_full_syn:+.4f} (Required: >= +0.0300) -> {'PASS' if cond1 else 'FAIL'}")

    print(f"\n2. 184-drug paired bootstrap 95% CI excludes zero:")
    print(f"   95% CI: [{lo_syn:+.4f}, {hi_syn:+.4f}] -> {'PASS' if cond2 else 'FAIL'}")

    print(f"\n3. Bilateral synergy AUROC does not decrease by > 0.01 from baseline (0.5070):")
    print(f"   Run C Bilateral Mean: {runC_bilat_syn_mean:.4f} vs Baseline: {base_bilat_syn_mean:.4f}")
    print(f"   Change: {-bilat_drop:+.4f} (Allowed drop: <= -0.0100) -> {'PASS' if cond3 else 'FAIL'}")

    verdict = "MET" if is_met else "NOT MET"
    print(f"\n>>> FINAL VERDICT: {verdict} <<<")

    return {
        "wall_clocks": wall_clocks,
        "runC_results": runC_results,
        "base_results": base_results,
        "bootstrap_full": (diff_macro, lo_macro, hi_macro, diff_syn, lo_syn, hi_syn),
        "bootstrap_sub": (diff_macro_sub, lo_macro_sub, hi_macro_sub, diff_syn_sub, lo_syn_sub, hi_syn_sub),
        "criteria": {
            "cond1": (cond1, delta_full_syn),
            "cond2": (cond2, lo_syn, hi_syn),
            "cond3": (cond3, runC_bilat_syn_mean),
            "verdict": verdict,
        },
    }


def main():
    wall_clocks, runC_ckpts = train_runC()
    evaluate_runC(wall_clocks, runC_ckpts)


if __name__ == "__main__":
    main()
