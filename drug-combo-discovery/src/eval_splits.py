"""
Evaluation helper for cold-drug split and its bilateral vs. unilateral subsets.

Evaluates SynergyGNN (current checkpoint) across:
1. Full cold-drug test split (all held-out pairs where drug_a in D_test or drug_b in D_test)
2. Bilateral cold-drug test pairs (strictest subset: neither drug in train)
3. Unilateral cold-drug test pairs (exactly one drug in train)

Prints a clean 3-row comparison table of AUROC and AUPR.
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
    SPLIT_TEST_PATH,
    MODELS_DIR,
    build_loaders,
    compute_class_weights,
)
from model import SynergyModule, CLASS_NAMES

CLASS_MAP = {"antagonism": 0, "additive": 1, "synergy": 2}


def compute_macro_metrics(labels_np: np.ndarray, probs: np.ndarray) -> tuple[float, float]:
    """Computes Macro AUROC (OVR) and Macro AUPR (unweighted mean across classes)."""
    try:
        auroc = float(roc_auc_score(labels_np, probs, multi_class="ovr", average="macro"))
    except ValueError:
        auroc = float("nan")

    aupr_per_class = []
    for c in range(3):
        binary_labels = (labels_np == c).astype(int)
        try:
            ap = average_precision_score(binary_labels, probs[:, c])
            aupr_per_class.append(ap)
        except ValueError:
            aupr_per_class.append(float("nan"))

    aupr = float(np.nanmean(aupr_per_class))
    return auroc, aupr


def compute_binary_synergy_metrics(labels_np: np.ndarray, probs: np.ndarray) -> tuple[float, float, float]:
    """Computes Binary Synergy AUROC, AUPR, and Lift (AUPR / prevalence)."""
    y_syn = (labels_np == 2).astype(int)
    scores = probs[:, 2]
    prev = float(np.mean(y_syn))
    if len(np.unique(y_syn)) < 2:
        return float("nan"), float("nan"), float("nan")
    try:
        auroc = float(roc_auc_score(y_syn, scores))
    except ValueError:
        auroc = float("nan")
    try:
        aupr = float(average_precision_score(y_syn, scores))
    except ValueError:
        aupr = float("nan")
    lift = aupr / (prev + 1e-12) if not np.isnan(aupr) else float("nan")
    return auroc, aupr, lift


def evaluate_cold_split_subsets(
    ckpt_path: str = os.path.join(MODELS_DIR, "synergy_gnn_final.ckpt"),
    heterodata_path: str = HETERODATA_PATH,
    batch_size: int = 256,
    device: str | None = None,
    eval_val: bool = True,
    return_details: bool = False,
    n_passes: int = 5,
    symmetric: bool = False,
) -> dict[str, dict[str, float]] | tuple:
    """
    Evaluates model predictions on val split, full cold-drug test, bilateral cold subset, and unilateral cold subset.
    When n_passes > 1, seeds torch/PyG (seeds 0 to n_passes-1) for deterministic evaluation, reporting mean and SD.
    When symmetric=True, evaluates both forward (A, B) and reverse (B, A) orderings per pair and averages probabilities.
    When symmetric=False, evaluates pairs in the single fixed order from labeled_pairs.csv (original eval behavior).
    """
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    device_obj = torch.device(device)

    print(f"\n[1/4] Loading HeteroData from {heterodata_path}...")
    heterodata = torch.load(heterodata_path, weights_only=False)
    _, val_loader, test_loader = build_loaders(heterodata, [], [], [])

    metadata = heterodata.metadata()
    num_nodes_dict = {nt: heterodata[nt].num_nodes for nt in heterodata.node_types}
    n_fallback = int((~heterodata["drug"].fp_mask).sum().item())
    class_weights = compute_class_weights(heterodata)

    print(f"\n[2/4] Loading model checkpoint from {ckpt_path} onto {device}...")
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

    results = {}
    mode_str = "Symmetric (S2 Averaged)" if symmetric else "Single Fixed-Order (Baseline)"

    # Optional: Validation split evaluation
    if eval_val:
        torch.manual_seed(42)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(42)
        np.random.seed(42)
        print(f"\n[Val Evaluation] Running inference over {len(val_loader)} val batches (seed=42, mode={mode_str})...")
        val_probs, val_labels = [], []
        with torch.no_grad():
            for idx, batch in enumerate(val_loader):
                batch = batch.to(device_obj)
                logits_fwd, labels = model(batch)
                if symmetric:
                    batch_rev = batch.clone()
                    edge_index_orig = batch_rev["drug", "synergy_pair", "drug"].edge_label_index
                    batch_rev["drug", "synergy_pair", "drug"].edge_label_index = edge_index_orig[[1, 0]]
                    logits_rev, _ = model(batch_rev)
                    p_fwd = F.softmax(logits_fwd, dim=-1)
                    p_rev = F.softmax(logits_rev, dim=-1)
                    p_sym = (p_fwd + p_rev) / 2.0
                    val_probs.append(p_sym.detach().cpu())
                else:
                    val_probs.append(F.softmax(logits_fwd, dim=-1).detach().cpu())
                if labels.shape[0] > 0:
                    val_labels.append(labels.detach().cpu())
        val_probs = torch.cat(val_probs, dim=0)
        val_labels = torch.cat(val_labels, dim=0)
        v_probs = val_probs.numpy()
        v_labels_np = val_labels.numpy()
        v_auroc, v_aupr = compute_macro_metrics(v_labels_np, v_probs)
        v_syn_auc, v_syn_aupr, v_lift = compute_binary_synergy_metrics(v_labels_np, v_probs)
        results["Validation Split"] = {
            "n_pairs": len(v_labels_np),
            "auroc": v_auroc,
            "aupr": v_aupr,
            "syn_auroc": v_syn_auc,
            "syn_aupr": v_syn_aupr,
            "lift": v_lift,
        }

    # Load pair metadata to identify bilateral vs unilateral subsets
    labels_df = pd.read_csv(LABELS_PATH)
    train_idx = pd.read_csv(SPLIT_TRAIN_PATH)["row_index"].values
    test_idx = pd.read_csv(SPLIT_TEST_PATH)["row_index"].values

    train_pairs = labels_df.iloc[train_idx]
    train_drugs = set(train_pairs["drug_a_kg_id"]) | set(train_pairs["drug_b_kg_id"])

    test_pairs = labels_df.iloc[test_idx].reset_index(drop=True)
    a_in_train = test_pairs["drug_a_kg_id"].isin(train_drugs).values
    b_in_train = test_pairs["drug_b_kg_id"].isin(train_drugs).values

    mask_bilateral = (~a_in_train) & (~b_in_train)
    mask_unilateral = (a_in_train & ~b_in_train) | (~a_in_train & b_in_train)

    subsets = {
        "Full cold-drug test (headline)": np.ones(len(test_pairs), dtype=bool),
        "Bilateral cold-drug (neither in train)": mask_bilateral,
        "Unilateral cold-drug (exactly one in train)": mask_unilateral,
    }

    # Multi-pass deterministic evaluation
    pass_probs_list = []
    pass_metrics_by_subset = {sub_name: [] for sub_name in subsets}

    print(f"\n[3/4] Running {n_passes}-pass deterministic evaluation (seeds 0 to {n_passes-1}, mode={mode_str})...")
    labels_np = None

    for pass_idx in range(n_passes):
        torch.manual_seed(pass_idx)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(pass_idx)
        np.random.seed(pass_idx)

        pass_probs = []
        pass_labels = []
        with torch.no_grad():
            for batch in test_loader:
                batch = batch.to(device_obj)
                logits_fwd, labels = model(batch)
                if symmetric:
                    batch_rev = batch.clone()
                    edge_index_orig = batch_rev["drug", "synergy_pair", "drug"].edge_label_index
                    batch_rev["drug", "synergy_pair", "drug"].edge_label_index = edge_index_orig[[1, 0]]
                    logits_rev, _ = model(batch_rev)
                    p_fwd = F.softmax(logits_fwd, dim=-1)
                    p_rev = F.softmax(logits_rev, dim=-1)
                    p_sym = (p_fwd + p_rev) / 2.0
                    pass_probs.append(p_sym.detach().cpu())
                else:
                    pass_probs.append(F.softmax(logits_fwd, dim=-1).detach().cpu())
                if labels.shape[0] > 0:
                    pass_labels.append(labels.detach().cpu())

        pass_probs = torch.cat(pass_probs, dim=0)
        pass_labels = torch.cat(pass_labels, dim=0)
        p_probs = pass_probs.numpy()
        if labels_np is None:
            labels_np = pass_labels.numpy()

        pass_probs_list.append(p_probs)

        for sub_name, mask in subsets.items():
            sub_y = labels_np[mask]
            sub_p = p_probs[mask]
            sub_auroc, sub_aupr = compute_macro_metrics(sub_y, sub_p)
            sub_syn_auc, sub_syn_aupr, sub_lift = compute_binary_synergy_metrics(sub_y, sub_p)
            pass_metrics_by_subset[sub_name].append({
                "macro_auroc": sub_auroc,
                "macro_aupr": sub_aupr,
                "syn_auroc": sub_syn_auc,
                "syn_aupr": sub_syn_aupr,
                "lift": sub_lift,
            })

    # Average probabilities across passes
    avg_probs = np.mean(pass_probs_list, axis=0)

    # Compute mean and SD across passes
    print("\n" + "=" * 115)
    print(f"EVALUATION RESULTS — Mode: {mode_str}")
    print("=" * 115)
    print(f"{'Split / Subset':<35} | {'Pairs':>8} | {'Macro AUROC (SD)':<18} | {'Macro AUPR (SD)':<16} | {'Syn AUROC (SD)':<16} | {'Syn AUPR (SD)':<15} | {'Lift':<6}")
    print("=" * 115)

    if eval_val and "Validation Split" in results:
        v_res = results["Validation Split"]
        print(f"{'Validation Split (seed 42)':<35} | {v_res['n_pairs']:>8,} | {v_res['auroc']:>7.4f}            | {v_res['aupr']:>7.4f}          | {v_res['syn_auroc']:>7.4f}          | {v_res['syn_aupr']:>7.4f}         | {v_res['lift']:>6.2f}")
        print("-" * 115)

    for sub_name, p_metrics in pass_metrics_by_subset.items():
        n_pairs = int(subsets[sub_name].sum())
        macro_aurocs = [m["macro_auroc"] for m in p_metrics]
        macro_auprs = [m["macro_aupr"] for m in p_metrics]
        syn_aurocs = [m["syn_auroc"] for m in p_metrics]
        syn_auprs = [m["syn_aupr"] for m in p_metrics]
        lifts = [m["lift"] for m in p_metrics]

        m_auroc, sd_auroc = np.mean(macro_aurocs), np.std(macro_aurocs)
        m_aupr, sd_aupr = np.mean(macro_auprs), np.std(macro_auprs)
        m_syn_auc, sd_syn_auc = np.mean(syn_aurocs), np.std(syn_aurocs)
        m_syn_aupr, sd_syn_aupr = np.mean(syn_auprs), np.std(syn_auprs)
        m_lift = np.mean(lifts)

        results[sub_name] = {
            "n_pairs": n_pairs,
            "auroc": m_auroc,
            "auroc_sd": sd_auroc,
            "aupr": m_aupr,
            "aupr_sd": sd_aupr,
            "syn_auroc": m_syn_auc,
            "syn_auroc_sd": sd_syn_auc,
            "syn_aupr": m_syn_aupr,
            "syn_aupr_sd": sd_syn_aupr,
            "lift": m_lift,
        }

        print(f"{sub_name:<35} | {n_pairs:>8,} | {m_auroc:>7.4f} (+/-{sd_auroc:.4f}) | {m_aupr:>7.4f} (+/-{sd_aupr:.4f}) | {m_syn_auc:>7.4f} (+/-{sd_syn_auc:.4f}) | {m_syn_aupr:>7.4f} (+/-{sd_syn_aupr:.4f})| {m_lift:>6.2f}")

    print("=" * 115)
    if return_details:
        return results, avg_probs, labels_np, mask_bilateral, mask_unilateral, test_pairs
    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Evaluate cold-drug split and subsets")
    parser.add_argument("--ckpt", type=str, default=None, help="Path to checkpoint file")
    parser.add_argument("--no-val", action="store_true", help="Skip validation set evaluation")
    parser.add_argument("--symmetric", action="store_true", help="Enable symmetric inference wrapper (averaging forward and reverse orderings)")
    parser.add_argument("--compare", action="store_true", help="Run both baseline fixed-order and symmetric inference side-by-side")
    args = parser.parse_args()

    default_ckpt = os.path.join(MODELS_DIR, "synergy_gnn_runA.ckpt")
    if args.ckpt is None:
        if os.path.exists(default_ckpt):
            ckpt = default_ckpt
        else:
            ckpt = os.path.join(MODELS_DIR, "synergy_gnn_final.ckpt")
    else:
        ckpt = args.ckpt

    if args.compare:
        print("\n" + "=" * 90)
        print(">>> 1/2: EVALUATING BASELINE (SINGLE FIXED-ORDER INFERENCE)...")
        print("=" * 90)
        base_res = evaluate_cold_split_subsets(ckpt_path=ckpt, eval_val=not args.no_val, symmetric=False)

        print("\n" + "=" * 90)
        print(">>> 2/2: EVALUATING POST-FIX (SYMMETRIC S2-AVERAGED INFERENCE)...")
        print("=" * 90)
        sym_res = evaluate_cold_split_subsets(ckpt_path=ckpt, eval_val=not args.no_val, symmetric=True)

        print("\n" + "=" * 110)
        print("SIDE-BY-SIDE COMPARISON: BASELINE (FIXED-ORDER) vs. POST-FIX (SYMMETRIC INFERENCE)")
        print("=" * 110)
        print(f"{'Split / Subset':<35} | {'Metric':<14} | {'Baseline (Fixed-Order)':<24} | {'Symmetric (Post-Fix)':<22} | {'Delta':<8}")
        print("-" * 110)
        for sub_name in ["Full cold-drug test (headline)", "Bilateral cold-drug (neither in train)", "Unilateral cold-drug (exactly one in train)"]:
            b = base_res[sub_name]
            s = sym_res[sub_name]
            d_auroc = s["auroc"] - b["auroc"]
            d_aupr = s["aupr"] - b["aupr"]
            d_syn_auc = s["syn_auroc"] - b["syn_auroc"]
            d_syn_aupr = s["syn_aupr"] - b["syn_aupr"]
            print(f"{sub_name:<35} | Macro AUROC    | {b['auroc']:>7.4f} (+/-{b['auroc_sd']:.4f})       | {s['auroc']:>7.4f} (+/-{s['auroc_sd']:.4f})      | {d_auroc:>+7.4f}")
            print(f"{'':<35} | Macro AUPR     | {b['aupr']:>7.4f} (+/-{b['aupr_sd']:.4f})       | {s['aupr']:>7.4f} (+/-{s['aupr_sd']:.4f})      | {d_aupr:>+7.4f}")
            print(f"{'':<35} | Syn AUROC      | {b['syn_auroc']:>7.4f} (+/-{b['syn_auroc_sd']:.4f})       | {s['syn_auroc']:>7.4f} (+/-{s['syn_auroc_sd']:.4f})      | {d_syn_auc:>+7.4f}")
            print(f"{'':<35} | Syn AUPR       | {b['syn_aupr']:>7.4f} (+/-{b['syn_aupr_sd']:.4f})       | {s['syn_aupr']:>7.4f} (+/-{s['syn_aupr_sd']:.4f})      | {d_syn_aupr:>+7.4f}")
            print("-" * 110)
        print("=" * 110)
    else:
        evaluate_cold_split_subsets(ckpt_path=ckpt, eval_val=not args.no_val, symmetric=args.symmetric)
