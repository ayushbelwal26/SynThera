"""
src/faithfulness_eval.py — Formal Explanation-Faithfulness Evaluation Suite
===========================================================================

Standardized evaluation module measuring the mechanistic faithfulness of
SynThera's GNNExplainer-derived edge attributions on held-out test splits.

Metrics Evaluated:
1. Sufficiency: Mask everything EXCEPT the top-k explanation edges.
   - confidence_retention = p_masked / p_original
   - class_preservation = (pred_class_masked == pred_class_original)
2. Necessity: Mask ONLY the top-k explanation edges.
   - necessity_delta = p_original - p_without_top_k
3. Random-Edge Ablation Control:
   - Repeat necessity and sufficiency masking with an identical number k of
     randomly sampled edges from the same local candidate subgraph.
   - Proves whether top-k explanation edges are genuinely load-bearing compared
     to noise perturbations.

Held-out Evaluation Set:
- Evaluates across a deterministic, stratified subset (default N=50 pairs)
  drawn from the 8,496 bilateral cold-drug test set (neither drug seen during training),
  representing the strictest out-of-distribution generalization benchmark.
"""

from __future__ import annotations

import os
import sys
import json
import time
import random
import argparse
from typing import Any, Dict, List, Tuple
from collections import defaultdict

import numpy as np
import pandas as pd
from scipy import stats
import torch
import torch.nn.functional as F

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from train import LABELS_PATH, SPLIT_TRAIN_PATH, SPLIT_TEST_PATH, compute_class_weights
from model import SynergyModule, CLASS_NAMES
from predict import load_model, predict_synergy, THRESHOLD_SYNERGY, THRESHOLD_ANTAGONISM
from explain import (
    _sample_batch,
    _score_edges,
    _necessity_check,
    _sufficiency_check,
    _build_name_lookups,
    _get_node_maps,
)

CHECKPOINT_PATH = os.path.join(ROOT_DIR, "models", "synergy_gnn_final.ckpt")
HETERODATA_PATH = os.path.join(ROOT_DIR, "data", "processed", "heterodata.pt")
OUTPUT_JSON_PATH = os.path.join(ROOT_DIR, "data", "processed", "faithfulness_benchmark.json")

CLASS_MAP = {"antagonism": 0, "additive": 1, "synergy": 2}


def get_bilateral_cold_test_set(
    labels_path: str = LABELS_PATH,
    train_split_path: str = SPLIT_TRAIN_PATH,
    test_split_path: str = SPLIT_TEST_PATH,
) -> pd.DataFrame:
    """
    Extracts the held-out bilateral cold-drug test pairs (neither drug seen in train).
    """
    labels_df = pd.read_csv(labels_path)
    train_idx = pd.read_csv(train_split_path)["row_index"].values
    test_idx = pd.read_csv(test_split_path)["row_index"].values

    train_pairs = labels_df.iloc[train_idx]
    train_drugs = set(train_pairs["drug_a_kg_id"]) | set(train_pairs["drug_b_kg_id"])

    test_pairs = labels_df.iloc[test_idx].reset_index(drop=True)
    a_in_train = test_pairs["drug_a_kg_id"].isin(train_drugs).values
    b_in_train = test_pairs["drug_b_kg_id"].isin(train_drugs).values

    mask_bilateral = (~a_in_train) & (~b_in_train)
    bilateral_df = test_pairs[mask_bilateral].reset_index(drop=True)
    return bilateral_df


def select_evaluation_subset(
    df: pd.DataFrame,
    sample_size: int = 50,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Selects a deterministic stratified sample across synergy classes from the bilateral test pairs.
    """
    if sample_size is None or sample_size >= len(df):
        return df

    np.random.seed(seed)
    # Stratified sampling across classes
    strata = []
    classes = df["synergy_class"].unique()
    per_class = sample_size // len(classes)
    remainder = sample_size % len(classes)

    for i, cls in enumerate(classes):
        cls_df = df[df["synergy_class"] == cls]
        n_take = per_class + (1 if i < remainder else 0)
        n_take = min(n_take, len(cls_df))
        sampled = cls_df.sample(n=n_take, random_state=seed + i)
        strata.append(sampled)

    sample_df = pd.concat(strata).sample(frac=1.0, random_state=seed).reset_index(drop=True)
    return sample_df


def evaluate_pair_faithfulness(
    row: pd.Series,
    module: SynergyModule,
    heterodata: Any,
    device: str,
    name_lookup: Any,
    drug_id2idx: dict[str, int],
    cell_line_map: dict[str, int],
    top_k: int = 10,
    rng: random.Random = None,
) -> Dict[str, Any]:
    """
    Evaluates Real vs. Random-Control necessity and sufficiency on a single drug pair.
    """
    if rng is None:
        rng = random.Random(42)

    da = row["drug_a_kg_id"]
    db = row["drug_b_kg_id"]
    cl = row["cell_line_name"]
    gt_class = row["synergy_class"]

    # 1. Canonical Symmetric Prediction
    pred = predict_synergy(
        drug_a_id=da,
        drug_b_id=db,
        cell_line_name=cl,
        module=module,
        heterodata=heterodata,
        device=device,
        use_cache=True,
    )
    pred_class = pred["prediction"]
    pred_idx = CLASS_MAP[pred_class]
    p_syn_orig = pred["p_synergy"]
    p_pred_orig = pred["p_" + pred_class]

    # 2. Local Subgraph Extraction & Perturbation Attribution (Option 4)
    a_idx = drug_id2idx[da]
    b_idx = drug_id2idx[db]
    cell_idx = cell_line_map[cl]
    batch = _sample_batch(heterodata, a_idx, b_idx, cell_idx)

    # 3. Extract Top-k Real Explanation Edges and All Candidate Subgraph Edges via Leave-One-Out
    top_edges, all_edges = _score_edges(
        batch=batch,
        name_lookup=name_lookup,
        top_k=top_k,
        module=module,
        pred_idx=pred_idx,
        original_prob=p_pred_orig,
        device=device,
        chunk_size=64,
    )
    k_actual = len(top_edges)

    if k_actual == 0:
        return {"skipped": True, "reason": "No edges in subgraph"}

    # Severing check: verify whether both target drugs have incident edges in top-k
    local_min = (batch["drug"].n_id == min(a_idx, b_idx)).nonzero(as_tuple=True)[0][0].item()
    local_max = (batch["drug"].n_id == max(a_idx, b_idx)).nonzero(as_tuple=True)[0][0].item()
    drugs_touched = set()
    for e in top_edges:
        if e.get("source_type") == "drug":
            drugs_touched.add(e["source_local"])
        if e.get("target_type") == "drug":
            drugs_touched.add(e["target_local"])

    both_drugs_connected = bool(local_min in drugs_touched and local_max in drugs_touched)

    # 4. Sample Random Edges of Identical Size from Candidate Set
    if len(all_edges) >= k_actual:
        rand_edges = rng.sample(all_edges, k_actual)
    else:
        rand_edges = list(all_edges)

    # 5. Real Explanation Faithfulness Checks
    # Necessity: mask ONLY top-k edges
    real_nec_pct, real_nec_score, real_nec_class = _necessity_check(
        module, batch, top_edges, pred_idx, p_pred_orig, device
    )
    # Sufficiency: mask everything EXCEPT top-k edges
    real_suf_ret, real_suf_class_ok, real_suf_score = _sufficiency_check(
        module, batch, top_edges, pred_idx, p_pred_orig, device
    )

    # 6. Random-Edge Control Checks
    rand_nec_pct, rand_nec_score, rand_nec_class = _necessity_check(
        module, batch, rand_edges, pred_idx, p_pred_orig, device
    )
    rand_suf_ret, rand_suf_class_ok, rand_suf_score = _sufficiency_check(
        module, batch, rand_edges, pred_idx, p_pred_orig, device
    )

    # Absolute necessity deltas
    real_nec_delta = p_pred_orig - real_nec_score
    rand_nec_delta = p_pred_orig - rand_nec_score

    # Sufficiency confidence retention ratio
    real_suf_ratio = real_suf_score / max(p_pred_orig, 1e-9)
    rand_suf_ratio = rand_suf_score / max(p_pred_orig, 1e-9)

    return {
        "skipped": False,
        "drug_a": da,
        "drug_b": db,
        "cell_line": cl,
        "ground_truth": gt_class,
        "predicted_class": pred_class,
        "original_confidence": p_pred_orig,
        "original_p_synergy": p_syn_orig,
        "k_edges": k_actual,
        "both_drugs_connected": both_drugs_connected,
        # Real Explanation Metrics
        "real_necessity_delta": real_nec_delta,
        "real_necessity_delta_pct": real_nec_pct,
        "real_necessity_score": real_nec_score,
        "real_necessity_class": real_nec_class,
        "real_sufficiency_ratio": real_suf_ratio,
        "real_sufficiency_ret_pct": real_suf_ret,
        "real_sufficiency_score": real_suf_score,
        "real_class_preserved": real_suf_class_ok,
        # Random Control Metrics
        "rand_necessity_delta": rand_nec_delta,
        "rand_necessity_delta_pct": rand_nec_pct,
        "rand_necessity_score": rand_nec_score,
        "rand_necessity_class": rand_nec_class,
        "rand_sufficiency_ratio": rand_suf_ratio,
        "rand_sufficiency_ret_pct": rand_suf_ret,
        "rand_sufficiency_score": rand_suf_score,
        "rand_class_preserved": rand_suf_class_ok,
        # Differences (Real - Random)
        "diff_necessity_delta": real_nec_delta - rand_nec_delta,
        "diff_sufficiency_ratio": real_suf_ratio - rand_suf_ratio,
    }


def run_faithfulness_benchmark(
    sample_size: int = 50,
    seed: int = 42,
    top_k: int = 10,
    device: str | None = None,
    save_json: bool = True,
) -> Dict[str, Any]:
    """
    Executes the full formal explanation-faithfulness benchmark suite.
    """
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    print("=" * 95)
    print("  SynThera Formal Explanation-Faithfulness Benchmark Suite")
    print("=" * 95)

    print(f"\n[1/4] Loading model checkpoint and HeteroData onto {device}...")
    t0 = time.time()
    module, heterodata, device = load_model(CHECKPOINT_PATH, HETERODATA_PATH, device=device)
    name_lookup, _ = _build_name_lookups(heterodata)
    node_maps = _get_node_maps(heterodata)
    drug_id2idx = node_maps.get("drug", {})
    cell_line_map = heterodata.cell_line_map
    print(f"      Loaded model in {time.time() - t0:.2f}s.")

    print(f"\n[2/4] Assembling bilateral cold-drug evaluation set...")
    bilateral_all = get_bilateral_cold_test_set()
    print(f"      Total bilateral cold-drug test pairs available: {len(bilateral_all):,}")
    eval_df = select_evaluation_subset(bilateral_all, sample_size=sample_size, seed=seed)
    print(f"      Evaluation subset size: {len(eval_df)} pairs (seed={seed}, stratified by class).")
    class_dist = eval_df["synergy_class"].value_counts().to_dict()
    print(f"      Subset class balance: {class_dist}")

    print(f"\n[3/4] Running Real vs. Random-Control edge ablation checks (top_k={top_k})...")
    rng = random.Random(seed)
    results_list = []
    t_start = time.time()

    for idx, row in eval_df.iterrows():
        pair_res = evaluate_pair_faithfulness(
            row=row,
            module=module,
            heterodata=heterodata,
            device=device,
            name_lookup=name_lookup,
            drug_id2idx=drug_id2idx,
            cell_line_map=cell_line_map,
            top_k=top_k,
            rng=rng,
        )
        if not pair_res.get("skipped", False):
            results_list.append(pair_res)

        if (len(results_list)) % 10 == 0 or len(results_list) == len(eval_df):
            elapsed = time.time() - t_start
            pace = elapsed / max(1, len(results_list))
            print(f"      Completed {len(results_list)}/{len(eval_df)} pairs ({pace:.2f}s/pair)...")

    # 4. Aggregate & Statistical Analysis
    print(f"\n[4/4] Aggregating benchmark statistics across {len(results_list)} evaluated pairs...")
    real_necs = [r["real_necessity_delta"] for r in results_list]
    rand_necs = [r["rand_necessity_delta"] for r in results_list]
    real_nec_pcts = [r["real_necessity_delta_pct"] for r in results_list]
    rand_nec_pcts = [r["rand_necessity_delta_pct"] for r in results_list]

    real_sufs = [r["real_sufficiency_ratio"] for r in results_list]
    rand_sufs = [r["rand_sufficiency_ratio"] for r in results_list]
    real_suf_pcts = [r["real_sufficiency_ret_pct"] for r in results_list]
    rand_suf_pcts = [r["rand_sufficiency_ret_pct"] for r in results_list]

    real_pres_pct = 100.0 * np.mean([1.0 if r["real_class_preserved"] else 0.0 for r in results_list])
    rand_pres_pct = 100.0 * np.mean([1.0 if r["rand_class_preserved"] else 0.0 for r in results_list])

    # Statistical significance testing
    try:
        nec_wilcoxon = stats.wilcoxon(real_necs, rand_necs, alternative="greater")
        nec_p_val = float(nec_wilcoxon.pvalue)
    except Exception:
        nec_p_val = float("nan")

    try:
        suf_wilcoxon = stats.wilcoxon(real_sufs, rand_sufs, alternative="greater")
        suf_p_val = float(suf_wilcoxon.pvalue)
    except Exception:
        suf_p_val = float("nan")

    summary = {
        "n_evaluated_pairs": len(results_list),
        "evaluation_split": "Bilateral Cold-Drug Held-Out Test Set (neither drug in train)",
        "sample_strategy": f"Stratified deterministic sample (seed={seed})",
        "top_k_edges": top_k,
        "necessity": {
            "real_mean_delta": float(np.mean(real_necs)),
            "real_median_delta": float(np.median(real_necs)),
            "real_std_delta": float(np.std(real_necs)),
            "real_mean_delta_pct": float(np.mean(real_nec_pcts)),
            "real_median_delta_pct": float(np.median(real_nec_pcts)),
            "random_mean_delta": float(np.mean(rand_necs)),
            "random_median_delta": float(np.median(rand_necs)),
            "random_std_delta": float(np.std(rand_necs)),
            "random_mean_delta_pct": float(np.mean(rand_nec_pcts)),
            "random_median_delta_pct": float(np.median(rand_nec_pcts)),
            "delta_difference_mean": float(np.mean(real_necs) - np.mean(rand_necs)),
            "wilcoxon_p_value_greater": nec_p_val,
        },
        "sufficiency": {
            "real_mean_ratio": float(np.mean(real_sufs)),
            "real_median_ratio": float(np.median(real_sufs)),
            "real_std_ratio": float(np.std(real_sufs)),
            "real_mean_ret_pct": float(np.mean(real_suf_pcts)),
            "real_median_ret_pct": float(np.median(real_suf_pcts)),
            "random_mean_ratio": float(np.mean(rand_sufs)),
            "random_median_ratio": float(np.median(rand_sufs)),
            "random_std_ratio": float(np.std(rand_sufs)),
            "random_mean_ret_pct": float(np.mean(rand_suf_pcts)),
            "random_median_ret_pct": float(np.median(rand_suf_pcts)),
            "ratio_difference_mean": float(np.mean(real_sufs) - np.mean(rand_sufs)),
            "wilcoxon_p_value_greater": suf_p_val,
        },
        "class_preservation": {
            "real_class_preserved_pct": real_pres_pct,
            "random_class_preserved_pct": rand_pres_pct,
            "preservation_lift": real_pres_pct - rand_pres_pct,
        },
        "both_drugs_connected_pct": float(100.0 * np.mean([1.0 if r.get("both_drugs_connected", False) else 0.0 for r in results_list])),
    }

    # Print Formatted Comparison Table
    print("\n" + "=" * 95)
    print("FAITHFULNESS EVALUATION BENCHMARK RESULTS (REAL vs. RANDOM-EDGE CONTROL)")
    print("=" * 95)
    print(f"{'Faithfulness Metric':<32} | {'Real GNN Explanations':<24} | {'Random Edge Control':<24} | {'Delta (Real - Rand)':<14}")
    print("-" * 95)
    print(f"{'Necessity Delta (Mean)':<32} | {summary['necessity']['real_mean_delta']:>+7.4f} ({summary['necessity']['real_mean_delta_pct']:>+6.2f}%)       | {summary['necessity']['random_mean_delta']:>+7.4f} ({summary['necessity']['random_mean_delta_pct']:>+6.2f}%)      | {summary['necessity']['delta_difference_mean']:>+7.4f}")
    print(f"{'Necessity Delta (Median)':<32} | {summary['necessity']['real_median_delta']:>+7.4f} ({summary['necessity']['real_median_delta_pct']:>+6.2f}%)       | {summary['necessity']['random_median_delta']:>+7.4f} ({summary['necessity']['random_median_delta_pct']:>+6.2f}%)      | {summary['necessity']['real_median_delta'] - summary['necessity']['random_median_delta']:>+7.4f}")
    print(f"{'Sufficiency Ratio (Mean)':<32} | {summary['sufficiency']['real_mean_ratio']:>7.4f} ({summary['sufficiency']['real_mean_ret_pct']:>6.1f}%)        | {summary['sufficiency']['random_mean_ratio']:>7.4f} ({summary['sufficiency']['random_mean_ret_pct']:>6.1f}%)       | {summary['sufficiency']['ratio_difference_mean']:>+7.4f}")
    print(f"{'Sufficiency Ratio (Median)':<32} | {summary['sufficiency']['real_median_ratio']:>7.4f} ({summary['sufficiency']['real_median_ret_pct']:>6.1f}%)        | {summary['sufficiency']['random_median_ratio']:>7.4f} ({summary['sufficiency']['random_median_ret_pct']:>6.1f}%)       | {summary['sufficiency']['real_median_ratio'] - summary['sufficiency']['random_median_ratio']:>+7.4f}")
    print(f"{'Class Preservation Rate':<32} | {summary['class_preservation']['real_class_preserved_pct']:>6.1f}%                   | {summary['class_preservation']['random_class_preserved_pct']:>6.1f}%                  | {summary['class_preservation']['preservation_lift']:>+6.1f}%")
    print(f"{'Both Drugs Connected Rate':<32} | {summary['both_drugs_connected_pct']:>6.1f}%                   | N/A                      | N/A")
    print("-" * 95)
    print(f"Necessity Wilcoxon Significance: p = {summary['necessity']['wilcoxon_p_value_greater']:.4e} "
          f"({'Significant p < 0.05' if summary['necessity']['wilcoxon_p_value_greater'] < 0.05 else 'Not Significant'})")
    print("=" * 95)

    if save_json:
        os.makedirs(os.path.dirname(OUTPUT_JSON_PATH), exist_ok=True)
        payload = {
            "summary": summary,
            "pair_evaluations": results_list,
        }
        with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        print(f"\n[Saved] Detailed benchmark records written to: {OUTPUT_JSON_PATH}")

    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SynThera Formal Explanation-Faithfulness Benchmark")
    parser.add_argument("--sample-size", type=int, default=50, help="Number of pairs to evaluate from bilateral cold test set (default: 50)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for sampling (default: 42)")
    parser.add_argument("--top-k", type=int, default=10, help="Number of explanation edges to ablate (default: 10)")
    parser.add_argument("--full", action="store_true", help="Run on all 8,496 bilateral cold-drug pairs (warning: multi-hour)")
    args = parser.parse_args()

    n_sample = None if args.full else args.sample_size
    run_faithfulness_benchmark(sample_size=n_sample, seed=args.seed, top_k=args.top_k)
