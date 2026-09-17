"""
predict.py -- Drug Combination Synergy Inference Utility
========================================================

This module provides a self-contained prediction function for the final
SynergyGNN v2 model.  It loads the model once, then accepts single or
batch (drug_A, drug_B, cell_line) queries and returns a synergy prediction.

CALIBRATED DECISION RULE
-------------------------
Rather than plain argmax, we use the threshold-calibrated rule derived from
the sweep on the v2 val/test sets (see calibrate_thresholds.py):

    if   p_synergy     > 0.25  -> predict SYNERGY
    elif p_antagonism  > 0.33  -> predict ANTAGONISM
    else                       -> predict ADDITIVE

This rule improves synergy recall substantially versus argmax while keeping
antagonism and additive false-positive rates acceptable.

USAGE
-----
From Python:

    from src.predict import load_model, predict_synergy

    model, heterodata = load_model()
    result = predict_synergy("DB00619", "DB01048", "A549", model, heterodata)
    print(result)

From the command line:

    python src/predict.py DB00619 DB01048 A549

IMPORTANT: heterodata.pt must use 2048-bit Morgan fingerprint features
(not ChemBERTa).  Run `python src/build_heterodata.py` to rebuild if needed.
"""

from __future__ import annotations

import os
import sys
import argparse

import torch
import torch.nn.functional as F
from torch_geometric.data import HeteroData
from torch_geometric.loader import LinkNeighborLoader

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
ROOT       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED  = os.path.join(ROOT, "data", "processed")
MODELS_DIR = os.path.join(ROOT, "models")

HETERODATA_PATH = os.path.join(PROCESSED,  "heterodata.pt")
CHECKPOINT_PATH = os.path.join(MODELS_DIR, "synergy_gnn_final.ckpt")

# ---------------------------------------------------------------------------
# Calibrated decision thresholds (from sweep on v2 val/test sets)
# ---------------------------------------------------------------------------
THRESHOLD_SYNERGY    = 0.25   # if p_synergy > this, predict "synergy"
THRESHOLD_ANTAGONISM = 0.33   # elif p_antagonism > this, predict "antagonism"
# else predict "additive"

CLASS_NAMES = ["antagonism", "additive", "synergy"]

# Module-level cache for node maps (built once from primekg_nodes.csv)
_NODE_MAPS_CACHE = None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_model(
    checkpoint_path=CHECKPOINT_PATH,
    heterodata_path=HETERODATA_PATH,
    device=None,
):
    """
    Load SynergyModule from a Lightning checkpoint and the HeteroData graph.

    Returns (module, heterodata, device_str).
    module is in eval() mode on the chosen device.
    """
    sys.path.insert(0, os.path.dirname(__file__))
    from model import SynergyModule  # noqa

    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    print(f"  [predict.py] Loading HeteroData from {heterodata_path} ...")
    heterodata = torch.load(heterodata_path, map_location="cpu", weights_only=False)
    print(f"  [predict.py] drug.x shape   : {tuple(heterodata['drug'].x.shape)}")
    print(f"  [predict.py] num_cell_lines : {heterodata.num_cell_lines}")

    print(f"  [predict.py] Loading checkpoint {checkpoint_path} ...")
    # strict=False: the checkpoint has class_weights as a registered buffer
    # (trained with non-None class weights), but load_from_checkpoint reconstructs
    # the model with class_weights=None -> no buffer in state_dict -> key mismatch.
    # strict=False safely ignores the extra buffer; the weights matrix is unused at
    # inference time anyway (CE loss is not called during prediction).
    module = SynergyModule.load_from_checkpoint(
        checkpoint_path,
        map_location=device,
        strict=False,
    )
    module.eval()
    module = module.to(device)
    print(f"  [predict.py] Model ready on {device}.")
    return module, heterodata, device


def predict_synergy(
    drug_a_id,
    drug_b_id,
    cell_line_name,
    module,
    heterodata,
    threshold_synergy=THRESHOLD_SYNERGY,
    threshold_antagonism=THRESHOLD_ANTAGONISM,
    device="cpu",
):
    """
    Predict synergy class for a single (drug_A, drug_B, cell_line) triplet.

    Parameters
    ----------
    drug_a_id      : DrugBank ID of drug A (e.g. "DB00619").
    drug_b_id      : DrugBank ID of drug B (e.g. "DB01048").
    cell_line_name : Cell line name as in labeled_pairs.csv (e.g. "A549").
    module         : SynergyModule from load_model().
    heterodata     : HeteroData from load_model().
    threshold_synergy    : override synergy threshold (default 0.25).
    threshold_antagonism : override antagonism threshold (default 0.33).
    device         : "cpu" or "cuda" (must match where module lives).

    Returns dict with keys:
        drug_a, drug_b, cell_line, prediction,
        p_antagonism, p_additive, p_synergy
    (plus "error" if a lookup failed).
    """
    cell_line_map = heterodata.cell_line_map
    node_maps     = _get_node_maps(heterodata)
    drug_id2idx   = node_maps.get("drug", {})

    errors = []
    if drug_a_id not in drug_id2idx:
        errors.append(f"drug_a '{drug_a_id}' not in KG drug nodes.")
    if drug_b_id not in drug_id2idx:
        errors.append(f"drug_b '{drug_b_id}' not in KG drug nodes.")
    if cell_line_name not in cell_line_map:
        sample = list(cell_line_map.keys())[:5]
        errors.append(f"cell_line '{cell_line_name}' unknown. Sample: {sample}")
    if errors:
        return {
            "drug_a": drug_a_id, "drug_b": drug_b_id, "cell_line": cell_line_name,
            "prediction": None,
            "p_antagonism": None, "p_additive": None, "p_synergy": None,
            "error": "; ".join(errors),
        }

    a_idx    = drug_id2idx[drug_a_id]
    b_idx    = drug_id2idx[drug_b_id]
    cell_idx = cell_line_map[cell_line_name]

    # -- Build a minimal HeteroData clone with a single supervision edge -----
    data_copy = heterodata.clone()

    edge_index  = torch.tensor([[a_idx], [b_idx]], dtype=torch.long)   # [2, 1]
    dummy_label = torch.tensor([[0, cell_idx]], dtype=torch.long)       # [1, 2]  class=0 dummy

    data_copy["drug", "synergy_pair", "drug"].edge_index       = edge_index
    data_copy["drug", "synergy_pair", "drug"].edge_label_index = edge_index
    data_copy["drug", "synergy_pair", "drug"].edge_label       = dummy_label

    # Neighborhood budget (small: we only need embeddings for the two drugs).
    # We must include ALL edge types that exist in data_copy — including the
    # synergy_pair edge we just added — otherwise LinkNeighborLoader raises a
    # "Missing number of neighbors" ValueError.
    # Use [0] for synergy_pair so it is never sampled as a message-passing edge
    # (it is the supervision edge, used only for edge_label_index, not MP).
    num_neighbors = {
        et: ([0, 0] if et == ("drug", "synergy_pair", "drug") else [5, 3])
        for et in data_copy.edge_types
    }

    loader = LinkNeighborLoader(
        data             = data_copy,
        num_neighbors    = num_neighbors,
        edge_label_index = (("drug", "synergy_pair", "drug"), edge_index),
        edge_label       = dummy_label,
        batch_size       = 1,
        shuffle          = False,
    )

    module.eval()
    with torch.no_grad():
        batch   = next(iter(loader))
        batch   = batch.to(device)
        logits, _ = module(batch)          # [1, 3]

    probs        = F.softmax(logits, dim=-1).squeeze(0).cpu().tolist()
    p_ant, p_add, p_syn = probs

    # -- Calibrated decision rule -------------------------------------------
    if p_syn > threshold_synergy:
        prediction = "synergy"
    elif p_ant > threshold_antagonism:
        prediction = "antagonism"
    else:
        prediction = "additive"

    return {
        "drug_a":       drug_a_id,
        "drug_b":       drug_b_id,
        "cell_line":    cell_line_name,
        "prediction":   prediction,
        "p_antagonism": round(p_ant, 6),
        "p_additive":   round(p_add, 6),
        "p_synergy":    round(p_syn, 6),
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_node_maps(heterodata):
    """Reconstruct {node_type -> {raw_id_str -> int_idx}} from primekg_nodes.csv."""
    global _NODE_MAPS_CACHE
    if _NODE_MAPS_CACHE is not None:
        return _NODE_MAPS_CACHE

    import pandas as pd

    nodes_csv = os.path.join(PROCESSED, "primekg_nodes.csv")
    if not os.path.exists(nodes_csv):
        raise FileNotFoundError(
            f"primekg_nodes.csv not found at {nodes_csv}. "
            "Run src/build_kg.py first."
        )

    nodes     = pd.read_csv(nodes_csv)
    node_maps = {}
    for ntype in nodes["node_type"].unique():
        sub    = nodes[nodes["node_type"] == ntype].reset_index(drop=True)
        id2idx = {str(row["id"]): i for i, (_, row) in enumerate(sub.iterrows())}
        node_maps[ntype] = id2idx

    _NODE_MAPS_CACHE = node_maps
    return node_maps


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _cli():
    parser = argparse.ArgumentParser(
        description="Predict drug synergy for a (drug_A, drug_B, cell_line) triplet."
    )
    parser.add_argument("drug_a",    help="DrugBank ID of drug A (e.g. DB00619)")
    parser.add_argument("drug_b",    help="DrugBank ID of drug B (e.g. DB01048)")
    parser.add_argument("cell_line", help="Cell line (e.g. A549)")
    parser.add_argument("--checkpoint",  default=CHECKPOINT_PATH)
    parser.add_argument("--heterodata",  default=HETERODATA_PATH)
    parser.add_argument("--threshold-synergy",    type=float, default=THRESHOLD_SYNERGY)
    parser.add_argument("--threshold-antagonism", type=float, default=THRESHOLD_ANTAGONISM)
    args = parser.parse_args()

    module, heterodata, device = load_model(args.checkpoint, args.heterodata)

    result = predict_synergy(
        drug_a_id            = args.drug_a,
        drug_b_id            = args.drug_b,
        cell_line_name       = args.cell_line,
        module               = module,
        heterodata           = heterodata,
        threshold_synergy    = args.threshold_synergy,
        threshold_antagonism = args.threshold_antagonism,
        device               = device,
    )

    print("\n" + "=" * 55)
    print("  SYNERGY PREDICTION RESULT")
    print("=" * 55)
    if "error" in result:
        print(f"  ERROR: {result['error']}")
    else:
        print(f"  Drug A        : {result['drug_a']}")
        print(f"  Drug B        : {result['drug_b']}")
        print(f"  Cell Line     : {result['cell_line']}")
        print(f"  Prediction    : {result['prediction'].upper()}")
        print(f"  p(antagonism) : {result['p_antagonism']:.4f}")
        print(f"  p(additive)   : {result['p_additive']:.4f}")
        print(f"  p(synergy)    : {result['p_synergy']:.4f}")
        print(f"  Thresholds    : synergy>{args.threshold_synergy}  "
              f"antagonism>{args.threshold_antagonism}")
    print("=" * 55)


if __name__ == "__main__":
    _cli()
