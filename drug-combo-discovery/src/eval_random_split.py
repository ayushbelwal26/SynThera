"""
src/eval_random_split.py — Random / Warm Split Evaluation CLI
=============================================================

Evaluates a checkpoint on the random/warm test split and computes
the same metrics as eval_paper_splits.py (Macro AUROC, Binary AUROC,
Precision@K, NDCG@K, etc.).

Usage
-----
  python -m src.eval_random_split --checkpoint models/synergy_gnn_random_split_seed42.ckpt

IMPORTANT METHODOLOGICAL NOTE
------------------------------
If you pass the FROZEN CHAMPION checkpoint (synergy_gnn_pair_interaction.ckpt),
this script will detect the leakage situation and print a clear warning:
the champion was trained on a cold-drug split, so its training set overlaps
with the random test set.  That result is NOT a valid held-out random test.

For a legitimate random-split test, use the dedicated checkpoint:
  models/synergy_gnn_random_split_seed42.ckpt

Protected (NEVER OVERWRITTEN):
  models/synergy_gnn_pair_interaction.ckpt
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from sklearn.metrics import roc_auc_score, average_precision_score

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR  = os.path.join(ROOT_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from model import SynergyModule
from train import (
    HETERODATA_PATH,
    LABELS_PATH,
    MODELS_DIR,
    NUM_NEIGHBORS,
    BATCH_SIZE,
    _sep,
)
from topk_eval import compute_group_topk
from eval_paper_splits import evaluate_metrics

PROCESSED   = os.path.join(ROOT_DIR, "data", "processed")
SPLITS_DIR  = os.path.join(PROCESSED, "splits_random")
BENCH_JSON  = os.path.join(PROCESSED, "random_benchmark.json")

RANDOM_TRAIN_CSV = os.path.join(SPLITS_DIR, "random_train.csv")
RANDOM_VAL_CSV   = os.path.join(SPLITS_DIR, "random_val.csv")
RANDOM_TEST_CSV  = os.path.join(SPLITS_DIR, "random_test.csv")

CHAMPION_CKPT    = os.path.join(MODELS_DIR, "synergy_gnn_pair_interaction.ckpt")
RANDOM_CKPT      = os.path.join(MODELS_DIR, "synergy_gnn_random_split_seed42.ckpt")

CLASS_MAP = {"antagonism": 0, "additive": 1, "synergy": 2}


def _check_leakage_risk(checkpoint_path: str) -> bool:
    """
    Returns True if the checkpoint is the champion (cold-drug trained),
    which means test-set leakage exists for the random split evaluation.
    """
    return os.path.abspath(checkpoint_path) == os.path.abspath(CHAMPION_CKPT)


def _build_test_loader(heterodata, labels_df, test_idx):
    """Build a LinkNeighborLoader for the random test set."""
    from torch_geometric.loader import LinkNeighborLoader

    drug_map = {v: k for k, v in enumerate(sorted(
        set(labels_df["drug_a_kg_id"]) | set(labels_df["drug_b_kg_id"])
    ))}
    cell_map = heterodata.cell_line_map

    sub = labels_df.iloc[test_idx].reset_index(drop=True)
    a = torch.tensor(sub["drug_a_kg_id"].map(drug_map).astype(int).values, dtype=torch.long)
    b = torch.tensor(sub["drug_b_kg_id"].map(drug_map).astype(int).values, dtype=torch.long)
    y = torch.tensor(sub["synergy_class"].map(CLASS_MAP).astype(int).values, dtype=torch.long)
    c = torch.tensor(sub["cell_line_name"].map(cell_map).astype(int).values, dtype=torch.long)

    edge_label_index = torch.stack([a, b], dim=0)
    edge_label       = torch.stack([y, c], dim=1)

    return LinkNeighborLoader(
        data              = heterodata,
        num_neighbors     = NUM_NEIGHBORS,
        edge_label_index  = (("drug", "synergy_pair", "drug"), edge_label_index),
        edge_label        = edge_label,
        batch_size        = BATCH_SIZE,
        shuffle           = False,
        num_workers       = 0,
        persistent_workers= False,
    )


def run_random_eval(
    checkpoint_path: str = RANDOM_CKPT,
    device: str | None = None,
    seed: int = 42,
    output_path: str | None = None,
) -> dict:
    """
    Evaluate checkpoint on the random/warm test split.

    Returns
    -------
    dict
        Full payload with metrics, leakage flag, and split statistics.
    """
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    is_champion = _check_leakage_risk(checkpoint_path)

    print("=" * 90)
    print("  SynThera — Random / Warm Split Evaluation")
    print("=" * 90)
    print(f"  Checkpoint : {checkpoint_path}")
    print(f"  Device     : {device}")
    print(f"  Seed       : {seed}")
    if is_champion:
        print()
        print("  !! LEAKAGE WARNING !!")
        print("  The champion checkpoint was trained on the cold-drug split.")
        print("  Many random test observations were in its training set.")
        print("  This evaluation result is NOT a valid held-out random-split test.")
        print("  For a clean result, use: models/synergy_gnn_random_split_seed42.ckpt")
        print()

    # ── Verify split files exist ─────────────────────────────────
    for p in [RANDOM_TRAIN_CSV, RANDOM_VAL_CSV, RANDOM_TEST_CSV, BENCH_JSON]:
        if not os.path.exists(p):
            raise FileNotFoundError(
                f"Random split file missing: {p}\n"
                f"Run: python -m src.build_random_split first."
            )

    with open(BENCH_JSON, encoding="utf-8") as fh:
        bench_meta = json.load(fh)

    # ── Load heterodata and model ─────────────────────────────────
    t0 = time.time()
    _sep("Loading HeteroData")
    heterodata = torch.load(HETERODATA_PATH, weights_only=False)

    metadata       = heterodata.metadata()
    num_nodes_dict = {nt: heterodata[nt].num_nodes for nt in heterodata.node_types}
    n_fallback     = int((~heterodata["drug"].fp_mask).sum().item())

    _sep("Loading Checkpoint")
    model = SynergyModule.load_from_checkpoint(
        checkpoint_path,
        metadata           = metadata,
        num_nodes_dict     = num_nodes_dict,
        num_fallback_drugs = n_fallback,
        num_cell_lines     = heterodata.num_cell_lines,
        num_layers         = 2,
        class_weights      = torch.ones(3),  # placeholder, overridden by ckpt weights
    )
    model.to(device)
    model.eval()
    print(f"  Model ready in {time.time()-t0:.2f}s")

    # ── Load split indices ────────────────────────────────────────
    labels_df = pd.read_csv(LABELS_PATH)
    test_idx  = pd.read_csv(RANDOM_TEST_CSV)["row_index"].tolist()
    test_df   = labels_df.iloc[test_idx].reset_index(drop=True)

    # ── Build test loader and run inference ───────────────────────
    _sep("Running symmetric GNN inference on random test set")
    test_loader = _build_test_loader(heterodata, labels_df, test_idx)

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
            orig_eli  = batch_rev["drug", "synergy_pair", "drug"].edge_label_index
            batch_rev["drug", "synergy_pair", "drug"].edge_label_index = orig_eli[[1, 0]]
            logits_rev, _ = model(batch_rev)

            p_fwd = F.softmax(logits_fwd, dim=-1)
            p_rev = F.softmax(logits_rev, dim=-1)
            pass_probs.append(((p_fwd + p_rev) / 2.0).detach().cpu())

    all_probs = torch.cat(pass_probs, dim=0).numpy()
    print(f"  Inference complete: {len(all_probs):,} pairs")

    # ── Compute metrics ───────────────────────────────────────────
    _sep("Computing metrics")
    res = evaluate_metrics(test_df, all_probs, k_list=[3, 5, 10])

    # ── Print results ─────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("  RANDOM / WARM SPLIT — Test Set Results")
    print("=" * 80)
    print(f"  {'Checkpoint':<26}: {os.path.basename(checkpoint_path)}")
    print(f"  {'Newly trained (random)':<26}: {'NO  (LEAKAGE WARNING above)' if is_champion else 'YES'}")
    print(f"  {'Test observations':<26}: {res['n_pairs']:,}")
    print(f"  {'Unique drugs':<26}: {res['n_unique_drugs']:,}")
    print(f"  {'Cell lines':<26}: {res['n_cell_lines']:,}")
    print(f"  {'Synergy prevalence':<26}: {res['synergy_prevalence']*100:.2f}% ({res['n_synergy']:,} pairs)")
    print("-" * 80)
    print(f"  {'Macro AUROC (OVR 3-cls)':<26}: {res['macro_auroc']:.4f}")
    print(f"  {'Macro AUPR (3-cls mean)':<26}: {res['macro_aupr']:.4f}")
    print(f"  {'Binary Synergy AUROC':<26}: {res['binary_synergy_auroc']:.4f}")
    print(f"  {'Binary Synergy AUPR':<26}: {res['binary_synergy_aupr']:.4f}")
    print("-" * 80)
    for k in [3, 5, 10]:
        print(f"  Precision@{k:<2}              : {res[f'precision@{k}']*100:6.2f}%"
              f"   | NDCG@{k:<2}: {res[f'ndcg@{k}']:.4f}")
    print("=" * 80)

    # Comparison table
    print("\n" + "=" * 96)
    print("  SynThera Benchmark Comparison Table")
    print("=" * 96)
    print(f"  {'Protocol':<22} {'Novelty Condition':<34} {'Macro AUROC':>12} {'Binary AUROC':>13} {'P@3':>8} {'NDCG@3':>8}")
    print("-" * 96)
    print(f"  {'Random/Warm':<22} {'observations randomly split':<34} {res['macro_auroc']:>12.4f} {res['binary_synergy_auroc']:>13.4f} {res['precision@3']*100:>7.2f}% {res['ndcg@3']:>8.4f}")
    print(f"  {'Pair-disjoint':<22} {'pair unseen':<34} {'0.6448':>12} {'0.5557':>13} {'44.73%':>8} {'0.4532':>8}")
    print(f"  {'LDO':<22} {'held-out drugs':<34} {'0.6542':>12} {'0.5662':>13} {'43.04%':>8} {'0.4426':>8}")
    print(f"  {'Strict bilateral':<22} {'both drugs unseen':<34} {'0.6225':>12} {'0.5373':>13} {'40.89%':>8} {'0.5665':>8}")
    print("=" * 96)
    if is_champion:
        print("\n  NOTE: Random/Warm row uses CHAMPION checkpoint (cold-drug trained).")
        print("  This is NOT a valid random-split test. Retrain with train_random_split.py.")
    else:
        print("\n  NOTE: Random/Warm row uses synergy_gnn_random_split_seed42.ckpt")
        print("  (trained on random_train.csv, evaluated on random_test.csv — CLEAN hold-out).")

    # ── Build payload ─────────────────────────────────────────────
    payload = {
        "split_name":              "random_warm",
        "checkpoint":              checkpoint_path,
        "checkpoint_basename":     os.path.basename(checkpoint_path),
        "is_champion_checkpoint":  is_champion,
        "leakage_warning":         is_champion,
        "leakage_note": (
            "Champion was trained on cold-drug split; random test overlaps with its training data. "
            "NOT a valid held-out random-split test."
            if is_champion else
            "Model trained on random_train.csv. Evaluation on random_test.csv is a clean hold-out."
        ),
        "device":                  device,
        "seed":                    seed,
        "split_metadata":          bench_meta,
        "metrics":                 res,
        "comparison_table": {
            "random_warm":      {
                "macro_auroc":            res["macro_auroc"],
                "binary_synergy_auroc":   res["binary_synergy_auroc"],
                "precision@3":            res["precision@3"],
                "ndcg@3":                 res["ndcg@3"],
            },
            "pair_disjoint":    {"macro_auroc": 0.6448, "binary_synergy_auroc": 0.5557, "precision@3": 0.4473, "ndcg@3": 0.4532},
            "leave_drug_out":   {"macro_auroc": 0.6542, "binary_synergy_auroc": 0.5662, "precision@3": 0.4304, "ndcg@3": 0.4426},
            "strict_bilateral": {"macro_auroc": 0.6225, "binary_synergy_auroc": 0.5373, "precision@3": 0.4089, "ndcg@3": 0.5665},
        },
    }

    if output_path:
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        print(f"\n  Results saved: {output_path}")

    return payload


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Evaluate SynThera on the random/warm observation split."
    )
    parser.add_argument(
        "--checkpoint",
        type=str,
        default=RANDOM_CKPT,
        help=f"Path to model checkpoint (default: {RANDOM_CKPT})",
    )
    parser.add_argument("--device", type=str, default=None,
                        help="Device (cuda/cpu). Default: auto-detect.")
    parser.add_argument("--seed",   type=int, default=42,
                        help="Inference random seed (default 42).")
    parser.add_argument("--output", type=str, default=None,
                        help="Output JSON path for machine-readable results.")
    args = parser.parse_args()

    run_random_eval(
        checkpoint_path=args.checkpoint,
        device=args.device,
        seed=args.seed,
        output_path=args.output,
    )
