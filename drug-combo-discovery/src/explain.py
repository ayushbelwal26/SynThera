"""
explain.py — Interpretable Explanations for Drug-Combination Synergy Predictions
==================================================================================

WHY NOT PyG GNNExplainer / AttentionExplainer?
-----------------------------------------------
PyG's built-in Explainer wrapper expects a model with a standard
``forward(x, edge_index)`` signature, but SynergyGNN takes a single
`HeteroData` batch object and returns ``(logits, labels)``.  Wrapping it to
match the explainer API would require dismantling the batch object, losing the
fallback-lookup routing and cell-line embedding — effectively rewriting half
the model.

APPROACH USED: Input-Gradient Edge Importance
----------------------------------------------
For each KG edge in the local sampled subgraph we compute a scalar importance
score as:

    importance(e) = ||grad_{x_src} p_predicted_class||_2

More concretely:
  1. Sample a local subgraph for the (drug_A, drug_B, cell_line) query via
     LinkNeighborLoader (same as predict.py does).
  2. Set requires_grad=True on the drug FP feature matrix.
  3. Run forward pass to get softmax probabilities.
  4. Backprop the predicted-class probability to drug feature tensors.
  5. For each KG edge (u -> v), score it by the L2 norm of the gradient at
     the source node.  Edges rooted at highly-influential source nodes get
     high scores.
  6. Sort, take top-10; resolve node IDs to human-readable names using
     primekg_nodes.csv.

FAITHFULNESS CHECK
------------------
After identifying the top-K edges, we remove those edges from the local
subgraph and re-run the forward pass.  The drop in predicted-class probability
(as a % of the original) is the faithfulness delta.

TEMPLATE-BASED NL EXPLANATION
------------------------------
We inspect the top-10 edges for three patterns and generate a single English
sentence.  If no pattern matches cleanly we fall back to a generic sentence.
"""

from __future__ import annotations

import os
import sys
import json
import copy
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

import torch
import torch.nn.functional as F
from torch_geometric.loader import NeighborLoader
from torch_geometric.data import Batch

# In-memory explanation cache: (d_min, d_max, cell_line, top_k, run_faithfulness, run_literature, disease_context) -> result dict
_EXPLANATION_CACHE: dict[tuple, dict[str, Any]] = {}


def clear_explanation_cache() -> None:
    """Clear the in-memory cache of computed explanations."""
    global _EXPLANATION_CACHE
    _EXPLANATION_CACHE.clear()

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
ROOT       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED  = os.path.join(ROOT, "data", "processed")
MODELS_DIR = os.path.join(ROOT, "models")
sys.path.insert(0, os.path.join(ROOT, "src"))

from predict import load_model, _get_node_maps, THRESHOLD_SYNERGY, THRESHOLD_ANTAGONISM
from literature import get_literature_for_explanation

HETERODATA_PATH = os.path.join(PROCESSED, "heterodata.pt")
CHECKPOINT_PATH = os.path.join(MODELS_DIR, "synergy_gnn_final.ckpt")

CLASS_NAMES = ["antagonism", "additive", "synergy"]

# Relations included in edge-importance scoring
EXPLAIN_RELATIONS = {
    "drug_protein",
    "indication",
    "off-label use",
    "contraindication",
    "disease_protein",
    "pathway_protein",
    "protein_protein",
    "disease_disease",
}

# ---------------------------------------------------------------------------
# Node-name resolver
# ---------------------------------------------------------------------------

_NAME_LOOKUP = None
_ID_LOOKUP   = None


def _build_name_lookups(heterodata):
    global _NAME_LOOKUP, _ID_LOOKUP
    if _NAME_LOOKUP is not None:
        return _NAME_LOOKUP, _ID_LOOKUP

    import pandas as pd

    nodes_csv = os.path.join(PROCESSED, "primekg_nodes.csv")
    nodes = pd.read_csv(nodes_csv)

    name_lookup = {}
    id_lookup   = {}

    for ntype in nodes["node_type"].unique():
        sub = nodes[nodes["node_type"] == ntype].reset_index(drop=True)
        name_lookup[ntype] = {i: str(row["name"]) for i, (_, row) in enumerate(sub.iterrows())}
        id_lookup[ntype]   = {i: str(row["id"])   for i, (_, row) in enumerate(sub.iterrows())}

    _NAME_LOOKUP = name_lookup
    _ID_LOOKUP   = id_lookup
    return _NAME_LOOKUP, _ID_LOOKUP


def _resolve_name(ntype, idx, name_lookup):
    return name_lookup.get(ntype, {}).get(idx, f"{ntype}#{idx}")


# ---------------------------------------------------------------------------
# Subgraph sampler
# ---------------------------------------------------------------------------

def _sample_batch(heterodata, a_idx, b_idx, cell_idx):
    """
    Sample a compact local 2-hop HeteroData subgraph around drugs a_idx and b_idx
    using NeighborLoader directly on the shared HeteroData (without cloning).
    Avoids duplicating the full HeteroData in RAM, eliminating container OOMs.
    Canonicalizes input nodes and adds both forward and reverse supervision edges
    for permutation-invariant gradient backpropagation and ablation.
    """
    min_idx, max_idx = min(a_idx, b_idx), max(a_idx, b_idx)
    num_neighbors = {et: [5, 3] for et in heterodata.edge_types}
    input_nodes = ("drug", torch.tensor([min_idx, max_idx], dtype=torch.long))

    loader = NeighborLoader(
        data=heterodata,
        num_neighbors=num_neighbors,
        input_nodes=input_nodes,
        batch_size=2,
        shuffle=False,
    )
    batch = next(iter(loader))

    # Identify batch-local indices of the two target drugs
    local_min = (batch["drug"].n_id == min_idx).nonzero(as_tuple=True)[0][0].item()
    local_max = (batch["drug"].n_id == max_idx).nonzero(as_tuple=True)[0][0].item()

    # Forward (min -> max) and Reverse (max -> min) supervision edges for symmetric evaluation
    edge_index = torch.tensor([[local_min, local_max], [local_max, local_min]], dtype=torch.long)
    dummy_label = torch.tensor([[0, cell_idx], [0, cell_idx]], dtype=torch.long)

    batch["drug", "synergy_pair", "drug"].edge_index = edge_index
    batch["drug", "synergy_pair", "drug"].edge_label_index = edge_index
    batch["drug", "synergy_pair", "drug"].edge_label = dummy_label

    return batch


# ---------------------------------------------------------------------------
# Edge importance scorer
# ---------------------------------------------------------------------------

def _score_edges(
    batch,
    name_lookup_or_grad=None,
    top_k: int = 10,
    module: Any = None,
    pred_idx: int = 2,
    original_prob: float | None = None,
    device: str = "cpu",
    chunk_size: int = 64,
    name_lookup: dict | None = None,
    grad_norms: dict | None = None,
):
    """
    Score KG edges in the local subgraph using direct leave-one-out perturbation scoring
    (Option 4), with fallback to gradient saliency if module is not provided.

    Leave-One-Out Perturbation Importance (Option 4):
      importance(e) = p_original - p_ablated_without_e
    Measures the direct drop in the predicted class probability when edge e is
    removed from the subgraph. Batch-evaluated in chunks via Batch.from_data_list
    for high computational throughput.
    """
    # Disambiguate positional arguments for backwards compatibility
    if module is None:
        if name_lookup_or_grad is not None and (hasattr(name_lookup_or_grad, "forward") or hasattr(name_lookup_or_grad, "eval")):
            module = name_lookup_or_grad
    if name_lookup is None:
        if isinstance(name_lookup_or_grad, dict) and not ("drug" in name_lookup_or_grad and isinstance(name_lookup_or_grad["drug"], torch.Tensor)):
            name_lookup = name_lookup_or_grad
    if grad_norms is None:
        if isinstance(name_lookup_or_grad, dict) and ("drug" in name_lookup_or_grad and isinstance(name_lookup_or_grad["drug"], torch.Tensor)):
            grad_norms = name_lookup_or_grad

    # Build local->global index maps for each node type present in this batch
    n_id_map: dict[str, torch.Tensor] = {}
    for ntype in batch.node_types:
        store = batch[ntype]
        if hasattr(store, "n_id") and store.n_id is not None:
            n_id_map[ntype] = store.n_id.cpu()

    seen: set[tuple] = set()   # deduplicate (src_global, rel, dst_global)
    candidate_edges = []

    for etype in batch.edge_types:
        src_type, rel, dst_type = etype
        if rel not in EXPLAIN_RELATIONS:
            continue
        store = batch[etype]
        if not hasattr(store, "edge_index") or store.edge_index is None:
            continue
        ei = store.edge_index
        if ei.shape[1] == 0:
            continue

        src_n_id = n_id_map.get(src_type)
        dst_n_id = n_id_map.get(dst_type)

        for k in range(ei.shape[1]):
            src_local = ei[0, k].item()
            dst_local = ei[1, k].item()

            # Map to global indices for name resolution
            src_global = src_n_id[src_local].item() if src_n_id is not None else src_local
            dst_global = dst_n_id[dst_local].item() if dst_n_id is not None else dst_local

            dedup_key = (src_global, rel, dst_global)
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            # Resolve human-readable names using global indices
            src_name = _resolve_name(src_type, src_global, name_lookup)
            dst_name = _resolve_name(dst_type, dst_global, name_lookup)

            candidate_edges.append({
                "etype":         etype,
                "source_type":   src_type,
                "source_local":  src_local,   # kept for faithfulness mask
                "source_global": src_global,
                "source":        src_name,
                "relation":      rel,
                "target_type":   dst_type,
                "target_local":  dst_local,
                "target_global": dst_global,
                "target":        dst_name,
                "importance":    0.01,
            })

    if len(candidate_edges) == 0:
        return [], []

    # 1. Leave-One-Out Perturbation Scoring (Option 4)
    if module is not None:
        module.eval()
        with torch.no_grad():
            if original_prob is None:
                batch_dev = batch.to(device)
                logits_base, _ = module(batch_dev)
                probs_base = F.softmax(logits_base, dim=-1)
                if probs_base.dim() == 2 and probs_base.shape[0] >= 2:
                    p_orig = ((probs_base[0, pred_idx] + probs_base[1, pred_idx]) / 2.0).item()
                else:
                    p_orig = probs_base.squeeze(0)[pred_idx].item()
            else:
                p_orig = float(original_prob)

            scores = []
            for i in range(0, len(candidate_edges), chunk_size):
                chunk = candidate_edges[i : i + chunk_size]
                data_list = []
                for edge_info in chunk:
                    variant = batch.clone()
                    etype = edge_info["etype"]
                    src_l = edge_info["source_local"]
                    dst_l = edge_info["target_local"]
                    ei = variant[etype].edge_index
                    mask = ~((ei[0] == src_l) & (ei[1] == dst_l))
                    variant[etype].edge_index = ei[:, mask]
                    data_list.append(variant)

                batched_data = Batch.from_data_list(data_list).to(device)
                logits_abl, _ = module(batched_data)
                probs_abl = F.softmax(logits_abl, dim=-1)
                # Each variant has 2 supervision pairs (forward and reverse ordering)
                p_abl = (probs_abl[0::2, pred_idx] + probs_abl[1::2, pred_idx]) / 2.0
                drop = (p_orig - p_abl).cpu().tolist()
                scores.extend(drop)

        for edge_info, score in zip(candidate_edges, scores):
            edge_info["importance"] = float(score)

    elif grad_norms is not None:
        # Fallback to gradient saliency if module is not provided
        src_norms = grad_norms.get("drug")
        for edge_info in candidate_edges:
            src_t = edge_info["source_type"]
            dst_t = edge_info["target_type"]
            src_l = edge_info["source_local"]
            dst_l = edge_info["target_local"]
            imp_val = 0.01
            if src_t == "drug" and src_norms is not None and src_l < len(src_norms):
                imp_val = max(imp_val, src_norms[src_l].item())
            if dst_t == "drug" and src_norms is not None and dst_l < len(src_norms):
                imp_val = max(imp_val, src_norms[dst_l].item())
            edge_info["importance"] = imp_val

    candidate_edges.sort(key=lambda e: e["importance"], reverse=True)
    return candidate_edges[:top_k], candidate_edges



# ---------------------------------------------------------------------------
# Template-based NL explanation
# ---------------------------------------------------------------------------

def _extract_drug_mechanism(drug_name, edges):
    """
    Find the highest-importance target (drug_protein) and indication (indication/off-label use)
    for this specific drug among its own edges.
    """
    targets = []       # (importance, target_name)
    indications = []   # (importance, disease_name)

    d_lower = drug_name.lower()

    for e in edges:
        rel = e["relation"]
        src = e["source"]
        tgt = e["target"]
        imp = e["importance"]

        is_src = (src.lower() == d_lower)
        is_tgt = (tgt.lower() == d_lower)

        if not (is_src or is_tgt):
            continue

        if rel == "drug_protein":
            partner = tgt if is_src else src
            targets.append((imp, partner))
        elif rel in ("indication", "off-label use"):
            partner = tgt if is_src else src
            indications.append((imp, partner))

    # Sort descending by importance
    targets.sort(key=lambda x: x[0], reverse=True)
    indications.sort(key=lambda x: x[0], reverse=True)

    top_target = targets[0][1] if targets else None
    top_disease = indications[0][1] if indications else None
    return top_target, top_disease


def _format_drug_clause(drug_name, top_target, top_disease):
    """
    Format the clause describing a single drug's primary mechanism.
    - If target and disease are available:
        '{drug_name} primarily acts on {top_target}, indicated for {top_disease}'
    - If only target is available:
        '{drug_name} primarily acts on {top_target}'
    - If only disease is available:
        '{drug_name} is indicated for {top_disease}'
    """
    if top_target and top_disease:
        return f"{drug_name} primarily acts on {top_target}, indicated for {top_disease}"
    elif top_target:
        return f"{drug_name} primarily acts on {top_target}"
    elif top_disease:
        return f"{drug_name} is indicated for {top_disease}"
    return None


def _get_class_suffix(predicted_class):
    cls = str(predicted_class).lower()
    if cls == "synergy":
        return "suggesting a complementary mechanism that may explain the predicted synergy."
    elif cls == "antagonism":
        return "though the model predicts antagonism, possibly due to competing or conflicting effects at this shared point in the network."
    elif cls == "additive":
        return "consistent with the model's prediction of an additive, non-synergistic interaction."
    return "reflecting their joint biological connections in the network."


def _generate_explanation(drug_a_name, drug_b_name, top_edges, all_edges=None, predicted_class="synergy"):
    drug_a_targets   = set()
    drug_b_targets   = set()
    protein_pathways = defaultdict(set)
    drug_a_diseases  = set()
    drug_b_diseases  = set()

    edges_for_exact = all_edges if all_edges is not None else top_edges

    for edge in edges_for_exact:
        src   = edge["source"]
        rel   = edge["relation"]
        tgt   = edge["target"]
        stype = edge.get("source_type", "")

        is_a_src = (src.lower() == drug_a_name.lower())
        is_b_src = (src.lower() == drug_b_name.lower())
        is_a_tgt = (tgt.lower() == drug_a_name.lower())
        is_b_tgt = (tgt.lower() == drug_b_name.lower())

        if rel == "drug_protein":
            if is_a_src:
                drug_a_targets.add(tgt)
            elif is_b_src:
                drug_b_targets.add(tgt)
            elif is_a_tgt:
                drug_a_targets.add(src)
            elif is_b_tgt:
                drug_b_targets.add(src)

        elif rel == "pathway_protein":
            if stype == "pathway":
                protein_pathways[tgt].add(src)
            else:
                protein_pathways[src].add(tgt)

        elif rel in ("indication", "off-label use"):
            if is_a_src:
                drug_a_diseases.add(tgt)
            elif is_b_src:
                drug_b_diseases.add(tgt)
            elif is_a_tgt:
                drug_a_diseases.add(src)
            elif is_b_tgt:
                drug_b_diseases.add(src)

    cls_suffix = _get_class_suffix(predicted_class)

    # Pattern 1: Shared protein target
    shared_targets = drug_a_targets & drug_b_targets
    if shared_targets:
        protein = next(iter(shared_targets))
        return (
            f"{drug_a_name} and {drug_b_name} both interact with {protein}, "
            f"{cls_suffix}"
        )

    # Pattern 2: Shared pathway via different proteins
    if drug_a_targets and drug_b_targets:
        for pa in drug_a_targets:
            for pb in drug_b_targets:
                shared_pws = protein_pathways.get(pa, set()) & protein_pathways.get(pb, set())
                if shared_pws:
                    pw = next(iter(shared_pws))
                    return (
                        f"{drug_a_name} affects {pa} and {drug_b_name} affects {pb}, "
                        f"both part of the {pw} pathway, {cls_suffix}"
                    )

    # Pattern 3: Shared disease indication
    shared_diseases = drug_a_diseases & drug_b_diseases
    if shared_diseases:
        disease = next(iter(shared_diseases))
        return (
            f"{drug_a_name} and {drug_b_name} are both indicated for {disease}, "
            f"{cls_suffix}"
        )

    # Pattern 4: Per-drug target / indication mechanism (independent actions)
    # Separately report each drug's single most important target/indication from its
    # own edges, even if they don't directly overlap in the knowledge graph.
    edges_for_mechanism = all_edges if all_edges is not None else top_edges
    target_a, disease_a = _extract_drug_mechanism(drug_a_name, edges_for_mechanism)
    target_b, disease_b = _extract_drug_mechanism(drug_b_name, edges_for_mechanism)

    clause_a = _format_drug_clause(drug_a_name, target_a, disease_a)
    clause_b = _format_drug_clause(drug_b_name, target_b, disease_b)

    if clause_a and clause_b:
        cls_lower = str(predicted_class).lower()
        if cls_lower == "synergy":
            tail = (
                "their combined network-level activity suggests a complementary "
                "mechanism that may explain the predicted synergy."
            )
        elif cls_lower == "antagonism":
            tail = (
                "the model predicts antagonism, possibly due to competing or "
                "conflicting effects across the network."
            )
        elif cls_lower == "additive":
            tail = (
                "their independent actions are consistent with the model's "
                "prediction of an additive, non-synergistic interaction."
            )
        else:
            tail = "the model's prediction reflects their combined network-level effects."

        return (
            f"{clause_a}, while {clause_b}. Although these mechanisms don't directly "
            f"overlap in the knowledge graph, {tail}"
        )

    # Pattern 5: Generic fallback (only if one or both drugs lack meaningful edges)
    cls_lower = str(predicted_class).lower()
    if cls_lower == "synergy":
        return (
            f"The model predicts synergy based on distributed connections in the biological "
            f"network between {drug_a_name} and {drug_b_name}, though no single clear "
            f"mechanism dominates in the local subgraph."
        )
    elif cls_lower == "antagonism":
        return (
            f"The model predicts antagonism based on distributed connections in the biological "
            f"network between {drug_a_name} and {drug_b_name}, though no single clear "
            f"mechanism dominates in the local subgraph."
        )
    elif cls_lower == "additive":
        return (
            f"The model predicts an additive interaction based on distributed connections in the biological "
            f"network between {drug_a_name} and {drug_b_name}, though no single clear "
            f"mechanism dominates in the local subgraph."
        )
    return (
        f"The model's prediction is based on shared connections in the biological "
        f"network between {drug_a_name} and {drug_b_name}, though no single clear "
        f"mechanism dominates in the local subgraph."
    )


# ---------------------------------------------------------------------------
# Faithfulness checks — necessity and sufficiency
# ---------------------------------------------------------------------------

def _necessity_check(
    module,
    batch,
    top_edges,
    predicted_class,
    original_prob,
    device,
    threshold_synergy=THRESHOLD_SYNERGY,
    threshold_antagonism=THRESHOLD_ANTAGONISM,
):
    """
    NECESSITY: Remove the top-K explanation edges from the full subgraph and
    rerun inference.  A large probability drop means those edges were necessary
    for the prediction.  GNNs are robust to edge removal in dense molecular graphs,
    so this probability drop (delta_pct) is often small — which is expected and
    scientifically documented.

    Formula:
        necessity_delta_pct = ((original_prob - ablated_score) / original_prob) * 100

    Returns:
        (delta_pct, ablated_score, ablated_class)
    """
    batch_pruned = batch.clone().to(device)

    # Build removal sets keyed by etype -> {(src_local, dst_local)}
    edges_to_remove: dict = defaultdict(set)
    for edge in top_edges:
        rel      = edge["relation"]
        src_type = edge["source_type"]
        dst_type = edge["target_type"]
        etype    = (src_type, rel, dst_type)
        edges_to_remove[etype].add((edge["source_local"], edge["target_local"]))

    for etype, pairs in edges_to_remove.items():
        if etype not in batch_pruned.edge_types:
            continue
        store = batch_pruned[etype]
        if not hasattr(store, "edge_index") or store.edge_index is None:
            continue
        ei = store.edge_index
        keep_mask = torch.ones(ei.shape[1], dtype=torch.bool)
        for k in range(ei.shape[1]):
            if (ei[0, k].item(), ei[1, k].item()) in pairs:
                keep_mask[k] = False
        store.edge_index = ei[:, keep_mask]

    module.eval()
    with torch.no_grad():
        logits_pruned, _ = module(batch_pruned)
        probs_raw = F.softmax(logits_pruned, dim=-1).cpu()
        if probs_raw.dim() == 2 and probs_raw.shape[0] >= 2:
            probs_pruned = (probs_raw[0] + probs_raw[1]) / 2.0
        elif probs_raw.dim() == 2:
            probs_pruned = probs_raw[0]
        else:
            probs_pruned = probs_raw

    ablated_score = probs_pruned[predicted_class].item()
    p_ant_pruned, p_add_pruned, p_syn_pruned = probs_pruned.tolist()
    if p_syn_pruned > threshold_synergy:
        ablated_class = "synergy"
    elif p_ant_pruned > threshold_antagonism:
        ablated_class = "antagonism"
    else:
        ablated_class = "additive"

    delta_pct = round((original_prob - ablated_score) / max(original_prob, 1e-9) * 100, 2)
    return delta_pct, ablated_score, ablated_class


def _sufficiency_check(
    module,
    batch,
    top_edges,
    predicted_class,
    original_prob,
    device,
    threshold_synergy=THRESHOLD_SYNERGY,
    threshold_antagonism=THRESHOLD_ANTAGONISM,
):
    """
    SUFFICIENCY: Build a heavily pruned subgraph that keeps ONLY the top-K
    explanation edges (all other message-passing edges are removed; all nodes
    are retained so the pair-scorer MLP can still run).

    Formula:
        sufficiency_pct = (new_prob / original_prob) * 100

    Re-run inference on this minimal subgraph and report:
      - sufficiency_retained_pct : new_prob / original_prob * 100
        (100% = top-K edges alone are sufficient to recover the full prediction;
         50% = they carry half the signal)
      - sufficiency_class_preserved : bool — does the calibrated prediction
        on the isolated subgraph match the original predicted class?
      - new_prob : float — raw predicted-class probability on isolated subgraph

    This is the decisive faithfulness metric: if 10 edges out of thousands
    can reproduce most of the model's confidence, those edges really are load-bearing.
    """
    batch_suf = batch.clone().to(device)

    # Build keep sets keyed by etype -> {(src_local, dst_local)}
    edges_to_keep: dict[tuple, set] = defaultdict(set)
    for edge in top_edges:
        rel      = edge["relation"]
        src_type = edge["source_type"]
        dst_type = edge["target_type"]
        etype    = (src_type, rel, dst_type)
        edges_to_keep[etype].add((edge["source_local"], edge["target_local"]))

    # Mask ALL message-passing edges except those in top_edges.
    # The supervision edge (synergy_pair) is never a message-passing edge so
    # leave it untouched — removing it would break the pair scorer.
    for etype in batch_suf.edge_types:
        src_type, rel, dst_type = etype
        if rel == "synergy_pair":
            continue   # supervision edge — keep
        store = batch_suf[etype]
        if not hasattr(store, "edge_index") or store.edge_index is None:
            continue
        ei = store.edge_index
        if ei.shape[1] == 0:
            continue

        keep_pairs = edges_to_keep.get(etype, set())
        if keep_pairs:
            # Keep only the explanation edges for this etype
            keep_mask = torch.zeros(ei.shape[1], dtype=torch.bool)
            for k in range(ei.shape[1]):
                if (ei[0, k].item(), ei[1, k].item()) in keep_pairs:
                    keep_mask[k] = True
            store.edge_index = ei[:, keep_mask]
        else:
            # This edge type has no explanation edges — zero it out entirely
            store.edge_index = ei[:, :0]   # empty [2, 0] tensor

    module.eval()
    with torch.no_grad():
        logits_suf, _ = module(batch_suf)
        probs_raw = F.softmax(logits_suf, dim=-1).cpu()
        if probs_raw.dim() == 2 and probs_raw.shape[0] >= 2:
            probs_suf = (probs_raw[0] + probs_raw[1]) / 2.0
        elif probs_raw.dim() == 2:
            probs_suf = probs_raw[0]
        else:
            probs_suf = probs_raw

    new_prob = probs_suf[predicted_class].item()
    p_ant_suf, p_add_suf, p_syn_suf = probs_suf.tolist()
    if p_syn_suf > threshold_synergy:
        suf_class_name = "synergy"
    elif p_ant_suf > threshold_antagonism:
        suf_class_name = "antagonism"
    else:
        suf_class_name = "additive"

    predicted_class_name = CLASS_NAMES[predicted_class]

    # % of original probability retained by the top-K edge subgraph
    retained_pct = round(new_prob / max(original_prob, 1e-9) * 100, 2)

    # Does the calibrated class match the original predicted class?
    class_preserved = (suf_class_name == predicted_class_name)

    return retained_pct, class_preserved, new_prob


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------

def explain_prediction(
    drug_a_id: str,
    drug_b_id: str,
    cell_line_name: str,
    module,
    heterodata,
    device="cpu",
    top_k=10,
    threshold_synergy=THRESHOLD_SYNERGY,
    threshold_antagonism=THRESHOLD_ANTAGONISM,
    run_faithfulness=True,
    run_literature=True,
    disease_context: Optional[str] = None,
    use_cache: bool = True,
) -> dict[str, Any]:
    """
    Generate an interpretable explanation for a (drug_A, drug_B, cell_line) prediction.

    Returns a JSON-serialisable dict:
      drug_a, drug_a_name, drug_b, drug_b_name, cell_line,
      predicted_class, score, p_antagonism, p_additive, p_synergy,
      top_edges (list of {source, relation, target, importance}),
      explanation_text, supporting_literature,
      faithfulness ({original_score, original_class, ablated_score, ablated_class,
                     sufficiency, necessity, explanation_faithful, rationale,
                     k_edges_ablated, error})
    """
    name_lookup, _  = _build_name_lookups(heterodata)
    node_maps        = _get_node_maps(heterodata)
    drug_id2idx      = node_maps.get("drug", {})
    cell_line_map    = heterodata.cell_line_map

    errors = []
    if drug_a_id not in drug_id2idx:
        errors.append(f"drug_a '{drug_a_id}' not in KG drug nodes.")
    if drug_b_id not in drug_id2idx:
        errors.append(f"drug_b '{drug_b_id}' not in KG drug nodes.")
    if cell_line_name not in cell_line_map:
        errors.append(f"cell_line '{cell_line_name}' unknown.")
    if errors:
        return {"error": "; ".join(errors)}

    a_idx    = drug_id2idx[drug_a_id]
    b_idx    = drug_id2idx[drug_b_id]
    cell_idx = cell_line_map[cell_line_name]

    drug_a_name = name_lookup["drug"].get(a_idx, drug_a_id)
    drug_b_name = name_lookup["drug"].get(b_idx, drug_b_id)

    # Check in-memory explanation cache (canonical drug order)
    d_min, d_max = min(drug_a_id, drug_b_id), max(drug_a_id, drug_b_id)
    cache_key = (d_min, d_max, cell_line_name, top_k, run_faithfulness, run_literature, disease_context)
    if use_cache and cache_key in _EXPLANATION_CACHE:
        cached = copy.deepcopy(_EXPLANATION_CACHE[cache_key])
        cached["drug_a"] = drug_a_id
        cached["drug_b"] = drug_b_id
        if drug_a_id != d_min:
            cached["drug_a_name"], cached["drug_b_name"] = cached["drug_b_name"], cached["drug_a_name"]
        return cached

    # Obtain canonical symmetric synergy prediction from shared predict_synergy entry point
    from predict import predict_synergy
    pred_res = predict_synergy(
        drug_a_id=drug_a_id,
        drug_b_id=drug_b_id,
        cell_line_name=cell_line_name,
        module=module,
        heterodata=heterodata,
        threshold_synergy=threshold_synergy,
        threshold_antagonism=threshold_antagonism,
        device=device,
    )
    predicted_class_name = pred_res["prediction"]
    p_ant = pred_res["p_antagonism"]
    p_add = pred_res["p_additive"]
    p_syn = pred_res["p_synergy"]
    predicted_class_idx = CLASS_NAMES.index(predicted_class_name)
    original_prob = {"antagonism": p_ant, "additive": p_add, "synergy": p_syn}[predicted_class_name]

    print(f"\n  [explain] Sampling subgraph for {drug_a_name} x {drug_b_name} @ {cell_line_name}...")
    batch = _sample_batch(heterodata, a_idx, b_idx, cell_idx)

    # Forward pass to obtain baseline predicted class probability
    batch_dev = batch.to(device)
    module.eval()
    with torch.no_grad():
        logits_base, _ = module(batch_dev)
        probs_base = F.softmax(logits_base, dim=-1)
        if probs_base.dim() == 2 and probs_base.shape[0] >= 2:
            p_target = ((probs_base[0, predicted_class_idx] + probs_base[1, predicted_class_idx]) / 2.0).item()
        else:
            p_target = probs_base.squeeze(0)[predicted_class_idx].item()

    print(f"  [explain] Predicted: {predicted_class_name.upper()} "
          f"(p_syn={p_syn:.3f}, p_add={p_add:.3f}, p_ant={p_ant:.3f})")

    # Score edges using direct leave-one-out perturbation (Option 4)
    print(f"  [explain] Computing leave-one-out edge importance across candidate edges...")
    top_edges, all_edges = _score_edges(
        batch=batch,
        name_lookup=name_lookup,
        top_k=top_k,
        module=module,
        pred_idx=predicted_class_idx,
        original_prob=p_target,
        device=device,
        chunk_size=64,
    )
    print(f"  [explain] Top {len(top_edges)} explanation edges identified via leave-one-out perturbation.")

    # ── Necessity & Sufficiency faithfulness checks (skipped during search) ─────────────────
    if run_faithfulness:
        if len(top_edges) == 0:
            necessity_delta = None
            suf_retained = None
            suf_class_ok = None
            suf_prob = None
            faithfulness = {
                "original_score": round(original_prob, 4),
                "original_class": predicted_class_name,
                "ablated_score": None,
                "ablated_class": None,
                "sufficiency": None,
                "necessity": None,
                "explanation_faithful": False,
                "rationale": "Faithfulness ablation could not be evaluated: no explanation edges identified in the local subgraph.",
                "k_edges_ablated": 0,
                "error": "No explanation edges available to ablate.",
            }
        else:
            try:
                print(f"  [explain] Running necessity ablation check (removing top {len(top_edges)} edges)...")
                necessity_delta, ablated_score, ablated_class = _necessity_check(
                    module,
                    batch,
                    top_edges,
                    predicted_class_idx,
                    original_prob,
                    device,
                    threshold_synergy=threshold_synergy,
                    threshold_antagonism=threshold_antagonism,
                )
                print(
                    f"  [explain] Necessity delta: {necessity_delta:+.1f}% "
                    f"(prob drop: {original_prob:.3f} -> {ablated_score:.3f}, class: {ablated_class})"
                )

                # ── Sufficiency faithfulness check ─────────────────────────────────────────────
                print(f"  [explain] Running sufficiency check (keeping ONLY top {len(top_edges)} edges)...")
                suf_retained, suf_class_ok, suf_prob = _sufficiency_check(
                    module,
                    batch,
                    top_edges,
                    predicted_class_idx,
                    original_prob,
                    device,
                    threshold_synergy=threshold_synergy,
                    threshold_antagonism=threshold_antagonism,
                )
                print(
                    f"  [explain] Sufficiency: {suf_retained:.1f}% of original probability retained "
                    f"with only {len(top_edges)} edges  |  class preserved: {suf_class_ok}"
                )

                is_faithful = bool(suf_retained >= 70.0 and suf_class_ok)
                if is_faithful:
                    rationale = (
                        f"The isolated {len(top_edges)}-edge attribution subgraph retains {suf_retained:.1f}% of original confidence "
                        f"with predicted class preserved, verifying that the cited pathway drives the GNN prediction."
                    )
                else:
                    rationale = (
                        f"The isolated attribution subgraph retains {suf_retained:.1f}% of confidence (below the 70.0% verification threshold "
                        f"or class preserved: {suf_class_ok}), indicating the prediction relies on broader multi-hop graph context."
                    )

                faithfulness = {
                    "original_score": round(original_prob, 4),
                    "original_class": predicted_class_name,
                    "ablated_score": round(ablated_score, 4),
                    "ablated_class": ablated_class,
                    "sufficiency": round(suf_retained, 2),
                    "necessity": round(necessity_delta, 2),
                    "explanation_faithful": is_faithful,
                    "rationale": rationale,
                    "k_edges_ablated": len(top_edges),
                    "error": None,
                }
            except Exception as ex:
                print(f"  [explain] Warning: Faithfulness ablation failed with error: {ex}")
                necessity_delta = None
                suf_retained = None
                suf_class_ok = None
                suf_prob = None
                faithfulness = {
                    "original_score": round(original_prob, 4),
                    "original_class": predicted_class_name,
                    "ablated_score": None,
                    "ablated_class": None,
                    "sufficiency": None,
                    "necessity": None,
                    "explanation_faithful": False,
                    "rationale": f"Faithfulness ablation computation failed: {str(ex)}",
                    "k_edges_ablated": len(top_edges),
                    "error": str(ex),
                }
    else:
        necessity_delta = None
        suf_retained    = None
        suf_class_ok    = None
        suf_prob        = None
        faithfulness    = None
        print("  [explain] Faithfulness checks skipped (run_faithfulness=False).")

    # ── NL explanation ─────────────────────────────────────────────────────
    explanation_text = _generate_explanation(
        drug_a_name, drug_b_name, top_edges, all_edges=all_edges, predicted_class=predicted_class_name
    )
    print(f"  [explain] {explanation_text}")

    # ── Supporting PubMed literature (RAG) ──────────────────────────────────
    if run_literature:
        print("  [explain] Fetching supporting literature from PubMed (RAG)...")
        from literature import retrieve_literature_rag
        literature_result = retrieve_literature_rag(
            drug_a_name      = drug_a_name,
            drug_b_name      = drug_b_name,
            disease_context  = disease_context,
            top_edges        = top_edges,
            explanation_text = explanation_text,
            max_citations    = 3,
        )
        supporting_literature = literature_result.get("citations", [])
    else:
        print("  [explain] Literature retrieval skipped (run_literature=False).")
        literature_result = None
        supporting_literature = []

    serialized_edges = [
        {
            "source":      e["source"],
            "source_type": e.get("source_type", ""),
            "relation":    e["relation"],
            "target":      e["target"],
            "target_type": e.get("target_type", ""),
            "importance":  round(float(e["importance"]), 6),
        }
        for e in top_edges
        if e["relation"] != "drug_drug"   # exclude structural drug-drug edges
    ]

    result = {
        "drug_a":                      drug_a_id,
        "drug_a_name":                 drug_a_name,
        "drug_b":                      drug_b_id,
        "drug_b_name":                 drug_b_name,
        "cell_line":                   cell_line_name,
        "predicted_class":             predicted_class_name,
        "score":                       round(p_syn, 6),
        "p_antagonism":                round(p_ant, 6),
        "p_additive":                  round(p_add, 6),
        "p_synergy":                   round(p_syn, 6),
        "top_edges":                   serialized_edges,
        "explanation_text":            explanation_text,
        # ── Supporting Literature (PubMed RAG) ───────────────────────────────
        "literature":                  literature_result,
        "supporting_literature":       supporting_literature,
        # ── Structured Faithfulness Object ───────────────────────────────
        "faithfulness":                faithfulness,
        # ── Backward-compatible top-level Faithfulness metrics ────────────
        "necessity_delta_pct":         necessity_delta,
        "sufficiency_retained_pct":    suf_retained,
        "sufficiency_class_preserved": suf_class_ok,
        "sufficiency_prob":            round(suf_prob, 6) if suf_prob is not None else None,
    }

    if use_cache:
        _EXPLANATION_CACHE[cache_key] = copy.deepcopy(result)

    return result


# ---------------------------------------------------------------------------
# Demo runner
# ---------------------------------------------------------------------------

def _run_demo(module, heterodata, device):
    demo_pairs = [
        # (drug_a_id, drug_b_id, cell_line, ground_truth_label)
        ("DB00853", "DB00531", "T98G",    "synergy"),     # Temozolomide x Cyclophosphamide
        ("DB00853", "DB01248", "OVCAR-5", "antagonism"),  # Temozolomide x Docetaxel
        ("DB01248", "DB01030", "A498",    "additive"),    # Docetaxel x Topotecan
    ]

    results = []
    for drug_a_id, drug_b_id, cell_line, gt in demo_pairs:
        print("\n" + "=" * 65)
        print(f"  EXPLAINING: {drug_a_id} x {drug_b_id}  |  cell={cell_line}")
        print(f"  Ground-truth label: {gt.upper()}")
        print("=" * 65)

        result = explain_prediction(
            drug_a_id      = drug_a_id,
            drug_b_id      = drug_b_id,
            cell_line_name = cell_line,
            module         = module,
            heterodata     = heterodata,
            device         = device,
        )
        result["ground_truth"] = gt
        results.append(result)

        print()
        print(f"  Drug A          : {result.get('drug_a_name', drug_a_id)} ({drug_a_id})")
        print(f"  Drug B          : {result.get('drug_b_name', drug_b_id)} ({drug_b_id})")
        print(f"  Cell Line       : {cell_line}")
        print(f"  Predicted Class : {result['predicted_class'].upper()}")
        print(f"  p_synergy       : {result['p_synergy']:.4f}")
        print(f"  p_additive      : {result['p_additive']:.4f}")
        print(f"  p_antagonism    : {result['p_antagonism']:.4f}")
        print()
        print("  Top-10 Explanation Edges:")
        for i, edge in enumerate(result["top_edges"], 1):
            print(f"    {i:2d}. [{edge['source']}] --[{edge['relation']}]--> [{edge['target']}]"
                  f"  (importance={edge['importance']:.4f})")
        print()
        print(f"  Explanation     : {result['explanation_text']}")
        print()
        print("  Faithfulness:")
        print(f"    Necessity   : {result['necessity_delta_pct']:+.1f}% drop in p(class) after"
              f" removing top edges   (small is expected -- GNNs are robust to edge loss)")
        print(f"    Sufficiency : {result['sufficiency_retained_pct']:.1f}% of p(class) retained"
              f" using ONLY top-{len(result['top_edges'])} edges   |"
              f"  class preserved: {result['sufficiency_class_preserved']}")
        print()
        lit = result.get("supporting_literature", [])
        if lit:
            print("  Supporting PubMed Literature:")
            for ref in lit:
                print(f"    - {ref['first_author']} ({ref['year']}). {ref['title']}")
                print(f"      PMID {ref['pmid']} | {ref['url']}")
        else:
            print("  Supporting PubMed Literature: (none retrieved)")

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Explain drug synergy predictions.")
    parser.add_argument("--checkpoint",  default=CHECKPOINT_PATH)
    parser.add_argument("--heterodata",  default=HETERODATA_PATH)
    parser.add_argument("--drug-a",      default=None)
    parser.add_argument("--drug-b",      default=None)
    parser.add_argument("--cell-line",   default=None)
    parser.add_argument("--demo",        action="store_true")
    parser.add_argument("--json-out",    action="store_true")
    args = parser.parse_args()

    print("\nLoading model...")
    module, heterodata, device = load_model(args.checkpoint, args.heterodata)

    if args.demo or args.drug_a is None:
        results = _run_demo(module, heterodata, device)
        print("\n\nJSON output:")
        print(json.dumps(results, indent=2))
    else:
        result = explain_prediction(
            drug_a_id      = args.drug_a,
            drug_b_id      = args.drug_b,
            cell_line_name = args.cell_line,
            module         = module,
            heterodata     = heterodata,
            device         = device,
        )
        if args.json_out:
            print(json.dumps(result, indent=2))
        else:
            print(f"\nPredicted: {result['predicted_class'].upper()}")
            print(f"Explanation: {result['explanation_text']}")
            print(f"Necessity   delta: {result['necessity_delta_pct']:+.1f}%")
            print(f"Sufficiency retained: {result['sufficiency_retained_pct']:.1f}%"
                  f"  |  class preserved: {result['sufficiency_class_preserved']}")
