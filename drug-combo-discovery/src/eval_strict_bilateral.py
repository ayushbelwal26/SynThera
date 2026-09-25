"""
src/eval_strict_bilateral.py — Strict Bilateral Cold-Drug Evaluation Suite
========================================================================

Evaluates SynThera's GNN synergy predictions on the STRICT bilateral cold-drug
test split, where BOTH Drug A and Drug B are strictly held out from BOTH training
and validation sets.

Drug Allocation (from build_heterodata.py with seed=42):
  - Train drugs: 70%
  - Val drugs:   15%
  - Test drugs:  15%

Strict Bilateral Condition:
  Drug A in test_drugs AND Drug B in test_drugs
  (Equivalently: neither drug in train_drugs nor val_drugs)

Comparative Reference:
  - Existing Bilateral Benchmark: 8,496 pairs (neither drug in train pairs,
    but 69.8% contain at least one drug from the validation split)
  - Strict Bilateral Benchmark: 2,565 pairs (both drugs strictly cold to train & val)

Metrics Evaluated:
  - Number of pairs
  - Number of unique drugs
  - Number of cell lines
  - Synergy prevalence
  - Macro AUROC (OVR, 3-class)
  - Macro AUPR (3-class mean)
  - Binary Synergy AUROC
  - Binary Synergy AUPR
  - Precision@3, NDCG@3
  - Precision@5, NDCG@5
  - Precision@10, NDCG@10
"""

from __future__ import annotations

import os
import sys
import json
import time
import random
import argparse
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, average_precision_score
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
    SPLIT_VAL_PATH,
    SPLIT_TEST_PATH,
    MODELS_DIR,
    build_loaders,
    compute_class_weights,
)
from model import SynergyModule
from topk_eval import compute_group_topk

CHECKPOINT_PATH = os.path.join(MODELS_DIR, "synergy_gnn_final.ckpt")
DEFAULT_OUTPUT_JSON = os.path.join(ROOT_DIR, "data", "processed", "strict_bilateral_benchmark.json")

CLASS_MAP = {"antagonism": 0, "additive": 1, "synergy": 2}


def get_drug_partition(
    labels_df: pd.DataFrame,
    seed: int = 42,
    val_frac: float = 0.15,
    test_frac: float = 0.15,
) -> Tuple[set[str], set[str], set[str]]:
    """
    Reconstructs the exact train/val/test drug allocation from build_heterodata.py.
    """
    rng = random.Random(seed)
    all_drugs = sorted(
        set(labels_df["drug_a_kg_id"].unique()) | set(labels_df["drug_b_kg_id"].unique())
    )
    rng.shuffle(all_drugs)

    n_total = len(all_drugs)
    n_test = max(1, round(n_total * test_frac))
    n_val = max(1, round(n_total * val_frac))

    test_drugs = set(all_drugs[:n_test])
    val_drugs = set(all_drugs[n_test : n_test + n_val])
    train_drugs = set(all_drugs[n_test + n_val :])

    return train_drugs, val_drugs, test_drugs


def evaluate_split_subset(
    subset_df: pd.DataFrame,
    probs: np.ndarray,
    k_list: List[int] = [3, 5, 10],
) -> Dict[str, Any]:
    """
    Computes all global discrimination and per-cell-line top-K ranking metrics
    for a given subset of test pairs.
    """
    n_pairs = len(subset_df)
    unique_drugs = len(set(subset_df["drug_a_kg_id"].unique()) | set(subset_df["drug_b_kg_id"].unique()))
    n_cell_lines = subset_df["cell_line_name"].nunique()

    y_true_binary = (subset_df["synergy_class"] == "synergy").astype(int).values
    n_synergy = int(y_true_binary.sum())
    synergy_prev = float(n_synergy / n_pairs) if n_pairs > 0 else 0.0

    # 1. Global Macro AUROC (OVR, 3-class)
    y_true_multi = subset_df["synergy_class"].map(CLASS_MAP).values
    try:
        macro_auroc = float(
            roc_auc_score(y_true_multi, probs, multi_class="ovr", average="macro")
        )
    except ValueError:
        macro_auroc = float("nan")

    # 2. Global Macro AUPR (unweighted mean across classes)
    macro_aupr_list = []
    for c_idx in range(3):
        bin_y = (y_true_multi == c_idx).astype(int)
        try:
            macro_aupr_list.append(average_precision_score(bin_y, probs[:, c_idx]))
        except ValueError:
            macro_aupr_list.append(float("nan"))
    macro_aupr = float(np.nanmean(macro_aupr_list))

    # 3. Binary Synergy AUROC & AUPR
    p_syn = probs[:, 2]
    try:
        binary_syn_auroc = float(roc_auc_score(y_true_binary, p_syn))
    except ValueError:
        binary_syn_auroc = float("nan")

    try:
        binary_syn_aupr = float(average_precision_score(y_true_binary, p_syn))
    except ValueError:
        binary_syn_aupr = float("nan")

    # 4. Contextual Top-K Ranking per cell line
    eval_df = subset_df.copy().reset_index(drop=True)
    eval_df["p_synergy"] = p_syn

    cl_metrics = []
    for cl, grp in eval_df.groupby("cell_line_name"):
        m = compute_group_topk(grp, "p_synergy", k_list=k_list)
        m["cell_line"] = cl
        cl_metrics.append(m)

    m_df = pd.DataFrame(cl_metrics)
    valid_rec = m_df[m_df["n_relevant"] >= 1]

    topk_res: Dict[str, float] = {
        "n_cell_lines_total": len(m_df),
        "n_cell_lines_with_synergy": len(valid_rec),
    }
    for k in k_list:
        mean_p = float(m_df[f"precision@{k}"].mean()) if len(m_df) > 0 else 0.0
        mean_ndcg = float(valid_rec[f"ndcg@{k}"].mean()) if len(valid_rec) > 0 else float("nan")
        mean_r = float(valid_rec[f"recall@{k}"].mean()) if len(valid_rec) > 0 else float("nan")

        topk_res[f"precision@{k}"] = mean_p
        topk_res[f"ndcg@{k}"] = mean_ndcg
        topk_res[f"recall@{k}"] = mean_r

    return {
        "n_pairs": n_pairs,
        "n_unique_drugs": unique_drugs,
        "n_cell_lines": n_cell_lines,
        "n_synergy": n_synergy,
        "synergy_prevalence": synergy_prev,
        "macro_auroc": macro_auroc,
        "macro_aupr": macro_aupr,
        "binary_synergy_auroc": binary_syn_auroc,
        "binary_synergy_aupr": binary_syn_aupr,
        **topk_res,
    }


def run_strict_bilateral_evaluation(
    checkpoint_path: str = CHECKPOINT_PATH,
    device: str | None = None,
    seed: int = 42,
    output_path: str = DEFAULT_OUTPUT_JSON,
    save_json: bool = True,
) -> Dict[str, Any]:
    """
    Executes symmetric inference across the held-out test split, partitions into
    existing bilateral vs. strict bilateral subsets, and computes side-by-side metrics.
    """
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    print("=" * 105)
    print("  SynThera STRICT BILATERAL COLD-DRUG BENCHMARK")
    print("=" * 105)
    print(f"Checkpoint: {checkpoint_path}")
    print(f"Device:     {device}")
    print(f"Seed:       {seed}")

    # 1. Load Data and Construct Loader
    print("\n[1/4] Loading HeteroData and Building Test Loader...")
    t0 = time.time()
    heterodata = torch.load(HETERODATA_PATH, weights_only=False)
    _, _, test_loader = build_loaders(heterodata, [], [], [])

    metadata = heterodata.metadata()
    num_nodes_dict = {nt: heterodata[nt].num_nodes for nt in heterodata.node_types}
    n_fallback = int((~heterodata["drug"].fp_mask).sum().item())
    class_weights = compute_class_weights(heterodata)

    # 2. Load Checkpoint
    print(f"\n[2/4] Loading SynergyModule Checkpoint onto {device}...")
    model = SynergyModule.load_from_checkpoint(
        checkpoint_path,
        metadata=metadata,
        num_nodes_dict=num_nodes_dict,
        num_fallback_drugs=n_fallback,
        num_cell_lines=heterodata.num_cell_lines,
        num_layers=2,
        class_weights=class_weights,
    )
    if getattr(model.model, "use_expression", False) and not hasattr(model.model, "expression_buffer"):
        expr_path = os.path.join(ROOT_DIR, "data", "processed", "cell_line_expression.pt")
        if os.path.exists(expr_path):
            expr = torch.load(expr_path, weights_only=True, map_location="cpu")
            model.model.register_buffer("expression_buffer", expr)
    model.to(device)
    model.eval()
    print(f"      Model loaded in {time.time() - t0:.2f}s.")
    print(f"      Enriched pair head: {getattr(model.model, 'enriched_pair_head', False)}")
    print(f"      Use expression:     {getattr(model.model, 'use_expression', False)}")
    if getattr(model.model, 'use_expression', False) and hasattr(model.model, 'expression_buffer'):
        print(f"      Expression buffer:  {model.model.expression_buffer.shape}")

    # 3. Symmetric GNN Inference over Test Loader
    print(f"\n[3/4] Running Symmetric GNN Inference across {len(test_loader)} test batches...")
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

    # 4. Load Split Indices and Define Subsets
    print("\n[4/4] Defining Partitions and Verifying Disjointness...")
    labels_df = pd.read_csv(LABELS_PATH)
    train_idx = pd.read_csv(SPLIT_TRAIN_PATH)["row_index"].values
    val_idx = pd.read_csv(SPLIT_VAL_PATH)["row_index"].values
    test_idx = pd.read_csv(SPLIT_TEST_PATH)["row_index"].values

    train_drugs, val_drugs, test_drugs = get_drug_partition(labels_df, seed=42)

    # Verification: verify partitions match split CSVs
    test_df = labels_df.iloc[test_idx].reset_index(drop=True)
    train_pairs_df = labels_df.iloc[train_idx]
    train_pairs_drugs = set(train_pairs_df["drug_a_kg_id"]) | set(train_pairs_df["drug_b_kg_id"])

    # Subset A: Existing Bilateral Cold-Drug (neither drug in train pairs)
    mask_existing = (~test_df["drug_a_kg_id"].isin(train_pairs_drugs)) & (~test_df["drug_b_kg_id"].isin(train_pairs_drugs))
    existing_df = test_df[mask_existing].copy().reset_index(drop=True)
    existing_probs = all_probs[mask_existing]

    # Subset B: Strict Bilateral Cold-Drug (both drugs in test_drugs; neither in train nor val)
    mask_strict = test_df["drug_a_kg_id"].isin(test_drugs) & test_df["drug_b_kg_id"].isin(test_drugs)
    strict_df = test_df[mask_strict].copy().reset_index(drop=True)
    strict_probs = all_probs[mask_strict]

    # Integrity assertions for strict benchmark
    train_or_val_drugs = train_drugs | val_drugs
    leak_a = strict_df["drug_a_kg_id"].isin(train_or_val_drugs).sum()
    leak_b = strict_df["drug_b_kg_id"].isin(train_or_val_drugs).sum()
    assert leak_a == 0, f"Integrity Failure: {leak_a} strict test pairs contain Drug A from train/val!"
    assert leak_b == 0, f"Integrity Failure: {leak_b} strict test pairs contain Drug B from train/val!"
    print(f"      [Integrity Pass] Strict bilateral test set has 0 overlap with train or val drugs.")

    # Calculate metrics for both
    res_existing = evaluate_split_subset(existing_df, existing_probs)
    res_strict = evaluate_split_subset(strict_df, strict_probs)

    # Print Formatted Comparison Table
    print("\n" + "=" * 105)
    print("BILATERAL COLD-DRUG EVALUATION: EXISTING vs. STRICT BENCHMARK")
    print("=" * 105)
    print(f"{'Metric / Characteristic':<32} | {'Existing Bilateral (Train-Cold)':<32} | {'Strict Bilateral (Train & Val Cold)':<32}")
    print("-" * 105)
    print(f"{'Number of Pairs':<32} | {res_existing['n_pairs']:>8,}                         | {res_strict['n_pairs']:>8,}")
    print(f"{'Number of Unique Drugs':<32} | {res_existing['n_unique_drugs']:>8,}                         | {res_strict['n_unique_drugs']:>8,}")
    print(f"{'Number of Cell Lines':<32} | {res_existing['n_cell_lines']:>8,}                         | {res_strict['n_cell_lines']:>8,}")
    print(f"{'Synergy Prevalence':<32} | {res_existing['synergy_prevalence']*100:>7.2f}%                         | {res_strict['synergy_prevalence']*100:>7.2f}%")
    print("-" * 105)
    print(f"{'Macro AUROC (OVR, 3-class)':<32} | {res_existing['macro_auroc']:>8.4f}                         | {res_strict['macro_auroc']:>8.4f}")
    print(f"{'Macro AUPR (3-class mean)':<32} | {res_existing['macro_aupr']:>8.4f}                         | {res_strict['macro_aupr']:>8.4f}")
    print(f"{'Binary Synergy AUROC':<32} | {res_existing['binary_synergy_auroc']:>8.4f}                         | {res_strict['binary_synergy_auroc']:>8.4f}")
    print(f"{'Binary Synergy AUPR':<32} | {res_existing['binary_synergy_aupr']:>8.4f}                         | {res_strict['binary_synergy_aupr']:>8.4f}")
    print("-" * 105)
    for k in [3, 5, 10]:
        p_ex = res_existing[f"precision@{k}"]
        p_st = res_strict[f"precision@{k}"]
        print(f"{f'Precision@{k} (Mean across cell lines)':<32} | {p_ex*100:>7.2f}%                         | {p_st*100:>7.2f}%")
        n_ex = res_existing[f"ndcg@{k}"]
        n_st = res_strict[f"ndcg@{k}"]
        print(f"{f'NDCG@{k} (Mean across cell lines)':<32} | {n_ex:>8.4f}                         | {n_st:>8.4f}")
    print("=" * 105)

    payload = {
        "evaluation_target": "Strict Bilateral Cold-Drug Evaluation",
        "checkpoint": checkpoint_path,
        "existing_bilateral": res_existing,
        "strict_bilateral": res_strict,
    }

    if save_json:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        print(f"\n[Saved] Strict bilateral benchmark results saved to: {output_path}")

    return payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SynThera Strict Bilateral Cold-Drug Evaluation")
    parser.add_argument("--checkpoint", type=str, default=CHECKPOINT_PATH, help="Path to checkpoint")
    parser.add_argument("--device", type=str, default=None, help="Device (cuda/cpu)")
    parser.add_argument("--seed", type=int, default=42, help="Seed for RNG")
    parser.add_argument("--output", type=str, default=DEFAULT_OUTPUT_JSON, help="Output JSON path")
    args = parser.parse_args()

    run_strict_bilateral_evaluation(
        checkpoint_path=args.checkpoint,
        device=args.device,
        seed=args.seed,
        output_path=args.output,
        save_json=True,
    )
