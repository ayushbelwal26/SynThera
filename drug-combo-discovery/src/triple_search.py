"""
src/triple_search.py - Phase C1 Three-Drug Combination Composed Pair Scoring

Implements three-drug combination discovery as COMPOSED PAIR SCORES ONLY per
FUTURE_SCOPE.md section 4.1.C. There is NO triple-synergy model and NO DrugComb
3-way labels. Every response, log, and result explicitly carries the caption:
"We compose pair scores; we do not have DrugComb 3-way synergy labels."

Formula:
  For candidate set {A, B, C}:
    V_min(A, B, C)  = min(V(A, B), V(A, C), V(B, C))  [Primary Bottleneck Aggregate]
    V_mean(A, B, C) = mean(V(A, B), V(A, C), V(B, C)) [Secondary Descriptive Aggregate]
    triple_toxicity_penalty = max(Tox(A, B), Tox(A, C), Tox(B, C)) [Safety Union]
"""

import os
import sys
import time
import math
import logging
import itertools
from typing import List, Dict, Tuple, Optional, Any, Set
from collections import defaultdict

import torch
import torch.nn.functional as F
from torch_geometric.data import HeteroData
from torch_geometric.loader import LinkNeighborLoader

# Ensure src/ is importable
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

try:
    from ranking import (
        compute_pair_score_v,
        DEFAULT_W_SYNERGY,
        DEFAULT_W_TOXICITY,
        DEFAULT_W_REDUNDANCY,
    )
    from search import (
        find_candidate_drugs,
        _load_model_cached,
        _load_resources,
        resolve_disease_nodes,
    )
except ImportError:
    from src.ranking import (
        compute_pair_score_v,
        DEFAULT_W_SYNERGY,
        DEFAULT_W_TOXICITY,
        DEFAULT_W_REDUNDANCY,
    )
    from src.search import (
        find_candidate_drugs,
        _load_model_cached,
        _load_resources,
        resolve_disease_nodes,
    )

logger = logging.getLogger("synthera.triple_search")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ---------------------------------------------------------------------------
# Constants & Mandatory Disclaimers
# ---------------------------------------------------------------------------

# Overriding Constraint: Every place this feature surfaces MUST carry this exact caption
COMPOSITION_CAPTION = "We compose pair scores; we do not have DrugComb 3-way synergy labels."

# Candidate pool hard cap to prevent O(N^3) combinatorial explosion
CANDIDATE_POOL_HARD_CAP = 20
DEFAULT_TIME_BUDGET_SEC = 15.0


# ---------------------------------------------------------------------------
# Core Composition Scoring
# ---------------------------------------------------------------------------

def compose_triple_result(
    drug_a: Any,
    drug_b: Any,
    drug_c: Any,
    pair_ab: Dict[str, Any],
    pair_ac: Dict[str, Any],
    pair_bc: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Pure composition logic for a three-drug combination {A, B, C}.
    Takes three constituent pairwise ranking blocks (pair_ab, pair_ac, pair_bc)
    and computes:
    - aggregate_min: min(v_ab, v_ac, v_bc) (bottleneck framing)
    - aggregate_mean: mean(v_ab, v_ac, v_bc)
    - triple_toxicity_penalty: max(tox_ab, tox_ac, tox_bc)
    - has_known_ddi: True if any pair has confirmed DDI; False if all pairs safe; None if any unindexed
    - bottleneck_pair: isolates the worst-performing pair defining aggregate_min
    - composition_caption: mandatory universal disclaimer

    Parameters
    ----------
    drug_a, drug_b, drug_c : Dict with 'drug_id' and 'drug_name', or string identifier.
    pair_ab, pair_ac, pair_bc : Full ranking blocks returned by compute_pair_score_v.

    Returns
    -------
    Dict[str, Any] matching the Phase C1 triple result schema.
    """
    def _extract_id_name(d: Any) -> Tuple[str, str]:
        if isinstance(d, dict):
            did = d.get("drug_id") or d.get("id") or str(d)
            dname = d.get("drug_name") or d.get("name") or did
            return str(did), str(dname)
        s = str(d)
        return s, s

    da_id, da_name = _extract_id_name(drug_a)
    db_id, db_name = _extract_id_name(drug_b)
    dc_id, dc_name = _extract_id_name(drug_c)

    v_ab = pair_ab["v_score"]
    v_ac = pair_ac["v_score"]
    v_bc = pair_bc["v_score"]

    tox_ab = pair_ab["toxicity_penalty"]
    tox_ac = pair_ac["toxicity_penalty"]
    tox_bc = pair_bc["toxicity_penalty"]

    # 1. Primary Aggregate: Bottleneck / Weak-Link min(V_AB, V_AC, V_BC)
    pair_scores = [
        (v_ab, da_name, db_name, "pair_ab", pair_ab),
        (v_ac, da_name, dc_name, "pair_ac", pair_ac),
        (v_bc, db_name, dc_name, "pair_bc", pair_bc),
    ]
    pair_scores.sort(key=lambda x: x[0])
    v_min, bottleneck_d1, bottleneck_d2, bottleneck_key, bottleneck_ranking = pair_scores[0]

    # 2. Secondary Aggregate: mean(V_AB, V_AC, V_BC)
    v_mean = round((v_ab + v_ac + v_bc) / 3.0, 4)

    # 3. Triple Toxicity Penalty: Union / max of constituent penalties
    triple_tox_penalty = round(max(tox_ab, tox_ac, tox_bc), 4)
    tox_candidates = [
        (tox_ab, da_name, db_name, "pair_ab", pair_ab),
        (tox_ac, da_name, dc_name, "pair_ac", pair_ac),
        (tox_bc, db_name, dc_name, "pair_bc", pair_bc),
    ]
    tox_candidates.sort(key=lambda x: x[0], reverse=True)
    max_tox, max_tox_d1, max_tox_d2, max_tox_key, max_tox_ranking = tox_candidates[0]

    # 4. Overall DDI Flag
    # True if ANY pair has confirmed DDI; False if ALL pairs confirmed Safe; None if any unindexed
    ddi_flags = [
        pair_ab["breakdown"]["has_known_ddi"],
        pair_ac["breakdown"]["has_known_ddi"],
        pair_bc["breakdown"]["has_known_ddi"],
    ]
    if any(f is True for f in ddi_flags):
        triple_has_ddi: Optional[bool] = True
    elif all(f is False for f in ddi_flags):
        triple_has_ddi = False
    else:
        triple_has_ddi = None

    return {
        "drug_a": da_id,
        "drug_a_name": da_name,
        "drug_b": db_id,
        "drug_b_name": db_name,
        "drug_c": dc_id,
        "drug_c_name": dc_name,
        "aggregate_min": round(v_min, 4),
        "aggregate_mean": v_mean,
        "score": round(v_min, 4),  # Alias for standard rank sorting
        "v_score": round(v_min, 4),
        "triple_toxicity_penalty": triple_tox_penalty,
        "has_known_ddi": triple_has_ddi,
        "bottleneck_pair": {
            "pair_key": bottleneck_key,
            "drug_1": bottleneck_d1,
            "drug_2": bottleneck_d2,
            "v_score": round(v_min, 4),
            "p_synergy": bottleneck_ranking["p_synergy"],
            "toxicity_penalty": bottleneck_ranking["toxicity_penalty"],
        },
        "max_toxicity_pair": {
            "pair_key": max_tox_key,
            "drug_1": max_tox_d1,
            "drug_2": max_tox_d2,
            "toxicity_penalty": round(max_tox, 4),
            "has_known_ddi": max_tox_ranking["breakdown"]["has_known_ddi"],
        },
        "pair_ab": pair_ab,
        "pair_ac": pair_ac,
        "pair_bc": pair_bc,
        "literature_all_three": None,  # Stubbed per 'never batch-PubMed' rule
        "composition_caption": COMPOSITION_CAPTION,
    }


def score_triple_combination(
    drug_a: Dict[str, Any],
    drug_b: Dict[str, Any],
    drug_c: Dict[str, Any],
    pair_rankings: Dict[Tuple[str, str], Dict[str, Any]],
    w_synergy: float = DEFAULT_W_SYNERGY,
    w_toxicity: float = DEFAULT_W_TOXICITY,
    w_redundancy: float = DEFAULT_W_REDUNDANCY,
    strict_known_only: bool = False,
) -> Dict[str, Any]:
    """
    Evaluates a candidate 3-drug set {A, B, C} by looking up its three pairwise
    ranking blocks (AB, AC, BC) and composing them via compose_triple_result().
    """
    da_id = drug_a["drug_id"]
    db_id = drug_b["drug_id"]
    dc_id = drug_c["drug_id"]

    key_ab = (min(da_id, db_id), max(da_id, db_id))
    key_ac = (min(da_id, dc_id), max(da_id, dc_id))
    key_bc = (min(db_id, dc_id), max(db_id, dc_id))

    def get_or_compute_ranking(k: Tuple[str, str], id_1: str, id_2: str) -> Dict[str, Any]:
        if k in pair_rankings:
            return pair_rankings[k]
        # Fallback if uncomputed
        r = compute_pair_score_v(
            id_1,
            id_2,
            p_synergy=0.5,
            w_synergy=w_synergy,
            w_toxicity=w_toxicity,
            w_redundancy=w_redundancy,
            strict_known_only=strict_known_only,
        )
        pair_rankings[k] = r
        return r

    ranking_ab = get_or_compute_ranking(key_ab, da_id, db_id)
    ranking_ac = get_or_compute_ranking(key_ac, da_id, dc_id)
    ranking_bc = get_or_compute_ranking(key_bc, db_id, dc_id)

    return compose_triple_result(
        drug_a=drug_a,
        drug_b=drug_b,
        drug_c=drug_c,
        pair_ab=ranking_ab,
        pair_ac=ranking_ac,
        pair_bc=ranking_bc,
    )


# ---------------------------------------------------------------------------
# Systematic Depth-3 Triple Search
# ---------------------------------------------------------------------------

def search_triple_combinations(
    disease_name: str,
    cell_line_name: str,
    heterodata: Optional[HeteroData] = None,
    module: Optional[Any] = None,
    device: Optional[str] = None,
    max_candidates: int = 10,
    top_k: int = 5,
    time_budget_sec: float = DEFAULT_TIME_BUDGET_SEC,
    w_synergy: float = DEFAULT_W_SYNERGY,
    w_toxicity: float = DEFAULT_W_TOXICITY,
    w_redundancy: float = DEFAULT_W_REDUNDANCY,
    strict_known_only: bool = False,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Discovers candidate three-drug combinations for a target disease indication
    and cell line using composed pairwise evaluations.

    Guarantees:
    1. Reuses filtered candidate pool logic (denies metals, zinc salts, buffers; applies CYP filter).
    2. Enforces hard cap (min(max_candidates, 20)) preventing combinatorial blowup.
    3. Evaluates all unique constituent pairs in batched GNN inference passes.
    4. Evaluates triples systematically against the hard time budget cap.
    5. Primary ranking is strictly sorted by aggregate_min descending.
    6. Attaches mandatory composition caption to response and every hit.
    """
    start_time = time.time()
    logger.info(
        f"[TRIPLE SEARCH] Beginning composed 3-drug discovery for '{disease_name}' @ '{cell_line_name}'. "
        f"Disclaimer: {COMPOSITION_CAPTION}"
    )

    # 1. Enforce candidate pool hard cap
    requested_pool = max_candidates
    capped_pool = min(max(3, max_candidates), CANDIDATE_POOL_HARD_CAP)
    if requested_pool > CANDIDATE_POOL_HARD_CAP:
        logger.warning(
            f"[TRIPLE SEARCH] Requested candidate pool ({requested_pool}) exceeds hard cap of {CANDIDATE_POOL_HARD_CAP}. "
            f"Capping at {CANDIDATE_POOL_HARD_CAP} to prevent combinatorial explosion."
        )

    # 2. Load model, graph, and node maps
    if module is None or heterodata is None:
        module, heterodata, device = _load_model_cached(device=device)

    _, node_maps, name_lookup, id_lookup, drug_targets = _load_resources(heterodata)
    drug_id2idx = node_maps["drug"]
    cell_line_map = getattr(heterodata, "cell_line_map", {})

    canonical_cl = None
    if cell_line_name in cell_line_map:
        canonical_cl = cell_line_name
    else:
        cl_lower = {k.lower(): k for k in cell_line_map.keys()}
        canonical_cl = cl_lower.get(cell_line_name.lower())

    if not canonical_cl:
        sample_cls = sorted(list(cell_line_map.keys()))[:8]
        raise ValueError(
            f"Cell line '{cell_line_name}' not found in knowledge graph. "
            f"Available cell lines include: {sample_cls} (total {len(cell_line_map)})."
        )
    cell_idx = cell_line_map[canonical_cl]

    # 3. Discover filtered candidates
    candidates = find_candidate_drugs(
        disease_name=disease_name,
        heterodata=heterodata,
        max_candidates=capped_pool,
    )

    metadata: Dict[str, Any] = {
        "disease": disease_name,
        "cell_line": canonical_cl,
        "candidate_pool_size": len(candidates),
        "n_triples_scored": 0,
        "n_pairs_scored": 0,
        "truncated": False,
        "time_taken_sec": 0.0,
        "composition_caption": COMPOSITION_CAPTION,
    }

    if len(candidates) < 3:
        logger.warning(
            f"[TRIPLE SEARCH] Fewer than 3 therapeutic candidates found ({len(candidates)}) for '{disease_name}'. "
            "Cannot form 3-drug combinations."
        )
        metadata["time_taken_sec"] = round(time.time() - start_time, 3)
        return [], metadata

    # 4. Generate all unique pairwise combinations among candidates
    # C(M, 2): at most C(20, 2) = 190 unique pairs
    unique_pairs = list(itertools.combinations(candidates, 2))
    n_unique_pairs = len(unique_pairs)
    logger.info(
        f"[TRIPLE SEARCH] Candidate pool of {len(candidates)} drugs yields {n_unique_pairs} "
        f"unique constituent pairs to score."
    )

    # 5. Batched GNN Inference for All Constituent Pairs (Option A: Symmetric Inference Wrapper)
    t_gnn_start = time.time()
    torch.manual_seed(42)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(42)

    sys.path.insert(0, os.path.join(ROOT, "src"))
    from predict import predict_synergy_batch, THRESHOLD_SYNERGY, THRESHOLD_ANTAGONISM
    pair_id_list = [(p[0]["drug_id"], p[1]["drug_id"]) for p in unique_pairs]
    batch_results = predict_synergy_batch(
        pairs=pair_id_list,
        cell_line_name=canonical_cl,
        module=module,
        heterodata=heterodata,
        threshold_synergy=THRESHOLD_SYNERGY,
        threshold_antagonism=THRESHOLD_ANTAGONISM,
        device=device,
    )
    all_probs = [[r["p_antagonism"], r["p_additive"], r["p_synergy"]] for r in batch_results]
    gnn_elapsed = time.time() - t_gnn_start
    logger.info(f"[TRIPLE SEARCH] Scored {n_unique_pairs} pairs via GNN in {gnn_elapsed:.2f}s.")

    # 6. Compute and cache V(pair) for all unique pairs
    pair_rankings: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for (cand_a, cand_b), probs in zip(unique_pairs, all_probs):
        da_id = cand_a["drug_id"]
        db_id = cand_b["drug_id"]
        p_ant, p_add, p_syn = probs
        key = (min(da_id, db_id), max(da_id, db_id))
        ranking_info = compute_pair_score_v(
            da_id,
            db_id,
            p_synergy=p_syn,
            w_synergy=w_synergy,
            w_toxicity=w_toxicity,
            w_redundancy=w_redundancy,
            strict_known_only=strict_known_only,
        )
        pair_rankings[key] = ranking_info

    metadata["n_pairs_scored"] = n_unique_pairs

    # 7. Systematically Compose All Triples C(M, 3)
    # For M=10: 120 triples; for M=15: 455 triples; for M=20: 1,140 triples
    candidate_triples = list(itertools.combinations(candidates, 3))
    scored_triples: List[Dict[str, Any]] = []
    truncated = False
    t_eval_start = time.time()

    for ca, cb, cc in candidate_triples:
        # Enforce hard timeout cap
        if time.time() - t_eval_start > time_budget_sec:
            logger.warning(
                f"[TRIPLE SEARCH] Reached hard time budget cap ({time_budget_sec}s). "
                f"Truncating search after scoring {len(scored_triples)} triples."
            )
            truncated = True
            break

        triple_eval = score_triple_combination(
            drug_a=ca,
            drug_b=cb,
            drug_c=cc,
            pair_rankings=pair_rankings,
            w_synergy=w_synergy,
            w_toxicity=w_toxicity,
            w_redundancy=w_redundancy,
            strict_known_only=strict_known_only,
        )
        scored_triples.append(triple_eval)

    metadata["n_triples_scored"] = len(scored_triples)
    metadata["truncated"] = truncated

    # 8. Sort by aggregate_min descending (weakest-link primary), secondary mean, stable IDs
    scored_triples.sort(
        key=lambda t: (
            -t["aggregate_min"],
            -t["aggregate_mean"],
            t["drug_a"],
            t["drug_b"],
            t["drug_c"],
        )
    )

    final_top_k = scored_triples[:top_k]
    for idx, hit in enumerate(final_top_k, 1):
        hit["rank"] = idx

    total_time = round(time.time() - start_time, 3)
    metadata["time_taken_sec"] = total_time

    logger.info(
        f"[TRIPLE SEARCH] Completed composed triple search. Returning top {len(final_top_k)} "
        f"triples (scored {len(scored_triples)} triples from {len(candidates)} candidates in {total_time}s). "
        f"Caption verified: '{COMPOSITION_CAPTION}'"
    )

    return final_top_k, metadata
