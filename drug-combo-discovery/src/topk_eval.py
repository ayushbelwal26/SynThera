"""
src/topk_eval.py — Formal Top-K Ranking & Early-Retrieval Evaluation Suite
==========================================================================

Evaluates the top-K ranking performance and early retrieval quality of SynThera's
GNN synergy predictions on the held-out bilateral cold-drug test split.

Metrics Evaluated:
1. Precision@K for K in {3, 5, 10}: Fraction of top-K recommended pairs that are truly synergistic.
2. Recall@K for K in {3, 5, 10}: Fraction of all synergistic pairs in a cell line captured in top-K.
3. NDCG@K for K in {3, 5, 10}: Normalized Discounted Cumulative Gain at rank K.
4. pAUC at FPR <= 0.10: Partial Area Under the ROC Curve focusing on the low false-alarm region.
5. Macro AUROC and AUPR: Global discrimination benchmarks for comparative reference.

Ranking Objectives Compared:
- p_synergy: Pure model synergy probability output (unpenalized).
- V(pair): Multi-objective clinical utility score discounting toxicity and target redundancy.
"""

from __future__ import annotations

import os
import sys
import json
import time
import argparse
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, roc_curve, average_precision_score, auc
import torch
import torch.nn.functional as F

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from train import (
    HETERODATA_PATH,
    LABELS_PATH,
    SPLIT_TRAIN_PATH,
    SPLIT_TEST_PATH,
    MODELS_DIR,
    build_loaders,
    compute_class_weights,
)
from model import SynergyModule
from ranking import compute_pair_score_v

CHECKPOINT_PATH = os.path.join(MODELS_DIR, "synergy_gnn_final.ckpt")
DEFAULT_OUTPUT_JSON = os.path.join(ROOT_DIR, "data", "processed", "topk_benchmark.json")


def compute_group_topk(
    group_df: pd.DataFrame,
    score_col: str,
    k_list: List[int] = [3, 5, 10],
) -> Dict[str, Any]:
    """
    Computes Precision@K, Recall@K, and NDCG@K for a single cell-line ranking context.
    """
    sorted_df = group_df.sort_values(by=score_col, ascending=False).reset_index(drop=True)
    y_rel = (sorted_df["synergy_class"] == "synergy").astype(int).values
    R = int(y_rel.sum())

    metrics: Dict[str, Any] = {
        "n_candidates": len(group_df),
        "n_relevant": R,
    }

    for k in k_list:
        y_k = y_rel[:k]
        prec_k = float(y_k.mean()) if k > 0 else 0.0
        rec_k = float(y_k.sum() / R) if R > 0 else float("nan")

        # DCG@K
        discounts = np.log2(np.arange(2, len(y_k) + 2))
        dcg_k = float((y_k / discounts).sum())

        # IDCG@K
        n_ideal = min(k, R)
        if n_ideal > 0:
            idcg_k = float((1.0 / np.log2(np.arange(2, n_ideal + 2))).sum())
            ndcg_k = float(dcg_k / idcg_k)
        else:
            ndcg_k = 0.0 if R > 0 else float("nan")

        metrics[f"precision@{k}"] = prec_k
        metrics[f"recall@{k}"] = rec_k
        metrics[f"ndcg@{k}"] = ndcg_k

    return metrics


def compute_pauc(
    y_true: np.ndarray,
    scores: np.ndarray,
    max_fpr: float = 0.10,
) -> Tuple[float, float, float]:
    """
    Computes Partial AUROC for false positive rate <= max_fpr.

    Returns:
        raw_pauc: Area under curve in [0, max_fpr] (random = max_fpr^2 / 2 = 0.005)
        norm_pauc: raw_pauc / max_fpr (scale 0.0 to 1.0, random = max_fpr / 2 = 0.05)
        mcclish_pauc: McClish standardized pAUC (scale 0.0 to 1.0, random = 0.50, perfect = 1.0)
    """
    fpr, tpr, _ = roc_curve(y_true, scores)
    idx = np.where(fpr <= max_fpr)[0]
    if len(idx) == 0:
        return 0.0, 0.0, 0.5

    fpr_sub = np.concatenate([fpr[idx], [max_fpr]])
    tpr_max = np.interp(max_fpr, fpr, tpr)
    tpr_sub = np.concatenate([tpr[idx], [tpr_max]])

    raw_pauc = float(auc(fpr_sub, tpr_sub))
    norm_pauc = float(raw_pauc / max_fpr)
    try:
        mcclish_pauc = float(roc_auc_score(y_true, scores, max_fpr=max_fpr))
    except Exception:
        mcclish_pauc = float("nan")

    return raw_pauc, norm_pauc, mcclish_pauc


def run_topk_evaluation(
    k_list: List[int] = [3, 5, 10],
    max_fpr: float = 0.10,
    device: str | None = None,
    save_json: bool = True,
    output_path: str = DEFAULT_OUTPUT_JSON,
    seed: int = 42,
) -> Dict[str, Any]:
    """
    Executes the full Top-K and early-retrieval ranking benchmark across bilateral cold-drug pairs.
    """
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    print("=" * 105)
    print("  SynThera Top-K Ranking & Early-Retrieval Evaluation Suite")
    print("=" * 105)

    print(f"\n[1/4] Loading HeteroData and Model Checkpoint onto {device}...")
    t0 = time.time()
    heterodata = torch.load(HETERODATA_PATH, weights_only=False)
    _, _, test_loader = build_loaders(heterodata, [], [], [])

    metadata = heterodata.metadata()
    num_nodes_dict = {nt: heterodata[nt].num_nodes for nt in heterodata.node_types}
    n_fallback = int((~heterodata["drug"].fp_mask).sum().item())
    class_weights = compute_class_weights(heterodata)

    model = SynergyModule.load_from_checkpoint(
        CHECKPOINT_PATH,
        metadata=metadata,
        num_nodes_dict=num_nodes_dict,
        num_fallback_drugs=n_fallback,
        num_cell_lines=heterodata.num_cell_lines,
        num_layers=2,
        class_weights=class_weights,
    )
    model.to(device)
    model.eval()
    print(f"      Model ready in {time.time() - t0:.2f}s.")

    print("\n[2/4] Running Symmetric GNN Inference across Held-Out Test Set...")
    t_inf = time.time()
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    np.random.seed(seed)

    pass_probs = []
    with torch.no_grad():
        for batch in test_loader:
            batch = batch.to(device)
            logits_fwd, _ = model(batch)
            batch_rev = batch.clone()
            orig_edge_idx = batch_rev["drug", "synergy_pair", "drug"].edge_label_index
            batch_rev["drug", "synergy_pair", "drug"].edge_label_index = orig_edge_idx[[1, 0]]
            logits_rev, _ = model(batch_rev)
            p_fwd = F.softmax(logits_fwd, dim=-1)
            p_rev = F.softmax(logits_rev, dim=-1)
            pass_probs.append(((p_fwd + p_rev) / 2.0).detach().cpu())

    all_probs = torch.cat(pass_probs, dim=0).numpy()
    print(f"      Inference completed across {len(all_probs):,} pairs in {time.time() - t_inf:.2f}s.")

    print("\n[3/4] Filtering Bilateral Cold-Drug Subset and Computing Multi-Objective V(pair)...")
    labels_df = pd.read_csv(LABELS_PATH)
    train_idx = pd.read_csv(SPLIT_TRAIN_PATH)["row_index"].values
    test_idx = pd.read_csv(SPLIT_TEST_PATH)["row_index"].values

    train_pairs = labels_df.iloc[train_idx]
    train_drugs = set(train_pairs["drug_a_kg_id"]) | set(train_pairs["drug_b_kg_id"])

    test_pairs = labels_df.iloc[test_idx].reset_index(drop=True)
    a_in_train = test_pairs["drug_a_kg_id"].isin(train_drugs).values
    b_in_train = test_pairs["drug_b_kg_id"].isin(train_drugs).values
    mask_bilateral = (~a_in_train) & (~b_in_train)

    bilateral_df = test_pairs[mask_bilateral].copy().reset_index(drop=True)
    bilateral_probs = all_probs[mask_bilateral]

    bilateral_df["p_antagonism"] = bilateral_probs[:, 0]
    bilateral_df["p_additive"] = bilateral_probs[:, 1]
    bilateral_df["p_synergy"] = bilateral_probs[:, 2]

    # Compute multi-objective V(pair)
    v_scores = []
    for _, r in bilateral_df.iterrows():
        v_res = compute_pair_score_v(
            drug_a_id=str(r["drug_a_kg_id"]),
            drug_b_id=str(r["drug_b_kg_id"]),
            p_synergy=float(r["p_synergy"]),
        )
        v_scores.append(v_res["v_score"])
    bilateral_df["v_pair"] = v_scores

    total_pairs = len(bilateral_df)
    n_synergy = int((bilateral_df["synergy_class"] == "synergy").sum())
    synergy_prev = float(n_synergy / total_pairs)
    print(f"      Total bilateral cold-drug pairs evaluated: {total_pairs:,}")
    print(f"      Ground-truth synergistic pairs: {n_synergy:,} ({synergy_prev*100:.2f}% base prevalence)")

    # Overall Global Metrics
    y_true_binary = (bilateral_df["synergy_class"] == "synergy").astype(int).values
    macro_auroc = float(roc_auc_score(
        bilateral_df["synergy_class"].map({"antagonism": 0, "additive": 1, "synergy": 2}),
        bilateral_probs,
        multi_class="ovr",
        average="macro",
    ))
    macro_aupr_list = [
        average_precision_score((bilateral_df["synergy_class"] == c).astype(int), bilateral_probs[:, i])
        for i, c in enumerate(["antagonism", "additive", "synergy"])
    ]
    macro_aupr = float(np.mean(macro_aupr_list))
    binary_syn_auroc = float(roc_auc_score(y_true_binary, bilateral_df["p_synergy"]))
    binary_syn_aupr = float(average_precision_score(y_true_binary, bilateral_df["p_synergy"]))

    # pAUC
    raw_pauc_syn, norm_pauc_syn, mcclish_syn = compute_pauc(y_true_binary, bilateral_df["p_synergy"], max_fpr=max_fpr)
    raw_pauc_v, norm_pauc_v, mcclish_v = compute_pauc(y_true_binary, bilateral_df["v_pair"], max_fpr=max_fpr)

    print("\n[4/4] Computing Per-Cell-Line Contextual Top-K Ranking Metrics...")
    topk_summary: Dict[str, Dict[str, Any]] = {}

    for score_name, col in [("p_synergy", "p_synergy"), ("v_pair", "v_pair")]:
        cl_metrics = []
        for cl, group in bilateral_df.groupby("cell_line_name"):
            m = compute_group_topk(group, col, k_list=k_list)
            m["cell_line"] = cl
            cl_metrics.append(m)
        m_df = pd.DataFrame(cl_metrics)
        valid_rec = m_df[m_df["n_relevant"] >= 1]

        res_dict: Dict[str, Any] = {
            "n_cell_lines_total": len(m_df),
            "n_cell_lines_with_synergy": len(valid_rec),
        }
        for k in k_list:
            mean_p = float(m_df[f"precision@{k}"].mean())
            mean_r = float(valid_rec[f"recall@{k}"].mean())
            mean_ndcg = float(valid_rec[f"ndcg@{k}"].mean())
            res_dict[f"precision@{k}"] = mean_p
            res_dict[f"recall@{k}"] = mean_r
            res_dict[f"ndcg@{k}"] = mean_ndcg
            res_dict[f"precision_lift@{k}"] = float(mean_p / (synergy_prev + 1e-12))

        topk_summary[score_name] = res_dict

    results_payload = {
        "evaluation_split": "Bilateral Cold-Drug Held-Out Test Set (neither drug in train)",
        "n_bilateral_pairs": total_pairs,
        "n_synergy_pairs": n_synergy,
        "base_synergy_prevalence": synergy_prev,
        "reference_global_metrics": {
            "macro_auroc_ovr": macro_auroc,
            "macro_aupr": macro_aupr,
            "binary_synergy_auroc": binary_syn_auroc,
            "binary_synergy_aupr": binary_syn_aupr,
        },
        "early_retrieval_pauc": {
            "max_fpr": max_fpr,
            "random_baseline_raw": float(max_fpr ** 2 / 2.0),
            "p_synergy": {
                "raw_pauc": raw_pauc_syn,
                "norm_pauc": norm_pauc_syn,
                "mcclish_standardized_pauc": mcclish_syn,
            },
            "v_pair": {
                "raw_pauc": raw_pauc_v,
                "norm_pauc": norm_pauc_v,
                "mcclish_standardized_pauc": mcclish_v,
            },
        },
        "topk_ranking": topk_summary,
    }

    # Print Formatted Comprehensive Benchmark Table
    print("\n" + "=" * 105)
    print("SYNTHERA FORMAL RANKING BENCHMARK (OVERALL DISCRIMINATION vs. TOP-K EARLY RETRIEVAL)")
    print("=" * 105)
    print(f"Evaluation Context: Bilateral Cold-Drug Test Pairs (N = {total_pairs:,} across {topk_summary['p_synergy']['n_cell_lines_total']} cell lines)")
    print(f"Base Synergy Prevalence: {synergy_prev*100:.2f}% (Random Precision@K Baseline)")
    print("-" * 105)
    print(f"{'Evaluation Metric':<36} | {'p_synergy (Model Only)':<24} | {'V(pair) (Tox-Adjusted)':<24} | {'Baseline / Reference':<14}")
    print("-" * 105)
    print(f"{'Macro AUROC (OVR, 3-class)':<36} | {macro_auroc:>7.4f}                  | N/A                      | 0.5000 (Random)")
    print(f"{'Macro AUPR (3-class mean)':<36} | {macro_aupr:>7.4f}                  | N/A                      | 0.3333 (Random)")
    print(f"{'Binary Synergy AUROC':<36} | {binary_syn_auroc:>7.4f}                  | N/A                      | 0.5000 (Random)")
    print(f"{'Binary Synergy AUPR':<36} | {binary_syn_aupr:>7.4f}                  | N/A                      | {synergy_prev:>6.4f} (Prevalence)")
    print("-" * 105)
    print(f"{'pAUC (FPR <= 0.10, Raw Area)':<36} | {raw_pauc_syn:>7.4f}                  | {raw_pauc_v:>7.4f}                  | 0.0050 (Random)")
    print(f"{'pAUC (FPR <= 0.10, McClish Std)':<36} | {mcclish_syn:>7.4f}                  | {mcclish_v:>7.4f}                  | 0.5000 (Random)")
    print("-" * 105)
    for k in k_list:
        p_syn = topk_summary["p_synergy"][f"precision@{k}"]
        p_v = topk_summary["v_pair"][f"precision@{k}"]
        lift_syn = topk_summary["p_synergy"][f"precision_lift@{k}"]
        print(f"{f'Precision@{k} (Mean across cell lines)':<36} | {p_syn:>6.2%} ({lift_syn:>4.2f}x lift)       | {p_v:>6.2%}                  | {synergy_prev:>6.2%} (Prevalence)")
    print("-" * 105)
    for k in k_list:
        r_syn = topk_summary["p_synergy"][f"recall@{k}"]
        r_v = topk_summary["v_pair"][f"recall@{k}"]
        print(f"{f'Recall@{k} (Mean across cell lines)':<36} | {r_syn:>6.2%}                  | {r_v:>6.2%}                  | N/A")
    print("-" * 105)
    for k in k_list:
        n_syn = topk_summary["p_synergy"][f"ndcg@{k}"]
        n_v = topk_summary["v_pair"][f"ndcg@{k}"]
        print(f"{f'NDCG@{k} (Mean across cell lines)':<36} | {n_syn:>7.4f}                  | {n_v:>7.4f}                  | N/A")
    print("=" * 105)

    if save_json:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results_payload, f, indent=2)
        print(f"\n[Saved] Top-K ranking benchmark results saved to: {output_path}")

    return results_payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SynThera Top-K Ranking Evaluation Suite")
    parser.add_argument("--k-values", nargs="+", type=int, default=[3, 5, 10], help="K values for ranking metrics (default: 3 5 10)")
    parser.add_argument("--max-fpr", type=float, default=0.10, help="Maximum FPR threshold for pAUC (default: 0.10)")
    parser.add_argument("--device", type=str, default=None, help="Device to run inference (default: cuda if available)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for evaluation (default: 42)")
    parser.add_argument("--output", type=str, default=DEFAULT_OUTPUT_JSON, help="Output JSON path")
    args = parser.parse_args()

    run_topk_evaluation(
        k_list=args.k_values,
        max_fpr=args.max_fpr,
        device=args.device,
        save_json=True,
        output_path=args.output,
        seed=args.seed,
    )
