"""
src/baselines/eval_baseline.py
==============================
Evaluation suite for DeepSynergy-style MLP baseline and direct side-by-side
comparison against SynThera HGT.
Phase B2 / Group 2 Item 4.

Computes the EXACT same metrics as topk_eval.py:
  - Macro AUROC (OVR, 3-class)
  - Macro AUPR (3-class mean)
  - Binary Synergy AUROC
  - Binary Synergy AUPR
  - pAUC (FPR <= 0.10, raw and McClish standardized)
  - Precision@K, Recall@K, NDCG@K for K in {3, 5, 10}
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
import torch
from torch.utils.data import DataLoader
from sklearn.metrics import roc_auc_score, average_precision_score, roc_curve, auc

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC_DIR = os.path.join(ROOT_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from baselines.mlp_baseline import DeepSynergyMLP
from baselines.train_baseline import (
    load_data_and_features,
    get_split_indices,
    PairDataset,
    BASELINES_DIR,
    PROCESSED_DIR,
    SPLITS_EXTRA_DIR,
    CLASS_MAP,
)
from topk_eval import compute_group_topk, compute_pauc

HGT_WARM_BENCHMARK_PATH = os.path.join(PROCESSED_DIR, "warm_random_gnn_benchmark.json")
HGT_COLD_BENCHMARK_PATH = os.path.join(PROCESSED_DIR, "topk_benchmark.json")
OUTPUT_COMPARISON_JSON = os.path.join(BASELINES_DIR, "comparison_benchmark.json")


def evaluate_mlp_predictions(
    model: DeepSynergyMLP,
    pairs_df: pd.DataFrame,
    drug_fps: torch.Tensor,
    drug_map: Dict[str, int],
    cell_map: Dict[str, int],
    device: torch.device,
    batch_size: int = 512,
    k_list: List[int] = [3, 5, 10],
    max_fpr: float = 0.10,
) -> Dict[str, Any]:
    """
    Runs symmetric evaluation of DeepSynergyMLP on a test pair DataFrame,
    computing all global and ranking metrics.
    """
    model.eval()
    dataset = PairDataset(pairs_df, drug_fps, drug_map, cell_map)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=False)

    pass_probs = []
    with torch.no_grad():
        for fp_a, fp_b, cell_idx, _ in loader:
            fp_a = fp_a.to(device, non_blocking=True)
            fp_b = fp_b.to(device, non_blocking=True)
            cell_idx = cell_idx.to(device, non_blocking=True)

            probs_sym, _ = model.forward_symmetric(fp_a, fp_b, cell_idx)
            pass_probs.append(probs_sym.cpu())

    all_probs = torch.cat(pass_probs, dim=0).numpy()
    eval_df = pairs_df.copy().reset_index(drop=True)
    eval_df["p_antagonism"] = all_probs[:, 0]
    eval_df["p_additive"] = all_probs[:, 1]
    eval_df["p_synergy"] = all_probs[:, 2]

    y_true_binary = (eval_df["synergy_class"] == "synergy").astype(int).values
    synergy_prev = float(y_true_binary.mean())

    # 1. Global discrimination metrics
    y_true_multi = eval_df["synergy_class"].map(CLASS_MAP).values
    macro_auroc = float(roc_auc_score(y_true_multi, all_probs, multi_class="ovr", average="macro"))
    macro_aupr_list = [
        average_precision_score((y_true_multi == i).astype(int), all_probs[:, i])
        for i in range(3)
    ]
    macro_aupr = float(np.mean(macro_aupr_list))
    binary_syn_auroc = float(roc_auc_score(y_true_binary, eval_df["p_synergy"]))
    binary_syn_aupr = float(average_precision_score(y_true_binary, eval_df["p_synergy"]))

    # 2. pAUC
    raw_pauc, norm_pauc, mcclish = compute_pauc(y_true_binary, eval_df["p_synergy"], max_fpr=max_fpr)

    # 3. Contextual top-K ranking per cell line
    cl_metrics = []
    for cl, grp in eval_df.groupby("cell_line_name"):
        m = compute_group_topk(grp, "p_synergy", k_list=k_list)
        m["cell_line"] = cl
        cl_metrics.append(m)
    m_df = pd.DataFrame(cl_metrics)
    valid_rec = m_df[m_df["n_relevant"] >= 1]

    topk_res = {}
    for k in k_list:
        mean_p = float(m_df[f"precision@{k}"].mean())
        mean_r = float(valid_rec[f"recall@{k}"].mean())
        mean_ndcg = float(valid_rec[f"ndcg@{k}"].mean())
        topk_res[f"precision@{k}"] = mean_p
        topk_res[f"recall@{k}"] = mean_r
        topk_res[f"ndcg@{k}"] = mean_ndcg
        topk_res[f"precision_lift@{k}"] = float(mean_p / (synergy_prev + 1e-12))

    return {
        "n_pairs": len(eval_df),
        "n_synergy": int(y_true_binary.sum()),
        "base_prevalence": synergy_prev,
        "macro_auroc": macro_auroc,
        "macro_aupr": macro_aupr,
        "binary_synergy_auroc": binary_syn_auroc,
        "binary_synergy_aupr": binary_syn_aupr,
        "raw_pauc": raw_pauc,
        "norm_pauc": norm_pauc,
        "mcclish_pauc": mcclish,
        **topk_res,
    }


def load_hgt_benchmarks() -> Tuple[Dict[str, Any], Dict[str, Any]]:
    # 1. Warm random HGT benchmark
    if not os.path.exists(HGT_WARM_BENCHMARK_PATH):
        raise FileNotFoundError(f"Missing {HGT_WARM_BENCHMARK_PATH}. Run scratch/eval_warm_gnn.py first.")
    with open(HGT_WARM_BENCHMARK_PATH, "r") as f:
        warm_hgt = json.load(f)

    # 2. Bilateral cold HGT benchmark
    if not os.path.exists(HGT_COLD_BENCHMARK_PATH):
        raise FileNotFoundError(f"Missing {HGT_COLD_BENCHMARK_PATH}. Run src/topk_eval.py first.")
    with open(HGT_COLD_BENCHMARK_PATH, "r") as f:
        cold_hgt_raw = json.load(f)

    cold_hgt = {
        "macro_auroc": cold_hgt_raw["reference_global_metrics"]["macro_auroc_ovr"],
        "macro_aupr": cold_hgt_raw["reference_global_metrics"]["macro_aupr"],
        "binary_synergy_auroc": cold_hgt_raw["reference_global_metrics"]["binary_synergy_auroc"],
        "binary_synergy_aupr": cold_hgt_raw["reference_global_metrics"]["binary_synergy_aupr"],
        "raw_pauc": cold_hgt_raw["early_retrieval_pauc"]["p_synergy"]["raw_pauc"],
        "mcclish_pauc": cold_hgt_raw["early_retrieval_pauc"]["p_synergy"]["mcclish_standardized_pauc"],
        "precision@3": cold_hgt_raw["topk_ranking"]["p_synergy"]["precision@3"],
        "precision@5": cold_hgt_raw["topk_ranking"]["p_synergy"]["precision@5"],
        "precision@10": cold_hgt_raw["topk_ranking"]["p_synergy"]["precision@10"],
        "recall@3": cold_hgt_raw["topk_ranking"]["p_synergy"]["recall@3"],
        "recall@5": cold_hgt_raw["topk_ranking"]["p_synergy"]["recall@5"],
        "recall@10": cold_hgt_raw["topk_ranking"]["p_synergy"]["recall@10"],
        "ndcg@3": cold_hgt_raw["topk_ranking"]["p_synergy"]["ndcg@3"],
        "ndcg@5": cold_hgt_raw["topk_ranking"]["p_synergy"]["ndcg@5"],
        "ndcg@10": cold_hgt_raw["topk_ranking"]["p_synergy"]["ndcg@10"],
    }
    return warm_hgt, cold_hgt


def run_full_evaluation():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Loading shared resources on {device}...")
    drug_fps, drug_map, cell_map, labels_df = load_data_and_features()

    warm_hgt, cold_hgt = load_hgt_benchmarks()

    # Load and evaluate Warm Random MLP Baseline
    print("\n[1/2] Evaluating DeepSynergy MLP Baseline on Warm Random Test Split...")
    warm_ckpt_path = os.path.join(BASELINES_DIR, "mlp_warm_random.pt")
    if not os.path.exists(warm_ckpt_path):
        raise FileNotFoundError(f"Missing checkpoint: {warm_ckpt_path}. Run train_baseline.py first.")

    warm_state = torch.load(warm_ckpt_path, map_location=device)
    model_warm = DeepSynergyMLP(
        fp_dim=2048,
        num_cell_lines=len(cell_map),
        cell_dim=64,
        hidden_dims=[512, 256, 128],
        dropout=0.2,
        num_classes=3,
    ).to(device)
    model_warm.load_state_dict(warm_state["model_state_dict"])

    test_warm_idx = pd.read_csv(os.path.join(SPLITS_EXTRA_DIR, "warm_random_test.csv"))["row_index"].tolist()
    test_warm_df = labels_df.iloc[test_warm_idx].reset_index(drop=True)
    warm_mlp_results = evaluate_mlp_predictions(
        model_warm, test_warm_df, drug_fps, drug_map, cell_map, device
    )

    # Load and evaluate Bilateral Cold MLP Baseline
    print("\n[2/2] Evaluating DeepSynergy MLP Baseline on Bilateral Cold-Drug Test Set...")
    cold_ckpt_path = os.path.join(BASELINES_DIR, "mlp_cold.pt")
    if not os.path.exists(cold_ckpt_path):
        raise FileNotFoundError(f"Missing checkpoint: {cold_ckpt_path}. Run train_baseline.py first.")

    cold_state = torch.load(cold_ckpt_path, map_location=device)
    model_cold = DeepSynergyMLP(
        fp_dim=2048,
        num_cell_lines=len(cell_map),
        cell_dim=64,
        hidden_dims=[512, 256, 128],
        dropout=0.2,
        num_classes=3,
    ).to(device)
    model_cold.load_state_dict(cold_state["model_state_dict"])

    train_cold_idx = pd.read_csv(os.path.join(PROCESSED_DIR, "split_train.csv"))["row_index"].tolist()
    train_cold_df = labels_df.iloc[train_cold_idx]
    train_drugs = set(train_cold_df["drug_a_kg_id"]) | set(train_cold_df["drug_b_kg_id"])

    test_cold_idx = pd.read_csv(os.path.join(PROCESSED_DIR, "split_test.csv"))["row_index"].tolist()
    test_cold_df = labels_df.iloc[test_cold_idx].reset_index(drop=True)

    a_in_train = test_cold_df["drug_a_kg_id"].isin(train_drugs).values
    b_in_train = test_cold_df["drug_b_kg_id"].isin(train_drugs).values
    bilateral_mask = (~a_in_train) & (~b_in_train)
    bilateral_cold_df = test_cold_df[bilateral_mask].reset_index(drop=True)

    cold_mlp_results = evaluate_mlp_predictions(
        model_cold, bilateral_cold_df, drug_fps, drug_map, cell_map, device
    )

    # Compile Side-by-Side Comparison
    payload = {
        "warm_random": {
            "synthera_hgt": warm_hgt,
            "deep_synergy_mlp": warm_mlp_results,
        },
        "bilateral_cold": {
            "synthera_hgt": cold_hgt,
            "deep_synergy_mlp": cold_mlp_results,
        },
    }
    with open(OUTPUT_COMPARISON_JSON, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"\n[Saved] Full comparison payload saved to: {OUTPUT_COMPARISON_JSON}")

    # Print Formatted Comparison Table
    print("\n" + "=" * 115)
    print("SIDE-BY-SIDE BENCHMARK: SYNTHERA HGT (KNOWLEDGE GRAPH) vs. DEEPSYNERGY MLP (FEEDFORWARD BASELINE)")
    print("=" * 115)
    print(f"{'Evaluation Metric':<32} | {'Warm Random: HGT':<18} | {'Warm: DeepSynergy':<18} | {'Cold: HGT':<18} | {'Cold: DeepSynergy':<18}")
    print("-" * 115)

    def _fmt(val: float, is_pct: bool = False, digits: int = 4) -> str:
        if is_pct:
            return f"{val*100:6.2f}%"
        return f"{val:6.{digits}f}"

    metrics_list = [
        ("Macro AUROC (OVR)", "macro_auroc", False),
        ("Macro AUPR (3-class mean)", "macro_aupr", False),
        ("Binary Synergy AUROC", "binary_synergy_auroc", False),
        ("Binary Synergy AUPR", "binary_synergy_aupr", False),
        ("pAUC (FPR<=0.10, raw)", "raw_pauc", False),
        ("pAUC (FPR<=0.10, McClish)", "mcclish_pauc", False),
        ("Precision@3", "precision@3", True),
        ("Precision@5", "precision@5", True),
        ("Precision@10", "precision@10", True),
        ("Recall@3", "recall@3", True),
        ("Recall@5", "recall@5", True),
        ("Recall@10", "recall@10", True),
        ("NDCG@3", "ndcg@3", False),
        ("NDCG@5", "ndcg@5", False),
        ("NDCG@10", "ndcg@10", False),
    ]

    for label, key, is_pct in metrics_list:
        hgt_w = _fmt(warm_hgt[key], is_pct)
        mlp_w = _fmt(warm_mlp_results[key], is_pct)
        hgt_c = _fmt(cold_hgt[key], is_pct)
        mlp_c = _fmt(cold_mlp_results[key], is_pct)
        print(f"{label:<32} | {hgt_w:<18} | {mlp_w:<18} | {hgt_c:<18} | {mlp_c:<18}")

    print("=" * 115)


if __name__ == "__main__":
    run_full_evaluation()
