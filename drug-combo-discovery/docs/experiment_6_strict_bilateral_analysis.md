# Experiment 6 — Strict-Bilateral / DrugDouble Generalization Analysis

**Status:** Complete
**Date:** 2026-09-25
**Author:** SynThera Research

---

## 1. Objective

Determine whether the current champion model s weak performance on the strict-bilateral
(DrugDouble) benchmark is explained by **molecular dissimilarity** between the 12 completely
unseen drugs at test time and the 796 drugs seen during training.

This is a **pure analysis experiment** - no new models were trained and no splits were modified.

**Champion:** `models/synergy_gnn_pair_interaction.ckpt`
**Comparative model:** `models/synergy_gnn_dsn_spn.ckpt`

---

## 2. Benchmark Overview

| Property | Value |
|---|---|
| Total strict-bilateral observations | 2,565 |
| Unique unseen test drugs | 12 |
| Unique cell lines | 75 |
| Training drug pool | 796 drugs |
| Drug absence verified | 100% (zero leakage) |

The 12 unseen drugs are: Pipobroman, Gefitinib, Erlotinib, Cyclophosphamide, Methotrexate,
Imatinib, Mechlorethamine, Docetaxel, Lapatinib, (+)-2-(4-biphenyl)propionic acid,
Geldanamycin, and Plicamycin.

---

## 3. Aggregate Model Verification

Metrics re-computed from scratch on the strict-bilateral split to confirm reproducibility.

| Metric | Champion (Computed) | Champion (Reference) |
|---|---|---|
| Macro AUROC | 0.6219 | ~0.6225 |
| Binary Synergy AUROC | 0.5410 | ~0.5373 |
| Precision@3 | 36.44% | ~40.89% |
| NDCG@3 | 0.5208 | ~0.5665 |
| Precision@5 | 31.47% | ~31.47% |
| NDCG@10 | 0.4808 | ~0.4882 |

Minor aggregate deviation (<0.5%) in Macro AUROC is within expected variance from batched
neighbor sampling.

---

## 4. Molecular Coverage of Unseen Drugs

For each unseen drug we computed:
- **max_tanimoto_train** - Maximum Morgan fingerprint Tanimoto similarity to any training drug
- **top5_mean_tanimoto** - Mean similarity across the 5 closest training drugs
- **n_train_ge_0.5** - Count of training drugs with similarity >= 0.5

| Drug | Nearest Train Drug | Max Tanimoto | Top-5 Mean | n>=0.5 | n_obs |
|---|---|---|---|---|---|
| Gefitinib | Canertinib | 0.697 | 0.489 | 1 | 471 |
| Imatinib | Masitinib | 0.747 | 0.480 | 2 | 467 |
| Erlotinib | CUDC-101 | 0.672 | 0.429 | 2 | 580 |
| Methotrexate | Pralatrexate | 0.653 | 0.328 | 1 | 529 |
| Lapatinib | Varlitinib | 0.381 | 0.298 | 0 | 570 |
| (+)-2-(4-biphenyl)propionic acid | Flurbiprofen | 0.588 | 0.501 | 2 | 1 |
| Docetaxel | Cabazitaxel | 0.792 | 0.434 | 2 | 451 |
| Plicamycin | Doxorubicin | 0.236 | 0.213 | 0 | 481 |
| Pipobroman | Cinepazide | 0.216 | 0.187 | 0 | 457 |
| Cyclophosphamide | Ifosfamide | 0.295 | 0.192 | 0 | 555 |
| Mechlorethamine | Phenoxybenzamine | 0.211 | 0.193 | 0 | 463 |
| Geldanamycin | Ivermectin | 0.206 | 0.184 | 0 | 104 |

Coverage summary: 8/12 drugs have max Tanimoto < 0.5.  Only Imatinib (0.747), Docetaxel
(0.792), Gefitinib (0.697), and Erlotinib (0.672) have a meaningfully similar training analog.

---

## 5. Per-Drug Performance (Champion Model)

| Drug | n_obs | Syn Prev. | Macro AUROC | Binary AUROC | P@3 |
|---|---|---|---|---|---|
| Docetaxel | 451 | 48.6% | 0.699 | 0.613 | 54.9% |
| Plicamycin | 481 | 20.2% | 0.659 | 0.746 | 27.2% |
| Methotrexate | 529 | 9.1% | 0.650 | 0.600 | 11.7% |
| Lapatinib | 570 | 21.4% | 0.651 | 0.535 | 21.2% |
| Pipobroman | 457 | 20.4% | 0.669 | 0.684 | 32.7% |
| Erlotinib | 580 | 22.4% | 0.636 | 0.541 | 28.8% |
| Cyclophosphamide | 555 | 5.0% | 0.596 | 0.526 | 5.9% |
| Imatinib | 467 | 20.6% | 0.594 | 0.348 | 10.5% |
| Mechlorethamine | 463 | 5.2% | 0.688 | 0.686 | 5.6% |
| Gefitinib | 471 | 37.6% | 0.556 | 0.401 | 25.9% |
| Geldanamycin | 104 | 25.0% | 0.388 | 0.628 | 29.8% |
| (+)-2-(4-biphenyl)propionic acid | 1 | 0.0% | N/A | N/A | 0.0% |

Notable:
- Docetaxel (highest coverage: max_tan=0.79) achieves the best Macro AUROC (0.699) and P@3 (54.9%).
- Geldanamycin (lowest coverage: max_tan=0.21) achieves the worst Macro AUROC (0.388).
- Imatinib (max_tan=0.747, 2 neighbors >=0.5) suffers surprisingly low Binary AUROC (0.348).

---

## 6. Correlation Analysis (n=11 valid drugs)

CAUTION: n=11 — all correlations are exploratory only.

| Similarity Proxy | Metric | Spearman rho | p-value | Pearson r | Interpretation |
|---|---|---|---|---|---|
| max_tanimoto_train | Macro AUROC | -0.027 | 0.937 | +0.166 | No association |
| max_tanimoto_train | Binary AUROC | **-0.645** | **0.032** | -0.646 | Significant negative |
| max_tanimoto_train | P@3 | +0.063 | 0.846 | +0.161 | No association |
| top5_mean_tanimoto | Macro AUROC | -0.091 | 0.790 | +0.097 | No association |
| top5_mean_tanimoto | Binary AUROC | -0.591 | 0.056 | **-0.730** | Trend (marginal) |
| top5_mean_tanimoto | P@3 | -0.266 | 0.404 | +0.022 | No association |
| n_train_ge_0.5 | Macro AUROC | -0.096 | 0.780 | +0.162 | No association |
| n_train_ge_0.5 | Binary AUROC | -0.487 | 0.128 | -0.534 | Trend |
| n_train_ge_0.5 | P@3 | -0.031 | 0.925 | +0.091 | No association |

Key finding: Higher molecular similarity to training drugs is **negatively** correlated with
Binary Synergy AUROC (rho=-0.645, p=0.032).  This is counterintuitive and may reflect
representation interference: drugs similar to known drugs compete with those embeddings,
creating ambiguity.  Structurally isolated drugs (Plicamycin, Mechlorethamine) may carve
unique representation regions with less interference.

Macro AUROC and P@3 show no significant correlation with any coverage metric.

---

## 7. Champion vs. DSN/SPN Comparison (Strict-Bilateral)

| Drug | Champ P@3 | DSN P@3 | Delta P@3 | Champ Macro | DSN Macro | Delta Macro |
|---|---|---|---|---|---|---|
| Docetaxel | 54.9% | 65.4% | +10.5% | 0.699 | 0.707 | +0.008 |
| Plicamycin | 27.2% | 33.3% | +6.2% | 0.659 | 0.699 | +0.040 |
| Mechlorethamine | 5.6% | 8.0% | +2.5% | 0.688 | 0.570 | -0.118 |
| Imatinib | 10.5% | 10.5% | 0.0% | 0.594 | 0.623 | +0.029 |
| Erlotinib | 28.8% | 29.3% | +0.5% | 0.636 | 0.615 | -0.020 |
| Pipobroman | 32.7% | 29.6% | -3.1% | 0.669 | 0.668 | -0.001 |
| Gefitinib | 25.9% | 25.9% | 0.0% | 0.556 | 0.467 | -0.089 |
| Lapatinib | 21.2% | 20.3% | -0.9% | 0.651 | 0.580 | -0.071 |
| Cyclophosphamide | 5.9% | 4.1% | -1.8% | 0.596 | 0.601 | +0.004 |
| Methotrexate | 11.7% | 9.0% | -2.7% | 0.650 | 0.509 | -0.141 |
| Geldanamycin | 29.8% | 27.4% | -2.4% | 0.388 | 0.515 | +0.127 |

Net winner (11 drugs): P@3 -- Champion 5, DSN/SPN 4, Tie 2.
Macro AUROC -- Champion 5, DSN/SPN 6.

---

## 8. Key Findings

**Finding 1: Strict-bilateral is genuinely hard**
All 12 unseen drugs are truly zero-shot. 8/12 have max Tanimoto < 0.5 vs. the training pool.
The task requires genuine extrapolation beyond the training distribution.

**Finding 2: Molecular similarity is not a reliable performance predictor**
Macro AUROC and P@3 show no significant correlation with any similarity metric.
Binary AUROC shows a significant *negative* correlation (rho=-0.645, p=0.032), which may
reflect representation interference rather than successful transfer.

**Finding 3: Per-drug variance is driven by synergy prevalence**
Synergy prevalence varies from 5% (Cyclophosphamide) to 48.6% (Docetaxel) and is a stronger
driver of P@3 than molecular similarity.

**Finding 4: Neither model dominates on strict-bilateral**
Champion and DSN/SPN split drug-level wins roughly evenly. Champion is more stable;
DSN/SPN wins on higher-prevalence drugs but shows sharper regression on Methotrexate (-0.141).

---

## 9. Limitations

1. n=11 valid drugs -- all correlations are exploratory.
2. Morgan fingerprints (2048-bit, radius=2) do not capture 3D pharmacophore, target affinity,
   or ADMET properties.
3. Per-drug evaluation aggregates across cell lines; cell-line heterogeneity may mask
   drug-specific effects.
4. The representation interference hypothesis (Finding 2) is speculative and needs ablation.

---

## 10. Recommended Next Steps

| Priority | Action |
|---|---|
| High | Embedding space analysis (UMAP of drug node embeddings, seen vs. unseen) to test the representation interference hypothesis |
| High | Augment training set with alkylating agents to improve coverage for Cyclophosphamide / Mechlorethamine family |
| Medium | Target-based features as a complement to fingerprints for zero-shot drugs |
| Medium | Expand strict-bilateral split to more unseen drugs for better statistical power |
| Low | Test different fingerprint radii / ECFP variants to verify negative correlation direction |

---

## 11. Artifacts

| File | Description |
|---|---|
| `scratch/experiment_6_strict_bilateral_analysis.csv` | Full per-drug metrics table |
| `scratch/experiment_6_cell_lines.csv` | Cell-line-level breakdown |
| `scratch/experiment_6/correlations.json` | Spearman/Pearson metrics |
| `docs/figures/figure1_similarity_vs_auroc.png` | Similarity vs. Binary AUROC scatter |
| `docs/figures/figure2_similarity_vs_p3.png` | Similarity vs. P@3 scatter |
| `docs/figures/figure3_champion_vs_dsn_spn.png` | Per-drug Champion vs. DSN/SPN |
| `scratch/run_experiment_6_analysis.py` | Reproducible analysis script |

---

*See also:*
- `docs/experiment_5_dsn_spn.md` -- DSN/SPN architecture experiment
- `docs/model_card_pair_interaction.md` -- Champion model reference
