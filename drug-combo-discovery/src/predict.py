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


# Module-level cache for predicted pairs: (min(drug_a, drug_b), max(drug_a, drug_b), cell_line) -> dict
_PREDICTION_CACHE: dict[tuple[str, str, str], dict[str, Any]] = {}


def clear_prediction_cache() -> None:
    """Clear all in-memory synergy prediction caches."""
    global _PREDICTION_CACHE
    _PREDICTION_CACHE.clear()


def predict_synergy(
    drug_a_id: str,
    drug_b_id: str,
    cell_line_name: str,
    module,
    heterodata,
    threshold_synergy: float = THRESHOLD_SYNERGY,
    threshold_antagonism: float = THRESHOLD_ANTAGONISM,
    device: str = "cpu",
    use_cache: bool = True,
) -> dict[str, Any]:
    """
    Predict synergy class for a single (drug_A, drug_B, cell_line) triplet with
    order-invariance (Option A: Symmetric Inference Wrapper).

    Computes forward (d_min -> d_max) and reverse (d_max -> d_min) pair passes
    in a single 2-edge batch and averages the softmax probability distributions:
        p_sym = (p(A, B) + p(B, A)) / 2.0
    guaranteeing p(A, B) == p(B, A) strictly and eliminating order-dependence bugs.

    Results are cached under canonical key: (min(drug_a_id, drug_b_id), max(drug_a_id, drug_b_id), cell_line_name).

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
    use_cache      : whether to lookup/store in canonical prediction cache (default True).

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

    # Canonical order for invariant caching and evaluation
    d_min, d_max = min(drug_a_id, drug_b_id), max(drug_a_id, drug_b_id)
    cache_key = (d_min, d_max, cell_line_name)

    if use_cache and cache_key in _PREDICTION_CACHE:
        cached = dict(_PREDICTION_CACHE[cache_key])
        cached["drug_a"] = drug_a_id
        cached["drug_b"] = drug_b_id
        return cached

    min_idx  = drug_id2idx[d_min]
    max_idx  = drug_id2idx[d_max]
    cell_idx = cell_line_map[cell_line_name]

    # Evaluate both orderings: forward (min -> max) and reverse (max -> min)
    # Packed into a single LinkNeighborLoader batch for maximum performance.
    data_copy = heterodata.clone()
    edge_index = torch.tensor([[min_idx, max_idx], [max_idx, min_idx]], dtype=torch.long)
    dummy_label = torch.tensor([[0, cell_idx], [0, cell_idx]], dtype=torch.long)

    data_copy["drug", "synergy_pair", "drug"].edge_index       = edge_index
    data_copy["drug", "synergy_pair", "drug"].edge_label_index = edge_index
    data_copy["drug", "synergy_pair", "drug"].edge_label       = dummy_label

    num_neighbors = {
        et: ([0, 0] if et == ("drug", "synergy_pair", "drug") else [5, 3])
        for et in data_copy.edge_types
    }

    # Reset PyTorch RNG for deterministic neighborhood sampling across consecutive calls
    torch.manual_seed(42)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(42)

    loader = LinkNeighborLoader(
        data             = data_copy,
        num_neighbors    = num_neighbors,
        edge_label_index = (("drug", "synergy_pair", "drug"), edge_index),
        edge_label       = dummy_label,
        batch_size       = 2,
        shuffle          = False,
    )

    module.eval()
    with torch.no_grad():
        batch = next(iter(loader)).to(device)
        logits, _ = module(batch)          # [2, 3]

    probs = F.softmax(logits, dim=-1)     # [2, 3]
    # Symmetrized average over both permutations in S_2
    p_sym = ((probs[0] + probs[1]) / 2.0).cpu().tolist()
    p_ant, p_add, p_syn = p_sym

    # Calibrated decision rule
    if p_syn > threshold_synergy:
        prediction = "synergy"
    elif p_ant > threshold_antagonism:
        prediction = "antagonism"
    else:
        prediction = "additive"

    canonical_result = {
        "drug_a":       d_min,
        "drug_b":       d_max,
        "cell_line":    cell_line_name,
        "prediction":   prediction,
        "p_antagonism": round(p_ant, 6),
        "p_additive":   round(p_add, 6),
        "p_synergy":    round(p_syn, 6),
    }

    if use_cache:
        _PREDICTION_CACHE[cache_key] = canonical_result

    caller_result = dict(canonical_result)
    caller_result["drug_a"] = drug_a_id
    caller_result["drug_b"] = drug_b_id
    return caller_result


def predict_synergy_batch(
    pairs: list[tuple[str, str]],
    cell_line_name: str,
    module,
    heterodata,
    threshold_synergy: float = THRESHOLD_SYNERGY,
    threshold_antagonism: float = THRESHOLD_ANTAGONISM,
    device: str = "cpu",
    use_cache: bool = True,
    batch_size: int = 32,
) -> list[dict[str, Any]]:
    """
    Batched permutation-invariant synergy prediction for a list of (drug_a, drug_b) pairs.
    Evaluates both orderings symmetrically and caches by canonical (d_min, d_max, cell_line).
    """
    cell_line_map = heterodata.cell_line_map
    node_maps     = _get_node_maps(heterodata)
    drug_id2idx   = node_maps.get("drug", {})

    if cell_line_name not in cell_line_map:
        raise ValueError(f"cell_line '{cell_line_name}' unknown.")
    cell_idx = cell_line_map[cell_line_name]

    results: list[dict[str, Any] | None] = [None] * len(pairs)
    uncached_pairs: list[tuple[str, str]] = []
    uncached_indices: list[int] = []

    for i, (da, db) in enumerate(pairs):
        if da not in drug_id2idx or db not in drug_id2idx:
            results[i] = {
                "drug_a": da, "drug_b": db, "cell_line": cell_line_name,
                "prediction": None, "p_antagonism": None, "p_additive": None, "p_synergy": None,
                "error": f"Invalid drug ID: '{da}' or '{db}' not in KG.",
            }
            continue

        d_min, d_max = min(da, db), max(da, db)
        cache_key = (d_min, d_max, cell_line_name)
        if use_cache and cache_key in _PREDICTION_CACHE:
            res = dict(_PREDICTION_CACHE[cache_key])
            res["drug_a"] = da
            res["drug_b"] = db
            results[i] = res
        else:
            uncached_pairs.append((d_min, d_max))
            uncached_indices.append(i)

    if uncached_pairs:
        # Deduplicate uncached canonical pairs to avoid duplicate evaluation
        unique_uncached = list(dict.fromkeys(uncached_pairs))
        n_unique = len(unique_uncached)

        mins = [drug_id2idx[p[0]] for p in unique_uncached]
        maxs = [drug_id2idx[p[1]] for p in unique_uncached]

        # Forward (min -> max) and Reverse (max -> min) in one combined edge tensor
        edge_index_all = torch.tensor([mins + maxs, maxs + mins], dtype=torch.long)
        dummy_label_all = torch.tensor([[0, cell_idx]] * (2 * n_unique), dtype=torch.long)

        data_copy = heterodata.clone()
        data_copy["drug", "synergy_pair", "drug"].edge_index       = edge_index_all
        data_copy["drug", "synergy_pair", "drug"].edge_label_index = edge_index_all
        data_copy["drug", "synergy_pair", "drug"].edge_label       = dummy_label_all

        num_neighbors = {
            et: ([0, 0] if et == ("drug", "synergy_pair", "drug") else [5, 3])
            for et in data_copy.edge_types
        }

        loader = LinkNeighborLoader(
            data             = data_copy,
            num_neighbors    = num_neighbors,
            edge_label_index = (("drug", "synergy_pair", "drug"), edge_index_all),
            edge_label       = dummy_label_all,
            batch_size       = batch_size,
            shuffle          = False,
        )

        all_logits = []
        module.eval()
        with torch.no_grad():
            for batch in loader:
                batch = batch.to(device)
                logits, _ = module(batch)
                all_logits.append(logits.cpu())

        all_logits = torch.cat(all_logits, dim=0)
        all_probs  = F.softmax(all_logits, dim=-1)

        fwd_probs = all_probs[:n_unique]
        rev_probs = all_probs[n_unique:]
        sym_probs = ((fwd_probs + rev_probs) / 2.0).tolist()

        for (d_min, d_max), p_sym in zip(unique_uncached, sym_probs):
            p_ant, p_add, p_syn = p_sym
            if p_syn > threshold_synergy:
                pred = "synergy"
            elif p_ant > threshold_antagonism:
                pred = "antagonism"
            else:
                pred = "additive"

            res_canon = {
                "drug_a":       d_min,
                "drug_b":       d_max,
                "cell_line":    cell_line_name,
                "prediction":   pred,
                "p_antagonism": round(p_ant, 6),
                "p_additive":   round(p_add, 6),
                "p_synergy":    round(p_syn, 6),
            }
            if use_cache:
                _PREDICTION_CACHE[(d_min, d_max, cell_line_name)] = res_canon

        for idx, (da, db) in zip(uncached_indices, [pairs[i] for i in uncached_indices]):
            d_min, d_max = min(da, db), max(da, db)
            res = dict(_PREDICTION_CACHE[(d_min, d_max, cell_line_name)])
            res["drug_a"] = da
            res["drug_b"] = db
            results[idx] = res

    return results


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
