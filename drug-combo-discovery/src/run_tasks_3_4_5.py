"""
run_tasks_3_4_5.py

Executes:
- Task 3: Validation diagnostics on all 30 per-epoch checkpoints in models/b0/.
- Task 4: Selection-rule comparison (Rules A, B, C) on test sets using 5-pass deterministic evaluation.
- Task 5: Better-powered paired cold-drug bootstrap on the full test set.
"""

import os
import sys
import glob
import re
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
from model import SynergyModule
from eval_splits import compute_macro_metrics, compute_binary_synergy_metrics

B0_DIR = os.path.join(MODELS_DIR, "b0")


# ─────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────

def load_environment():
    heterodata = torch.load(HETERODATA_PATH, weights_only=False)
    _, val_loader, test_loader = build_loaders(heterodata, [], [], [])

    labels_df = pd.read_csv(LABELS_PATH)
    train_idx = pd.read_csv(SPLIT_TRAIN_PATH)["row_index"].values
    val_idx = pd.read_csv(SPLIT_VAL_PATH)["row_index"].values
    test_idx = pd.read_csv(SPLIT_TEST_PATH)["row_index"].values

    train_df = labels_df.iloc[train_idx].reset_index(drop=True)
    val_df = labels_df.iloc[val_idx].reset_index(drop=True)
    test_df = labels_df.iloc[test_idx].reset_index(drop=True)

    train_drugs = set(train_df["drug_a_kg_id"]) | set(train_df["drug_b_kg_id"])
    test_drugs = set(test_df["drug_a_kg_id"]) | set(test_df["drug_b_kg_id"])
    cold_test_drugs = test_drugs - train_drugs

    # Validation subsets
    val_a_in_train = val_df["drug_a_kg_id"].isin(train_drugs).values
    val_b_in_train = val_df["drug_b_kg_id"].isin(train_drugs).values
    mask_bilat_val = (~val_a_in_train) & (~val_b_in_train)

    # Test subsets
    test_a_in_train = test_df["drug_a_kg_id"].isin(train_drugs).values
    test_b_in_train = test_df["drug_b_kg_id"].isin(train_drugs).values
    mask_bilat_test = (~test_a_in_train) & (~test_b_in_train)
    mask_unilat_test = (test_a_in_train & ~test_b_in_train) | (~test_a_in_train & test_b_in_train)
    mask_full_test = np.ones(len(test_df), dtype=bool)

    masks_test = {
        "Full": mask_full_test,
        "Bilateral": mask_bilat_test,
        "Unilateral": mask_unilat_test,
    }

    class_weights = compute_class_weights(heterodata)

    return (
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
    )


def evaluate_model_on_val(model, val_loader, mask_bilat_val, class_weights, device="cuda"):
    device_obj = torch.device(device if torch.cuda.is_available() else "cpu")
    cw = class_weights.to(device_obj)

    torch.manual_seed(42)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(42)
    np.random.seed(42)

    val_logits, val_labels = [], []
    total_loss = 0.0
    total_pairs = 0

    with torch.no_grad():
        for batch in val_loader:
            batch = batch.to(device_obj)
            logits, labels = model(batch)
            if logits.shape[0] > 0:
                loss = F.cross_entropy(logits, labels, weight=cw, reduction="sum")
                total_loss += loss.item()
                total_pairs += logits.shape[0]
                val_logits.append(logits.detach().cpu())
                val_labels.append(labels.detach().cpu())

    val_loss = total_loss / (total_pairs + 1e-12)
    val_logits = torch.cat(val_logits, dim=0)
    val_labels = torch.cat(val_labels, dim=0)
    probs = F.softmax(val_logits, dim=-1).numpy()
    labels_np = val_labels.numpy()

    # Val Macro AUROC (all pairs)
    val_macro_auroc, _ = compute_macro_metrics(labels_np, probs)
    # Val Synergy AUROC (all pairs)
    val_syn_auroc, _, _ = compute_binary_synergy_metrics(labels_np, probs)

    # Val Macro AUROC (bilateral val subset only)
    bilat_y = labels_np[mask_bilat_val]
    bilat_p = probs[mask_bilat_val]
    val_bilat_macro_auroc, _ = compute_macro_metrics(bilat_y, bilat_p)

    return {
        "val_loss": val_loss,
        "val_macro_auroc": val_macro_auroc,
        "val_syn_auroc": val_syn_auroc,
        "val_bilat_macro_auroc": val_bilat_macro_auroc,
    }


def evaluate_model_on_test_5pass(model, test_loader, masks_test, device="cuda", n_passes=5):
    device_obj = torch.device(device if torch.cuda.is_available() else "cpu")

    pass_probs = []
    labels_np = None

    pass_metrics = {sub: [] for sub in masks_test}

    for p_idx in range(n_passes):
        torch.manual_seed(p_idx)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(p_idx)
        np.random.seed(p_idx)

        logits_list, labels_list = [], []
        with torch.no_grad():
            for batch in test_loader:
                batch = batch.to(device_obj)
                logits, labels = model(batch)
                if logits.shape[0] > 0:
                    logits_list.append(logits.detach().cpu())
                    labels_list.append(labels.detach().cpu())

        logits_all = torch.cat(logits_list, dim=0)
        labels_all = torch.cat(labels_list, dim=0)
        probs_p = F.softmax(logits_all, dim=-1).numpy()
        if labels_np is None:
            labels_np = labels_all.numpy()

        pass_probs.append(probs_p)

        for sub, mask in masks_test.items():
            sub_y = labels_np[mask]
            sub_p = probs_p[mask]
            sub_macro_auc, _ = compute_macro_metrics(sub_y, sub_p)
            sub_syn_auc, sub_syn_aupr, sub_lift = compute_binary_synergy_metrics(sub_y, sub_p)
            pass_metrics[sub].append({
                "macro_auroc": sub_macro_auc,
                "syn_auroc": sub_syn_auc,
                "syn_aupr": sub_syn_aupr,
                "lift": sub_lift,
            })

    mean_probs = np.mean(pass_probs, axis=0)

    results = {}
    for sub, m_list in pass_metrics.items():
        macro_aucs = [m["macro_auroc"] for m in m_list]
        syn_aucs = [m["syn_auroc"] for m in m_list]
        syn_auprs = [m["syn_aupr"] for m in m_list]
        lifts = [m["lift"] for m in m_list]

        results[sub] = {
            "macro_auroc_mean": np.mean(macro_aucs),
            "macro_auroc_sd": np.std(macro_aucs),
            "syn_auroc_mean": np.mean(syn_aucs),
            "syn_auroc_sd": np.std(syn_aucs),
            "syn_aupr_mean": np.mean(syn_auprs),
            "syn_aupr_sd": np.std(syn_auprs),
            "lift_mean": np.mean(lifts),
            "lift_sd": np.std(lifts),
        }

    return results, mean_probs, labels_np


# ─────────────────────────────────────────────────────────────────
# TASK 5: Paired Cold-Drug Bootstrap on Full Test Set
# ─────────────────────────────────────────────────────────────────

def paired_cold_drug_bootstrap_full_test(
    test_df: pd.DataFrame,
    labels_np: np.ndarray,
    probs_A: np.ndarray,
    probs_B: np.ndarray,
    cold_test_drugs: set,
    metric_type: str = "macro_ovr",
    n_bootstraps: int = 1000,
    seed: int = 42,
) -> tuple[float, float, float, int, int]:
    """
    Cold-drug paired bootstrap on the FULL test set.
    Resamples unique cold test drugs with replacement.
    A pair is kept if and only if all of its cold drugs are in the bootstrap resample.
    Returns:
      (mean_diff, ci_lower, ci_upper, n_valid_iterations, n_unique_cold_drugs)
    """
    rng = np.random.RandomState(seed)
    cold_drugs_arr = np.array(sorted(list(cold_test_drugs)))
    n_cold = len(cold_drugs_arr)

    a_drugs = test_df["drug_a_kg_id"].values
    b_drugs = test_df["drug_b_kg_id"].values

    a_is_cold = np.isin(a_drugs, cold_drugs_arr)
    b_is_cold = np.isin(b_drugs, cold_drugs_arr)

    diffs = []
    for _ in range(n_bootstraps):
        sampled_cold = set(rng.choice(cold_drugs_arr, size=n_cold, replace=True))

        # A pair is kept if every drug that is cold is in sampled_cold
        a_ok = (~a_is_cold) | np.isin(a_drugs, list(sampled_cold))
        b_ok = (~b_is_cold) | np.isin(b_drugs, list(sampled_cold))
        pair_mask = a_ok & b_ok

        if pair_mask.sum() < 20:
            continue

        sub_y = labels_np[pair_mask]

        if metric_type == "macro_ovr":
            if len(np.unique(sub_y)) < 3:
                continue
            try:
                auc_A = roc_auc_score(sub_y, probs_A[pair_mask], multi_class="ovr", average="macro")
                auc_B = roc_auc_score(sub_y, probs_B[pair_mask], multi_class="ovr", average="macro")
                diffs.append(auc_A - auc_B)
            except ValueError:
                continue
        elif metric_type == "binary_synergy":
            sub_y_bin = (sub_y == 2).astype(int)
            if len(np.unique(sub_y_bin)) < 2:
                continue
            try:
                auc_A = roc_auc_score(sub_y_bin, probs_A[pair_mask, 2])
                auc_B = roc_auc_score(sub_y_bin, probs_B[pair_mask, 2])
                diffs.append(auc_A - auc_B)
            except ValueError:
                continue

    diff_arr = np.array(diffs)
    mean_diff = float(np.mean(diff_arr))
    ci_lower = float(np.percentile(diff_arr, 2.5))
    ci_upper = float(np.percentile(diff_arr, 97.5))

    return mean_diff, ci_lower, ci_upper, len(diffs), n_cold


# ─────────────────────────────────────────────────────────────────
# Main Pipeline
# ─────────────────────────────────────────────────────────────────

def run():
    print("=" * 90)
    print("  DIAGNOSTICS & SELECTION-RULE COMPARISON PIPELINE")
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

    # ── Task 3: Validation Diagnostics on All Saved Epoch Checkpoints ──
    print("\n" + "=" * 90)
    print("  TASK 3: VALIDATION DIAGNOSTICS FOR ALL EPOCHS")
    print("=" * 90)

    seeds = [1, 2, 3, 42]
    val_records = []

    for s in seeds:
        # Find all checkpoints for this seed
        pattern = os.path.join(B0_DIR, f"seed{s}_epoch*.ckpt")
        ckpts = sorted(glob.glob(pattern), key=lambda x: int(re.search(r"epoch(\d+)", x).group(1)))
        print(f"\nEvaluating Seed {s} ({len(ckpts)} epochs)...")

        for ckpt in ckpts:
            epoch_num = int(re.search(r"epoch(\d+)", ckpt).group(1))
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

            m = evaluate_model_on_val(model, val_loader, mask_bilat_val, class_weights)
            val_records.append({
                "seed": s,
                "epoch": epoch_num,
                "ckpt_path": ckpt,
                "val_loss": m["val_loss"],
                "val_macro_auroc": m["val_macro_auroc"],
                "val_syn_auroc": m["val_syn_auroc"],
                "val_bilat_macro_auroc": m["val_bilat_macro_auroc"],
            })
            print(f"  Seed {s:>2} | Epoch {epoch_num:>2} | Val Loss: {m['val_loss']:.4f} | "
                  f"Val Macro AUROC: {m['val_macro_auroc']:.4f} | "
                  f"Val Syn AUROC: {m['val_syn_auroc']:.4f} | "
                  f"Val Bilat Macro AUROC: {m['val_bilat_macro_auroc']:.4f}")

    df_val = pd.DataFrame(val_records)

    # ── Task 4: Selection Rules ──
    print("\n" + "=" * 90)
    print("  TASK 4: SELECTION-RULE COMPARISON")
    print("=" * 90)

    # For each seed, select checkpoints using validation only:
    # Rule A: min val_loss
    # Rule B: max val_bilat_macro_auroc
    # Rule C: max val_macro_auroc
    selected_ckpts = {}

    for s in seeds:
        sub_df = df_val[df_val["seed"] == s]
        epoch_A = sub_df.sort_values("val_loss", ascending=True).iloc[0]
        epoch_B = sub_df.sort_values("val_bilat_macro_auroc", ascending=False).iloc[0]
        epoch_C = sub_df.sort_values("val_macro_auroc", ascending=False).iloc[0]

        selected_ckpts[s] = {
            "A": {"epoch": int(epoch_A["epoch"]), "ckpt": epoch_A["ckpt_path"]},
            "B": {"epoch": int(epoch_B["epoch"]), "ckpt": epoch_B["ckpt_path"]},
            "C": {"epoch": int(epoch_C["epoch"]), "ckpt": epoch_C["ckpt_path"]},
        }

    print("\nSelected Epochs per Seed:")
    print(f"{'Seed':<6} | {'Rule A (min val_loss)':<24} | {'Rule B (max bilat AUROC)':<26} | {'Rule C (max all-val AUROC)':<26}")
    print("-" * 86)
    for s in seeds:
        print(f"{s:<6} | Epoch {selected_ckpts[s]['A']['epoch']:<18} | Epoch {selected_ckpts[s]['B']['epoch']:<20} | Epoch {selected_ckpts[s]['C']['epoch']:<20}")

    # Now evaluate each selected checkpoint on test using 5-pass deterministic evaluation
    print("\nEvaluating Selected Checkpoints on Test Sets (5-pass deterministic)...")
    test_eval_results = []
    selected_probs = {}  # (seed, rule) -> mean_probs

    for s in seeds:
        for rule in ["A", "B", "C"]:
            info = selected_ckpts[s][rule]
            ckpt = info["ckpt"]
            ep = info["epoch"]

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

            m_dict, mean_probs, test_labels_np = evaluate_model_on_test_5pass(model, test_loader, masks_test)
            selected_probs[(s, rule)] = mean_probs

            for sub in ["Full", "Bilateral", "Unilateral"]:
                test_eval_results.append({
                    "seed": s,
                    "rule": rule,
                    "epoch": ep,
                    "subset": sub,
                    "macro_auroc": m_dict[sub]["macro_auroc_mean"],
                    "macro_auroc_sd": m_dict[sub]["macro_auroc_sd"],
                    "syn_auroc": m_dict[sub]["syn_auroc_mean"],
                    "syn_auroc_sd": m_dict[sub]["syn_auroc_sd"],
                    "syn_aupr": m_dict[sub]["syn_aupr_mean"],
                    "syn_aupr_sd": m_dict[sub]["syn_aupr_sd"],
                    "lift": m_dict[sub]["lift_mean"],
                    "lift_sd": m_dict[sub]["lift_sd"],
                })

    df_test_eval = pd.DataFrame(test_eval_results)

    # Print summary tables per subset and rule
    for sub in ["Full", "Bilateral", "Unilateral"]:
        print(f"\n{'='*100}\n  TEST SUBSET: {sub}\n{'='*100}")
        print(f"{'Rule':<6} | {'Seed':<6} | {'Epoch':<6} | {'Macro AUROC':<12} | {'Syn AUROC':<12} | {'Syn AUPR':<12} | {'Lift (AUPR/prev)':<16}")
        print("-" * 100)
        sub_df = df_test_eval[df_test_eval["subset"] == sub]
        for rule in ["A", "B", "C"]:
            r_df = sub_df[sub_df["rule"] == rule]
            for _, row in r_df.iterrows():
                print(f"Rule {rule:<1} | {int(row['seed']):<6} | {int(row['epoch']):<6} | "
                      f"{row['macro_auroc']:>7.4f} (+/-{row['macro_auroc_sd']:.4f}) | "
                      f"{row['syn_auroc']:>7.4f} (+/-{row['syn_auroc_sd']:.4f}) | "
                      f"{row['syn_aupr']:>7.4f} (+/-{row['syn_aupr_sd']:.4f}) | "
                      f"{row['lift']:>6.2f} (+/-{row['lift_sd']:.2f})")

            # Mean and SD across the 4 seeds
            m_auc = r_df["macro_auroc"].mean()
            sd_auc = r_df["macro_auroc"].std()
            m_syn = r_df["syn_auroc"].mean()
            sd_syn = r_df["syn_auroc"].std()
            m_pr = r_df["syn_aupr"].mean()
            sd_pr = r_df["syn_aupr"].std()
            m_lift = r_df["lift"].mean()
            sd_lift = r_df["lift"].std()
            print(f"Mean {rule:<1} | {'ALL':<6} | {'-':<6} | "
                  f"{m_auc:>7.4f} (+/-{sd_auc:.4f}) | "
                  f"{m_syn:>7.4f} (+/-{sd_syn:.4f}) | "
                  f"{m_pr:>7.4f} (+/-{sd_pr:.4f}) | "
                  f"{m_lift:>6.2f} (+/-{sd_lift:.2f})")
            print("-" * 100)

    # ── Task 5: Better-Powered Paired Bootstrap on Full Test Set ──
    print("\n" + "=" * 90)
    print("  TASK 5: BETTER-POWERED PAIRED COLD-DRUG BOOTSTRAP (Full Test Set)")
    print("=" * 90)

    # 1. Also load and run 5-pass deterministic eval for Run A
    runA_ckpt = os.path.join(MODELS_DIR, "synergy_gnn_runA.ckpt")
    print(f"\nRunning 5-pass deterministic eval for Run A ({os.path.basename(runA_ckpt)})...")
    model_runA = SynergyModule.load_from_checkpoint(
        runA_ckpt,
        metadata=metadata,
        num_nodes_dict=num_nodes_dict,
        num_fallback_drugs=n_fallback,
        num_cell_lines=heterodata.num_cell_lines,
        num_layers=2,
        class_weights=class_weights,
    )
    model_runA.to(device_obj)
    model_runA.eval()
    _, probs_runA, _ = evaluate_model_on_test_5pass(model_runA, test_loader, masks_test)

    # Bootstrap comparisons to run:
    # A. B minus A (Macro AUROC & Synergy AUROC) for each seed and averaged across seeds
    # B. C minus A (Macro AUROC & Synergy AUROC) for each seed and averaged across seeds
    # C. Run A minus Seed 42 baseline (Rule A seed 42)
    # D. Run A minus mean of single-seed baselines (Rule A)

    # Paired comparisons
    print("\n1. Rule B minus Rule A (max bilateral val AUROC vs min val_loss):")
    for metric in ["macro_ovr", "binary_synergy"]:
        seed_diffs = []
        for s in seeds:
            p_B = selected_probs[(s, "B")]
            p_A = selected_probs[(s, "A")]
            diff, ci_lo, ci_hi, n_v, n_c = paired_cold_drug_bootstrap_full_test(
                test_df, test_labels_np, p_B, p_A, cold_test_drugs, metric_type=metric, seed=42
            )
            seed_diffs.append((diff, ci_lo, ci_hi))
            print(f"   Seed {s:>2} [{metric:<14}] : Mean Diff = {diff:+.4f}, 95% CI = [{ci_lo:+.4f}, {ci_hi:+.4f}]")
        avg_diff = np.mean([x[0] for x in seed_diffs])
        avg_ci_lo = np.mean([x[1] for x in seed_diffs])
        avg_ci_hi = np.mean([x[2] for x in seed_diffs])
        print(f"   => Average B - A [{metric:<14}]: Mean Diff = {avg_diff:+.4f}, Avg 95% CI = [{avg_ci_lo:+.4f}, {avg_ci_hi:+.4f}]")

    print("\n2. Rule C minus Rule A (max all-val AUROC vs min val_loss):")
    for metric in ["macro_ovr", "binary_synergy"]:
        seed_diffs = []
        for s in seeds:
            p_C = selected_probs[(s, "C")]
            p_A = selected_probs[(s, "A")]
            diff, ci_lo, ci_hi, n_v, n_c = paired_cold_drug_bootstrap_full_test(
                test_df, test_labels_np, p_C, p_A, cold_test_drugs, metric_type=metric, seed=42
            )
            seed_diffs.append((diff, ci_lo, ci_hi))
            print(f"   Seed {s:>2} [{metric:<14}] : Mean Diff = {diff:+.4f}, 95% CI = [{ci_lo:+.4f}, {ci_hi:+.4f}]")
        avg_diff = np.mean([x[0] for x in seed_diffs])
        avg_ci_lo = np.mean([x[1] for x in seed_diffs])
        avg_ci_hi = np.mean([x[2] for x in seed_diffs])
        print(f"   => Average C - A [{metric:<14}]: Mean Diff = {avg_diff:+.4f}, Avg 95% CI = [{avg_ci_lo:+.4f}, {avg_ci_hi:+.4f}]")

    print("\n3. Run A minus Seed 42 Baseline (Rule A):")
    p_42_A = selected_probs[(42, "A")]
    for metric in ["macro_ovr", "binary_synergy"]:
        diff, ci_lo, ci_hi, n_v, n_c = paired_cold_drug_bootstrap_full_test(
            test_df, test_labels_np, probs_runA, p_42_A, cold_test_drugs, metric_type=metric, seed=42
        )
        print(f"   [{metric:<14}] : Mean Diff = {diff:+.4f}, 95% CI = [{ci_lo:+.4f}, {ci_hi:+.4f}] (Unique cold test drugs: {n_c})")

    print("\n4. Run A minus Single-Seed Baselines (Rule A):")
    for metric in ["macro_ovr", "binary_synergy"]:
        seed_diffs = []
        for s in seeds:
            p_s_A = selected_probs[(s, "A")]
            diff, ci_lo, ci_hi, n_v, n_c = paired_cold_drug_bootstrap_full_test(
                test_df, test_labels_np, probs_runA, p_s_A, cold_test_drugs, metric_type=metric, seed=42
            )
            seed_diffs.append((diff, ci_lo, ci_hi))
            print(f"   Run A - Seed {s:>2} [{metric:<14}] : Mean Diff = {diff:+.4f}, 95% CI = [{ci_lo:+.4f}, {ci_hi:+.4f}]")
        avg_diff = np.mean([x[0] for x in seed_diffs])
        avg_ci_lo = np.mean([x[1] for x in seed_diffs])
        avg_ci_hi = np.mean([x[2] for x in seed_diffs])
        print(f"   => Run A - Mean of Single-Seed Baselines [{metric:<14}]: Mean Diff = {avg_diff:+.4f}, Avg 95% CI = [{avg_ci_lo:+.4f}, {avg_ci_hi:+.4f}] (Unique cold test drugs: {n_c})")

    print("=" * 90)


if __name__ == "__main__":
    run()
