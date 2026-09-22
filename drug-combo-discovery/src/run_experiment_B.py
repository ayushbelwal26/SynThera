"""
src/run_experiment_B.py
======================
Executes Experiment Run B: Drug-level regularization during training.

Changes:
1. Fingerprint bit dropout: randomly zero out 10% of each drug's 2048-bit Morgan FP bits before projection.
2. Drug-edge masking: for a random 15% of drugs in each training batch, drop a random half of non-drug-drug graph edges.
3. Seeds: 1, 2, 3, 42. Checkpoints saved to models/runB_seed{N}.ckpt.
4. Deterministic 5-pass evaluation (eval_splits.py).
5. 184-drug paired cold-drug bootstrap comparing Run B mean prediction vs baseline mean prediction.
6. Evaluates against pre-declared success criterion.
"""

import os
import sys
import time
import glob
import re
import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
sys.path.insert(0, SRC)

from train import main as train_main, load_data, build_loaders
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


def run_training():
    wall_clocks = {}
    saved_ckpts = {}

    print("=" * 90)
    print("  RUN B: TRAINING 4 SEEDS WITH DRUG-LEVEL REGULARIZATION")
    print("=" * 90)

    for s in SEEDS:
        run_name = f"runB_seed{s}"
        ckpt_path = os.path.join(MODELS_DIR, f"{run_name}.ckpt")

        print(f"\n>>> Starting training for Seed {s} ({run_name})...")
        t0 = time.time()
        saved_path, elapsed = train_main(
            run_name=run_name,
            seed=s,
            save_all_epochs=False,
            checkpoint_dir=MODELS_DIR,
            use_regularization=True,
            fp_dropout=0.10,
            drug_mask_frac=0.15,
            edge_drop_frac=0.50,
        )
        wall_clocks[s] = elapsed
        saved_ckpts[s] = ckpt_path
        print(f">>> Seed {s} finished in {elapsed:.1f}s ({elapsed/60:.2f} min). Checkpoint: {ckpt_path}")

    return wall_clocks, saved_ckpts


def run_evaluation(wall_clocks, runB_ckpts):
    print("\n" + "=" * 90)
    print("  RUN B: EVALUATION & PAIRED BOOTSTRAP")
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

    # 1. Evaluate Run B models (5-pass deterministic)
    runB_results = {}
    runB_probs = {}
    test_labels_np = None

    print("\n--- Evaluating Run B Checkpoints (5-pass deterministic) ---")
    for s in SEEDS:
        ckpt = runB_ckpts[s]
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
        runB_results[s] = res_dict
        runB_probs[s] = mean_p
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
    mean_prob_runB = np.mean([runB_probs[s] for s in SEEDS], axis=0)
    mean_prob_base = np.mean([base_probs[s] for s in SEEDS], axis=0)

    # ── Report Test Metrics ──
    print("\n" + "=" * 100)
    print("  RUN B TEST METRICS (5-Pass Deterministic Evaluation)")
    print("=" * 100)

    subsets = ["Full", "Bilateral"]
    for sub in subsets:
        print(f"\n--- SUBSET: {sub} Test Set ---")
        print(f"{'Model / Seed':<20} | {'Macro AUROC':<16} | {'Syn AUROC':<16} | {'Syn AUPR':<16} | {'Lift':<12}")
        print("-" * 88)
        for s in SEEDS:
            m = runB_results[s][sub]
            print(f"Run B Seed {s:<9} | {m['macro_auroc_mean']:.4f} (+/-{m['macro_auroc_sd']:.4f}) | "
                  f"{m['syn_auroc_mean']:.4f} (+/-{m['syn_auroc_sd']:.4f}) | "
                  f"{m['syn_aupr_mean']:.4f} (+/-{m['syn_aupr_sd']:.4f}) | "
                  f"{m['lift_mean']:.2f} (+/-{m['lift_sd']:.2f})")

        # Mean and SD across seeds
        m_aucs = [runB_results[s][sub]["macro_auroc_mean"] for s in SEEDS]
        s_aucs = [runB_results[s][sub]["syn_auroc_mean"] for s in SEEDS]
        s_auprs = [runB_results[s][sub]["syn_aupr_mean"] for s in SEEDS]
        lifts = [runB_results[s][sub]["lift_mean"] for s in SEEDS]
        print("-" * 88)
        print(f"{'Run B Mean (All)':<20} | {np.mean(m_aucs):.4f} (+/-{np.std(m_aucs):.4f}) | "
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

    # ── Task 5 Utility: Paired Cold-Drug Bootstrap on Full Test Set ──
    print("\n" + "=" * 100)
    print("  184-DRUG PAIRED COLD-DRUG BOOTSTRAP (Full Test Set)")
    print("=" * 100)

    # 1. Run B Mean Prediction vs Baseline Mean Prediction
    diff_macro, lo_macro, hi_macro, _, n_c = paired_cold_drug_bootstrap_full_test(
        test_df, test_labels_np, mean_prob_runB, mean_prob_base, cold_test_drugs, metric_type="macro_ovr", seed=42
    )
    diff_syn, lo_syn, hi_syn, _, _ = paired_cold_drug_bootstrap_full_test(
        test_df, test_labels_np, mean_prob_runB, mean_prob_base, cold_test_drugs, metric_type="binary_synergy", seed=42
    )

    print(f"\n>>> Run B Mean Prediction minus Baseline Mean Prediction (Cold test drugs: {n_c}):")
    print(f"    Macro AUROC (OVR)    : Mean Diff = {diff_macro:+.4f}, 95% CI = [{lo_macro:+.4f}, {hi_macro:+.4f}]")
    print(f"    Binary Synergy AUROC : Mean Diff = {diff_syn:+.4f}, 95% CI = [{lo_syn:+.4f}, {hi_syn:+.4f}]")

    # 2. Per-seed paired comparisons
    print("\n>>> Per-Seed Paired Comparisons (Run B Seed s minus Baseline Seed s):")
    seed_diffs_macro = []
    seed_diffs_syn = []
    for s in SEEDS:
        d_m, l_m, h_m, _, _ = paired_cold_drug_bootstrap_full_test(
            test_df, test_labels_np, runB_probs[s], base_probs[s], cold_test_drugs, metric_type="macro_ovr", seed=42
        )
        d_s, l_s, h_s, _, _ = paired_cold_drug_bootstrap_full_test(
            test_df, test_labels_np, runB_probs[s], base_probs[s], cold_test_drugs, metric_type="binary_synergy", seed=42
        )
        seed_diffs_macro.append((d_m, l_m, h_m))
        seed_diffs_syn.append((d_s, l_s, h_s))
        print(f"    Seed {s:>2} Macro AUROC  : Mean Diff = {d_m:+.4f}, 95% CI = [{l_m:+.4f}, {h_m:+.4f}]")
        print(f"    Seed {s:>2} Synergy AUROC: Mean Diff = {d_s:+.4f}, 95% CI = [{l_s:+.4f}, {h_s:+.4f}]")

    # ── Pre-Declared Success Criterion Evaluation ──
    print("\n" + "=" * 100)
    print("  PRE-DECLARED SUCCESS CRITERION EVALUATION")
    print("=" * 100)

    # Values for criteria:
    runB_full_syn_mean = float(np.mean([runB_results[s]["Full"]["syn_auroc_mean"] for s in SEEDS]))
    base_full_syn_mean = 0.5673
    delta_full_syn = runB_full_syn_mean - base_full_syn_mean

    # CI excludes zero:
    ci_excludes_zero = (lo_syn > 0) or (hi_syn < 0)

    # Bilateral synergy AUROC does not decrease by more than 0.01 from baseline Mean A (0.5070):
    runB_bilat_syn_mean = float(np.mean([runB_results[s]["Bilateral"]["syn_auroc_mean"] for s in SEEDS]))
    base_bilat_syn_mean = 0.5070
    bilat_drop = base_bilat_syn_mean - runB_bilat_syn_mean
    bilat_ok = bilat_drop <= 0.0100

    cond1 = delta_full_syn >= 0.0300
    cond2 = ci_excludes_zero
    cond3 = bilat_ok

    is_met = cond1 and cond2 and cond3

    print(f"1. Full-test synergy AUROC improvement >= +0.03:")
    print(f"   Run B Mean: {runB_full_syn_mean:.4f} vs Baseline: {base_full_syn_mean:.4f}")
    print(f"   Delta: {delta_full_syn:+.4f} (Required: >= +0.0300) -> {'PASS' if cond1 else 'FAIL'}")

    print(f"\n2. Paired bootstrap 95% CI excludes zero:")
    print(f"   95% CI: [{lo_syn:+.4f}, {hi_syn:+.4f}] -> {'PASS' if cond2 else 'FAIL'}")

    print(f"\n3. Bilateral synergy AUROC does not decrease by > 0.01 from baseline (0.5070):")
    print(f"   Run B Bilateral Mean: {runB_bilat_syn_mean:.4f} vs Baseline: {base_bilat_syn_mean:.4f}")
    print(f"   Change: {-bilat_drop:+.4f} (Allowed drop: <= -0.0100) -> {'PASS' if cond3 else 'FAIL'}")

    verdict = "MET" if is_met else "NOT MET"
    print(f"\n>>> FINAL VERDICT: {verdict} <<<")

    return {
        "wall_clocks": wall_clocks,
        "runB_results": runB_results,
        "base_results": base_results,
        "bootstrap": {
            "mean_macro": (diff_macro, lo_macro, hi_macro),
            "mean_syn": (diff_syn, lo_syn, hi_syn),
            "seeds_macro": seed_diffs_macro,
            "seeds_syn": seed_diffs_syn,
        },
        "criteria": {
            "cond1": (cond1, delta_full_syn),
            "cond2": (cond2, lo_syn, hi_syn),
            "cond3": (cond3, runB_bilat_syn_mean),
            "verdict": verdict,
        },
    }


def main():
    wall_clocks, runB_ckpts = run_training()
    run_evaluation(wall_clocks, runB_ckpts)


if __name__ == "__main__":
    main()
