# Experiment 5 — Drug-Specific Subnetwork (DSN) → Synergy Prediction Network (SPN) Architecture

## 1. Objective

The objective of Experiment 5 is to evaluate whether decoupling drug context conditioning into a shared **Drug-Specific Subnetwork (DSN)** followed by an explicitly permutation-symmetric **Synergy Prediction Network (SPN)** improves combination synergy prediction and ranking over the current champion pair-interaction architecture (`models/synergy_gnn_pair_interaction.ckpt`).

This is a strict **architecture-only** experiment. No datasets, splits, labels, features (e.g. no CCLE, no ChemBERTa, no target features), or evaluation protocols were altered.

---

## 2. Hypothesis

The central hypothesis was:
> Modeling each drug node separately in the context of the cell line ($z_A = \text{DSN}(h_A, h_{\text{cell}})$, $z_B = \text{DSN}(h_B, h_{\text{cell}})$) before computing symmetric drug–drug interactions ($z_{\text{sum}}, z_{\text{prod}}, z_{\text{diff}}$) provides richer contextual representations that resolve pair ordering dependencies and improve inductive synergy prediction—particularly on unseen drugs.

---

## 3. Architecture Description

The proposed DSN/SPN model replaces the concatenated pair scorer with a two-stage contextual and interaction pipeline:

```text
                        Cell Representation (h_cell)
                                     │
                    ┌────────────────┴────────────────┐
                    │                                 │
                Drug A (h_A)                      Drug B (h_B)
                    │                                 │
                    ▼                                 ▼
             Shared DSN Module                 Shared DSN Module
            Linear(256 -> 128)                Linear(256 -> 128)
                   ELU                               ELU
               Dropout(0.3)                      Dropout(0.3)
            Linear(128 -> 128)                Linear(128 -> 128)
                    │                                 │
                    ▼                                 ▼
                z_A(cell)                         z_B(cell)
                    │                                 │
                    └────────────────┬────────────────┘
                                     │
                       Symmetric Interaction Engine
                        z_sum  = z_A + z_B
                        z_prod = z_A * z_B
                        z_diff = |z_A - z_B|
                                     │
                                     ▼
                      pair_repr = [z_sum || z_prod || z_diff || h_cell] (512-d)
                                     │
                                     ▼
                       Synergy Prediction Network (SPN)
                              Linear(512 -> 128)
                                     ELU
                                 Dropout(0.3)
                               Linear(128 -> 3)
                                     │
                                     ▼
                          3-class logits (Ant / Add / Syn)
```

### Key Architectural Distinctions:
1. **Shared DSN Weights**: Drugs A and B pass through the exact same module instances, guaranteeing zero artificial slot identity.
2. **Context Conditioning**: Cell line representation is incorporated at both the individual drug contextualization stage (DSN) and the final interaction stage (SPN).
3. **Exact Invariance**: The pair representation is purely composed of commutative and order-invariant operations ($+$, $\times$, $|\cdot - \cdot|$), ensuring $f(A, B, \text{cell}) \equiv f(B, A, \text{cell})$ by construction.

---

## 4. Parameter Counts

| Model Component | Champion (`pair_interaction`) | DSN / SPN | Difference |
| :--- | :---: | :---: | :---: |
| Drug FP Projection (`Linear(2048, 128)`) | 262,144 | 262,144 | 0 |
| Fallback Drug Embedding | 105,600 | 105,600 | 0 |
| Non-drug Embedding & Projection Tables | 2,126,592 | 2,126,592 | 0 |
| 2-layer Heterogeneous Graph Transformer (HGT) | 772,096 | 772,096 | 0 |
| Cell Line Embedding & Projection | 15,360 | 15,360 | 0 |
| Head Module | 85,315 (Scorer: 640→128→3) | 118,339 (DSN: 256→128→128, SPN: 512→128→3) | +33,024 |
| **Total Trainable Parameters** | **3,367,107** | **3,400,131** | **+33,024 (+0.98%)** |

The parameter budget increased by less than 1%, satisfying the design constraint of avoiding parameter bloat.

---

## 5. Symmetry Mechanism

In the champion model, the pair head concatenated raw representations $[h_A, h_B, h_A \odot h_B, |h_A - h_B|, h_{\text{cell}}]$. Because $[h_A, h_B]$ was asymmetric, permutation invariance relied on test-time forward/reverse averaging $(f(A, B) + f(B, A)) / 2$.

In DSN/SPN, permutation symmetry is guaranteed **by mathematical construction**:
1. $z_A = \text{DSN}([h_A \parallel h_{\text{cell}}])$
2. $z_B = \text{DSN}([h_B \parallel h_{\text{cell}}])$
3. $\text{pair\_repr}(A, B) = [z_A + z_B \parallel z_A \odot z_B \parallel |z_A - z_B| \parallel h_{\text{cell}}]$
4. Swapping inputs yields:
   $$\text{pair\_repr}(B, A) = [z_B + z_A \parallel z_B \odot z_A \parallel |z_B - z_A| \parallel h_{\text{cell}}] \equiv \text{pair\_repr}(A, B)$$
Hence, $f(A, B, \text{cell}) = f(B, A, \text{cell})$ holds identically without requiring test-time duplicate forward passes.

---

## 6. Symmetry Unit Test Results

The suite `tests/test_dsn_spn_architecture.py` and dedicated batch verification scripts were executed before and after training:

| Test Item | Specification | Result | Tolerance | Status |
| :--- | :--- | :---: | :---: | :---: |
| **Shared Parameters** | Drug A & B share identical DSN weights | Verified | Exact identity | **PASS** |
| **Pre-Training Symmetry** | Max $|f(A, B) - f(B, A)|$ on random embeddings | $0.00\times 10^0$ | $\le 1.0\times 10^{-6}$ | **PASS** |
| **Cell Sensitivity** | Mean $|f(A, B, C_1) - f(A, B, C_2)|$ | $0.1759$ | $> 1.0\times 10^{-3}$ | **PASS** |
| **Post-Training Symmetry** | Max $|f(A, B) - f(B, A)|$ across 2,816 validation pairs | $9.54\times 10^{-7}$ | $\le 1.0\times 10^{-6}$ | **PASS** |
| **PyG Batch Symmetry** | Swapping `edge_label_index` in mini-batch | $0.00\times 10^0$ | $\le 1.0\times 10^{-6}$ | **PASS** |
| **Champion Protection** | `models/synergy_gnn_pair_interaction.ckpt` intact | 39.27 MB | Untouched | **PASS** |

---

## 7. Training Configuration

* **Checkpoint Destination**: `models/synergy_gnn_dsn_spn.ckpt`
* **Optimizer**: AdamW ($\text{lr}=10^{-3}$, $\text{weight\_decay}=10^{-4}$)
* **Scheduler**: CosineAnnealingLR ($T_{\max}=30$, $\eta_{\min}=10^{-5}$)
* **Batch Size**: 256
* **Loss Function**: Softened inverse-frequency weighted cross-entropy ($\alpha = [1.4877, 0.6890, 1.5051]$)
* **Early Stopping**: Monitored `val_loss`, patience = 5 epochs
* **Stopping Point**: Epoch 2 reached best `val_loss` = 0.95935; training terminated at epoch 7. Total training wall-clock time: 5.6 minutes on NVIDIA GeForce GTX 1650.

---

## 8. Dataset and Split Confirmation

Split integrity was re-validated against the frozen benchmark protocol (`tests/test_paper_splits.py` passed all 9 test assertions):
* Train set: 78,414 pairs (zero leakage to test drugs)
* Validation set: 35,072 pairs (zero row overlap with train/test)
* Test set: 37,778 pairs (zero pair overlap with train)

---

## 9. Benchmark Results

### A. Primary Benchmark: Strict Bilateral / DrugDouble (2,565 pairs)
*Both drugs strictly unseen in training and validation sets (Zero-shot drug pair generalization).*

| Metric | Champion (`pair_interaction`) | DSN / SPN | Difference ($\Delta$) |
| :--- | :---: | :---: | :---: |
| **Macro AUROC** | **0.6225** | 0.6178 | -0.0047 |
| **Binary Synergy AUROC** | 0.5373 | **0.5457** | +0.0084 |
| **Precision@3** | **40.89%** | 23.56% | **-17.33%** |
| **NDCG@3** | **0.5665** | 0.3252 | **-0.2413** |
| **Precision@5** | **31.47%** | 21.33% | -10.14% |
| **NDCG@5** | **0.5090** | 0.3320 | -0.1770 |
| **Precision@10** | **24.99%** | 24.72% | -0.27% |
| **NDCG@10** | **0.4882** | 0.4033 | -0.0849 |

### B. Secondary Benchmark: LDO-Single / DrugSingle (29,282 pairs)
*One novel/held-out drug paired with a known training drug partner.*

| Metric | Champion (`pair_interaction`) | DSN / SPN | Difference ($\Delta$) |
| :--- | :---: | :---: | :---: |
| **Macro AUROC** | 0.6569 | **0.6769** | **+0.0200** |
| **Binary Synergy AUROC** | 0.5683 | **0.6040** | **+0.0357** |
| **Precision@3** | 39.45% | **42.83%** | **+3.38%** |
| **NDCG@3** | 0.4161 | **0.4438** | **+0.0277** |
| **Precision@5** | — | 40.13% | — |
| **NDCG@5** | — | 0.4247 | — |
| **Precision@10** | — | 35.57% | — |
| **NDCG@10** | — | 0.3884 | — |

*(Clean LDO All 31,847 pairs: Macro AUROC 0.6542 → 0.6723 (+0.0181); Binary AUROC 0.5662 → 0.5997 (+0.0335); P@3 43.04% → 42.19%; NDCG@3 0.4426 → 0.4573).*

### C. Tertiary Benchmark: Pair-Disjoint / LPO (37,778 pairs)
*Pairs strictly absent from training, though individual drugs may appear in other training combinations.*

| Metric | Champion (`pair_interaction`) | DSN / SPN | Difference ($\Delta$) |
| :--- | :---: | :---: | :---: |
| **Macro AUROC** | 0.6448 | **0.6630** | **+0.0182** |
| **Binary Synergy AUROC** | 0.5557 | **0.5922** | **+0.0365** |
| **Precision@3** | 44.73% | **45.57%** | **+0.84%** |
| **NDCG@3** | 0.4532 | **0.4837** | **+0.0305** |
| **Precision@5** | — | 40.68% | — |
| **NDCG@5** | — | 0.4471 | — |
| **Precision@10** | — | 35.74% | — |
| **NDCG@10** | — | 0.4024 | — |

---

## 10. Comprehensive Comparison Against the Champion

| Split | Metric | Current Champion | DSN / SPN | Absolute Difference ($\Delta$) | Relative Change |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Strict Bilateral** | Macro AUROC | 0.6225 | 0.6178 | -0.0047 | -0.75% |
| **Strict Bilateral** | Binary AUROC | 0.5373 | 0.5457 | +0.0084 | +1.56% |
| **Strict Bilateral** | Precision@3 | **40.89%** | 23.56% | **-17.33%** | **-42.38%** |
| **Strict Bilateral** | NDCG@3 | **0.5665** | 0.3252 | **-0.2413** | **-42.60%** |
| **LDO-Single** | Macro AUROC | 0.6569 | 0.6769 | +0.0200 | +3.04% |
| **LDO-Single** | Binary AUROC | 0.5683 | 0.6040 | +0.0357 | +6.28% |
| **LDO-Single** | Precision@3 | 39.45% | 42.83% | +3.38% | +8.57% |
| **LDO-Single** | NDCG@3 | 0.4161 | 0.4438 | +0.0277 | +6.66% |
| **Pair-Disjoint** | Macro AUROC | 0.6448 | 0.6630 | +0.0182 | +2.82% |
| **Pair-Disjoint** | Binary AUROC | 0.5557 | 0.5922 | +0.0365 | +6.57% |
| **Pair-Disjoint** | Precision@3 | 44.73% | 45.57% | +0.84% | +1.88% |
| **Pair-Disjoint** | NDCG@3 | 0.4532 | 0.4837 | +0.0305 | +6.73% |

---

## 11. Failure Mode and Behavioral Analysis

The empirical results reveal a stark dichotomy between the **bilateral unseen** setting and the **partially seen / pair-disjoint** settings:

1. **Why LDO-Single and Pair-Disjoint Improved**:
   When at least one drug (or both drugs separately) has been seen during training, conditioning each drug individually on the cell line embedding through the DSN produces a substantially cleaner contextual vector. The SPN interaction head leveraged these refined representations to gain $+0.0200$ Macro AUROC and $+0.0357$ Binary AUROC on LDO-Single, and $+0.0182$ Macro AUROC on Pair-Disjoint.

2. **Why Strict Bilateral Ranking Collapsed**:
   In the Strict Bilateral regime, **neither** drug was present in the training graph. Both drugs rely entirely on their inductive Morgan fingerprint projections.
   In the champion model, the raw embeddings $[h_A, h_B]$ were fed directly into the interaction head alongside explicit interaction terms ($h_A \odot h_B$ and $|h_A - h_B|$). This allowed the linear scorer to directly compare inductive drug features against cell embeddings.
   In DSN/SPN, however, both unseen drug embeddings are forced through an intermediate non-linear transformation ($\text{DSN}$) conditioned on the cell embedding *prior* to interaction calculation. Because the DSN was trained on known drugs, it overfits the manifold of familiar drug-context embeddings. When fed two completely unseen inductive vectors, the DSN maps both into uncalibrated regions of the contextual latent space. Consequently, while discrimination between classes across the entire test set remained marginally stable (AUROC 0.6178 vs 0.6225), **top-k cell-line ranking collapsed completely** (Precision@3 plummeted from $40.89\%$ to $23.56\%$, and NDCG@3 dropped from $0.5665$ to $0.3252$).

---

## 12. Final Conclusion

Per the evaluation protocol hierarchy, the primary decision criterion is the **Strict Bilateral / DrugDouble** benchmark, which represents the true zero-shot drug-combination discovery challenge.

Because the DSN/SPN architecture causes a severe degradation in strict bilateral ranking performance (Precision@3 fell by $17.33\%$ and NDCG@3 fell by $0.2413$), the verdict for Experiment 5 is:

### **REGRESSION**

### Recommendation:
* **Do NOT replace the current champion.** The existing champion (`models/synergy_gnn_pair_interaction.ckpt`) remains the superior model for zero-shot synergy discovery.
* **Preserve architectural insights**: The DSN/SPN mechanism demonstrated strong gains in LDO-Single and Pair-Disjoint regimes where at least one drug is characterized. Future work should investigate residual shortcut connections directly passing the inductive representations $[h_A, h_B]$ around the DSN, or regularizing the DSN with molecular inductive constraints.
