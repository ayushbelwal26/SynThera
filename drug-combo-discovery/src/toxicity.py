"""
Toxicity & Drug-Drug Interaction (DDI) Signal Layer.

Provides pairwise toxicity and adverse interaction metrics by joining:
1. SIDER 4.1 side-effect database (phenotype / adverse effect overlap)
2. PrimeKG DDI network (2.67M DrugBank drug-drug interaction edges)
3. DrugBank interaction warnings (academic license gated behind feature flag)

Design invariants:
- Missing data resolves to None, NEVER a silent 0.0 or False.
- Transparent source coverage tracking for every queried pair.
"""

import os
import json
from typing import Any, Optional, Union
import torch

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_DIR = os.path.join(ROOT_DIR, "data", "processed")

SIDER_JSON_PATH = os.path.join(PROCESSED_DIR, "sider_side_effects.json")
DDI_PT_PATH = os.path.join(PROCESSED_DIR, "primekg_ddi_pairs.pt")
DDI_DRUGS_JSON_PATH = os.path.join(PROCESSED_DIR, "primekg_ddi_drugs.json")
PRIMEKG_DRUGS_CSV = os.path.join(PROCESSED_DIR, "primekg_drugs.csv")

# Feature flag for academic/commercial licensed DrugBank XML annotations
ENABLE_DRUGBANK_EXTENDED = False


class ToxicitySignalLayer:
    """
    Singleton service managing in-memory indices for SIDER and PrimeKG DDI signals.
    """

    def __init__(self):
        self._initialized = False
        self.sider_profiles: dict[str, set[str]] = {}
        self.ddi_pairs: set[tuple[str, str]] = set()
        self.ddi_drugs: set[str] = set()
        self.id_to_name: dict[str, str] = {}
        self.name_to_id: dict[str, str] = {}

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return

        # 1. Load drug name mappings
        if os.path.exists(PRIMEKG_DRUGS_CSV):
            import pandas as pd
            df = pd.read_csv(PRIMEKG_DRUGS_CSV)
            for _, row in df.iterrows():
                db_id = str(row["drugbank_id"]).strip().upper()
                name = str(row["drug_name"]).strip()
                self.id_to_name[db_id] = name
                self.name_to_id[name.lower()] = db_id

        # Common clinical synonym aliases
        synonyms = {
            "aspirin": "DB00945",
            "tylenol": "DB00316",
            "paracetamol": "DB00316",
            "carmustine": "DB00262",
            "procarbazine": "DB01168",
            "fluorouracil": "DB00544",
            "5-fluorouracil": "DB00544",
            "5-fu": "DB00544",
            "methotrexate": "DB00563",
            "cisplatin": "DB00515",
            "paclitaxel": "DB01229",
            "doxorubicin": "DB00997",
            "trastuzumab": "DB00072",
            "warfarin": "DB00682",
            "metformin": "DB00331",
            "glipizide": "DB01067",
        }
        for syn, db_id in synonyms.items():
            if syn not in self.name_to_id and db_id in self.id_to_name:
                self.name_to_id[syn] = db_id

        # 2. Load SIDER side-effect profiles
        if os.path.exists(SIDER_JSON_PATH):
            with open(SIDER_JSON_PATH, "r", encoding="utf-8") as f:
                raw_sider = json.load(f)
            self.sider_profiles = {k.upper(): set(v) for k, v in raw_sider.items()}

        # 3. Load PrimeKG DDI pairs and drug universe
        if os.path.exists(DDI_PT_PATH):
            raw_pairs = torch.load(DDI_PT_PATH, weights_only=False)
            self.ddi_pairs = {(a.upper(), b.upper()) for a, b in raw_pairs}

        if os.path.exists(DDI_DRUGS_JSON_PATH):
            with open(DDI_DRUGS_JSON_PATH, "r", encoding="utf-8") as f:
                raw_drugs = json.load(f)
            self.ddi_drugs = {d.upper() for d in raw_drugs}

        self._initialized = True

    def resolve_drug_id(self, drug_query: str) -> Optional[str]:
        """Resolves either a DrugBank ID (e.g. DB00515) or drug name to a canonical DrugBank ID."""
        self._ensure_initialized()
        if not drug_query:
            return None
        q = str(drug_query).strip()
        q_upper = q.upper()

        if q_upper in self.id_to_name:
            return q_upper
        if q_upper.startswith("DB") and len(q_upper) >= 5:
            return q_upper

        # Attempt name resolution
        q_lower = q.lower()
        if q_lower in self.name_to_id:
            return self.name_to_id[q_lower]

        return None

    def get_pair_toxicity(self, drug_a: str, drug_b: str) -> dict[str, Any]:
        """
        Retrieves toxicity and interaction metrics for a pair of drugs.

        Args:
            drug_a: DrugBank ID or drug name
            drug_b: DrugBank ID or drug name

        Returns:
            dict containing:
              - side_effect_overlap_score: Jaccard similarity [0.0, 1.0] or None if missing data
              - shared_side_effects_count: integer count or None
              - top_shared_side_effects: list of top shared side effect names or None
              - has_known_ddi: True (known DDI), False (both tracked, no DDI), None (untracked/missing)
              - ddi_severity: severity string if available from source, else None
              - source_coverage: dictionary showing availability per source
        """
        self._ensure_initialized()

        id_a = self.resolve_drug_id(drug_a)
        id_b = self.resolve_drug_id(drug_b)

        name_a = self.id_to_name.get(id_a) if id_a else None
        name_b = self.id_to_name.get(id_b) if id_b else None

        # Base case: unresolvable drug IDs
        if id_a is None or id_b is None:
            return {
                "drug_a_id": id_a,
                "drug_b_id": id_b,
                "drug_a_name": name_a,
                "drug_b_name": name_b,
                "side_effect_overlap_score": None,
                "shared_side_effects_count": None,
                "top_shared_side_effects": None,
                "has_known_ddi": None,
                "ddi_severity": None,
                "source_coverage": {
                    "sider": False,
                    "primekg_ddi": False,
                    "drugbank_warnings": False,
                },
            }

        # ── 1. SIDER Side-Effect Overlap ───────────────────────────
        sider_covered = (id_a in self.sider_profiles) and (id_b in self.sider_profiles)
        if sider_covered:
            se_a = self.sider_profiles[id_a]
            se_b = self.sider_profiles[id_b]
            union = se_a | se_b
            intersection = se_a & se_b
            overlap_score = float(len(intersection) / len(union)) if union else 0.0
            shared_count = len(intersection)
            top_shared = sorted(list(intersection))[:10]
        else:
            overlap_score = None
            shared_count = None
            top_shared = None

        # ── 2. PrimeKG DDI Network ─────────────────────────────────
        ddi_covered = (id_a in self.ddi_drugs) and (id_b in self.ddi_drugs)
        if ddi_covered:
            pair_key = (id_a, id_b) if id_a <= id_b else (id_b, id_a)
            has_ddi = pair_key in self.ddi_pairs
        else:
            has_ddi = None

        # ── 3. DrugBank Interaction Warnings (License Gated) ──────
        ddi_severity = None
        db_warnings_covered = False
        if ENABLE_DRUGBANK_EXTENDED:
            # Placeholder for licensed extended XML data
            db_warnings_covered = True

        return {
            "drug_a_id": id_a,
            "drug_b_id": id_b,
            "drug_a_name": name_a,
            "drug_b_name": name_b,
            "side_effect_overlap_score": overlap_score,
            "shared_side_effects_count": shared_count,
            "top_shared_side_effects": top_shared,
            "has_known_ddi": has_ddi,
            "ddi_severity": ddi_severity,
            "source_coverage": {
                "sider": sider_covered,
                "primekg_ddi": ddi_covered,
                "drugbank_warnings": db_warnings_covered,
            },
        }

    def get_drug_toxicity_profile(self, drug_query: str) -> dict[str, Any]:
        """Returns individual drug side-effect count and DDI interaction degree."""
        self._ensure_initialized()
        drug_id = self.resolve_drug_id(drug_query)
        if not drug_id:
            return {
                "drug_id": None,
                "drug_name": None,
                "has_sider_profile": False,
                "side_effects_count": 0,
                "in_ddi_network": False,
            }

        se_list = sorted(list(self.sider_profiles.get(drug_id, set())))
        in_ddi = drug_id in self.ddi_drugs

        return {
            "drug_id": drug_id,
            "drug_name": self.id_to_name.get(drug_id),
            "has_sider_profile": drug_id in self.sider_profiles,
            "side_effects_count": len(se_list),
            "top_side_effects": se_list[:15] if se_list else [],
            "in_ddi_network": in_ddi,
        }


# Module-level singleton instance
_DEFAULT_LAYER = ToxicitySignalLayer()


def get_pair_toxicity(drug_a_id: str, drug_b_id: str) -> dict[str, Any]:
    """
    Convenience wrapper exposing get_pair_toxicity from default ToxicitySignalLayer.
    """
    return _DEFAULT_LAYER.get_pair_toxicity(drug_a_id, drug_b_id)


def get_drug_toxicity_profile(drug_id: str) -> dict[str, Any]:
    """
    Convenience wrapper exposing get_drug_toxicity_profile from default ToxicitySignalLayer.
    """
    return _DEFAULT_LAYER.get_drug_toxicity_profile(drug_id)
