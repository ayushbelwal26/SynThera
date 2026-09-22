# SynThera Technical Documentation & Evaluation Caveats

## 1. Multi-Objective Pair Ranking Formulation $V(\text{pair})$

SynThera ranks drug combinations using a multi-objective composite value function rather than raw synergy probability alone:

$$V(\text{pair}) = w_{\text{synergy}} \cdot p_{\text{synergy}} - w_{\text{toxicity}} \cdot \text{toxicity\_penalty}(\text{pair}) - w_{\text{redundancy}} \cdot \text{redundancy\_penalty}(\text{pair})$$

### Default Parameterization
- $w_{\text{synergy}} = 1.0$
- $w_{\text{toxicity}} = 0.35$
- $w_{\text{redundancy}} = 0.10$

### Toxicity Penalty Formulation
The toxicity penalty joins biomedical graph knowledge from PrimeKG and empirical side-effect frequencies from SIDER 4.1:

$$\text{toxicity\_penalty} = \alpha_{\text{ddi}} \cdot \text{ddi\_risk} + \alpha_{\text{se}} \cdot \text{se\_risk}$$

where $\alpha_{\text{ddi}} = 0.65$ and $\alpha_{\text{se}} = 0.35$.

#### Documented Unknown-Risk Policy
Missing graph data must never silently default to $0.0$ penalty (confirmed safe):
- **Confirmed Toxic (`has_known_ddi = True`):** $\text{ddi\_risk} = 1.0$
- **Confirmed Safe (`has_known_ddi = False`):** $\text{ddi\_risk} = 0.0$
- **Unindexed DDI (`has_known_ddi = None`):** $\text{ddi\_risk} = 0.35$ (baseline uncertainty penalty)
- **Known Side-Effect Profile:** $\text{se\_risk} = \text{Jaccard overlap in SIDER}$
- **Unindexed Side Effects (`side_effect_overlap = None`):** $\text{se\_risk} = 0.15$ (empirical small-molecule mean)

Ordering guarantee:
$$\text{Confirmed Safe } (0.0) < \text{Unknown Risk } (0.28) < \text{Confirmed Toxic } (0.70 - 1.0)$$

---

## 2. Composed Three-Drug Combination Scoring (Phase C1)

Three-drug combination discovery in SynThera is evaluated strictly as **composed pairwise scores**:

> **Mandatory Universal Caption:**
> *"We compose pair scores; we do not have DrugComb 3-way synergy labels."*

For a triplet $\{A, B, C\}$:
- **Primary Bottleneck Ranker:**
  $$V_{\text{min}}(A, B, C) = \min\big(V(A, B), V(A, C), V(B, C)\big)$$
- **Secondary Descriptive Aggregate:**
  $$V_{\text{mean}}(A, B, C) = \frac{V(A, B) + V(A, C) + V(B, C)}{3}$$
- **Triple Toxicity Union:**
  $$\text{Tox}_{\text{triple}} = \max\big(\text{Tox}(A, B), \text{Tox}(A, C), \text{Tox}(B, C)\big)$$
- **Adverse DDI Flag:** $\text{True}$ if any pair has confirmed DDI; $\text{False}$ if all pairs are confirmed safe; $\text{None}$ if any pair is unindexed.

---

## 3. Critical Clinical & Pharmacological Caveats

### Static Graph Signal vs. Clinical Protocol Management
> [!IMPORTANT]
> **Toxicity penalties reflect known adverse-interaction and side-effect-overlap signals from static databases (PrimeKG DDI edges, SIDER) only. They do not account for clinical dose staggering or scheduling that mitigates real-world risk in established regimens.**
>
> For example, **Procarbazine + a nitrosourea + Vincristine** (the PCV or PCV-analog regimen, where Carmustine serves as a close nitrosourea analog stand-in for Lomustine, still used clinically for high-grade and anaplastic oligodendroglioma) is flagged with high toxicity penalties by this system despite being a real standard-of-care combination. This occurs because the underlying drugs have documented overlapping neurotoxicity and myelosuppression risk that clinicians manage via dose reduction, cyclical intervals, and routine hematologic monitoring — dimensions this system does not model.
>
> A high toxicity penalty flags a pair or triple worth **clinical scrutiny**, not necessarily an unsafe combination in practice.

---

## 4. Benchmark Reference Case: Procarbazine + Carmustine + Vincristine @ T98G

Evaluation of the triplet $\{ \text{Procarbazine (DB01168)}, \text{Carmustine (DB00262)}, \text{Vincristine (DB00541)} \}$ in Glioblastoma (`T98G`) demonstrates the multi-pair toxicity demotion mechanism:

| Constituent Pair | $p_{\text{synergy}}$ | `has_known_ddi` | SIDER SE Overlap | `toxicity_penalty` | $V(\text{pair})$ | Documented Clinical Overlap |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Procarbazine × Carmustine** | ~0.93 | **`True`** | 22.18% | **`0.7276`** | ~0.67 – 0.68 | Severe additive myelosuppression (bone marrow depression) |
| **Procarbazine × Vincristine** | ~0.71 | **`True`** | 20.09% | **`0.7203`** | ~0.46 | Additive peripheral neuropathy, CNS toxicity, myelosuppression |
| **Carmustine × Vincristine** | ~0.84 | **`True`** | 21.59% | **`0.7256`** | ~0.58 | Additive myelosuppression, pulmonary and hematologic toxicity |

### Triple Summary Metrics
- **`aggregate_min`**: `0.37 - 0.47` (bottleneck pair: *Procarbazine × Vincristine*)
- **`aggregate_mean`**: `~0.54 - 0.58`
- **`triple_toxicity_penalty`**: `0.7276` ($\max(0.7276, 0.7203, 0.7256)$)
- **`has_known_ddi`**: `True`
- **Candidate Pool Search Rank (`POST /search-triple`):** **#80 of 120** in Glioblastoma candidates.
  Because all three constituent pairs carry confirmed DDI edges (`ddi_risk = 1.0`), this triplet is heavily penalized and demoted below safer synergistic combinations that lack adverse DDI interactions.
