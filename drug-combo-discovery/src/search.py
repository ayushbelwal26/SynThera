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
import math
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

# ---------------------------------------------------------------------------
# Therapeutic Candidate Quality Filter (Allow/Deny Rules)
# ---------------------------------------------------------------------------

# Platinum coordination chemotherapy drugs (MUST BE PRESERVED)
# Matches cisplatin, carboplatin, oxaliplatin, nedaplatin, lobaplatin, satraplatin, etc.
# Excludes pure elemental platinum ('platinum', 'platinum cation').
_PLATINUM_CHEMOTHERAPY_PATTERN = re.compile(
    r"\b(cisplatin|carboplatin|oxaliplatin|nedaplatin|lobaplatin|heptaplatin|picoplatin|satraplatin)\b|\b\w*platin\b",
    re.IGNORECASE,
)

# Known approved inorganic / organometallic / photodynamic oncology therapeutics
# E.g., Arsenic trioxide is FDA-approved for acute promyelocytic leukemia (APL)
_ONCOLOGY_THERAPEUTIC_WHITELIST_IDS = {
    "DB01169",  # Arsenic trioxide (Trisenox, APL leukemia therapy)
    "DB00707",  # Porfimer sodium (Photodynamic antineoplastic therapy)
    "DB00252",  # Bleomycin (Glycopeptide antineoplastic)
}

_ONCOLOGY_THERAPEUTIC_WHITELIST_NAMES = {
    "arsenic trioxide",
    "porfimer sodium",
    "bleomycin",
}

# Elemental metals and pure mineral cations (DENY)
_ELEMENTAL_MINERAL_PATTERN = re.compile(
    r"^(zinc|copper|magnesium|calcium|manganese|iron|cobalt|nickel|chromium|cadmium|lead|"
    r"barium|strontium|lithium|aluminum|sodium|potassium|arsenic|selenium|titanium|gallium|"
    r"silver|gold|bismuth|mercury|platinum)(\s+(cation|ion|elemental|powder|metal|colloidal|unspecified form))?$",
    re.IGNORECASE,
)

# Simple inorganic metal salts (DENY): metal cation + simple counterion
_INORGANIC_METAL_SALT_PATTERN = re.compile(
    r"^(zinc|copper|magnesium|calcium|manganese|ferrous|ferric|iron|aluminum|sodium|potassium|"
    r"lithium|barium|strontium|bismuth|silver|gold|ammonium|cadmium|lead|mercury|titanium)\b"
    r".*\b(chloride|dichloride|trichloride|sulfate|oxide|trioxide|dioxide|hydroxide|trihydroxide|"
    r"carbonate|bicarbonate|phosphate|acetate|gluconate|citrate|bromide|iodide|fluoride|nitrate|"
    r"stearate|undecylenate|pyrithione|picolinate|ascorbate|glycinate|trisilicate|hypochlorite|"
    r"peroxide|salicylate|dextran|pyrophosphate|gluceptate|tartrate|fumarate|lactate)\b",
    re.IGNORECASE,
)

# Any zinc compound (dietary mineral / supplement / inorganic salt)
_ZINC_SUPPLEMENT_PATTERN = re.compile(r"\bzinc\b", re.IGNORECASE)

# Solvents, excipients, vehicles, buffers (DENY)
_SOLVENT_EXCIPIENT_PATTERN = re.compile(
    r"\b(water|sterile water|heavy water|deuterium oxide|saline|normal saline|ringer's solution|"
    r"glycerol|glycerin|propylene glycol|polyethylene glycol|peg-\d+|ethylene glycol|"
    r"dimethyl sulfoxide|dmso|mineral oil|paraffin|petrolatum|polysorbate|tween\s*\d+|"
    r"sodium lauryl sulfate|sodium dodecyl sulfate)\b",
    re.IGNORECASE,
)

# Non-therapeutic diagnostic agents and contrast media (DENY)
_DIAGNOSTIC_AGENT_PATTERN = re.compile(
    r"\b(indocyanine green|fluorescein|trypan blue|patent blue|iohexol|iopamidol|iodixanol|"
    r"diatrizoate|ioxaglate|gadopentetate|gadoteridol|gadobutrol)\b",
    re.IGNORECASE,
)

# Non-drug biological entities (cell lines, tissues, primary cells erroneously typed as 'drug' nodes in KG)
_NON_DRUG_ENTITY_PATTERN = re.compile(
    r"\b(keratinocyte|fibroblast|cell line|tissue|epithelial|endothelial|myoblast|hepatocyte|"
    r"lymphoblast|monocyte|macrophage|primary cell|stem cell|foreskin|cell sample|tissue sample|"
    r"bio-sample|cell culture|cell strain)\b",
    re.IGNORECASE,
)


def is_valid_therapeutic_candidate(drug_name: str, drug_id: str = "") -> bool:
    """
    Classify whether an entity in PrimeKG is a plausible therapeutic drug candidate.

    Rule hierarchy:
    1. Deny non-drug biological entities (cell lines, tissues, fibroblasts).
    2. Whitelist known approved oncology inorganics/complexes (e.g. Arsenic trioxide DB01169).
    3. Whitelist platinum coordination chemotherapy drugs (e.g. Cisplatin, Carboplatin,
       Oxaliplatin, Nedaplatin), while excluding pure elemental platinum.
    4. Deny elemental metals and mineral cations (Zinc, Copper, Magnesium, Potassium, etc.).
    5. Deny simple inorganic metal salts (Zinc chloride, Zinc sulfate, Magnesium sulfate,
       Calcium chloride, Sodium chloride, etc.).
    6. Deny all zinc mineral/dietary supplements.
    7. Deny solvents, excipients, vehicles, and buffers (DMSO, Glycerol, Water, Saline, etc.).
    8. Deny diagnostic contrast media and radiopaque dyes without antineoplastic activity.
    """
    name_clean = drug_name.strip()
    name_lower = name_clean.lower()

    # 1. Deny non-drug biological entity artifacts
    if _NON_DRUG_ENTITY_PATTERN.search(name_clean):
        return False

    # 2. Allow known approved oncology inorganics / complexes
    if (drug_id and drug_id.upper() in _ONCOLOGY_THERAPEUTIC_WHITELIST_IDS) or (
        name_lower in _ONCOLOGY_THERAPEUTIC_WHITELIST_NAMES
    ):
        return True

    # 3. Allow platinum coordination chemotherapeutic agents (excluding elemental platinum metal)
    if _PLATINUM_CHEMOTHERAPY_PATTERN.search(name_clean):
        if not re.match(r"^(platinum|platinum\s+cation)$", name_clean, re.IGNORECASE):
            return True

    # 4. Deny elemental metals and mineral cations
    if _ELEMENTAL_MINERAL_PATTERN.match(name_clean):
        return False

    # 5. Deny simple inorganic metal salts
    if _INORGANIC_METAL_SALT_PATTERN.match(name_clean):
        return False

    # 6. Deny zinc dietary supplements and salts
    if _ZINC_SUPPLEMENT_PATTERN.search(name_clean):
        return False

    # 7. Deny solvents, excipients, vehicles
    if _SOLVENT_EXCIPIENT_PATTERN.search(name_clean):
        return False

    # 8. Deny diagnostic / contrast media
    if _DIAGNOSTIC_AGENT_PATTERN.search(name_clean):
        return False

    return True


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
        d_id = drug_id_lookup[d_idx]
        if not is_valid_therapeutic_candidate(d_name, d_id):
            logger.debug(f"Excluding non-therapeutic entity from direct candidates: '{d_name}' ({d_id})")
            continue
        shared = len(disease_proteins & drug_targets[d_idx]) if disease_proteins else 0
        direct_candidates.append({
            "drug_id": d_id,
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
            d_id = drug_id_lookup[d_idx]
            if not is_valid_therapeutic_candidate(d_name, d_id):
                continue
            # Only consider overlap with NON-CYP disease proteins
            shared_non_cyp = targets & disease_proteins_non_cyp
            if not shared_non_cyp:
                # Either no overlap, or overlap is entirely CYP — skip
                continue
            score = len(shared_non_cyp) / len(targets)
            indirect_candidates.append({
                "drug_id": d_id,
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
# Stage 2: Real GNN-Driven Combination Discovery (Beam, Greedy & MCTS)
# ---------------------------------------------------------------------------

def mcts_search_combinations(
    disease_name: str,
    cell_line_name: str,
    heterodata: Optional[HeteroData] = None,
    module: Optional[Any] = None,
    device: Optional[str] = None,
    max_candidate_drugs: int = 20,
    n_simulations: int = 50,
    mcts_c: float = 1.414,
    time_budget_sec: float = 15.0,
    top_k: int = 5,
    seed_drug_id: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Search candidate drug combinations using Monte Carlo Tree Search (MCTS) with UCT
    over depth-2 combination pairs, using the trained SynergyGNN as the terminal value function.

    MCTS Formulation:
    - Root (Depth 0): Uninitialized combination state.
    - Depth 1: Selection of first drug d_a from filtered therapeutic candidate pool.
    - Depth 2: Selection of partner drug d_b (d_b != d_a) from candidate pool.
    - Terminal State: Candidate pair (d_a, d_b).
    - Evaluation: Scored with trained SynergyGNN model (cached so each unique pair is scored at most once).
    - Value Function: v = p_synergy in [0, 1].
    - UCT Selection: Balances exploitation (average synergy score) and exploration (c * sqrt(ln(N_parent) / N_child)).
    - Guardrails: Strict wall-clock timeout (time_budget_sec, default 15s) sets truncated=true if hit.
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

    # 3. Candidate Generation (with non-drug and CYP filtering)
    candidates = find_candidate_drugs(
        disease_name,
        heterodata=heterodata,
        node_maps=node_maps,
        max_candidates=max_candidate_drugs,
    )
    candidates = [
        c for c in candidates
        if is_valid_therapeutic_candidate(c["drug_name"], c["drug_id"])
    ]

    if seed_drug_id and seed_drug_id in drug_id2idx:
        existing_ids = {c["drug_id"] for c in candidates}
        if seed_drug_id not in existing_ids:
            from explain import _build_name_lookups
            name_lookup, _ = _build_name_lookups(heterodata)
            seed_name = name_lookup.get("drug", {}).get(drug_id2idx[seed_drug_id], seed_drug_id)
            candidates.insert(0, {
                "drug_id": seed_drug_id,
                "drug_name": seed_name,
                "match_type": "seed",
                "score": 1.0,
                "shared_targets": 0,
            })

    if len(candidates) < 2:
        logger.warning(
            f"Fewer than 2 candidate drugs ({len(candidates)}) found for disease '{disease_name}'. Cannot form pairs."
        )
        return [], {
            "search_method": "mcts",
            "n_simulations": 0,
            "n_pairs_scored": 0,
            "candidate_pool_size": len(candidates),
            "truncated": False,
            "mcts_c": mcts_c,
            "cache_hits": 0,
            "max_candidates_scored": 0,
        }

    # Deterministic seeding for reproducibility
    torch.manual_seed(42)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(42)

    cand_ids = [c["drug_id"] for c in candidates]
    cand_by_id = {c["drug_id"]: c for c in candidates}

    # Internal pair evaluation cache and visit tracker
    pair_cache: Dict[Tuple[str, str], Dict[str, Any]] = {}
    pair_visits: Dict[Tuple[str, str], int] = {}
    cache_hits = 0
    n_pairs_scored = 0

    def score_single_pair(d_a: str, d_b: str) -> Dict[str, Any]:
        nonlocal n_pairs_scored
        a_idx = drug_id2idx[d_a]
        b_idx = drug_id2idx[d_b]
        data_work = heterodata.clone()
        edge_index = torch.tensor([[a_idx], [b_idx]], dtype=torch.long)
        dummy_label = torch.tensor([[0, cell_idx]], dtype=torch.long)

        data_work["drug", "synergy_pair", "drug"].edge_index = edge_index
        data_work["drug", "synergy_pair", "drug"].edge_label_index = edge_index
        data_work["drug", "synergy_pair", "drug"].edge_label = dummy_label

        num_neighbors = {
            et: ([0, 0] if et == ("drug", "synergy_pair", "drug") else [5, 3])
            for et in data_work.edge_types
        }
        loader = LinkNeighborLoader(
            data=data_work,
            num_neighbors=num_neighbors,
            edge_label_index=(("drug", "synergy_pair", "drug"), edge_index),
            edge_label=dummy_label,
            batch_size=1,
            shuffle=False,
        )
        module.eval()
        with torch.no_grad():
            batch = next(iter(loader)).to(device)
            logits, _ = module(batch)
            probs = F.softmax(logits, dim=-1)[0].tolist()

        n_pairs_scored += 1
        p_ant, p_add, p_syn = probs
        if p_syn > THRESHOLD_SYNERGY:
            pred = "synergy"
        elif p_ant > THRESHOLD_ANTAGONISM:
            pred = "antagonism"
        else:
            pred = "additive"

        return {
            "p_antagonism": p_ant,
            "p_additive": p_add,
            "p_synergy": p_syn,
            "predicted_class": pred,
        }

    class MCTSNode:
        def __init__(self, drug_id: Optional[str] = None, parent: Optional['MCTSNode'] = None, depth: int = 0):
            self.drug_id = drug_id
            self.parent = parent
            self.depth = depth
            self.children: Dict[str, 'MCTSNode'] = {}
            self.visits: int = 0
            self.total_value: float = 0.0

        @property
        def q_value(self) -> float:
            return self.total_value / self.visits if self.visits > 0 else 0.0

    root = MCTSNode(depth=0)
    start_time = time.time()
    truncated = False
    sims_completed = 0

    for sim_idx in range(n_simulations):
        if time.time() - start_time >= time_budget_sec:
            truncated = True
            logger.warning(
                f"[MCTS] Wall-clock time budget ({time_budget_sec}s) reached after {sim_idx} simulations. "
                "Truncating search."
            )
            break

        # 1. Selection & Expansion
        curr = root
        # Depth 0: Choose first drug d_a
        unvisited_roots = [d for d in cand_ids if d not in curr.children]
        if unvisited_roots:
            # Deterministic selection in candidate priority order
            pick_d = unvisited_roots[0]
            child = MCTSNode(drug_id=pick_d, parent=curr, depth=1)
            curr.children[pick_d] = child
            curr = child
        else:
            log_n = math.log(max(curr.visits, 1))
            best_uct = -1e9
            best_child = None
            for d in cand_ids:
                ch = curr.children[d]
                uct = ch.q_value + mcts_c * math.sqrt(log_n / max(ch.visits, 1))
                if uct > best_uct or (uct == best_uct and (best_child is None or d < best_child.drug_id)):
                    best_uct = uct
                    best_child = ch
            curr = best_child

        # Depth 1: Choose partner drug d_b (d_b != d_a)
        d_a = curr.drug_id
        partner_cands = [d for d in cand_ids if d != d_a]
        unvisited_partners = [d for d in partner_cands if d not in curr.children]
        if unvisited_partners:
            pick_p = unvisited_partners[0]
            child = MCTSNode(drug_id=pick_p, parent=curr, depth=2)
            curr.children[pick_p] = child
            curr = child
        else:
            log_n = math.log(max(curr.visits, 1))
            best_uct = -1e9
            best_child = None
            for p in partner_cands:
                ch = curr.children[p]
                uct = ch.q_value + mcts_c * math.sqrt(log_n / max(ch.visits, 1))
                if uct > best_uct or (uct == best_uct and (best_child is None or p < best_child.drug_id)):
                    best_uct = uct
                    best_child = ch
            curr = best_child

        # 2. Simulation (Terminal State Evaluation at Depth 2)
        d_b = curr.drug_id
        pair_key = (min(d_a, d_b), max(d_a, d_b))
        pair_visits[pair_key] = pair_visits.get(pair_key, 0) + 1

        if pair_key in pair_cache:
            eval_res = pair_cache[pair_key]
            cache_hits += 1
        else:
            eval_res = score_single_pair(d_a, d_b)
            pair_cache[pair_key] = eval_res

        v = eval_res["p_synergy"]

        # 3. Backpropagation
        node = curr
        while node is not None:
            node.visits += 1
            node.total_value += v
            node = node.parent

        sims_completed += 1

    elapsed = time.time() - start_time
    logger.info(
        f"[MCTS SEARCH] Completed {sims_completed} simulations ({n_pairs_scored} unique pairs scored, "
        f"{cache_hits} cache hits, truncated={truncated}) in {elapsed:.2f}s."
    )

    metadata = {
        "search_method": "mcts",
        "n_simulations": sims_completed,
        "n_pairs_scored": n_pairs_scored,
        "candidate_pool_size": len(candidates),
        "truncated": truncated,
        "mcts_c": mcts_c,
        "cache_hits": cache_hits,
        "max_candidates_scored": n_pairs_scored,
    }

    # 4. Compile and rank candidates strictly by GNN score
    scored_pairs: List[Dict[str, Any]] = []
    for pair_key, eval_res in pair_cache.items():
        da_id, db_id = pair_key
        ca = cand_by_id[da_id]
        cb = cand_by_id[db_id]
        p_syn = eval_res["p_synergy"]
        p_add = eval_res["p_additive"]
        p_ant = eval_res["p_antagonism"]

        is_speculative = (ca["match_type"] == "target_overlap" or cb["match_type"] == "target_overlap")
        high_confidence_caveat = bool(p_syn > _HIGH_CONFIDENCE_THRESHOLD and is_speculative)

        scored_pairs.append({
            "drug_a": da_id,
            "drug_a_name": ca["drug_name"],
            "drug_b": db_id,
            "drug_b_name": cb["drug_name"],
            "drug_a_match_type": ca["match_type"],
            "drug_b_match_type": cb["match_type"],
            "score": round(p_syn, 4),
            "p_synergy": round(p_syn, 4),
            "p_additive": round(p_add, 4),
            "p_antagonism": round(p_ant, 4),
            "predicted_class": eval_res["predicted_class"],
            "cell_line": cell_line_name,
            "search_method": "mcts",
            "mcts_visits": pair_visits.get(pair_key, 1),
            "high_confidence_caveat": high_confidence_caveat,
            "faithfulness": None,
        })

    # Sort strictly by p_synergy descending, with stable tie-breaking on drug IDs
    scored_pairs.sort(key=lambda x: (-x["p_synergy"], x["drug_a"], x["drug_b"]))

    final_hits = scored_pairs[:top_k]
    for i, hit in enumerate(final_hits, 1):
        hit["rank"] = i

    return final_hits, metadata


def beam_search_combinations(
    disease_name: str,
    cell_line_name: str,
    heterodata: Optional[HeteroData] = None,
    module: Optional[Any] = None,
    device: Optional[str] = None,
    max_candidate_drugs: int = 20,
    beam_width: int = 5,
    top_k: int = 5,
    search_method: str = "beam",
    seed_drug_id: Optional[str] = None,
    n_simulations: int = 50,
    mcts_c: float = 1.414,
    time_budget_sec: float = 15.0,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Search candidate drug combinations using a state-space Beam Search, Greedy Search,
    or Monte Carlo Tree Search (MCTS) driven directly by the trained SynergyGNN pair scorer.

    State-Space Formulation (Depth 2 for 2-Drug Combinations):
    - Depth 1 (Anchor Selection):
      If seed_drug_id is provided, anchor beam initializes with [seed_drug].
      Otherwise, expands from root to top-B candidate drugs prioritized by disease
      indication relevance and target overlap.
      (For greedy search, B = 1).
    - Depth 2 (Partner Expansion):
      Expands each anchor in the beam with eligible candidate drugs from the filtered
      candidate pool, forming unique candidate pairs (d_a, d_b).
    - Batched GNN Scoring:
      All candidate pairs are scored in a batched forward pass through the trained
      SynergyGNN model without heuristic tier overrides.
    - Beam Pruning:
      Prunes the candidate pool to the top-K pairs ranked strictly by p_synergy descending,
      using stable tie-breaking on (drug_a, drug_b) IDs to guarantee reproducibility.
    """
    if search_method.lower() == "mcts":
        return mcts_search_combinations(
            disease_name=disease_name,
            cell_line_name=cell_line_name,
            heterodata=heterodata,
            module=module,
            device=device,
            max_candidate_drugs=max_candidate_drugs,
            n_simulations=n_simulations,
            mcts_c=mcts_c,
            time_budget_sec=time_budget_sec,
            top_k=top_k,
            seed_drug_id=seed_drug_id,
        )

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

    # 3. Stage 1: Candidate Generation (with non-drug and CYP filtering)
    candidates = find_candidate_drugs(
        disease_name,
        heterodata=heterodata,
        node_maps=node_maps,
        max_candidates=max_candidate_drugs,
    )

    # Ensure candidate pool contains only plausible therapeutic drugs
    candidates = [
        c for c in candidates
        if is_valid_therapeutic_candidate(c["drug_name"], c["drug_id"])
    ]

    # If seed drug requested, ensure it is anchored in candidate pool
    if seed_drug_id and seed_drug_id in drug_id2idx:
        existing_ids = {c["drug_id"] for c in candidates}
        if seed_drug_id not in existing_ids:
            from explain import _build_name_lookups
            name_lookup, _ = _build_name_lookups(heterodata)
            seed_name = name_lookup.get("drug", {}).get(drug_id2idx[seed_drug_id], seed_drug_id)
            candidates.insert(0, {
                "drug_id": seed_drug_id,
                "drug_name": seed_name,
                "match_type": "seed",
                "score": 1.0,
                "shared_targets": 0,
            })

    method_clean = "greedy" if search_method.lower() == "greedy" or beam_width <= 1 else "beam"
    effective_b = 1 if method_clean == "greedy" else max(1, beam_width)

    metadata: Dict[str, Any] = {
        "search_method": method_clean,
        "beam_width": effective_b,
        "candidate_pool_size": len(candidates),
        "max_candidates_scored": 0,
    }

    if len(candidates) < 2:
        logger.warning(
            f"Fewer than 2 candidate drugs ({len(candidates)}) found for disease '{disease_name}'. "
            "Cannot form pairs."
        )
        return [], metadata

    # 4. State-Space Expansion: Depth 1 Anchor Selection
    if seed_drug_id:
        anchors = [c for c in candidates if c["drug_id"] == seed_drug_id]
        if not anchors:
            anchors = candidates[:1]
    else:
        # Beam of width B top candidate drugs
        anchors = candidates[:effective_b]

    # Depth 2 Partner Expansion: Pair anchors with partner drugs from candidate pool
    unique_pairs_dict: Dict[Tuple[str, str], Tuple[Dict[str, Any], Dict[str, Any]]] = {}
    for anchor in anchors:
        for partner in candidates:
            if anchor["drug_id"] == partner["drug_id"]:
                continue  # no self-pairs
            # Canonical unordered key
            pair_key = (
                min(anchor["drug_id"], partner["drug_id"]),
                max(anchor["drug_id"], partner["drug_id"]),
            )
            if pair_key not in unique_pairs_dict:
                # Maintain anchor as drug_a if seed specified
                if seed_drug_id and partner["drug_id"] == seed_drug_id:
                    unique_pairs_dict[pair_key] = (partner, anchor)
                else:
                    unique_pairs_dict[pair_key] = (anchor, partner)

    # Sort pairs canonically by drug IDs to guarantee deterministic ordering
    pairs = sorted(
        unique_pairs_dict.values(),
        key=lambda p: (p[0]["drug_id"], p[1]["drug_id"]),
    )
    num_pairs = len(pairs)
    metadata["max_candidates_scored"] = num_pairs

    logger.info(
        f"[{method_clean.upper()} SEARCH] Expanding {len(anchors)} anchor(s) into {num_pairs} "
        f"candidate pairs from pool of {len(candidates)} drugs for '{disease_name}' @ '{cell_line_name}'."
    )

    if num_pairs == 0:
        return [], metadata

    # 5. Batched GNN Scoring Pass
    t_start = time.time()
    # Seed RNG to ensure identical neighbor sampling and bitwise reproducible scores across reruns
    torch.manual_seed(42)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(42)

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
        f"\n[Stage 2] {method_clean.title()} search scored {num_pairs} candidate pairs in {scoring_duration:.2f}s "
        f"({(scoring_duration / max(num_pairs, 1)) * 1000:.1f}ms per pair) on {device}."
    )

    # 6. Parse and Rank Candidates Strictly by Model Score (with stable tie-breaking)
    scored_pairs: List[Dict[str, Any]] = []
    for p, probs in zip(pairs, all_probs):
        p_ant, p_add, p_syn = probs
        if p_syn > THRESHOLD_SYNERGY:
            pred = "synergy"
        elif p_ant > THRESHOLD_ANTAGONISM:
            pred = "antagonism"
        else:
            pred = "additive"

        is_speculative = (
            p[0]["match_type"] == "target_overlap" or p[1]["match_type"] == "target_overlap"
        )
        high_confidence_caveat = bool(p_syn > _HIGH_CONFIDENCE_THRESHOLD and is_speculative)

        scored_pairs.append({
            "drug_a": p[0]["drug_id"],
            "drug_a_name": p[0]["drug_name"],
            "drug_b": p[1]["drug_id"],
            "drug_b_name": p[1]["drug_name"],
            "drug_a_match_type": p[0]["match_type"],
            "drug_b_match_type": p[1]["match_type"],
            "score": round(p_syn, 4),
            "p_synergy": round(p_syn, 4),
            "p_additive": round(p_add, 4),
            "p_antagonism": round(p_ant, 4),
            "predicted_class": pred,
            "cell_line": cell_line_name,
            "search_method": method_clean,
            "high_confidence_caveat": high_confidence_caveat,
            "faithfulness": None,  # Batch search leaves faithfulness null
        })

    # Beam Pruning: Sort strictly by GNN score descending, breaking ties stably by drug IDs
    scored_pairs.sort(key=lambda x: (-x["p_synergy"], x["drug_a"], x["drug_b"]))

    # Assign ranks
    final_hits = scored_pairs[:top_k]
    for i, hit in enumerate(final_hits, 1):
        hit["rank"] = i

    return final_hits, metadata


def score_candidate_pairs(
    disease_name: str,
    cell_line_name: str,
    heterodata: Optional[HeteroData] = None,
    module: Optional[Any] = None,
    device: Optional[str] = None,
    max_candidate_drugs: int = 20,
    top_k: int = 5,
    search_method: str = "beam",
    beam_width: int = 5,
    n_simulations: int = 50,
    mcts_c: float = 1.414,
    time_budget_sec: float = 15.0,
) -> List[Dict[str, Any]]:
    """
    Backward-compatible wrapper around beam_search_combinations().
    Returns the top-K pairs ranked strictly by GNN synergy score.
    """
    pairs, _ = beam_search_combinations(
        disease_name=disease_name,
        cell_line_name=cell_line_name,
        heterodata=heterodata,
        module=module,
        device=device,
        max_candidate_drugs=max_candidate_drugs,
        beam_width=beam_width,
        top_k=top_k,
        search_method=search_method,
        n_simulations=n_simulations,
        mcts_c=mcts_c,
        time_budget_sec=time_budget_sec,
    )
    return pairs


# ---------------------------------------------------------------------------
# Stage 3: Full Explanations on Top-K Pairs
# ---------------------------------------------------------------------------

def get_full_explanations_for_top_k(
    top_k_pairs: List[Dict[str, Any]],
    cell_line_name: str,
    module: Optional[Any] = None,
    heterodata: Optional[HeteroData] = None,
    device: Optional[str] = None,
    inspect_top_k: int = 0,
) -> List[Dict[str, Any]]:
    """
    Run the explain_prediction() pipeline on the top-K pairs selected by Stage 2.
    Batch search skips faithfulness ablation (faithfulness=null) to ensure sub-second
    response times, unless inspect_top_k > 0 is explicitly requested.

    Parameters:
    -----------
    top_k_pairs : List[Dict[str, Any]]
        Output list of top-K pairs from beam_search_combinations().
    cell_line_name : str
        Target cell line.
    module : SynergyModule, optional
    heterodata : HeteroData, optional
    device : str, optional
    inspect_top_k : int, default 0
        Number of top hits (0-3) to run in-silico faithfulness ablation on.

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

    print(f"\n[Stage 3] Generating explanations for top {len(top_k_pairs)} pairs (inspect_top_k={inspect_top_k})...")
    t_start = time.time()

    for idx, pair in enumerate(top_k_pairs, 1):
        drug_a_id = pair["drug_a"]
        drug_b_id = pair["drug_b"]
        a_name = pair.get("drug_a_name", drug_a_id)
        b_name = pair.get("drug_b_name", drug_b_id)

        # Compute real faithfulness and literature RAG only if requested within inspect_top_k limit
        should_inspect = bool(idx <= inspect_top_k)

        print(f"\n--- [{idx}/{len(top_k_pairs)}] Explaining {a_name} + {b_name} @ {cell_line_name} (inspect={should_inspect}) ---")
        t_pair = time.time()
        expl = explain_prediction(
            drug_a_id=drug_a_id,
            drug_b_id=drug_b_id,
            cell_line_name=cell_line_name,
            module=module,
            heterodata=heterodata,
            device=device,
            run_faithfulness=should_inspect,
            run_literature=should_inspect,
            disease_context=pair.get("disease", ""),
        )
        expl_duration = time.time() - t_pair
        print(f"    Completed in {expl_duration:.2f}s")
        expl["rank"] = pair.get("rank", idx)
        expl["search_method"] = pair.get("search_method", "beam")
        if "score" in pair:
            expl["score"] = pair["score"]
        if "p_synergy" in pair:
            expl["p_synergy"] = pair["p_synergy"]
        if "p_additive" in pair:
            expl["p_additive"] = pair["p_additive"]
        if "p_antagonism" in pair:
            expl["p_antagonism"] = pair["p_antagonism"]
        if "predicted_class" in pair:
            expl["predicted_class"] = pair["predicted_class"]
        if "mcts_visits" in pair:
            expl["mcts_visits"] = pair["mcts_visits"]
        if not should_inspect:
            expl["faithfulness"] = None
            expl["literature"] = None
            expl["supporting_literature"] = []
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
