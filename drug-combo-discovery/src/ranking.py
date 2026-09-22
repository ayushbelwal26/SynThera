"""
src/ranking.py
==============
Multi-Objective Combination Ranking Function V(pair) for SynThera.
Phase B2 implementation per FUTURE_SCOPE.md Section 4.1.B.

Objective Formulation:
----------------------
    V(pair) = w_synergy * p_synergy
              - w_toxicity * toxicity_penalty(pair)
              - w_redundancy * redundancy_penalty(pair)

Inspectability & Policy Design:
-------------------------------
1. Toxicity Penalty:
   Derived from PrimeKG DDI network (has_known_ddi) and SIDER 4.1 (side_effect_overlap_score):
       toxicity_penalty = alpha_ddi * ddi_risk + alpha_se * se_risk
   where alpha_ddi = 0.65, alpha_se = 0.35.

   DOCUMENTED UNKNOWN-RISK POLICY:
   Missing data (None from has_known_ddi or side_effect_overlap_score) MUST NOT silently
   become 0.0 penalty. An unindexed compound or missing profile carries baseline uncertainty.
   - If has_known_ddi is True  -> ddi_risk = 1.0 (confirmed adverse interaction)
   - If has_known_ddi is False -> ddi_risk = 0.0 (confirmed safe / no interaction reported)
   - If has_known_ddi is None  -> ddi_risk = UNKNOWN_DDI_PENALTY (0.35)
   - If side_effect_overlap is float -> se_risk = score
   - If side_effect_overlap is None  -> se_risk = UNKNOWN_SE_PENALTY (0.15, empirical small-molecule mean)

   Ordering Guarantee:
       Confirmed Safe (0.0) < Unknown Risk (0.28) < Confirmed Toxic (0.70 - 1.0)

2. Redundancy Penalty:
   Reuses precomputed Phase A target-complementarity features (target_jaccard in PPI space).
   If a pair was precomputed in Phase A, returns target_jaccard in [0.0, 1.0].
   If a pair is unindexed or missing target data, returns None (and logs a TODO note),
   contributing 0.0 to subtraction without fabricating a proxy metric.

3. Configurable Weights & Inspectability:
   Default named weights: w_synergy = 1.0, w_toxicity = 0.35, w_redundancy = 0.10.
   Reported verbatim in any API response.
"""

import os
import logging
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("ranking")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED = os.path.join(ROOT, "data", "processed")
TARGET_PARQUET = os.path.join(PROCESSED, "target_complementarity_features.parquet")
PRIMEKG_DRUGS_CSV = os.path.join(PROCESSED, "primekg_drugs.csv")

# ---------------------------------------------------------------------------
# Default Configuration Constants
# ---------------------------------------------------------------------------

DEFAULT_W_SYNERGY: float = 1.0
DEFAULT_W_TOXICITY: float = 0.35
DEFAULT_W_REDUNDANCY: float = 0.10

ALPHA_DDI: float = 0.65
ALPHA_SE: float = 0.35

# Documented Unknown-Risk Policy Constants
UNKNOWN_DDI_PENALTY: float = 0.35   # Distinct from confirmed safe 0.0 and confirmed toxic 1.0
UNKNOWN_SE_PENALTY: float = 0.15    # Empirical average Jaccard overlap among small molecules

# In-memory cache for precomputed Phase A target redundancy features: (id_a, id_b) -> target_jaccard
_REDUNDANCY_LOOKUP: Optional[Dict[Tuple[str, str], float]] = None


def _load_redundancy_lookup() -> Dict[Tuple[str, str], float]:
    """Lazy-load precomputed Phase A target-complementarity features into memory."""
    global _REDUNDANCY_LOOKUP
    if _REDUNDANCY_LOOKUP is not None:
        return _REDUNDANCY_LOOKUP

    lookup: Dict[Tuple[str, str], float] = {}
    if os.path.exists(TARGET_PARQUET) and os.path.exists(PRIMEKG_DRUGS_CSV):
        try:
            import pandas as pd
            drugs_df = pd.read_csv(PRIMEKG_DRUGS_CSV, usecols=["drugbank_id"])
            idx2id = drugs_df["drugbank_id"].to_dict()
            pq = pd.read_parquet(TARGET_PARQUET, columns=["drug_a", "drug_b", "target_jaccard"])
            for _, row in pq.iterrows():
                ia = int(row["drug_a"])
                ib = int(row["drug_b"])
                if ia in idx2id and ib in idx2id:
                    ida = str(idx2id[ia]).strip().upper()
                    idb = str(idx2id[ib]).strip().upper()
                    pair_key = (min(ida, idb), max(ida, idb))
                    lookup[pair_key] = float(row["target_jaccard"])
            logger.info(f"Loaded {len(lookup)} precomputed target redundancy pairs from Phase A.")
        except Exception as e:
            logger.warning(f"Could not load target redundancy parquet ({e}). Will return None.")
    else:
        logger.info("Target complementarity parquet not found; redundancy penalties will default to None.")

    _REDUNDANCY_LOOKUP = lookup
    return _REDUNDANCY_LOOKUP


def compute_toxicity_penalty(
    drug_a_id: str,
    drug_b_id: str,
    strict_known_only: bool = False,
) -> Tuple[float, Dict[str, Any]]:
    """
    Computes the composite toxicity penalty for a drug pair in [0.0, 1.0].

    Implements the documented unknown-risk policy:
    - has_known_ddi == True  -> ddi_risk = 1.0
    - has_known_ddi == False -> ddi_risk = 0.0
    - has_known_ddi is None  -> ddi_risk = UNKNOWN_DDI_PENALTY (0.35)
    - side_effect_overlap is float -> se_risk = score
    - side_effect_overlap is None  -> se_risk = UNKNOWN_SE_PENALTY (0.15)

    Returns:
        (penalty_score, details_dict)
    """
    try:
        from toxicity import get_pair_toxicity
    except ImportError:
        from src.toxicity import get_pair_toxicity

    tox_res = get_pair_toxicity(drug_a_id, drug_b_id)
    has_ddi = tox_res.get("has_known_ddi")
    se_overlap = tox_res.get("side_effect_overlap_score")

    unknown_ddi = has_ddi is None
    unknown_se = se_overlap is None
    unknown_risk_applied = unknown_ddi or unknown_se

    if strict_known_only and unknown_risk_applied:
        raise ValueError(
            f"Strict known mode active: pair ({drug_a_id}, {drug_b_id}) contains missing toxicity data."
        )

    # DDI Risk
    if has_ddi is True:
        ddi_risk = 1.0
    elif has_ddi is False:
        ddi_risk = 0.0
    else:
        ddi_risk = UNKNOWN_DDI_PENALTY

    # Side Effect Risk
    if se_overlap is not None:
        se_risk = float(se_overlap)
    else:
        se_risk = UNKNOWN_SE_PENALTY

    penalty = round(ALPHA_DDI * ddi_risk + ALPHA_SE * se_risk, 4)

    details = {
        "has_known_ddi": has_ddi,
        "side_effect_overlap_score": se_overlap,
        "shared_side_effects_count": tox_res.get("shared_side_effects_count"),
        "top_shared_side_effects": tox_res.get("top_shared_side_effects"),
        "ddi_risk": ddi_risk,
        "se_risk": se_risk,
        "unknown_risk_applied": unknown_risk_applied,
        "is_unknown_ddi": unknown_ddi,
        "is_unknown_se": unknown_se,
        "source_coverage": tox_res.get("source_coverage", {}),
    }

    return penalty, details


def compute_redundancy_penalty(
    drug_a_id: str,
    drug_b_id: str,
) -> Tuple[Optional[float], Dict[str, Any]]:
    """
    Computes the target/pathway redundancy penalty in [0.0, 1.0] by reusing
    Phase A target complementarity features (target_jaccard).

    Returns:
        (redundancy_penalty, details_dict)
        If unindexed or missing, redundancy_penalty is None (with a logged TODO).
    """
    lookup = _load_redundancy_lookup()
    da = str(drug_a_id).strip().upper()
    db = str(drug_b_id).strip().upper()
    pair_key = (min(da, db), max(da, db))

    if pair_key in lookup:
        jaccard = round(lookup[pair_key], 4)
        return jaccard, {
            "available": True,
            "target_jaccard": jaccard,
            "source": "primekg_phase_a_target_complementarity",
        }
    else:
        return None, {
            "available": False,
            "target_jaccard": None,
            "source": None,
            "note": "TODO: Precompute target overlap for unindexed candidate pairs",
        }


def compute_pair_score_v(
    drug_a_id: str,
    drug_b_id: str,
    p_synergy: float,
    w_synergy: float = DEFAULT_W_SYNERGY,
    w_toxicity: float = DEFAULT_W_TOXICITY,
    w_redundancy: float = DEFAULT_W_REDUNDANCY,
    strict_known_only: bool = False,
) -> Dict[str, Any]:
    """
    Evaluates the inspectable multi-objective value function V(pair):

        V(pair) = w_synergy * p_synergy
                  - w_toxicity * toxicity_penalty(pair)
                  - w_redundancy * redundancy_penalty(pair)

    Returns a complete inspectable breakdown dictionary.
    """
    tox_penalty, tox_details = compute_toxicity_penalty(
        drug_a_id, drug_b_id, strict_known_only=strict_known_only
    )
    red_penalty, red_details = compute_redundancy_penalty(drug_a_id, drug_b_id)

    # Redundancy penalty subtraction: 0.0 if not available / None
    red_subtraction = (w_redundancy * red_penalty) if red_penalty is not None else 0.0

    raw_v = (w_synergy * p_synergy) - (w_toxicity * tox_penalty) - red_subtraction
    v_score = round(raw_v, 4)

    return {
        "v_score": v_score,
        "score": v_score,  # Alias for backward compatibility with search runners
        "p_synergy": round(float(p_synergy), 4),
        "toxicity_penalty": tox_penalty,
        "redundancy_penalty": red_penalty,
        "weights": {
            "w_synergy": round(float(w_synergy), 4),
            "w_toxicity": round(float(w_toxicity), 4),
            "w_redundancy": round(float(w_redundancy), 4),
            "alpha_ddi": ALPHA_DDI,
            "alpha_se": ALPHA_SE,
        },
        "breakdown": {
            "has_known_ddi": tox_details["has_known_ddi"],
            "side_effect_overlap": tox_details["side_effect_overlap_score"],
            "shared_side_effects_count": tox_details.get("shared_side_effects_count"),
            "top_shared_side_effects": tox_details.get("top_shared_side_effects"),
            "ddi_risk": tox_details["ddi_risk"],
            "se_risk": tox_details["se_risk"],
            "unknown_risk_applied": tox_details["unknown_risk_applied"],
            "source_coverage": tox_details["source_coverage"],
            "redundancy_available": red_details["available"],
            "redundancy_note": red_details.get("note"),
        },
    }
