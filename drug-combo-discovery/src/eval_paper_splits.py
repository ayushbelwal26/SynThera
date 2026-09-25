"""
src/eval_paper_splits.py — Master Reproducible Evaluation CLI for Paper Splits
=============================================================================

Provides unified, deterministic evaluation for:
  1. strict_bilateral : 2,565 pairs (DrugDouble zero-shot: both drugs unseen in train & val)
  2. leave_drug_out   : 31,847 pairs (Clean LDO: all pairs with >=1 held-out test drug and 0 val overlap;
                        includes DrugSingle and DrugDouble sub-populations)
  3. pair_disjoint    : 37,778 pairs (Leave-Pair-Out: all pairs strictly absent from training pairs)

Usage:
  python -m src.eval_paper_splits --split strict_bilateral --checkpoint models/synergy_gnn_pair_interaction.ckpt
  python -m src.eval_paper_splits --split leave_drug_out --checkpoint models/synergy_gnn_pair_interaction.ckpt
  python -m src.eval_paper_splits --split pair_disjoint --checkpoint models/synergy_gnn_pair_interaction.ckpt
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

DEFAULT_CKPT = os.path.join(MODELS_DIR, "synergy_gnn_pair_interaction.ckpt")
CLASS_MAP = {"antagonism": 0, "additive": 1, "synergy": 2}


def get_drug_partition(
    labels_df: pd.DataFrame,
    seed: int = 42,
    val_frac: float = 0.15,
    test_frac: float = 0.15,
) -> Tuple[set[str], set[str], set[str]]:
    """Reconstructs the exact train/val/test drug allocation (seed 42)."""
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


def evaluate_metrics(
    subset_df: pd.DataFrame,
    probs: np.ndarray,
    k_list: List[int] = [3, 5, 10],
) -> Dict[str, Any]:
    """Computes all classification discrimination and contextual ranking metrics."""
    n_pairs = len(subset_df)
    unique_drugs = len(set(subset_df["drug_a_kg_id"].unique()) | set(subset_df["drug_b_kg_id"].unique()))
    n_cell_lines = subset_df["cell_line_name"].nunique()

    y_true_binary = (subset_df["synergy_class"] == "synergy").astype(int).values
    n_synergy = int(y_true_binary.sum())
    synergy_prev = float(n_synergy / n_pairs) if n_pairs > 0 else 0.0

    y_true_multi = subset_df["synergy_class"].map(CLASS_MAP).values
    try:
        macro_auroc = float(roc_auc_score(y_true_multi, probs, multi_class="ovr", average="macro"))
    except ValueError:
        macro_auroc = float("nan")

    macro_aupr_list = []
    for c_idx in range(3):
        bin_y = (y_true_multi == c_idx).astype(int)
        try:
            macro_aupr_list.append(average_precision_score(bin_y, probs[:, c_idx]))
        except ValueError:
            macro_aupr_list.append(float("nan"))
    macro_aupr = float(np.nanmean(macro_aupr_list))

    p_syn = probs[:, 2]
    try:
        bin_syn_auroc = float(roc_auc_score(y_true_binary, p_syn))
    except ValueError:
        bin_syn_auroc = float("nan")

    try:
        bin_syn_aupr = float(average_precision_score(y_true_binary, p_syn))
    except ValueError:
        bin_syn_aupr = float("nan")

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
        topk_res[f"precision@{k}"] = float(m_df[f"precision@{k}"].mean()) if len(m_df) > 0 else 0.0
        topk_res[f"ndcg@{k}"] = float(valid_rec[f"ndcg@{k}"].mean()) if len(valid_rec) > 0 else float("nan")
        topk_res[f"recall@{k}"] = float(valid_rec[f"recall@{k}"].mean()) if len(valid_rec) > 0 else float("nan")

    return {
        "n_pairs": n_pairs,
        "n_unique_drugs": unique_drugs,
        "n_cell_lines": n_cell_lines,
        "n_synergy": n_synergy,
        "synergy_prevalence": synergy_prev,
        "macro_auroc": macro_auroc,
        "macro_aupr": macro_aupr,
        "binary_synergy_auroc": bin_syn_auroc,
        "binary_synergy_aupr": bin_syn_aupr,
        **topk_res,
    }


def run_evaluation(
    split_name: str,
    checkpoint_path: str = DEFAULT_CKPT,
    device: str | None = None,
    seed: int = 42,
    output_path: str | None = None,
) -> Dict[str, Any]:
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    print("=" * 95)
    print(f"  SynThera Paper Split Evaluation: {split_name.upper()}")
    print("=" * 95)
    print(f"Checkpoint : {checkpoint_path}")
    print(f"Device     : {device}")
    print(f"Seed       : {seed}")

    # Load HeteroData
    t0 = time.time()
    heterodata = torch.load(HETERODATA_PATH, weights_only=False)
    _, _, test_loader = build_loaders(heterodata, [], [], [])

    metadata = heterodata.metadata()
    num_nodes_dict = {nt: heterodata[nt].num_nodes for nt in heterodata.node_types}
    n_fallback = int((~heterodata["drug"].fp_mask).sum().item())
    class_weights = compute_class_weights(heterodata)

    # Load Checkpoint
    model = SynergyModule.load_from_checkpoint(
        checkpoint_path,
        metadata=metadata,
        num_nodes_dict=num_nodes_dict,
        num_fallback_drugs=n_fallback,
        num_cell_lines=heterodata.num_cell_lines,
        num_layers=2,
        class_weights=class_weights,
    )
    model.to(device)
    model.eval()

    # Symmetric GNN inference across test set
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    np.random.seed(seed)

    print(f"\nRunning symmetric GNN inference over {len(test_loader)} batches...")
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
    print(f"Inference completed across {len(all_probs):,} pairs in {time.time() - t0:.2f}s.")

    # Load partitions
    labels_df = pd.read_csv(LABELS_PATH)
    train_idx = pd.read_csv(SPLIT_TRAIN_PATH)["row_index"].values
    val_idx = pd.read_csv(SPLIT_VAL_PATH)["row_index"].values
    test_idx = pd.read_csv(SPLIT_TEST_PATH)["row_index"].values
    test_df = labels_df.iloc[test_idx].reset_index(drop=True)

    train_drugs, val_drugs, test_drugs = get_drug_partition(labels_df, seed=seed)

    train_pairs_df = labels_df.iloc[train_idx]
    train_pair_drugs = set(train_pairs_df["drug_a_kg_id"]) | set(train_pairs_df["drug_b_kg_id"])

    # Subset filtering based on split_name
    if split_name == "strict_bilateral":
        mask = test_df["drug_a_kg_id"].isin(test_drugs) & test_df["drug_b_kg_id"].isin(test_drugs)
        target_df = test_df[mask].copy().reset_index(drop=True)
        target_probs = all_probs[mask]

        # Assertions
        assert target_df["drug_a_kg_id"].isin(train_drugs | val_drugs).sum() == 0
        assert target_df["drug_b_kg_id"].isin(train_drugs | val_drugs).sum() == 0

        res = evaluate_metrics(target_df, target_probs)
        title = "STRICT BILATERAL (DrugDouble: Both drugs unseen in train & val)"

    elif split_name == "leave_drug_out":
        # Clean LDO: all pairs with >=1 held-out test drug, strictly zero val drug overlap
        mask = (~test_df["drug_a_kg_id"].isin(val_drugs)) & (~test_df["drug_b_kg_id"].isin(val_drugs))
        target_df = test_df[mask].copy().reset_index(drop=True)
        target_probs = all_probs[mask]

        # Assertions
        assert target_df["drug_a_kg_id"].isin(val_drugs).sum() == 0
        assert target_df["drug_b_kg_id"].isin(val_drugs).sum() == 0

        res = evaluate_metrics(target_df, target_probs)
        title = "LEAVE-DRUG-OUT (Clean LDO: >=1 held-out drug, 0 val overlap)"

    elif split_name == "pair_disjoint":
        # Pair-disjoint: all test pairs are strictly disjoint from train pairs
        # In test_df, 100% of pairs have 0 overlap with train_pair_drugs
        target_df = test_df.copy().reset_index(drop=True)
        target_probs = all_probs

        def canonical(df):
            return set(tuple(sorted([r["drug_a_kg_id"], r["drug_b_kg_id"]])) for _, r in df.iterrows())

        train_pair_set = canonical(train_pairs_df)
        test_pair_set = canonical(test_df)
        assert len(train_pair_set & test_pair_set) == 0, "Pair leakage detected!"

        res = evaluate_metrics(target_df, target_probs)
        title = "PAIR-DISJOINT / LEAVE-PAIR-OUT (0 pair overlap with training)"

    else:
        raise ValueError(f"Unknown split: {split_name}. Choose from: strict_bilateral, leave_drug_out, pair_disjoint")

    # Print Table
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)
    print(f"  Observations (Pairs)    : {res['n_pairs']:,}")
    print(f"  Unique Drugs            : {res['n_unique_drugs']:,}")
    print(f"  Cell Lines Evaluated    : {res['n_cell_lines']:,}")
    print(f"  Synergy Prevalence      : {res['synergy_prevalence']*100:.2f}% ({res['n_synergy']:,} pairs)")
    print("-" * 80)
    print(f"  Macro AUROC (OVR, 3-cls): {res['macro_auroc']:.4f}")
    print(f"  Macro AUPR  (3-cls mean): {res['macro_aupr']:.4f}")
    print(f"  Binary Synergy AUROC    : {res['binary_synergy_auroc']:.4f}")
    print(f"  Binary Synergy AUPR     : {res['binary_synergy_aupr']:.4f}")
    print("-" * 80)
    for k in [3, 5, 10]:
        print(f"  Precision@{k:<2}              : {res[f'precision@{k}']*100:6.2f}%   | NDCG@{k:<2}: {res[f'ndcg@{k}']:.4f}")
    print("=" * 80)

    payload = {
        "split_name": split_name,
        "checkpoint": checkpoint_path,
        "metrics": res,
    }

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        print(f"\nResults saved to: {output_path}")

    return payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate SynThera on Published Paper Splits")
    parser.add_argument(
        "--split",
        type=str,
        required=True,
        choices=["strict_bilateral", "leave_drug_out", "pair_disjoint"],
        help="Evaluation split to benchmark",
    )
    parser.add_argument(
        "--checkpoint",
        type=str,
        default=DEFAULT_CKPT,
        help="Path to model checkpoint",
    )
    parser.add_argument("--device", type=str, default=None, help="Device (cuda/cpu)")
    parser.add_argument("--seed", type=int, default=42, help="Seed")
    parser.add_argument("--output", type=str, default=None, help="Output JSON path")
    args = parser.parse_args()

    run_evaluation(
        split_name=args.split,
        checkpoint_path=args.checkpoint,
        device=args.device,
        seed=args.seed,
        output_path=args.output,
    )
