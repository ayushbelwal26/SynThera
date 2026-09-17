"""
src/search.py — Disease-driven Drug Combination Discovery & Synergy Search.

Pipeline Stages:
- Stage 1: Candidate Drug Discovery (find_candidate_drugs)
  Traverses PrimeKG for direct indications/off-label uses and target-overlap proteins.
- Stage 2: Candidate Pair Scoring (score_candidate_pairs)
  Forms all unique pairs from candidates (e.g. 20 drugs -> 190 pairs), runs a fast
  forward-only GNN scoring pass, and ranks pairs by p_synergy descending.
- Stage 3: Full Explanations on Top-K (get_full_explanations_for_top_k)
  Takes the top-K scored pairs and runs full graph-attribution explanations,
  necessity/sufficiency faithfulness tests, and PubMed literature retrieval.
"""

import os
import sys
import re
import time
import logging
import argparse
from collections import defaultdict
from typing import Dict, List, Optional, Tuple, Any

import torch
import torch.nn.functional as F
from torch_geometric.data import HeteroData
from torch_geometric.loader import LinkNeighborLoader

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("search")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED = os.path.join(ROOT, "data", "processed")
DEFAULT_HETERODATA = os.path.join(PROCESSED, "heterodata.pt")
DEFAULT_CHECKPOINT = os.path.join(ROOT, "models", "synergy_gnn_final.ckpt")

# In-memory caches for fast repeated queries
_HETERODATA_CACHE = None
_MODULE_CACHE = None
_NODE_MAPS_CACHE = None
_NAME_LOOKUP_CACHE = None
_ID_LOOKUP_CACHE = None
_DRUG_TARGETS_CACHE = None
_CYP_PROTEIN_INDICES_CACHE: Optional[set] = None

# Pattern matching cytochrome P450 enzyme names (shared hepatic metabolism, not disease mechanism)
_CYP_NAME_PATTERN = re.compile(r"^CYP\d", re.IGNORECASE)

# Pattern matching non-drug biological entities (cell lines, tissues, primary cells erroneously typed as 'drug' nodes in KG)
_NON_DRUG_ENTITY_PATTERN = re.compile(
    r"\b(keratinocyte|fibroblast|cell line|tissue|epithelial|endothelial|myoblast|hepatocyte|"
    r"lymphoblast|monocyte|macrophage|primary cell|stem cell|foreskin|cell sample|tissue sample|"
    r"bio-sample|cell culture|cell strain)\b",
    re.IGNORECASE,
)

# p_synergy threshold above which we flag a result as potentially out-of-distribution
_HIGH_CONFIDENCE_THRESHOLD = 0.95


# ---------------------------------------------------------------------------
# Helper: Lazy graph & model loader
# ---------------------------------------------------------------------------

def _build_cyp_protein_set(prot_name_lookup: Dict[int, str]) -> set:
    """Return the set of protein integer indices whose names match the CYP enzyme pattern."""
    return {idx for idx, name in prot_name_lookup.items() if _CYP_NAME_PATTERN.match(name)}


def _load_resources(
    heterodata: Optional[HeteroData] = None,
    node_maps: Optional[Dict[str, Dict[str, int]]] = None,
) -> Tuple[HeteroData, Dict[str, Dict[str, int]], Dict[str, Dict[int, str]], Dict[str, Dict[int, str]], Dict[int, set]]:
    """
    Ensure heterodata, node_maps, name/id lookups, and drug targets are loaded
    and cached in memory.
    """
    global _HETERODATA_CACHE, _NODE_MAPS_CACHE, _NAME_LOOKUP_CACHE, _ID_LOOKUP_CACHE
    global _DRUG_TARGETS_CACHE, _CYP_PROTEIN_INDICES_CACHE

    if heterodata is None:
        if _HETERODATA_CACHE is None:
            if not os.path.exists(DEFAULT_HETERODATA):
                raise FileNotFoundError(f"HeteroData not found at {DEFAULT_HETERODATA}. Run pipeline first.")
            logger.info(f"Loading HeteroData from {DEFAULT_HETERODATA}...")
            _HETERODATA_CACHE = torch.load(DEFAULT_HETERODATA, map_location="cpu", weights_only=False)
        heterodata = _HETERODATA_CACHE

    if node_maps is None:
        if _NODE_MAPS_CACHE is None:
            sys.path.insert(0, os.path.join(ROOT, "src"))
            from predict import _get_node_maps
            _NODE_MAPS_CACHE = _get_node_maps(heterodata)
        node_maps = _NODE_MAPS_CACHE

    if _NAME_LOOKUP_CACHE is None or _ID_LOOKUP_CACHE is None:
        sys.path.insert(0, os.path.join(ROOT, "src"))
        from explain import _build_name_lookups
        _NAME_LOOKUP_CACHE, _ID_LOOKUP_CACHE = _build_name_lookups(heterodata)

    if _DRUG_TARGETS_CACHE is None:
        dp_edge = heterodata[("drug", "drug_protein", "gene/protein")].edge_index
        dt = defaultdict(set)
        for d, p in zip(dp_edge[0].tolist(), dp_edge[1].tolist()):
            dt[d].add(p)
        _DRUG_TARGETS_CACHE = dt

    if _CYP_PROTEIN_INDICES_CACHE is None:
        _CYP_PROTEIN_INDICES_CACHE = _build_cyp_protein_set(_NAME_LOOKUP_CACHE.get("gene/protein", {}))
        logger.info(f"CYP metabolic enzyme filter: {len(_CYP_PROTEIN_INDICES_CACHE)} CYP proteins identified and excluded from indirect matching.")

    return heterodata, node_maps, _NAME_LOOKUP_CACHE, _ID_LOOKUP_CACHE, _DRUG_TARGETS_CACHE


def _load_model_cached(
    checkpoint_path: str = DEFAULT_CHECKPOINT,
    heterodata: Optional[HeteroData] = None,
    device: Optional[str] = None,
):
    """Load and cache the trained SynergyModule and HeteroData."""
    global _MODULE_CACHE, _HETERODATA_CACHE

    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    if _MODULE_CACHE is None or _HETERODATA_CACHE is None:
        sys.path.insert(0, os.path.join(ROOT, "src"))
        from predict import load_model
        module, hdata, dev = load_model(
            checkpoint_path=checkpoint_path,
            heterodata_path=DEFAULT_HETERODATA if heterodata is None else None,
            device=device,
        )
        _MODULE_CACHE = module
        if _HETERODATA_CACHE is None:
            _HETERODATA_CACHE = hdata

    return _MODULE_CACHE, _HETERODATA_CACHE, device


# ---------------------------------------------------------------------------
# Stage 1: Disease Name Resolver & Candidate Discovery
# ---------------------------------------------------------------------------

def resolve_disease_nodes(
    disease_name: str,
    dis_name_lookup: Dict[int, str],
) -> Tuple[List[int], List[str]]:
    """
    Resolve a user-provided disease string to one or more disease node indices
    in the PrimeKG graph.
    """
    q = disease_name.strip().lower()
    if not q:
        return [], []

    def is_valid(name: str) -> bool:
        nl = name.lower()
        if "excluding" in nl and "excluding" not in q:
            return False
        if "susceptibility to" in nl and "susceptibility" not in q:
            return False
        return True

    # 1. Exact match
    exact = [idx for idx, name in dis_name_lookup.items() if name.lower() == q and is_valid(name)]
    if exact:
        return exact, [dis_name_lookup[i] for i in exact]

    # 2. Normalized exact match (strip parenthesis)
    norm_exact = [
        idx for idx, name in dis_name_lookup.items()
        if re.sub(r"\s*\(.*?\)", "", name.lower()).strip() == q and is_valid(name)
    ]
    if norm_exact:
        sub = [
            idx for idx, name in dis_name_lookup.items()
            if q in name.lower() and is_valid(name)
        ]
        combined = list(dict.fromkeys(norm_exact + sub))
        return combined, [dis_name_lookup[i] for i in combined]

    # 3. Substring match
    sub = [
        idx for idx, name in dis_name_lookup.items()
        if q in name.lower() and is_valid(name)
    ]
    if sub:
        return sub, [dis_name_lookup[i] for i in sub]

    # 4. Synonym / token match (common oncology synonyms)
    synonyms = {
        "carcinoma": ["carcinoma", "cancer", "neoplasm", "tumor", "malignant"],
        "cancer": ["cancer", "carcinoma", "neoplasm", "tumor", "malignant"],
        "tumor": ["tumor", "neoplasm", "cancer", "carcinoma"],
        "neoplasm": ["neoplasm", "tumor", "cancer", "carcinoma"],
        "ovarian": ["ovarian", "ovary"],
    }
    tokens = re.findall(r"\w+", q)
    token_patterns = []
    for t in tokens:
        if t in synonyms:
            token_patterns.append(synonyms[t])
        else:
            token_patterns.append([t])

    matches = []
    for idx, name in dis_name_lookup.items():
        if not is_valid(name):
            continue
        nl = name.lower()
        if all(any(variant in nl for variant in group) for group in token_patterns):
            matches.append(idx)

    if matches:
        return matches, [dis_name_lookup[i] for i in matches]

    return [], []


def find_candidate_drugs(
    disease_name: str,
    heterodata: Optional[HeteroData] = None,
    node_maps: Optional[Dict[str, Dict[str, int]]] = None,
    max_candidates: int = 30,
    max_indirect_fraction: float = 0.30,
) -> List[Dict[str, Any]]:
    """
    Find drugs plausibly relevant to a given disease by traversing the PrimeKG graph.

    Two tiers of candidates:
    - Direct: drugs with an 'indication' or 'off-label use' edge to the disease node(s).
    - Indirect (target_overlap): drugs whose targets overlap with disease-associated proteins,
      EXCLUDING any drug whose ONLY shared proteins are CYP (cytochrome P450) metabolic enzymes —
      which reflect shared hepatic metabolism, not a shared disease mechanism.

    Composition rule: indirect candidates are capped at max_indirect_fraction of max_candidates
    (default 30%), so direct-indication drugs dominate the pool.
    """
    global _CYP_PROTEIN_INDICES_CACHE

    data, n_maps, name_lookup, id_lookup, drug_targets = _load_resources(heterodata, node_maps)

    # Ensure CYP index set is populated
    if _CYP_PROTEIN_INDICES_CACHE is None:
        _CYP_PROTEIN_INDICES_CACHE = _build_cyp_protein_set(name_lookup.get("gene/protein", {}))

    cyp_indices: set = _CYP_PROTEIN_INDICES_CACHE

    dis_name_lookup = name_lookup["disease"]
    drug_name_lookup = name_lookup["drug"]
    drug_id_lookup = id_lookup["drug"]

    disease_node_indices, matched_names = resolve_disease_nodes(disease_name, dis_name_lookup)
    if not disease_node_indices:
        logger.warning(
            f"Disease '{disease_name}' could not be resolved to any node in PrimeKG. "
            "Returning empty candidate list."
        )
        return []

    ind_edge = data[("drug", "indication", "disease")].edge_index
    off_edge = data[("drug", "off-label use", "disease")].edge_index
    dp_edge = data[("disease", "disease_protein", "gene/protein")].edge_index

    direct_drug_indices = set()
    for d_idx in disease_node_indices:
        direct_drug_indices.update(ind_edge[0][ind_edge[1] == d_idx].tolist())
        direct_drug_indices.update(off_edge[0][off_edge[1] == d_idx].tolist())

    disease_proteins = set()
    for d_idx in disease_node_indices:
        disease_proteins.update(dp_edge[1][dp_edge[0] == d_idx].tolist())

    # Non-CYP disease proteins: the mechanistically relevant subset
    disease_proteins_non_cyp = disease_proteins - cyp_indices

    # ---- Direct candidates ----
    direct_candidates: List[Dict[str, Any]] = []
    for d_idx in direct_drug_indices:
        d_name = drug_name_lookup[d_idx]
        if _NON_DRUG_ENTITY_PATTERN.search(d_name):
            logger.warning(f"Excluding non-drug biological entity artifact from direct candidates: '{d_name}' ({drug_id_lookup[d_idx]})")
            continue
        shared = len(disease_proteins & drug_targets[d_idx]) if disease_proteins else 0
        direct_candidates.append({
            "drug_id": drug_id_lookup[d_idx],
            "drug_name": d_name,
            "match_type": "direct",
            "score": 1.0,
            "shared_targets": shared,
        })

    direct_candidates.sort(key=lambda x: (x["shared_targets"], x["drug_name"]), reverse=True)

    # ---- Indirect candidates (target_overlap, CYP-filtered) ----
    indirect_candidates: List[Dict[str, Any]] = []
    if disease_proteins_non_cyp:
        for d_idx, targets in drug_targets.items():
            if d_idx in direct_drug_indices:
                continue
            d_name = drug_name_lookup[d_idx]
            if _NON_DRUG_ENTITY_PATTERN.search(d_name):
                continue
            # Only consider overlap with NON-CYP disease proteins
            shared_non_cyp = targets & disease_proteins_non_cyp
            if not shared_non_cyp:
                # Either no overlap, or overlap is entirely CYP — skip
                continue
            score = len(shared_non_cyp) / len(targets)
            indirect_candidates.append({
                "drug_id": drug_id_lookup[d_idx],
                "drug_name": d_name,
                "match_type": "target_overlap",
                "score": round(score, 4),
                "shared_targets": len(shared_non_cyp),
            })

        indirect_candidates.sort(key=lambda x: (x["shared_targets"], x["score"]), reverse=True)
    elif disease_proteins:
        # All disease proteins are CYP — warn and skip indirect entirely
        logger.warning(
            f"All disease-associated proteins for '{disease_name}' are CYP enzymes. "
            "Skipping indirect candidate matching to avoid metabolism-only false positives."
        )

    # ---- Composition: direct-first, indirect capped at max_indirect_fraction ----
    max_direct = max_candidates  # fill with as many direct as we have
    max_indirect = max(0, round(max_candidates * max_indirect_fraction))

    combined: List[Dict[str, Any]] = direct_candidates[:max_direct]
    if len(combined) < max_candidates:
        # Only supplement with indirect if we haven't filled from direct alone
        indirect_slots = min(max_indirect, max_candidates - len(combined))
        combined.extend(indirect_candidates[:indirect_slots])

    n_direct = sum(1 for c in combined if c["match_type"] == "direct")
    n_indirect = len(combined) - n_direct
    logger.info(
        f"Candidate pool for '{disease_name}': {len(combined)} drugs "
        f"({n_direct} direct-indication, {n_indirect} target-overlap/speculative). "
        f"CYP-only indirect candidates excluded."
    )

    return combined


# ---------------------------------------------------------------------------
# Stage 2: Fast Candidate Pair Scoring (Lightweight Forward Pass)
# ---------------------------------------------------------------------------

def score_candidate_pairs(
    disease_name: str,
    cell_line_name: str,
    heterodata: Optional[HeteroData] = None,
    module: Optional[Any] = None,
    device: Optional[str] = None,
    max_candidate_drugs: int = 20,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """
    Form all unique pairs from the candidate drug pool and score them using
    a fast forward-only pass through the trained GNN model.

    Parameters:
    -----------
    disease_name : str
        Target disease (e.g. 'glioblastoma').
    cell_line_name : str
        Target cell line (e.g. 'T98G'). Validated against known cell lines.
    heterodata : HeteroData, optional
    module : SynergyModule, optional
    device : str, optional ('cuda' or 'cpu')
    max_candidate_drugs : int, default 20
        Maximum candidate drugs to form pairs from (20 drugs = 190 pairs).
    top_k : int, default 5
        Number of top-scoring pairs to return.

    Returns:
    --------
    List[Dict[str, Any]]:
        Top-K pairs sorted by p_synergy descending:
        [{drug_a, drug_b, p_synergy, p_additive, p_antagonism, predicted_class, ...}]
    """
    sys.path.insert(0, os.path.join(ROOT, "src"))
    from predict import THRESHOLD_SYNERGY, THRESHOLD_ANTAGONISM, _get_node_maps

    # 1. Load resources & model
    if module is None or heterodata is None:
        module, heterodata, device = _load_model_cached(heterodata=heterodata, device=device)
    elif device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    node_maps = _get_node_maps(heterodata)
    drug_id2idx = node_maps.get("drug", {})
    cell_line_map = heterodata.cell_line_map

    # 2. Validate cell line strictly
    if cell_line_name not in cell_line_map:
        sample_cls = sorted(list(cell_line_map.keys()))[:8]
        raise ValueError(
            f"Cell line '{cell_line_name}' is not recognized in knowledge graph. "
            f"Available cell lines include: {sample_cls} (total {len(cell_line_map)})."
        )

    cell_idx = cell_line_map[cell_line_name]

    # 3. Stage 1: Find candidate drugs
    candidates = find_candidate_drugs(
        disease_name,
        heterodata=heterodata,
        node_maps=node_maps,
        max_candidates=max_candidate_drugs,
    )

    if len(candidates) < 2:
        logger.warning(
            f"Fewer than 2 candidate drugs ({len(candidates)}) found for disease '{disease_name}'. "
            "Cannot form pairs."
        )
        return []

    # 4. Form all unique unordered pairs
    pairs = []
    for i in range(len(candidates)):
        for j in range(i + 1, len(candidates)):
            pairs.append((candidates[i], candidates[j]))

    num_pairs = len(pairs)
    logger.info(f"Formed {num_pairs} unique candidate pairs from {len(candidates)} drugs for '{disease_name}' @ '{cell_line_name}'.")

    # 5. Lightweight batched forward pass
    t_start = time.time()

    a_indices = [drug_id2idx[p[0]["drug_id"]] for p in pairs]
    b_indices = [drug_id2idx[p[1]["drug_id"]] for p in pairs]

    data_work = heterodata.clone()
    edge_index_all = torch.tensor([a_indices, b_indices], dtype=torch.long)
    dummy_label_all = torch.tensor([[0, cell_idx]] * num_pairs, dtype=torch.long)

    data_work["drug", "synergy_pair", "drug"].edge_index = edge_index_all
    data_work["drug", "synergy_pair", "drug"].edge_label_index = edge_index_all
    data_work["drug", "synergy_pair", "drug"].edge_label = dummy_label_all

    num_neighbors = {
        et: ([0, 0] if et == ("drug", "synergy_pair", "drug") else [5, 3])
        for et in data_work.edge_types
    }

    loader = LinkNeighborLoader(
        data=data_work,
        num_neighbors=num_neighbors,
        edge_label_index=(("drug", "synergy_pair", "drug"), edge_index_all),
        edge_label=dummy_label_all,
        batch_size=32,
        shuffle=False,
    )

    all_logits = []
    module.eval()
    with torch.no_grad():
        for batch in loader:
            batch = batch.to(device)
            logits, _ = module(batch)
            all_logits.append(logits.cpu())

    all_logits = torch.cat(all_logits, dim=0)
    all_probs = F.softmax(all_logits, dim=-1).tolist()

    scoring_duration = time.time() - t_start
    print(
        f"\n[Stage 2] Scored {num_pairs} candidate pairs in {scoring_duration:.2f}s "
        f"({(scoring_duration / num_pairs) * 1000:.1f}ms per pair) on {device}."
    )

    # 6. Parse and sort results
    ood_flagged = 0
    scored_pairs: List[Dict[str, Any]] = []
    for p, probs in zip(pairs, all_probs):
        p_ant, p_add, p_syn = probs
        if p_syn > THRESHOLD_SYNERGY:
            pred = "synergy"
        elif p_ant > THRESHOLD_ANTAGONISM:
            pred = "antagonism"
        else:
            pred = "additive"

        # Out-of-distribution sanity flag: extremely high confidence on a speculative pair
        # warrants extra scrutiny — model may be overconfident outside training distribution
        is_speculative = (
            p[0]["match_type"] == "target_overlap" or p[1]["match_type"] == "target_overlap"
        )
        high_confidence_caveat = bool(p_syn > _HIGH_CONFIDENCE_THRESHOLD and is_speculative)
        if high_confidence_caveat:
            ood_flagged += 1

        # Determine pair evidence tier:
        # Tier 1: both direct indication matches
        # Tier 2: mixed (one direct, one target_overlap)
        # Tier 3: both target_overlap
        match_a, match_b = p[0]["match_type"], p[1]["match_type"]
        if match_a == "direct" and match_b == "direct":
            tier = 1
            pair_tier_name = "both_direct"
        elif match_a == "direct" or match_b == "direct":
            tier = 2
            pair_tier_name = "mixed"
        else:
            tier = 3
            pair_tier_name = "both_indirect"

        scored_pairs.append({
            "drug_a": p[0]["drug_id"],
            "drug_a_name": p[0]["drug_name"],
            "drug_b": p[1]["drug_id"],
            "drug_b_name": p[1]["drug_name"],
            "drug_a_match_type": match_a,
            "drug_b_match_type": match_b,
            "pair_tier": tier,
            "pair_tier_name": pair_tier_name,
            "p_synergy": round(p_syn, 4),
            "p_additive": round(p_add, 4),
            "p_antagonism": round(p_ant, 4),
            "predicted_class": pred,
            "cell_line": cell_line_name,
            "high_confidence_caveat": high_confidence_caveat,
        })

    # Tiered ranking: Sort first by pair_tier ascending (Tier 1 > Tier 2 > Tier 3),
    # then by p_synergy descending within each tier.
    scored_pairs.sort(key=lambda x: (x["pair_tier"], -x["p_synergy"]))

    if ood_flagged > 0:
        print(
            f"\n[Stage 2] [!] {ood_flagged} pair(s) flagged high_confidence_caveat=True "
            f"(p_synergy > {_HIGH_CONFIDENCE_THRESHOLD:.0%} on speculative/indirect drug). "
            "These involve target-overlap candidates without a direct disease indication — "
            "treat with extra scrutiny before presenting as strong findings."
        )

    return scored_pairs[:top_k]


# ---------------------------------------------------------------------------
# Stage 3: Full Explanations on Top-K Pairs
# ---------------------------------------------------------------------------

def get_full_explanations_for_top_k(
    top_k_pairs: List[Dict[str, Any]],
    cell_line_name: str,
    module: Optional[Any] = None,
    heterodata: Optional[HeteroData] = None,
    device: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Run the full explain_prediction() pipeline (subgraph sampling, gradient
    attribution, necessity & sufficiency faithfulness checks, and PubMed
    literature retrieval) ONLY on the top-K pairs selected by Stage 2.

    Parameters:
    -----------
    top_k_pairs : List[Dict[str, Any]]
        Output list of top-K pairs from score_candidate_pairs().
    cell_line_name : str
        Target cell line.
    module : SynergyModule, optional
    heterodata : HeteroData, optional
    device : str, optional

    Returns:
    --------
    List[Dict[str, Any]]:
        List of full explanation dictionaries matching explain_prediction() format.
    """
    sys.path.insert(0, os.path.join(ROOT, "src"))
    from explain import explain_prediction

    if module is None or heterodata is None:
        module, heterodata, device = _load_model_cached(heterodata=heterodata, device=device)
    elif device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    full_explanations: List[Dict[str, Any]] = []

    print(f"\n[Stage 3] Generating full explanations for top {len(top_k_pairs)} pairs...")
    t_start = time.time()

    for idx, pair in enumerate(top_k_pairs, 1):
        drug_a_id = pair["drug_a"]
        drug_b_id = pair["drug_b"]
        a_name = pair.get("drug_a_name", drug_a_id)
        b_name = pair.get("drug_b_name", drug_b_id)

        print(f"\n--- [{idx}/{len(top_k_pairs)}] Explaining {a_name} + {b_name} @ {cell_line_name} ---")
        t_pair = time.time()
        expl = explain_prediction(
            drug_a_id=drug_a_id,
            drug_b_id=drug_b_id,
            cell_line_name=cell_line_name,
            module=module,
            heterodata=heterodata,
            device=device,
            run_faithfulness=False,  # Skip ablation during search; computed on-demand via /predict
        )
        expl_duration = time.time() - t_pair
        print(f"    Completed in {expl_duration:.2f}s")
        full_explanations.append(expl)

    total_expl_duration = time.time() - t_start
    print(f"\n[Stage 3] Generated all {len(top_k_pairs)} explanations in {total_expl_duration:.2f}s.")

    return full_explanations


# ---------------------------------------------------------------------------
# CLI / Demo Runner
# ---------------------------------------------------------------------------

def _run_stage2_demo(
    disease: str = "glioblastoma",
    cell_line: str = "T98G",
    max_candidates: int = 20,
    top_k: int = 5,
) -> None:
    """Run full Stage 1 + Stage 2 + Stage 3 pipeline and report total wall-clock time."""
    print("\n" + "=" * 78)
    print("  SYNTHERA: END-TO-END DRUG COMBINATION DISCOVERY & EXPLANATION PIPELINE")
    print("=" * 78)
    print(f"Target Disease   : {disease}")
    print(f"Target Cell Line : {cell_line}")
    print(f"Candidate Pool   : {max_candidates} drugs ({max_candidates * (max_candidates - 1) // 2} pairs)")
    print(f"Top-K Explanations: {top_k}")
    print("=" * 78)

    t_pipeline_start = time.time()

    # Pre-load resources
    t0 = time.time()
    module, heterodata, device = _load_model_cached()
    t_load = time.time() - t0
    print(f"\n[Init] Model and graph ready in {t_load:.2f}s (device: {device}).")

    # Stage 1: Candidate Drug Discovery
    t1 = time.time()
    candidates = find_candidate_drugs(disease, heterodata=heterodata, max_candidates=max_candidates)
    t_stage1 = time.time() - t1
    print(f"\n[Stage 1] Found {len(candidates)} candidate drugs in {t_stage1:.3f}s:")
    for i, c in enumerate(candidates[:8], 1):
        print(f"  {i:>2}. {c['drug_name']:<30} ({c['drug_id']}) | {c['match_type']:<15} | score={c['score']:.3f}")
    if len(candidates) > 8:
        print(f"  ... ({len(candidates) - 8} more)")

    # Stage 2: Candidate Pair Scoring
    t2 = time.time()
    top_pairs = score_candidate_pairs(
        disease_name=disease,
        cell_line_name=cell_line,
        heterodata=heterodata,
        module=module,
        device=device,
        max_candidate_drugs=max_candidates,
        top_k=top_k,
    )
    t_stage2 = time.time() - t2

    print(f"\n[Stage 2] Top {len(top_pairs)} Candidate Pairs (Ranked by Evidence Tier, then p_synergy):")
    print("-" * 90)
    print(f"{'#':<3} {'Drug A':<22} {'Drug B':<22} {'Tier':<14} {'Class':<10} {'p_Syn':<8} {'p_Add':<8} {'p_Ant'}")
    print("-" * 90)
    for i, p in enumerate(top_pairs, 1):
        tier_label = f"T{p['pair_tier']}:{p['pair_tier_name']}"
        print(
            f"{i:<3} {p['drug_a_name']:<22} {p['drug_b_name']:<22} "
            f"{tier_label:<14} {p['predicted_class'].upper():<10} {p['p_synergy']:<8.4f} "
            f"{p['p_additive']:<8.4f} {p['p_antagonism']:.4f}"
        )
    print("-" * 90)

    # Stage 3: Full Explanations on Top-K
    t3 = time.time()
    full_explanations = get_full_explanations_for_top_k(
        top_k_pairs=top_pairs,
        cell_line_name=cell_line,
        module=module,
        heterodata=heterodata,
        device=device,
    )
    t_stage3 = time.time() - t3

    total_pipeline_time = time.time() - t_pipeline_start

    # Print formatted explanations
    print("\n" + "=" * 78)
    print("  FULL BIOLOGICALLY GROUNDED EXPLANATIONS FOR TOP CANDIDATES")
    print("=" * 78)

    for i, expl in enumerate(full_explanations, 1):
        print(f"\n[{i}] {expl['drug_a_name']} + {expl['drug_b_name']} @ {expl['cell_line']}")
        print(f"    Predicted: {expl['predicted_class'].upper()} (p_syn={expl['p_synergy']:.3f}, p_add={expl['p_additive']:.3f}, p_ant={expl['p_antagonism']:.3f})")
        print(f"    Faithfulness: Necessity={expl.get('necessity_delta_pct', 0.0):+.1f}% | Sufficiency={expl.get('sufficiency_retained_pct', 0.0):.1f}%")
        print(f"    Mechanism: \"{expl.get('explanation_text')}\"")

        lit = expl.get("supporting_literature", [])
        if lit:
            print("    Supporting Literature:")
            for item in lit:
                print(f"      - {item.get('first_author', '')} ({item.get('year', '')}): \"{item.get('title', '')}\" [PMID {item.get('pmid', '')}]")
        else:
            print("    Supporting Literature: (No direct matching literature found)")

    # Pipeline Performance Summary
    print("\n" + "=" * 78)
    print("  PIPELINE WALL-CLOCK PERFORMANCE BREAKDOWN")
    print("=" * 78)
    print(f"  Model & Graph Warmup        : {t_load:.2f}s")
    print(f"  Stage 1 (Candidate Discovery) : {t_stage1:.3f}s")
    print(f"  Stage 2 (Scoring 190 Pairs)   : {t_stage2:.2f}s  ({(t_stage2 / 190) * 1000:.1f}ms / pair)")
    print(f"  Stage 3 (Explanations Top-5)  : {t_stage3:.2f}s  ({t_stage3 / max(1, len(full_explanations)):.2f}s / pair)")
    print(f"  Total End-to-End Pipeline   : {total_pipeline_time:.2f}s")
    print("=" * 78 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="SynThera Disease-driven Drug Combination Discovery & Synergy Search."
    )
    parser.add_argument(
        "--disease",
        type=str,
        default="glioblastoma",
        help="Disease name to search combinations for (default: 'glioblastoma').",
    )
    parser.add_argument(
        "--cell-line",
        type=str,
        default="T98G",
        help="Cell line to evaluate synergy on (default: 'T98G').",
    )
    parser.add_argument(
        "--max-candidates",
        type=int,
        default=20,
        help="Max candidate drugs from Stage 1 (default: 20 -> 190 pairs).",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of top candidate pairs to explain (default: 5).",
    )
    parser.add_argument(
        "--stage1-only",
        action="store_true",
        help="Run Stage 1 candidate discovery only.",
    )

    args = parser.parse_args()

    if args.stage1_only:
        candidates = find_candidate_drugs(args.disease, max_candidates=args.max_candidates)
        print(f"Found {len(candidates)} candidates for '{args.disease}':")
        for i, c in enumerate(candidates, 1):
            print(f"{i:>2}. {c['drug_name']:<30} ({c['drug_id']}) | {c['match_type']:<15} | score={c['score']:.3f}")
    else:
        _run_stage2_demo(
            disease=args.disease,
            cell_line=args.cell_line,
            max_candidates=args.max_candidates,
            top_k=args.top_k,
        )
