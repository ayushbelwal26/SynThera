# Experiment 7 — Random / Warm Observation Split Benchmark

## 1. Executive Summary

In preclinical drug combination synergy prediction, literature frequently reports validation results using random observation-level (warm) splits, where individual synergy measurements (drug A, drug B, cell line) are partitioned randomly into train, validation, and test subsets.

Experiment 7 establishes and evaluates a standardized, reproducible **70/15/15 random observation-level benchmark** for SynThera (`data/processed/splits_random/`, `data/processed/random_benchmark.json`).

### Key Takeaway
- On a random observation-level split, **99.03%** of test observations involve an unordered drug pair already present in the training set across different cell lines or replicate measurements, and **100%** of test observations have at least one partner drug observed in training.
- Consequently, random split performance reflects **in-distribution interpolation** across familiar chemical space, cell lines, and partner interactions, rather than zero-shot generalization to novel compounds.
- SynThera strictly demarcates this warm split from its cold-drug benchmarks (Pair-Disjoint, Leave-Drug-Out, and Strict Bilateral).
- When trained from scratch on this random split, SynThera achieves **0.8212 Macro AUROC**, **0.7876 Binary Synergy AUROC**, and **70.94% Precision@3**. This is **+19.9 points higher Macro AUROC** and **+25.0 points higher Binary AUROC** than the zero-shot Strict Bilateral benchmark (0.6225 and 0.5373), providing direct empirical evidence of the warm–cold generalization gap.

---

## 2. Benchmark Protocol & Split Statistics

The partition was built using `src/build_random_split.py` from `data/processed/labeled_pairs.csv` (151,264 observations) using a fixed random seed (`seed=42`, `np.random.default_rng(42)`):

| Partition | Observations | Fraction | Unique Drugs | Unique Pairs | Unique Cell Lines |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Train** | 105,884 | 70.0% | 915 | 3,841 | 80 |
| **Validation** | 22,690 | 15.0% | 323 | 3,015 | 78 |
| **Test** | 22,690 | 15.0% | 295 | 2,987 | 78 |
| **Total** | 151,264 | 100.0% | 1,138 | 4,311 | 80 |

### Overlap & Warm Property
- **Drug Overlap**: 182 drugs overlap between train and test. 100.0% of test observations contain at least one drug seen in training; 99.46% contain both drugs seen in training.
- **Pair Overlap**: 2,766 unordered drug pairs overlap between train and test. **99.03% of test observations** (22,469 / 22,690) have their exact unordered pair present in training.
- **Cell Line Overlap**: 100.0% of test cell lines are present in training.

---

## 3. Methodological Integrity & Leakage Prevention

### Why the Frozen Champion Cannot Be Evaluated on the Random Test Set
The SynThera champion model (`models/synergy_gnn_pair_interaction.ckpt`) was trained on the cold-drug inductive split (`data/processed/split_train.csv`). In that split:
- 78,414 training rows from the champion's training set are randomly assigned to the test set of the random benchmark.
- Evaluating the frozen champion on `random_test.csv` would constitute massive train-test contamination, invalidating the evaluation.

### Clean Model Protocol
To establish a genuine, uncontaminated benchmark result:
1. A fresh model was initialized and trained strictly from scratch on `random_train.csv` (`src/train_random_split.py`).
2. Architecture, hyperparameters, and features are identical to the champion:
   - `SynergyModule` with `enriched_pair_head=True` (640-d symmetric representation: $[h_A; h_B; h_A \odot h_B; |h_A - h_B|; h_{cell}]$)
   - Heterogeneous GNN with HGT message-passing over the biomedical Knowledge Graph (drug, disease, protein, pathway)
   - 1024-d Morgan circular fingerprints
   - Softened inverse-frequency class weights computed on `random_train.csv`
   - AdamW optimizer ($\text{lr}=10^{-3}$, $\text{weight decay}=10^{-4}$), early stopping on validation loss ($\text{patience}=5$)
3. Model artifact saved strictly to: `models/synergy_gnn_random_split_seed42.ckpt`.
4. The frozen champion checkpoint (`models/synergy_gnn_pair_interaction.ckpt`, SHA-256 `271a592e065879f2`) was verified untouched.

---

## 4. Evaluation Results

The evaluation protocol follows `eval_paper_splits.py`, using symmetric GNN forward passes (averaging forward $(A, B)$ and reversed $(B, A)$ inference).

### Random Split Test Results (`synergy_gnn_random_split_seed42.ckpt`)

- **Held-out Test Observations**: 22,690
- **Synergy Prevalence**: 14.94% (3,391 synergistic pairs)
- **Cell Lines Represented**: 78 (77 with $\ge 1$ synergy pair)

| Metric | Random / Warm Split Value |
| :--- | :---: |
| **Macro AUROC (OVR 3-class)** | **0.8212** |
| **Macro AUPR (3-class mean)** | **0.6504** |
| **Binary Synergy AUROC** | **0.7876** |
| **Binary Synergy AUPR** | **0.4176** |
| **Precision@3** | **70.94%** |
| **NDCG@3** | **0.7279** |
| **Precision@5** | **65.13%** |
| **NDCG@5** | **0.7017** |
| **Precision@10** | **56.67%** |
| **NDCG@10** | **0.6903** |

---

## 5. SynThera Cross-Benchmark Comparison

| Protocol | Generalization Condition | Macro AUROC | Binary Synergy AUROC | Precision@3 | NDCG@3 |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Random / Warm (Exp 7)** | Observations randomly partitioned (warm) | **0.8212** | **0.7876** | **70.94%** | **0.7279** |
| **Leave-Drug-Out (LDO)** | Partner drug novel to training | **0.6542** | **0.5662** | **43.04%** | **0.4426** |
| **Pair-Disjoint (LPO)** | Drug pair unseen in training | **0.6448** | **0.5557** | **44.73%** | **0.4532** |
| **Strict Bilateral** | Both drugs completely unseen (zero-shot) | **0.6225** | **0.5373** | **40.89%** | **0.5665** |

---

## 6. Scientific Interpretation & Literature Context

1. **Warm vs. Cold Generalization**:
   - On a random split, the model attains **0.8212 Macro AUROC** and **70.94% Precision@3**.
   - Moving from random/warm observation splitting to cold-drug inductive splitting results in a severe performance drop:
     - Macro AUROC drops by **-16.7 to -19.9 points** (from 0.8212 down to 0.6542 in LDO, 0.6448 in Pair-Disjoint, and 0.6225 in Strict Bilateral).
     - Binary Synergy AUROC drops by **-22.1 to -25.0 points** (from 0.7876 down to 0.5662 in LDO and 0.5373 in Strict Bilateral).
     - Precision@3 drops from **70.94%** down to **40.89%** in the zero-shot strict bilateral regime.
   - This drop directly demonstrates that the apparent high accuracy reported in literature using random splits is driven primarily by **memorization and interpolation across known drug pairs and shared biological contexts**, rather than transferable molecular synergy principles.

2. **Benchmarking Recommendations for the Field**:
   - For clinical repurposing within known drug libraries and characterized cell lines, warm split metrics indicate strong multi-task interpolation ability.
   - For discovery of novel synergistic combinations involving investigational small molecules or uncharacterized targets, **Pair-Disjoint** and **Strict Bilateral** benchmarks are mandatory to avoid severe over-optimism.

---

## 7. Verification & Reproducibility

### Checkpoint and Data Hashes (SHA-256)
- Champion checkpoint (`models/synergy_gnn_pair_interaction.ckpt`): `271a592e065879f2` (**VERIFIED UNCHANGED**)
- Cold-drug train split (`data/processed/split_train.csv`): `6511b36236c4d767` (**VERIFIED UNCHANGED**)
- Cold-drug val split (`data/processed/split_val.csv`): `2cf620f5db8e8cd1` (**VERIFIED UNCHANGED**)
- Cold-drug test split (`data/processed/split_test.csv`): `75f64e9761b1ad9d` (**VERIFIED UNCHANGED**)
- Pair-disjoint benchmark (`data/processed/pair_disjoint_benchmark.json`): `f6766d9694da89f2` (**VERIFIED UNCHANGED**)
- Leave-drug-out benchmark (`data/processed/leave_drug_out_benchmark.json`): `eaf3fecd65f8458a` (**VERIFIED UNCHANGED**)
- Strict-bilateral benchmark (`data/processed/strict_bilateral_benchmark.json`): `e252b2a42e459f0f` (**VERIFIED UNCHANGED**)

### Execution Commands
```powershell
# 1. Build random split
python -m src.build_random_split

# 2. Train clean random-split model
python -m src.train_random_split

# 3. Evaluate random-split model
python -m src.eval_random_split --checkpoint models/synergy_gnn_random_split_seed42.ckpt --output data/processed/random_eval_results.json

# 4. Run test suites
python -m unittest tests/test_random_split.py
python -m unittest tests/test_paper_splits.py
```
