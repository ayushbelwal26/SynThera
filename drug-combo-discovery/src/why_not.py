"""
src/why_not.py — Grounded "Why Not Drug X?" Diagnostic Agent for SynThera.

Answers why a specific drug is missing, filtered, or ranked below top combinations
for a given disease and cell line.

Rule-based intent parsing (no LLMs):
- why not <drug>
- compare <drug A> vs <drug B>
- why is <drug A> ranked below <drug B>
- unsupported question -> returns error + hint
"""

import re
import time
import logging
from typing import Dict, List, Optional, Tuple, Any

from search import (
    is_valid_therapeutic_candidate,
    find_candidate_drugs,
    beam_search_combinations,
    _load_model_cached,
)

logger = logging.getLogger("why_not")

# ---------------------------------------------------------------------------
# Rule-Based Intent Parsers
# ---------------------------------------------------------------------------

_WHY_NOT_PATTERNS = [
    re.compile(r"^\s*why\s+(?:not|isn['’]?t(?:\s+there)?|is\s+not)\s+(?:use\s+|consider\s+)?(.+?)(?:\s+included|\s+ranked|\s+present|\s+here)?$", re.IGNORECASE),
    re.compile(r"^\s*why\s+is\s+(.+?)\s+(?:missing|not\s+ranked|not\s+in|not\s+included)(?:\s+here)?$", re.IGNORECASE),
    re.compile(r"^\s*why\s+(?:was\s+|is\s+)?(.+?)\s+(?:excluded|dropped|filtered|omitted)(?:\s+from\s+search)?$", re.IGNORECASE),
    re.compile(r"^\s*(?:what\s+about|how\s+about)\s+(.+?)$", re.IGNORECASE),
]

_COMPARE_PATTERNS = [
    re.compile(r"^\s*compare\s+(.+?)\s+(?:vs\.?|versus|and|to)\s+(.+?)$", re.IGNORECASE),
    re.compile(r"^\s*(.+?)\s+(?:vs\.?|versus)\s+(.+?)$", re.IGNORECASE),
]

_RANKED_BELOW_PATTERNS = [
    re.compile(r"^\s*why\s+is\s+(.+?)\s+(?:ranked\s+below|lower\s+than|worse\s+than)\s+(.+?)$", re.IGNORECASE),
    re.compile(r"^\s*(.+?)\s+vs\s+(.+?)\s+ranking$", re.IGNORECASE),
]


def parse_why_not_intent(
    question: str,
    drug_x_raw: Optional[str] = None,
) -> Tuple[str, Dict[str, Any]]:
    """
    Parse natural question using deterministic rules/regex into one of:
    - ('why_not', {'drug_x': ...})
    - ('compare', {'drug_a': ..., 'drug_b': ...})
    - ('ranked_below', {'drug_a': ..., 'drug_b': ...})
    - ('unsupported_question', {})
    """
    q_orig = (question or "").strip()

    # If drug_x is explicitly passed via API parameter
    if drug_x_raw and drug_x_raw.strip():
        return "why_not", {"drug_x": drug_x_raw.strip()}

    if not q_orig:
        return "unsupported_question", {}

    q = q_orig.rstrip("?").strip()

    # Check 'ranked_below' patterns first
    for pat in _RANKED_BELOW_PATTERNS:
        m = pat.match(q)
        if m:
            d_a = m.group(1).strip().strip("\"'").rstrip("?")
            d_b = m.group(2).strip().strip("\"'").rstrip("?")
            if d_a and d_b:
                return "ranked_below", {"drug_a": d_a, "drug_b": d_b}

    # Check 'compare' patterns
    for pat in _COMPARE_PATTERNS:
        m = pat.match(q)
        if m:
            d_a = m.group(1).strip().strip("\"'").rstrip("?")
            d_b = m.group(2).strip().strip("\"'").rstrip("?")
            if d_a and d_b:
                return "compare", {"drug_a": d_a, "drug_b": d_b}

    # Check 'why_not' patterns
    for pat in _WHY_NOT_PATTERNS:
        m = pat.match(q)
        if m:
            drug = m.group(1).strip().strip("\"'").rstrip("?")
            drug = re.sub(
                r"\s+(?:included|ranked|present|here|in\s+top-?[kK]|in\s+search|suggested|recommended)\b.*$",
                "",
                drug,
                flags=re.IGNORECASE,
            ).strip()
            # Filter out general question tokens
            if drug.lower() not in {"the weather", "you", "it", "this", "that", "cancer"}:
                return "why_not", {"drug_x": drug}

    return "unsupported_question", {}


# ---------------------------------------------------------------------------
# Drug Resolution Helper
# ---------------------------------------------------------------------------

def resolve_drug_query(
    query: str,
    drug_alias_map: Dict[str, str],
    drug_list: Optional[List[Dict[str, str]]] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Resolve a drug query string to (drugbank_id, canonical_name).
    Returns (None, None) if compound cannot be resolved.
    """
    q_clean = query.strip()
    q_lower = q_clean.lower()
    q_upper = q_clean.upper()

    id_to_name = {d["id"]: d["name"] for d in drug_list} if drug_list else {}

    # 1. Direct DrugBank ID match (e.g. DB00853)
    if q_upper in drug_alias_map or q_upper.startswith("DB"):
        db_id = drug_alias_map.get(q_lower, q_upper)
        if db_id in id_to_name:
            return db_id, id_to_name[db_id]
        if db_id in drug_alias_map.values():
            return db_id, id_to_name.get(db_id, q_clean)

    # 2. Exact alias match (case-insensitive)
    if q_lower in drug_alias_map:
        db_id = drug_alias_map[q_lower]
        return db_id, id_to_name.get(db_id, q_clean.title())

    # 3. Substring / prefix search across drug list
    if drug_list:
        for d in drug_list:
            if d["name"].lower() == q_lower:
                return d["id"], d["name"]
        for d in drug_list:
            if q_lower in d["name"].lower() or d["name"].lower().startswith(q_lower):
                return d["id"], d["name"]

    return None, None


# ---------------------------------------------------------------------------
# Core Analysis Engine
# ---------------------------------------------------------------------------

def analyze_why_not(
    disease_name: str,
    cell_line_name: str,
    question: str,
    drug_x_raw: Optional[str] = None,
    search_method: str = "beam",
    max_candidate_drugs: int = 15,
    heterodata: Optional[Any] = None,
    module: Optional[Any] = None,
    device: Optional[str] = None,
    drug_alias_map: Optional[Dict[str, str]] = None,
    drug_list: Optional[List[Dict[str, str]]] = None,
    run_literature: bool = True,
) -> Dict[str, Any]:
    """
    Execute grounded 'Why Not Drug X' diagnosis.
    Returns structured JSON with intent, status, verdict, scores, and template text.
    """
    t_start = time.time()

    # 1. Parse Question Intent
    intent, extracted = parse_why_not_intent(question, drug_x_raw)
    if intent == "unsupported_question":
        return {
            "error": "unsupported_question",
            "hint": "Ask why not <drug> for the current disease and cell line.",
        }

    # Load model and graph if needed
    if module is None or heterodata is None:
        module, heterodata, device = _load_model_cached(heterodata=heterodata, device=device)
    elif device is None:
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"

    if drug_alias_map is None:
        drug_alias_map = {}

    target_query = extracted.get("drug_x") or extracted.get("drug_a") or ""

    # 2. Step 1: Resolve Drug X
    db_id, drug_name = resolve_drug_query(target_query, drug_alias_map, drug_list)

    if not db_id or not drug_name:
        return {
            "intent": intent,
            "drug_x": {"id": None, "name": target_query},
            "status": "unknown_drug",
            "best_pair": None,
            "reference_top": None,
            "verdict": "not_in_graph",
            "explanation_text": (
                f"Drug '{target_query}' could not be resolved to any compound in the PrimeKG / DrugComb knowledge graph. "
                "Please verify the generic drug name or DrugBank ID."
            ),
            "literature": None,
            "faithfulness": None,
        }

    drug_x_obj = {"id": db_id, "name": drug_name}

    # 3. Step 2: Therapeutic Candidate Filter
    is_valid = is_valid_therapeutic_candidate(drug_name, db_id)
    if not is_valid:
        return {
            "intent": intent,
            "drug_x": drug_x_obj,
            "status": "filtered",
            "best_pair": None,
            "reference_top": None,
            "verdict": "filtered",
            "explanation_text": (
                f"{drug_name} ({db_id}) was excluded prior to combination scoring by the therapeutic candidate filter "
                "(identified as an inorganic metal salt, solvent, or non-therapeutic excipient). "
                "It cannot be recommended or scored as an oncology therapeutic."
            ),
            "literature": None,
            "faithfulness": None,
        }

    # 4. Step 3: Graph Presence Check
    node_maps = getattr(heterodata, "node_maps", {})
    drug_id2idx = node_maps.get("drug", {})
    if not drug_id2idx:
        from predict import _get_node_maps
        drug_id2idx = _get_node_maps(heterodata).get("drug", {})

    if db_id not in drug_id2idx:
        return {
            "intent": intent,
            "drug_x": drug_x_obj,
            "status": "unknown_drug",
            "best_pair": None,
            "reference_top": None,
            "verdict": "not_in_graph",
            "explanation_text": (
                f"{drug_name} ({db_id}) is not present in the PrimeKG / DrugComb graph topology. "
                "Predictions cannot be formed without topological features."
            ),
            "literature": None,
            "faithfulness": None,
        }

    # 5. Step 4: GNN Pair Scoring against Disease Candidate Pool
    disease_clean = disease_name.strip()
    cell_clean = cell_line_name.strip()

    # Retrieve disease candidate pool
    candidates = find_candidate_drugs(
        disease_clean,
        heterodata=heterodata,
        max_candidates=max_candidate_drugs,
    )
    valid_candidates = [
        c for c in candidates if is_valid_therapeutic_candidate(c["drug_name"], c["drug_id"])
    ]

    # Baseline search #1 hit for comparison
    ref_pairs, _ = beam_search_combinations(
        disease_name=disease_clean,
        cell_line_name=cell_clean,
        heterodata=heterodata,
        module=module,
        device=device,
        max_candidate_drugs=max_candidate_drugs,
        beam_width=5,
        top_k=1,
        search_method=search_method,
    )
    ref_top = ref_pairs[0] if ref_pairs else None
    ref_top_obj = None
    if ref_top:
        ref_top_obj = {
            "drug_a": ref_top["drug_a"],
            "drug_a_name": ref_top["drug_a_name"],
            "drug_b": ref_top["drug_b"],
            "drug_b_name": ref_top["drug_b_name"],
            "score": ref_top["score"],
            "p_synergy": ref_top["p_synergy"],
            "predicted_class": ref_top["predicted_class"],
            "cell_line": ref_top["cell_line"],
        }

    # Targeted evaluation of drug X against the candidate pool
    x_pairs, _ = beam_search_combinations(
        disease_name=disease_clean,
        cell_line_name=cell_clean,
        heterodata=heterodata,
        module=module,
        device=device,
        seed_drug_id=db_id,
        max_candidate_drugs=max_candidate_drugs,
        beam_width=1,
        top_k=3,
        search_method="beam",
    )

    if not x_pairs:
        return {
            "intent": intent,
            "drug_x": drug_x_obj,
            "status": "scored",
            "best_pair": None,
            "reference_top": ref_top_obj,
            "verdict": "weaker",
            "explanation_text": (
                f"{drug_name} ({db_id}) could not form valid candidate pairs in the candidate pool for {disease_clean}."
            ),
            "literature": None,
            "faithfulness": None,
        }

    best_pair = x_pairs[0]
    best_pair_obj = {
        "drug_a": best_pair["drug_a"],
        "drug_a_name": best_pair["drug_a_name"],
        "drug_b": best_pair["drug_b"],
        "drug_b_name": best_pair["drug_b_name"],
        "score": best_pair["score"],
        "p_synergy": best_pair["p_synergy"],
        "predicted_class": best_pair["predicted_class"],
        "cell_line": best_pair["cell_line"],
    }

    # Determine partner name
    partner_name = best_pair["drug_b_name"] if best_pair["drug_a"] == db_id else best_pair["drug_a_name"]
    partner_id = best_pair["drug_b"] if best_pair["drug_a"] == db_id else best_pair["drug_a"]

    # 6. Step 5: Verdict & Grounded Explanation Generation
    p_x = float(best_pair["p_synergy"])
    p_ref = float(ref_top["p_synergy"]) if ref_top else 0.0
    delta = p_x - p_ref

    # Verdict classification
    if delta >= -0.02:
        verdict = "competitive"
    else:
        verdict = "weaker"

    # Contextual check: was X already in candidate pool?
    cand_ids = [c["drug_id"] for c in valid_candidates]
    if db_id in cand_ids:
        cand_rank = cand_ids.index(db_id) + 1
        cand_note = f"{drug_name} is ranked #{cand_rank} in the {disease_clean} candidate pool."
        if search_method == "beam" and cand_rank > 5:
            search_note = (
                f"Because beam search prioritizes the top B=5 anchors, {drug_name} was outside the anchor expansion window."
            )
        elif search_method == "greedy" and cand_rank > 1:
            search_note = (
                f"Because greedy search expands exclusively from the single top anchor (#{1}), {drug_name} was not expanded."
            )
        else:
            search_note = "Although expanded, other combination pairings achieved higher synergy scores."
    else:
        cand_note = f"{drug_name} has no direct indication or target-overlap edges for {disease_clean} in PrimeKG."
        search_note = "It was evaluated via targeted anchor injection against the candidate pool."

    # Comparison text against reference #1
    if ref_top:
        ref_text = f"Current search #1 is {ref_top['drug_a_name']}+{ref_top['drug_b_name']} at {p_ref:.4f}."
        if p_x < p_ref:
            comp_text = f"{drug_name} pairing is lower (Δ={delta:.4f}), so {search_method} did not rank it in the top-K."
        else:
            comp_text = f"{drug_name} pairing is competitive (Δ={delta:+.4f}), but search ranking prioritized earlier anchor candidates."
    else:
        ref_text = ""
        comp_text = ""

    explanation_text = (
        f"{drug_name} ({db_id}) is a valid therapeutic in the graph. {cand_note} "
        f"Best scored partner in this pool: {partner_name} @ {cell_clean} with p_synergy={p_x:.4f} ({best_pair['predicted_class']}). "
        f"{ref_text} {comp_text} {search_note} "
        f"This is a model score, not a clinical recommendation. Inspect the pair for subgraph + papers."
    )

    # 7. Step 6: Single-Pair Literature Grounding (Max 1 Citation)
    lit_obj = None
    if run_literature:
        try:
            from literature import retrieve_literature_rag
            lit_res = retrieve_literature_rag(
                drug_a_name=drug_name,
                drug_b_name=partner_name,
                disease_context=disease_clean,
                max_citations=1,
            )
            cits = lit_res.get("citations", [])
            if cits:
                lit_obj = {
                    "citations": cits[:1],
                    "query_used": lit_res.get("query_used", ""),
                    "retrieval_method": lit_res.get("retrieval_method", "ncbi_eutilities_keyword_overlap"),
                }
        except Exception as e:
            logger.warning(f"[why_not] Literature retrieval failed: {e}")
            lit_obj = None

    elapsed = time.time() - t_start
    logger.info(f"[why_not] Completed diagnosis for {drug_name} ({db_id}) in {elapsed:.2f}s (verdict={verdict}).")

    return {
        "intent": intent,
        "drug_x": drug_x_obj,
        "status": "scored",
        "best_pair": best_pair_obj,
        "reference_top": ref_top_obj,
        "verdict": verdict,
        "explanation_text": explanation_text,
        "literature": lit_obj,
        "faithfulness": None,  # Skip ablation for fast diagnosis; user can click Inspect
    }
