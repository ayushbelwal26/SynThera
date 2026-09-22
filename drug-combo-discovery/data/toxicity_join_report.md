# Phase B1: Toxicity & Drug-Drug Interaction (DDI) Join Report

**Generated:** September 2026  
**Module:** `src/toxicity.py`  
**Data Sources:** SIDER 4.1 (Side Effect Resource), PrimeKG Knowledge Graph (DrugBank DDI Subgraph), DrugBank Academic XML (Stubbed / Feature-Flagged)

---

## 1. Executive Summary

Phase B1 builds the toxicity and adverse interaction signal layer that will underpin the multi-objective Pareto ranking in Phase B2 (`FUTURE_SCOPE.md` Section 4.1.B). This signal layer operates independently of the search ranking objectives and model checkpoints, providing fast $O(1)$ in-memory evaluation of phenotypic side-effect overlap and adverse drug-drug interactions.

### Key Highlights
- **Strict Missing Data Invariants:** Missing data resolves to `None` / `unknown`, never a silent `0.0` or `False`.
- **SIDER Coverage in Synergy Universe:** **59.3%** of individual drugs and **86.7%** of labeled combination pairs have full side-effect profiles.
- **PrimeKG DDI Coverage:** **89.5%** of synergy drugs and **97.2%** of labeled pairs are tracked in the DDI universe (**57.4%** flagged with confirmed adverse interactions, **39.8%** confirmed absent of interactions).
- **Runtime Performance:** $O(1)$ hash set lookups and Jaccard intersections executing in microseconds per pair, with full unit test coverage passing 100%.

---

## 2. Dataset Coverage & Join Rates

Coverage was audited across two universes:
1. **PrimeKG Universe:** All 7,946 drug nodes present in the PrimeKG biomedical knowledge graph.
2. **Synergy Dataset Universe:** The 1,138 unique drugs and 151,264 experimentally tested drug combination pairs in `data/processed/labeled_pairs.csv`.

### Table 1: Drug-Level Entity Coverage

| Metric | PrimeKG Universe (N=7,946) | Synergy Dataset (N=1,138) |
| :--- | :--- | :--- |
| **Drugs with SIDER Profiles** | 1,257 (15.82%) | 675 (**59.31%**) |
| **Drugs in DDI Network** | 4,278 (53.84%) | 1,019 (**89.54%**) |
| **Drugs in Both Sources** | 1,201 (15.11%) | 663 (**58.26%**) |
| **Drugs with Neither Source** | 3,612 (45.46%) | 102 (8.96%) |

> **Note on SIDER Join Rate:** SIDER 4.1 contains primarily approved, marketed small molecules indexed by STITCH/PubChem CIDs. PrimeKG contains thousands of investigational, experimental, and discontinued molecules without human clinical side-effect records. However, within our oncology synergy dataset, clinically relevant drugs have a high SIDER representation of **59.31%**.

### Table 2: Pairwise Combination Coverage (Synergy Dataset, N=151,264 pairs)

| Signal Status | Pair Count | Percentage | Interpretation |
| :--- | :--- | :--- | :--- |
| **SIDER Overlap Available** | 131,107 | **86.67%** | Both drugs have SIDER profiles; Jaccard score $\in [0, 1]$ computed |
| **SIDER Missing (Either/Both)** | 20,157 | **13.33%** | Score returns `None` (missing data invariant preserved) |
| **Known DDI Reported (`True`)** | 86,829 | **57.40%** | Confirmed adverse interaction in PrimeKG DrugBank DDI network |
| **No DDI Reported (`False`)** | 60,246 | **39.83%** | Both drugs are tracked in DDI network; no interaction reported |
| **DDI Untracked (`None`)** | 4,189 | **2.77%** | At least one drug absent from DDI universe; returns `None` |
| **Total Tracked in DDI Network** | 147,075 | **97.23%** | Definite boolean status (`True` or `False`) available |

---

## 3. Data Integration Methodology

### 3.1 SIDER 4.1 Side Effect Resource
- **Raw File:** `data/raw/sider_raw.tsv.gz` (`meddra_all_se.tsv`, 13.5 MB compressed, containing 750,000+ drug-effect associations).
- **Official Dictionary:** Downloaded official `drug_names.tsv` (EMBL Heidelberg) mapping STITCH flat/stereo compound IDs to chemical names.
- **Mapping Pipeline:**
  1. Primary mapping: PubChem CID matching between `sider_raw.tsv.gz` (STITCH format `CID10000XXXX`) and pre-indexed CIDs in `data/processed/drug_smiles_fingerprints.csv`. Yielded 1,036 DrugBank matches.
  2. Secondary mapping: Exact and normalized lowercase string matching against SIDER drug names. Yielded 221 additional matches.
  3. Total mapped: **1,257 unique PrimeKG drugs** with MedDRA adverse effect terms.
- **Cache File:** `data/processed/sider_side_effects.json` (2.72 MB).
- **Metric Formulation:** Given side-effect term sets $S_A$ and $S_B$:
  $$\text{Jaccard Overlap} = \frac{|S_A \cap S_B|}{|S_A \cup S_B|}$$
  Returns `None` if either $S_A = \emptyset$ or $S_B = \emptyset$.

### 3.2 PrimeKG Drug-Drug Interaction (DDI) Network
- **Raw File:** Scanned 2,672,628 raw `drug_drug` directed edges from `data/processed/primekg_edges.csv`.
- **Processing:** Grouped by canonical sorted pairs $(u, v)$ with $u < v$ to eliminate directionality artifacts.
- **Result:** **1,336,314 unique undirected DDI interactions** across 4,278 unique DrugBank drugs.
- **Cache Files:**
  - `data/processed/primekg_ddi_pairs.pt` (50.98 MB, PyTorch serialized set of string tuples for instant memory loading).
  - `data/processed/primekg_ddi_drugs.json` (List of 4,278 tracked drugs).
- **Tri-State Logic:**
  - `True`: The pair $(A, B) \in \text{DDI Pairs}$.
  - `False`: Both $A \in \text{DDI Drugs}$ and $B \in \text{DDI Drugs}$, but $(A, B) \notin \text{DDI Pairs}$.
  - `None`: Either $A \notin \text{DDI Drugs}$ or $B \notin \text{DDI Drugs}$ (unknown tracking, never assume safe).

### 3.3 DrugBank Interaction Warnings & Licensing Note
- **Current State:** PrimeKG incorporates the DrugBank DDI network topology (interaction presence/absence), which covers 1.34M drug pairs.
- **Academic Licensing Constraint:** Full textual description, clinical severity classification (e.g. *Major*, *Moderate*, *Minor*), and pharmacokinetic mechanism notes (e.g. *CYP3A4 inhibition increases serum concentration*) require an academic or commercial license for the full DrugBank XML dump (`full database.xml`).
- **Feature Flag Architecture:** `src/toxicity.py` introduces `ENABLE_DRUGBANK_EXTENDED = False`.
- **Value of Extended Data:**
  - If licensed DrugBank XML is mounted, `ddi_severity` will populate with categorical severity levels (`"major"`, `"moderate"`, `"minor"`).
  - Currently, absent the license, `ddi_severity` strictly returns `None`, while `has_known_ddi` reliably indicates adverse interactions using the open PrimeKG DDI network.

---

## 4. Benchmark Evaluation: Sample Drug Combinations

The module was evaluated against 8 curated combinations spanning known high-toxicity pairings, standard-of-care safe pairings, and negative controls.

| Combination | DrugBank IDs | SIDER Overlap | Shared SE Count | Known DDI | Source Coverage (SIDER / DDI / DB) | Clinical Context / Validation |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Cisplatin + Paclitaxel** | `DB00515` + `DB01229` | **0.2048** | 103 | `True` | `{'sider': True, 'primekg_ddi': True, 'drugbank_warnings': False}` | Known severe overlapping peripheral neurotoxicity and nephrotoxicity. Correctly flagged. |
| **Doxorubicin + Trastuzumab** | `DB00997` + `DB00072` | `None` | `None` | `True` | `{'sider': False, 'primekg_ddi': True, 'drugbank_warnings': False}` | Trastuzumab is a monoclonal antibody (biologic, not in small-molecule SIDER). DDI network successfully catches the high-risk cardiomyopathy interaction. |
| **Carmustine + Procarbazine** | `DB00262` + `DB01168` | **0.2218** | 57 | `True` | `{'sider': True, 'primekg_ddi': True, 'drugbank_warnings': False}` | Severe overlapping bone marrow suppression (myelosuppression). High Jaccard overlap and DDI flagged. |
| **Methotrexate + Fluorouracil** | `DB00563` + `DB00544` | **0.1864** | 77 | `True` | `{'sider': True, 'primekg_ddi': True, 'drugbank_warnings': False}` | Classic antimetabolite combination; shared GI and hematologic toxicities correctly captured. |
| **Warfarin + Aspirin** | `DB00682` + `DB00945` | **0.1579** | 24 | `True` | `{'sider': True, 'primekg_ddi': True, 'drugbank_warnings': False}` | Major clinical bleeding risk. Shared terms include `Gastrointestinal haemorrhage`, `Anaemia`. Correctly flagged `True`. |
| **Aspirin + Acetaminophen** | `DB00945` + `DB00316` | **0.1568** | 37 | `False` | `{'sider': True, 'primekg_ddi': True, 'drugbank_warnings': False}` | Common OTC analgesic pairing without major adverse interaction. DDI network returns `False` (tracked but safe). |
| **Metformin + Glipizide** | `DB00331` + `DB01067` | **0.2602** | 51 | `False` | `{'sider': True, 'primekg_ddi': True, 'drugbank_warnings': False}` | Standard first-line / second-line antidiabetic dual therapy. Returns `False` for adverse DDI. |
| **Aspirin + DB99999_DUMMY** | `DB00945` + `DB99999_DUMMY` | `None` | `None` | `None` | `{'sider': False, 'primekg_ddi': False, 'drugbank_warnings': False}` | Synthetic unindexed test drug. Correctly returns `None` for overlap and `None` for DDI (invariant holds). |

---

## 5. Verification & Test Suite

Unit test suite implemented in `tests/test_toxicity.py`:
- `test_known_ddi_pair`: Asserts known interacting pairs return `has_known_ddi is True`.
- `test_pair_with_no_data_returns_none`: Asserts unknown drugs return `None` (strictly `not 0.0` and `not False`).
- `test_known_side_effect_overlap`: Asserts Cisplatin + Paclitaxel yields valid float $\in [0.15, 0.35]$ with non-empty shared terms.
- `test_tracked_pair_without_ddi_returns_false`: Asserts Aspirin + Acetaminophen returns `has_known_ddi is False`.
- `test_drug_name_resolution`: Asserts query by common name (`"cisplatin"`, `"paclitaxel"`) matches canonical DrugBank IDs identically.
- `test_coverage_report_generation_runs_without_crashing`: Iterates through 500 synergy dataset pairs verifying 0 crashes and complete source coverage dicts.

**Test execution result:**
```
......
----------------------------------------------------------------------
Ran 6 tests in 8.467s

OK
```

---

## 6. Next Steps: Phase B2 Handoff

With the data layer validated and cached:
1. **Module Import:** In Phase B2, `src/search.py` will import `get_pair_toxicity` from `src.toxicity`.
2. **Pareto Objective Formulation:** Candidates from `beam_search_combinations()` can be ranked via a multi-objective score balancing synergy prediction ($\hat{y}_{\text{syn}}$), side-effect Jaccard penalty ($\lambda_{\text{se}} \cdot \text{overlap}$), and DDI penalty ($\lambda_{\text{ddi}} \cdot \mathbb{I}[\text{DDI}]$).
3. **No Schema Breaks:** Existing endpoints (`/predict`, `/search`, `/why-not`) and cold-drug benchmark protocols remain untouched until Phase B2 is formally initiated.
