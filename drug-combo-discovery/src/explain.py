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
from collections import defaultdict

import torch
import torch.nn.functional as F
from torch_geometric.loader import LinkNeighborLoader

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
    data_copy = heterodata.clone()

    edge_index  = torch.tensor([[a_idx], [b_idx]], dtype=torch.long)
    dummy_label = torch.tensor([[0, cell_idx]], dtype=torch.long)

    data_copy["drug", "synergy_pair", "drug"].edge_index       = edge_index
    data_copy["drug", "synergy_pair", "drug"].edge_label_index = edge_index
    data_copy["drug", "synergy_pair", "drug"].edge_label       = dummy_label

    num_neighbors = {
        et: ([0, 0] if et == ("drug", "synergy_pair", "drug") else [10, 5])
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
    return next(iter(loader))


# ---------------------------------------------------------------------------
# Edge importance scorer
# ---------------------------------------------------------------------------

def _score_edges(batch, grad_norms, name_lookup, top_k=10):
    """
    Score every KG edge in the local subgraph by the source node's gradient norm.

    IMPORTANT: edge_index values are *batch-local* indices (0 .. N_local-1).
    To resolve node names from primekg_nodes.csv we need the *global* integer
    index, which PyG's NeighborLoader stores in batch[ntype].n_id.
    We map: src_global = batch[src_type].n_id[src_local]
    """
    # Build local->global index maps for each node type present in this batch
    n_id_map: dict[str, torch.Tensor] = {}
    for ntype in batch.node_types:
        store = batch[ntype]
        if hasattr(store, "n_id") and store.n_id is not None:
            n_id_map[ntype] = store.n_id.cpu()

    seen: set[tuple] = set()   # deduplicate (src_global, rel, dst_global)
    scored_edges = []

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

        src_norms = grad_norms.get(src_type)
        dst_norms = grad_norms.get(dst_type)
        src_n_id  = n_id_map.get(src_type)
        dst_n_id  = n_id_map.get(dst_type)

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

            # Importance: gradient L2-norm at drug node (batch-local index)
            imp_val = 0.01
            if src_norms is not None and src_local < len(src_norms):
                imp_val = max(imp_val, src_norms[src_local].item())
            if dst_norms is not None and dst_local < len(dst_norms):
                imp_val = max(imp_val, dst_norms[dst_local].item())
            importance = imp_val

            # Resolve human-readable names using global indices
            src_name = _resolve_name(src_type, src_global, name_lookup)
            dst_name = _resolve_name(dst_type, dst_global, name_lookup)

            scored_edges.append({
                "source_type":   src_type,
                "source_local":  src_local,   # kept for faithfulness mask
                "source_global": src_global,
                "source":        src_name,
                "relation":      rel,
                "target_type":   dst_type,
                "target_local":  dst_local,
                "target_global": dst_global,
                "target":        dst_name,
                "importance":    importance,
            })

    scored_edges.sort(key=lambda e: e["importance"], reverse=True)
    return scored_edges[:top_k], scored_edges


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

def _necessity_check(module, batch, top_edges, predicted_class, original_prob, device):
    """
    NECESSITY: Remove the top-K explanation edges from the full subgraph and
    rerun inference.  A large probability drop means those edges were necessary
    for the prediction.  GNNs are robust to edge removal, so this number is
    often small — which is expected, not a bug.

    Returns % drop in predicted-class probability (positive = drop, negative = rise).
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
        probs_pruned      = F.softmax(logits_pruned, dim=-1).squeeze(0).cpu()

    new_prob  = probs_pruned[predicted_class].item()
    delta_pct = round((original_prob - new_prob) / max(original_prob, 1e-9) * 100, 2)
    return delta_pct


def _sufficiency_check(
    module,
    batch,
    top_edges,
    predicted_class,
    original_prob,
    device,
):
    """
    SUFFICIENCY: Build a heavily pruned subgraph that keeps ONLY the top-K
    explanation edges (all other message-passing edges are removed; all nodes
    are retained so the pair-scorer MLP can still run).

    Re-run inference on this minimal subgraph and report:
      - sufficiency_retained_pct : new_prob / original_prob * 100
        (100% = top-K edges alone are sufficient to recover the full prediction;
         50% = they carry half the signal)
      - sufficiency_class_preserved : bool — does argmax still agree with the
        original calibrated prediction?

    This is the more diagnostic faithfulness metric for our pitch: if 10 edges
    out of thousands can reproduce most of the model's confidence, those edges
    really are load-bearing.
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
        probs_suf      = F.softmax(logits_suf, dim=-1).squeeze(0).cpu()

    new_prob     = probs_suf[predicted_class].item()
    argmax_class = probs_suf.argmax().item()

    # % of original probability retained by the 10-edge subgraph
    retained_pct = round(new_prob / max(original_prob, 1e-9) * 100, 2)

    # Does the argmax class match the original predicted class?
    class_preserved = (argmax_class == predicted_class)

    return retained_pct, class_preserved, new_prob


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------

def explain_prediction(
    drug_a_id,
    drug_b_id,
    cell_line_name,
    module,
    heterodata,
    device="cpu",
    top_k=10,
    threshold_synergy=THRESHOLD_SYNERGY,
    threshold_antagonism=THRESHOLD_ANTAGONISM,
    run_faithfulness=True,
):
    """
    Generate an interpretable explanation for a (drug_A, drug_B, cell_line) prediction.

    Returns a JSON-serialisable dict:
      drug_a, drug_a_name, drug_b, drug_b_name, cell_line,
      predicted_class, score, p_antagonism, p_additive, p_synergy,
      top_edges (list of {source, relation, target, importance}),
      explanation_text, faithfulness_delta_pct
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

    print(f"\n  [explain] Sampling subgraph for {drug_a_name} x {drug_b_name} @ {cell_line_name}...")
    batch = _sample_batch(heterodata, a_idx, b_idx, cell_idx)

    # Forward + grad
    batch_dev = batch.to(device)
    drug_feats = batch_dev["drug"].x.float().detach().requires_grad_(True)
    batch_dev["drug"].x = drug_feats

    module.eval()
    logits, _ = module(batch_dev)
    probs  = F.softmax(logits, dim=-1).squeeze(0)
    p_ant, p_add, p_syn = probs.tolist()

    if p_syn > threshold_synergy:
        predicted_class_name = "synergy"
        predicted_class_idx  = 2
    elif p_ant > threshold_antagonism:
        predicted_class_name = "antagonism"
        predicted_class_idx  = 0
    else:
        predicted_class_name = "additive"
        predicted_class_idx  = 1

    original_prob = probs[predicted_class_idx].item()
    print(f"  [explain] Predicted: {predicted_class_name.upper()} "
          f"(p_syn={p_syn:.3f}, p_add={p_add:.3f}, p_ant={p_ant:.3f})")

    # Backprop
    probs[predicted_class_idx].backward()
    drug_grad = drug_feats.grad
    grad_norms = {}
    if drug_grad is not None:
        grad_norms["drug"] = drug_grad.norm(dim=-1).detach().cpu()

    # Score edges using CPU batch (for name resolution)
    top_edges, all_edges = _score_edges(batch, grad_norms, name_lookup, top_k=top_k)
    print(f"  [explain] Top {len(top_edges)} explanation edges identified.")

    # ── Necessity faithfulness check (optional — skipped during search) ──────────────────────
    if run_faithfulness:
        print("  [explain] Running necessity check (remove top edges)...")
        necessity_delta = _necessity_check(
            module, batch, top_edges, predicted_class_idx, original_prob, device
        )
        print(f"  [explain] Necessity delta: {necessity_delta:+.1f}% (drop in predicted-class prob)")

        # ── Sufficiency faithfulness check ─────────────────────────────────────────────
        print("  [explain] Running sufficiency check (keep ONLY top edges)...")
        suf_retained, suf_class_ok, suf_prob = _sufficiency_check(
            module, batch, top_edges, predicted_class_idx, original_prob, device
        )
        print(
            f"  [explain] Sufficiency: {suf_retained:.1f}% of original probability retained "
            f"with only {len(top_edges)} edges  |  class preserved: {suf_class_ok}"
        )
    else:
        necessity_delta = None
        suf_retained    = None
        suf_class_ok    = None
        suf_prob        = None
        print("  [explain] Faithfulness checks skipped (run_faithfulness=False).")

    # ── NL explanation ─────────────────────────────────────────────────────
    explanation_text = _generate_explanation(
        drug_a_name, drug_b_name, top_edges, all_edges=all_edges, predicted_class=predicted_class_name
    )
    print(f"  [explain] {explanation_text}")

    # ── Supporting PubMed literature ───────────────────────────────────────
    # Retrieve up to 2 relevant PubMed citations for the primary drug+term
    # that drove the explanation template.  Returns [] on any failure.
    print("  [explain] Fetching supporting literature from PubMed...")
    supporting_literature = get_literature_for_explanation(
        drug_a_name      = drug_a_name,
        drug_b_name      = drug_b_name,
        explanation_text = explanation_text,
        top_edges        = top_edges,
        all_edges        = all_edges,
        max_results      = 2,
    )

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

    return {
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
        # ── Supporting Literature (PubMed) ───────────────────────────────
        "supporting_literature":       supporting_literature,
        # ── Faithfulness metrics ─────────────────────────────────────────
        # Necessity: how much does removing the top-K edges hurt the prediction?
        # (small values are expected due to GNN robustness -- not a bug)
        "necessity_delta_pct":         necessity_delta,
        # Sufficiency: with ONLY the top-K edges, how much of the original
        # prediction confidence is retained?  High = edges are load-bearing.
        "sufficiency_retained_pct":    suf_retained,
        "sufficiency_class_preserved": suf_class_ok,
        # Raw probabilities on sufficiency-only subgraph (for debugging)
        "sufficiency_prob":            round(suf_prob, 6) if suf_prob is not None else None,
    }


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
