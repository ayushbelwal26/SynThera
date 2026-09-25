"""
src/familiarity.py
==================
Applicability-Domain / Prediction-Familiarity Indicator for SynThera.
Phase B2 / Group 2 Item 5 Implementation.

Background & Empirical Justification:
-------------------------------------
Evaluation on held-out test splits (Group 2 Items 3 & 5) established that the
Synergy GNN model exhibits distinct behavioral regimes based on compound training
exposure:

1. High-Familiarity / Anchor Regimes (>= 50 training pairs):
   - 58 anchor drugs in the training set appear in 50 to 3,756 combinations.
   - When at least one compound belongs to this anchor set, the model achieves:
     * AUROC: 0.5881 (+0.064 higher than bilateral cold)
     * AUPR: 0.2413 (+0.038 higher than bilateral cold)
     * Class Separation Delta (mean p_syn for true synergy vs non-synergy):
       +0.0525 (vs +0.0148 for novel pairs -- a 3.5x improvement).
     * Accounts for 83.5% of all informative high-confidence predictions
       (p_synergy >= 0.50), where precision reaches 33.72%.

2. Limited-Familiarity Regimes (1 to 49 training pairs):
   - 738 compounds present in training data but with low multiplicity.
   - Provides localized topological anchoring in the knowledge graph.

3. Novel / Cold-Drug Regimes (0 training pairs):
   - Held-out test compounds not present in training combinations.
   - Model operates in purely inductive zero-shot mode via node features and graph structure.
   - Subject to Item 3's probability compression effect (mean p_synergy ~ 0.22 - 0.25,
     Delta = +0.0148, AUROC = 0.5232).

Thresholds:
-----------
- "high":    raw_score >= 50   (Anchor compound with extensive multi-context training data)
- "limited": 1 <= raw_score < 50 (Compound present in training data with limited pairs)
- "novel":   raw_score == 0    (Unseen in training set; inductive cold-drug prediction)
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger("familiarity")

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_DIR = os.path.join(ROOT_DIR, "data", "processed")

CACHE_JSON_PATH = os.path.join(PROCESSED_DIR, "drug_training_frequencies.json")
LABELS_PATH = os.path.join(PROCESSED_DIR, "labeled_pairs.csv")
SPLIT_TRAIN_PATH = os.path.join(PROCESSED_DIR, "split_train.csv")

THRESHOLD_HIGH: int = 50
THRESHOLD_LIMITED: int = 1

_DRUG_FREQ_CACHE: Optional[Dict[str, int]] = None


def _load_or_build_frequencies() -> Dict[str, int]:
    """
    Loads drug training frequencies from cached JSON, or compiles from
    split_train.csv + labeled_pairs.csv on first call.
    """
    global _DRUG_FREQ_CACHE
    if _DRUG_FREQ_CACHE is not None:
        return _DRUG_FREQ_CACHE

    if os.path.exists(CACHE_JSON_PATH):
        try:
            with open(CACHE_JSON_PATH, "r", encoding="utf-8") as f:
                _DRUG_FREQ_CACHE = json.load(f)
                return _DRUG_FREQ_CACHE
        except Exception as e:
            logger.warning(f"Failed to read {CACHE_JSON_PATH}: {e}. Recomputing...")

    # Recompute from training split
    if not os.path.exists(SPLIT_TRAIN_PATH) or not os.path.exists(LABELS_PATH):
        logger.warning(f"Training split or labels not found at {SPLIT_TRAIN_PATH}. Returning empty.")
        _DRUG_FREQ_CACHE = {}
        return _DRUG_FREQ_CACHE

    import pandas as pd

    labels_df = pd.read_csv(LABELS_PATH)
    train_idx = pd.read_csv(SPLIT_TRAIN_PATH)["row_index"].values
    train_pairs = labels_df.iloc[train_idx]

    counts: Dict[str, int] = {}
    for d in list(train_pairs["drug_a_kg_id"]) + list(train_pairs["drug_b_kg_id"]):
        d_str = str(d).strip()
        counts[d_str] = counts.get(d_str, 0) + 1

    # Save to disk for instantaneous subsequent loads
    try:
        with open(CACHE_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(counts, f, indent=2)
    except Exception as e:
        logger.warning(f"Could not persist {CACHE_JSON_PATH}: {e}")

    _DRUG_FREQ_CACHE = counts
    return _DRUG_FREQ_CACHE


def get_drug_familiarity(drug_id: str) -> Dict[str, Any]:
    """
    Returns the applicability-domain familiarity indicator for a single compound.

    Parameters
    ----------
    drug_id : str
        Canonical DrugBank ID (e.g. 'DB00853').

    Returns
    -------
    dict
        - level: 'high' | 'limited' | 'novel'
        - raw_score: float (count of appearances in training combinations)
        - basis: human-readable explanation citing empirical threshold
    """
    freqs = _load_or_build_frequencies()
    clean_id = str(drug_id).strip()
    count = int(freqs.get(clean_id, 0))

    if count >= THRESHOLD_HIGH:
        level = "high"
        basis = f"Seen in {count:,} training pairs (anchor compound: >= {THRESHOLD_HIGH} pairs)"
    elif count >= THRESHOLD_LIMITED:
        level = "limited"
        basis = f"Seen in {count:,} training pair{'s' if count > 1 else ''} (limited exposure: 1-{THRESHOLD_HIGH - 1} pairs)"
    else:
        level = "novel"
        basis = "Unseen in training set (0 training pairs: inductive / cold-drug prediction)"

    return {
        "level": level,
        "raw_score": float(count),
        "basis": basis,
    }


def get_pair_familiarity(drug_a_id: str, drug_b_id: str) -> Dict[str, Any]:
    """
    Combines individual drug familiarities into a joint combination familiarity assessment.

    Parameters
    ----------
    drug_a_id : str
        DrugBank ID of first compound.
    drug_b_id : str
        DrugBank ID of second compound.

    Returns
    -------
    dict
        - drug_a: get_drug_familiarity(drug_a_id)
        - drug_b: get_drug_familiarity(drug_b_id)
        - pair_level: 'high' | 'moderate' | 'limited' | 'novel'
        - summary: scientific summary of the prediction confidence domain
    """
    fam_a = get_drug_familiarity(drug_a_id)
    fam_b = get_drug_familiarity(drug_b_id)

    cnt_a = int(fam_a["raw_score"])
    cnt_b = int(fam_b["raw_score"])

    if cnt_a >= THRESHOLD_HIGH and cnt_b >= THRESHOLD_HIGH:
        pair_level = "high"
        summary = (
            f"Both compounds are well-characterized training anchors ({cnt_a:,} and {cnt_b:,} pairs). "
            "High confidence domain."
        )
    elif cnt_a >= THRESHOLD_HIGH or cnt_b >= THRESHOLD_HIGH:
        anchor_cnt = max(cnt_a, cnt_b)
        partner_lvl = fam_b["level"] if cnt_a >= THRESHOLD_HIGH else fam_a["level"]
        pair_level = "moderate"
        summary = (
            f"Combination is anchored by a high-frequency compound ({anchor_cnt:,} training pairs); "
            f"partner compound is {partner_lvl}. Informative prediction domain."
        )
    elif cnt_a >= THRESHOLD_LIMITED or cnt_b >= THRESHOLD_LIMITED:
        pair_level = "limited"
        summary = "Both compounds have limited training exposure. Moderate uncertainty."
    else:
        pair_level = "novel"
        summary = (
            "Bilateral cold prediction: neither compound appeared in training combinations. "
            "Operates in inductive zero-shot mode subject to background score compression."
        )

    return {
        "drug_a": fam_a,
        "drug_b": fam_b,
        "pair_level": pair_level,
        "summary": summary,
    }
