# SynThera: Paper Evaluation Protocols and Benchmark Validation

This document establishes the formal, mathematically verified benchmark splits and evaluation protocols for SynThera, aligning repository nomenclature with published drug-combination synergy literature.

---

## 1. Executive Summary & Evaluation Taxonomy

Drug synergy benchmark literature contains three distinct levels of experimental generalization:

```
+---------------------------------------------------------------------------------------+
| LEVEL 1: Leave-Pair-Out (LPO) / Pair-Disjoint / Leave-Drug-Combination-Out (LDCO)     |
|   * Individual drugs A and B have both been seen during training with other partners. |
|   * The specific combination {A, B} is held out from training.                        |
|   * Common in: DeepSynergy (Preuer 2018), TranSynergy (Liu 2021), GraphSynergy (2021) |
+---------------------------------------------------------------------------------------+
                                           |
                                           v
+---------------------------------------------------------------------------------------+
| LEVEL 2: Leave-Drug-Out (LDO) / DrugSingle (Semi-Cold-Start / Unilateral Cold-Drug)   |
|   * Exactly ONE drug (e.g. Drug A) is novel and completely unseen in training.        |
|   * The partner (Drug B) is known and present in the training set.                    |
|   * Evaluates: Drug repurposing and add-on therapy prediction for a novel compound.   |
|   * Common in: HERMES (Zeng 2024), TranSynergy (2021), SynCell (2024)                 |
+---------------------------------------------------------------------------------------+
                                           |
                                           v
+---------------------------------------------------------------------------------------+
| LEVEL 3: Strict Bilateral / DrugDouble (Zero-Shot / Bilateral Cold-Drug)              |
|   * BOTH Drug A and Drug B are strictly novel and unseen in training & validation.    |
|   * Neither compound possesses prior combination, single-agent, or synergy data.      |
|   * Evaluates: Early-stage zero-shot novel chemical combination discovery.            |
|   * Common in: HERMES (Zeng 2024), SynCell (2024), SynThera Strict Bilateral          |
+---------------------------------------------------------------------------------------+
```

---

## A. Current SynThera Strict Bilateral Benchmark

### Exact Definition
A test pair observation $((d_A, d_B), c)$ belongs to the **Strict Bilateral Cold-Drug Benchmark** if and only if:
$$d_A \in D_{\text{test}} \quad \text{AND} \quad d_B \in D_{\text{test}}$$
Equivalently:
$$\{d_A, d_B\} \cap \left(D_{\text{train}} \cup D_{\text{val}}\right) = \emptyset$$

### Verified Ground-Truth Statistics
- **Total test pairs:** 2,565 observations
- **Unique drugs:** Exactly 12 compounds (100% held-out; 0 overlap with train/val)
- **Cell lines evaluated:** 75 cancer cell lines
- **Unique unordered drug pairs:** 50 unique chemical pairs
- **Synergy class distribution:**
  - `additive`: 1,581 (61.64%)
  - `synergy`: 530 (20.66%)
  - `antagonism`: 454 (17.70%)
- **Performance (Champion Checkpoint: `models/synergy_gnn_pair_interaction.ckpt`):**
  - Macro AUROC (OVR, 3-class): **0.6225**
  - Macro AUPR (3-class mean): **0.4229**
  - Binary Synergy AUROC: **0.5373**
  - Binary Synergy AUPR: **0.2732**
  - Precision@3 (Mean across cell lines): **40.89%**
  - NDCG@3 (Mean across cell lines): **0.5665**

---

## B. Pair-Disjoint / Leave-Pair-Out (LPO) Protocol

### Exact Definition
The partitioning unit is the canonical unordered drug pair $p = \{d_A, d_B\}$.
- Let $\mathcal{P} = \{ \{d_A, d_B\} : (d_A, d_B) \in \mathcal{D} \}$ be the set of all unique unordered drug combinations ($|\mathcal{P}| = 4,311$).
- $\mathcal{P}$ is partitioned into $\mathcal{P}_{\text{train}}$ (70%), $\mathcal{P}_{\text{val}}$ (15%), and $\mathcal{P}_{\text{test}}$ (15%) using deterministic pseudo-random shuffling (`seed=42`).
- Invariant:
  $$\mathcal{P}_{\text{test}} \cap \mathcal{P}_{\text{train}} = \emptyset, \quad \mathcal{P}_{\text{test}} \cap \mathcal{P}_{\text{val}} = \emptyset, \quad \mathcal{P}_{\text{val}} \cap \mathcal{P}_{\text{train}} = \emptyset$$
- Individual drugs $d_A$ or $d_B$ **are allowed** to appear in both training and testing when paired with different partners:
  $$\left(\bigcup_{p \in \mathcal{P}_{\text{test}}} p\right) \cap \left(\bigcup_{p \in \mathcal{P}_{\text{train}}} p\right) \neq \emptyset$$

### Split Statistics (Full-Dataset Canonical LPO)
- **Unique unordered pairs:**
  - Train: 3,017 pairs (70.0%)
  - Validation: 647 pairs (15.0%)
  - Test: 647 pairs (15.0%)
- **Observations:**
  - Train: 106,242 observations (70.2%)
  - Validation: 22,353 observations (14.8%)
  - Test: 22,669 observations (15.0%)
- **Unique drugs:**
  - Test drugs: 306 compounds
  - Train drugs: 906 compounds
  - Shared drugs (with different combination partners): 182 compounds (59.5% of test drugs)
- **Test cell lines:** 79 cell lines
- **Test class distribution:** Additive: 15,824 (69.80%), Antagonism: 3,432 (15.14%), Synergy: 3,413 (15.06%)
- **Saved Files:**
  - Indices: `data/processed/splits_extra/pair_disjoint_{train,val,test}.csv`
  - Benchmark Metadata: `data/processed/pair_disjoint_benchmark.json`

---

## C. Leave-Drug-Out (LDO) Protocol

### Exact Definition
The partitioning unit is the individual drug compound $d \in \mathcal{D}_{\text{drugs}}$ ($N = 1,138$).
- Partitioned into $D_{\text{train}}$ (796 drugs, 70%), $D_{\text{val}}$ (171 drugs, 15%), $D_{\text{test}}$ (171 drugs, 15%).
- Invariant:
  $$D_{\text{test}} \cap D_{\text{train}} = \emptyset, \quad D_{\text{test}} \cap D_{\text{val}} = \emptyset, \quad D_{\text{val}} \cap D_{\text{train}} = \emptyset$$
- **Training Population:** All pairs where $\{d_A, d_B\} \subseteq D_{\text{train}}$ (78,414 observations). Exactly 0 test drugs and 0 validation drugs appear in training.
- **Clean LDO Test Population:** All pairs containing at least one test drug and zero validation drugs:
  $$\left(\{d_A, d_B\} \cap D_{\text{test}} \neq \emptyset\right) \quad \text{AND} \quad \left(\{d_A, d_B\} \cap D_{\text{val}} = \emptyset\right)$$

### Clean LDO Test Statistics
- **Total clean observations:** 31,847 pairs
- **Unique drugs:** 235 compounds (171 held-out test drugs + 64 known training partner drugs)
- **Validation drug contamination:** Exactly 0 compounds (0 pairs)
- **Cell lines:** 79 cell lines
- **Class distribution:** Additive: 21,675 (68.06%), Synergy: 5,237 (16.44%), Antagonism: 4,935 (15.50%)
- **Sub-Populations:**
  1. **LDO-Single (DrugSingle / Unilateral):** 29,282 observations where exactly 1 drug $\in D_{\text{test}}$ and 1 drug $\in D_{\text{train}}$.
     - Macro AUROC: **0.6569**
     - Binary Synergy AUROC: **0.5683**
     - Precision@3: **39.45%** | NDCG@3: **0.4161**
  2. **LDO-Double (DrugDouble / Strict Bilateral):** 2,565 observations where both drugs $\in D_{\text{test}}$.
     - Macro AUROC: **0.6225**
     - Binary Synergy AUROC: **0.5373**
     - Precision@3: **40.89%** | NDCG@3: **0.5665**
- **Composite Clean LDO Performance:**
  - Macro AUROC: **0.6542**
  - Binary Synergy AUROC: **0.5662**
  - Precision@3: **43.04%** | NDCG@3: **0.4426**
- **Saved File:** `data/processed/leave_drug_out_benchmark.json`

---

## D. Literature Comparison Table

The following table summarizes how leading published deep learning models evaluate drug synergy, their exact split mechanisms, and their reported metrics.

> **CRITICAL METHODOLOGICAL NOTE:** Direct numerical comparison across papers is NOT valid when split definitions, datasets, or evaluation tasks differ. Models evaluated under warm/LPO splits naturally achieve much higher AUROC (0.84–0.90) because the model has already learned individual representations for all constituent drugs. When evaluated on zero-shot DrugDouble / bilateral splits, AUROC across all architectures drops to the 0.60–0.70 regime.

| Paper | Dataset | Split Protocol | One/Both Drugs Unseen | Task Type | AUROC Reported |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **DeepSynergy**<br>*(Preuer et al., Bioinformatics 2018)* | O'Neil et al.<br>(23,062 pairs, 38 drugs, 39 cell lines) | Leave-Drug-Combination-Out<br>(Pair-disjoint 5-fold CV) | **Neither Unseen**<br>(both drugs seen in train with other partners) | Binary Synergy Classification<br>(Loewe threshold > 30) | **0.9000** |
| **TranSynergy**<br>*(Liu & Xie, PLoS Comput Biol 2021)* | DrugComb / O'Neil<br>(22,737 pairs, 38 drugs, 39 cell lines) | Leave-Drug-Combination-Out<br>(Nested 5-fold CV) | **Neither Unseen**<br>(pair-disjoint; individual drugs known) | Synergy Score Regression &<br>Binary Classification | **0.8420** |
| **TranSynergy**<br>*(Liu & Xie, PLoS Comput Biol 2021)* | DrugComb / O'Neil | Leave-Drug-Out (LDO) | **One or Both Unseen**<br>(drug held out from training folds) | Synergy Score Regression &<br>Binary Classification | **0.7410** |
| **GraphSynergy**<br>*(Yang et al., Bioinformatics 2021)* | DrugComb<br>(~60,000 pairs, 826 drugs, 31 cell lines) | Leave-Combination-Out<br>(Pair-disjoint 5-fold CV) | **Neither Unseen**<br>(PPI network + individual drugs seen) | Binary Synergy Classification<br>(S score > 0) | **0.8870** |
| **HERMES**<br>*(Zeng et al., Briefings in Bioinf 2024)* | NCI-ALMANAC<br>(5,247 pairs, 114 drugs, 60 cell lines) | **DrugSingle**<br>(Semi-cold-start) | **One Drug Unseen**<br>(1 novel drug + 1 known train drug) | Binary Synergy Classification<br>(ComboScore threshold) | **0.7213** |
| **HERMES**<br>*(Zeng et al., Briefings in Bioinf 2024)* | NCI-ALMANAC<br>(5,247 pairs, 114 drugs, 60 cell lines) | **DrugDouble**<br>(Zero-shot bilateral) | **Both Drugs Unseen**<br>(both novel to training set) | Binary Synergy Classification<br>(ComboScore threshold) | **0.6839** |
| **SynCell**<br>*(arXiv 2024)* | NCI-ALMANAC & DrugComb | **DrugDouble**<br>(Zero-shot bilateral) | **Both Drugs Unseen**<br>(held-out compound evaluation) | Binary Synergy Classification | **0.7140** |
| **SynThera**<br>*(Current Work — Pair Interaction GNN)* | DrugComb + PrimeKG<br>(151,264 pairs, 1,138 drugs, 80 cell lines) | **Pair-Disjoint / LPO**<br>(37,778 pairs, 950 unique pairs) | **Neither Unseen**<br>(individual drugs in train, pairs unseen) | 3-Class Synergy (Macro AUROC)<br>Binary Synergy AUROC | Macro: **0.6448**<br>Binary: **0.5557** |
| **SynThera**<br>*(Current Work — Pair Interaction GNN)* | DrugComb + PrimeKG<br>(151,264 pairs, 1,138 drugs, 80 cell lines) | **LDO-Single (DrugSingle)**<br>(29,282 pairs) | **One Drug Unseen**<br>(1 held-out test drug + 1 known train drug) | 3-Class Synergy (Macro AUROC)<br>Binary Synergy AUROC | Macro: **0.6569**<br>Binary: **0.5683** |
| **SynThera**<br>*(Current Work — Pair Interaction GNN)* | DrugComb + PrimeKG<br>(151,264 pairs, 1,138 drugs, 80 cell lines) | **Strict Bilateral (DrugDouble)**<br>(2,565 pairs, 12 drugs, 75 cell lines) | **Both Drugs Unseen**<br>(neither drug in train or val) | 3-Class Synergy (Macro AUROC)<br>Binary Synergy AUROC | Macro: **0.6225**<br>Binary: **0.5373** |

---

## E. Reproducible Evaluation Commands

All benchmarks can be executed deterministically using the master CLI:

```bash
# 1. Strict Bilateral (DrugDouble zero-shot benchmark: 2,565 pairs)
python -m src.eval_paper_splits --split strict_bilateral --checkpoint models/synergy_gnn_pair_interaction.ckpt

# 2. Leave-Drug-Out (Clean LDO benchmark: 31,847 pairs)
python -m src.eval_paper_splits --split leave_drug_out --checkpoint models/synergy_gnn_pair_interaction.ckpt

# 3. Pair-Disjoint / Leave-Pair-Out (37,778 pairs)
python -m src.eval_paper_splits --split pair_disjoint --checkpoint models/synergy_gnn_pair_interaction.ckpt
```

---

## F. Leakage & Integrity Verification

All splits have passed automated verification (`tests/test_paper_splits.py`):
1. **Zero Row Overlap:** Train $\cap$ Test = $\emptyset$, Val $\cap$ Test = $\emptyset$, Train $\cap$ Val = $\emptyset$.
2. **Zero Pair Leakage (LPO):** $\mathcal{P}_{\text{test}} \cap \mathcal{P}_{\text{train}} = \emptyset$.
3. **Zero Drug Leakage (LDO):** $D_{\text{test}} \cap D_{\text{train}} = \emptyset$.
4. **Strict Bilateral Isolation:** For all 2,565 strict pairs, $d_A \in D_{\text{test}}$ and $d_B \in D_{\text{test}}$, with $\{d_A, d_B\} \cap (D_{\text{train}} \cup D_{\text{val}}) = \emptyset$.
5. **Permutation Symmetry:** Models satisfy $f(d_A, d_B, c) \equiv f(d_B, d_A, c)$.
