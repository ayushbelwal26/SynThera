# SynThera: Technical Specification & Architecture Manual

Comprehensive architectural, algorithmic, and engineering documentation for **SynThera: Explainable Drug Combination Discovery for Multi-Drug Resistant Conditions**.

---

## Table of Contents
1. [Executive Overview & Scientific Philosophy](#1-executive-overview--scientific-philosophy)
2. [Full Technology Stack & System Architecture](#2-full-technology-stack--system-architecture)
3. [Heterogeneous Graph Transformer (HGT / SynergyGNN)](#3-heterogeneous-graph-transformer-hgt--synergygnn)
4. [Combinatorial Search & Discovery Engine](#4-combinatorial-search--discovery-engine)
5. [Multi-Objective Value Function $V(\text{pair})$ & Toxicity Layer](#5-multi-objective-value-function-vtextpair--toxicity-layer)
6. [Explainability, Graph Attribution & In-Silico Faithfulness](#6-explainability-graph-attribution--in-silico-faithfulness)
7. [Counterfactual Diagnostic "Why Not?" Reasoning Engine](#7-counterfactual-diagnostic-why-not-reasoning-engine)
8. [Real-Time Retrieve-Then-Cite PubMed RAG Engine](#8-real-time-retrieve-then-cite-pubmed-rag-engine)
9. [Strictly Grounded Tool-Calling Conversational Assistant](#9-strictly-grounded-tool-calling-conversational-assistant)
10. [REST API Specification & Service Architecture](#10-rest-api-specification--service-architecture)
11. [Frontend User Interface & Interaction Design](#11-frontend-user-interface--interaction-design)
12. [Benchmark Evaluations & Scientific Protocols](#12-benchmark-evaluations--scientific-protocols)

---

## 1. Executive Overview & Scientific Philosophy

### 1.1 The Challenge: Multi-Drug Resistance (MDR) in Oncology
Cancers frequently develop resistance to monotherapies through compensatory pathway activation, target mutations, and heterogeneous clonal selection. While combinatorial therapies offer the potential to overcome resistance and achieve synergistic tumor suppression at lower doses, searching the combinatorial space of approved and experimental small molecules is intractable through high-throughput wet-lab screening alone ($>10^7$ candidate pairs across hundreds of cancer cell lines).

### 1.2 The SynThera Solution
**SynThera** is an end-to-end artificial intelligence and computational biology platform that:
1. **Predicts drug synergy** across cancer cell lines using a multi-relational Heterogeneous Graph Transformer (HGT).
2. **Discovers candidate combinations** using constrained Beam Search, Greedy Search, and Monte Carlo Tree Search (MCTS).
3. **Optimizes a multi-objective value function** balancing calibrated synergy probability against drug-drug interaction (DDI) risk, side-effect overlap, and target redundancy.
4. **Delivers mechanistic explanations** via gradient-based edge attribution over 2-hop local subgraphs, verified through in-silico faithfulness ablation experiments.
5. **Retrieves peer-reviewed clinical citations** via real-time NCBI PubMed E-Utilities RAG.
6. **Diagnoses rejected candidates** through counterfactual "Why Not?" reasoning.
7. **Empowers researchers via a grounded conversational agent** operating under a zero-hallucination policy bounded by deterministic core tools.

### 1.3 Core Scientific Principle: Cold-Drug Inductive Generalization
Standard drug synergy benchmarks in machine learning literature suffer from **massive transductive data leakage**. When drug pairs are split randomly into train and test sets, if Drug A is seen with Drug B in training, evaluating $(\text{Drug A}, \text{Drug C})$ during testing simply exploits single-drug marginal promiscuity rather than learning true combinatorial interaction mechanics. This yields artificially inflated test AUROC scores ($>0.85$) that fail wet-lab transfer.

SynThera strictly enforces a **Leave-Drugs-Out Cold-Split Protocol**:
* A designated 15% of drugs are held out and **completely absent** from all training combinations:
  $$\mathcal{D}_{\text{train}} \cap \mathcal{D}_{\text{test}} = \emptyset$$
* Test combinations consist of:
  * **Unilateral cold pairs (~29,282 pairs):** Exactly one drug was completely unseen during training.
  * **Bilateral cold pairs (~8,496 pairs):** Neither drug appeared anywhere in any training combination (the strictest inductive transfer setting).
* Achieving **0.64 AUROC** and **0.44 AUPR** (against a ~0.16 random base rate) on strictly cold pairs reflects genuine inductive generalization over biomedical knowledge topology.

---

## 2. Full Technology Stack & System Architecture

```
                                 SYNTHERA SYSTEM ARCHITECTURE
                                 
 +-----------------------------------------------------------------------------------------+
 |                               Biomedical Knowledge Base                                 |
 |  PrimeKG (10 Node Types, 24 Edge Types, 2.67M DDI Edges)  |  DrugComb Synergy Labels   |
 |  SIDER 4.1 Side Effects  |  CCLE/DepMap Gene Expression   |  RDKit 2048-bit Morgan FP  |
 +-----------------------------------------------------------------------------------------+
                                              |
                                              v
 +-----------------------------------------------------------------------------------------+
 |                               Core Machine Learning & Discovery                         |
 |  - Heterogeneous Graph Transformer (PyG HGTConv, 2 layers, 4 heads, hidden_dim=128)     |
 |  - Bilateral Pair Pooling: [h_A ⊙ h_B, |h_A - h_B|, h_A + h_B] + Cell Line Conditioning   |
 |  - Multiclass Focal Loss (gamma=2.0) with softened inverse-frequency class weights       |
 |  - Search Engine: Beam Search (width=5), Greedy Search, MCTS with UCT exploration        |
 |  - Multi-Objective Ranker: V(pair) = w_syn*p_syn - w_tox*Tox - w_red*Red                |
 +-----------------------------------------------------------------------------------------+
                                              |
                                              v
 +-----------------------------------------------------------------------------------------+
 |                           Attribution, Faithfulness & Diagnostic                        |
 |  - Integrated Gradients / Saliency on 2-hop local subgraphs (NeighborLoader)           |
 |  - In-Silico Faithfulness: Sufficiency & Necessity edge ablation validation             |
 |  - Counterfactual Diagnostic 'Why Not?' decision tree & heuristic filter analyzer      |
 |  - Retrieve-Then-Cite PubMed RAG (NCBI E-Utilities: ESearch, ESummary, EFetch)          |
 +-----------------------------------------------------------------------------------------+
                                              |
                     +------------------------+------------------------+
                     v                                                 v
 +----------------------------------------+        +--------------------------------------+
 |       Grounded Conversational Agent    |        |             FastAPI Backend          |
 |  - OpenRouter API (Free Zero-Cost Tier)|        |  - Uvicorn ASGI Server               |
 |  - 4 Deterministic Tool Binders        |        |  - Pydantic v2 Request/Response DTOs |
 |  - Zero-Hallucination System Prompt    |        |  - Thread-safe Memory Caching        |
 |  - Step H Claim-Level Verifier (100%)  |        |  - Endpoints: /predict, /search, etc |
 +----------------------------------------+        +--------------------------------------+
                     |                                                 |
                     +------------------------+------------------------+
                                              |
                                              v
 +-----------------------------------------------------------------------------------------+
 |                                  Frontend Client (React 19)                             |
 |  - Vite 8 + TypeScript 5.8 + Tailwind CSS v4                                            |
 |  - Cytoscape.js & React Flow Subgraph Visualizer                                        |
 |  - Interactive Discovery & Analysis Consoles with Real-Time Research Chat Terminal      |
 +-----------------------------------------------------------------------------------------+
```

### 2.1 Backend Technologies
| Layer / Role | Technology | Purpose & Specification |
|---|---|---|
| **Language & Runtime** | Python 3.10 / 3.11 | Core runtime environment |
| **Deep Learning Framework** | PyTorch 2.6.0 (CPU / CUDA) | Tensor operations, autograd, parameter optimization |
| **Graph Neural Networks** | PyTorch Geometric (PyG) 2.6.0 + `pyg_lib` | HeteroData abstractions, `HGTConv`, `NeighborLoader` |
| **Model Framework** | PyTorch Lightning 2.5.0 | Modular training loops, checkpointing, metrics logging |
| **Cheminformatics** | RDKit | SMILES parsing, 2048-bit Morgan Fingerprints (radius=2) |
| **Data Processing** | NumPy, Pandas, SciPy, Scikit-learn | Array manipulation, evaluation metrics (AUROC/AUPR) |
| **Web API Framework** | FastAPI (ASGI) + Uvicorn | High-performance asynchronous REST API |
| **Data Validation** | Pydantic v2 | Strict schema typing and request/response validation |
| **LLM Gateway** | OpenRouter API (OpenAI SDK / HTTP) | Multi-provider LLM gateway supporting zero-cost models |
| **Literature Retrieval** | NCBI Entrez E-Utilities | PubMed RAG (`esearch.fcgi`, `esummary.fcgi`, `efetch.fcgi`) |

### 2.2 Frontend Technologies
| Layer / Role | Technology | Purpose & Specification |
|---|---|---|
| **Core Framework** | React 19.2 + TypeScript 5.8 | Component architecture and type-safe state management |
| **Build & Tooling** | Vite 8.3 + ESBuild | Rapid hot-module reloading and optimized bundling |
| **Styling** | Tailwind CSS v4.3 + CSS Custom Properties | Responsive design system, dark mode tokens, typography |
| **Iconography** | Lucide React | Clean, domain-appropriate scientific UI icons |
| **Graph Visualization** | @xyflow/react + Cytoscape.js / HTML Canvas | 2D interactive force-directed biomedical network visualizer |
| **Routing** | React Router DOM v7 | Client-side routing between Discovery, Analysis, Evidence, and Graph views |

---

## 3. Heterogeneous Graph Transformer (HGT / SynergyGNN)

### 3.1 Heterogeneous Graph Representation (`HeteroData`)
SynThera models biological entities and their relationships as a typed multi-relational graph derived from **PrimeKG**:
* **10 Node Types:** `drug`, `disease`, `gene/protein`, `pathway`, `biological_process`, `molecular_function`, `cellular_component`, `anatomy`, `effect/phenotype`, `exposure`.
* **24 Relational Edge Types:** Includes `drug-target` (indication/contraindication), `target-pathway`, `protein-protein interaction (PPI)`, `drug-phenotype`, `disease-phenotype`, and `drug-drug interaction (DDI)`.
* **Structural Graph Safeguard:** The `drug-drug` interaction relation is used strictly for structural message passing; its edges are **never used as supervision targets** to prevent label leakage.

### 3.2 Input Node Representations
1. **Small-Molecule Drugs (~7,122 nodes):**
   * Transformed into 2048-bit Morgan fingerprints using RDKit ($\text{radius}=2, \text{nBits}=2048$).
   * Projected to the common model hidden dimension:
     $$x_{\text{drug}} = \text{Linear}(2048 \to 128)(\text{FP})$$
2. **Biologics / Fallback Drugs (~824 nodes):**
   * Compounds lacking SMILES representations utilize a learnable embedding dictionary:
     $$x_{\text{fallback}} = \text{Embedding}(N_{\text{fallback}}, 128)$$
   * Dynamic routing is governed by an in-memory boolean mask `fp_mask`.
3. **Biomedical Entities (`gene/protein`, `pathway`, `disease`):**
   * Initialized with 64-dimensional learnable embeddings and projected into the common representation space:
     $$x_v = \text{Linear}(64 \to 128)(\text{Embedding}_v(idx_v))$$
4. **Cancer Cell-Line Conditioning:**
   * Cell lines are conditioned using DepMap/CCLE gene expression profiles or projected 64-dimensional cell embeddings to capture tissue-specific transcriptomic baselines.

### 3.3 HGT Convolution Architecture (`HGTConv`)
To capture multi-relational biological semantics without homogenizing edge types, SynThera utilizes a 2-layer Heterogeneous Graph Transformer:

$$\text{Attention}(s, e, t) = \text{Softmax}_{t} \left( \frac{K(s) W_{\phi(e)}^{\text{ATT}} Q(t)^T}{\sqrt{d}} \right)$$

$$\text{Message}(s, e, t) = V(s) W_{\phi(e)}^{\text{MSG}}$$

$$h_t^{(l)} = \text{LayerNorm}\left( \text{ELU}\left( \sum_{s \in \mathcal{N}(t)} \text{Attention}(s, e, t) \cdot \text{Message}(s, e, t) \right) + h_t^{(l-1)} \right)$$

* **Hyperparameters:** `hidden_dim = 128`, `num_heads = 4`, `num_layers = 2`, `dropout = 0.3`.
* Multi-head cross-attention preserves type-specific relational semantics between targets, pathways, and phenotypic nodes.

### 3.4 Bilateral Symmetric Pair Representation & Classification Head
In nature, the combination of $(\text{Drug A}, \text{Drug B})$ is functionally identical to $(\text{Drug B}, \text{Drug A})$. To guarantee mathematical symmetry and eliminate ordering bias:

$$h_{\text{pair}} = \left[ h_A \odot h_B \,\|\, |h_A - h_B| \,\|\, h_A + h_B \right] \in \mathbb{R}^{3 \times \text{hidden\_dim}}$$

The conditioned pair vector is concatenated with the cell line embedding:
$$z = \left[ h_{\text{pair}} \,\|\, h_{\text{cell\_line}} \right]$$

The classification head scores 3 discrete experimental classes:
$$\hat{y} = \text{Softmax}\left( \text{MLP}(z) \right) \in \mathbb{R}^3 \quad \text{where } \{0: \text{antagonism}, 1: \text{additive}, 2: \text{synergy}\}$$

### 3.5 Loss Function: Class-Weighted Multi-Class Focal Loss
Experimental synergy labels in DrugComb are heavily skewed toward additive and antagonistic pairs. Standard cross-entropy leads to majority-class overfitting. SynThera implements multi-class Focal Loss (Lin et al., 2017) with softened inverse-frequency class weights:

$$\text{FL}(p_t) = -\alpha_t (1 - p_t)^\gamma \log(p_t)$$

where:
* $\gamma = 2.0$ dynamically focuses gradient backpropagation on hard, ambiguous borderline cases.
* $\alpha_t$ provides class rebalancing based on training split class frequencies.
* Optimized using AdamW with `CosineAnnealingLR` and gradient clipping ($0.5$).

---

## 4. Combinatorial Search & Discovery Engine

### 4.1 Candidate Generation & Therapeutic Filtering (`src/search.py`)
Evaluating all possible drug combinations ($>2.5 \times 10^7$ pairs) is computationally prohibitive. SynThera executes a multi-stage candidate generation and filtration pipeline:

1. **Disease Indication Expansion:**
   * Identifies approved drugs with direct indication edges to the target disease in PrimeKG.
2. **Phenotypic & Pathway Neighbor Expansion:**
   * Traverses targets downstream of disease-associated pathways and shared biological processes to identify secondary candidates.
3. **Excipient, Buffer, and Solvent Filtering:**
   * Removes non-therapeutic compounds and formulation additives that cause false positives (e.g., *Zinc chloride, Sodium chloride, Calcium carbonate, Water, Glycerol, Hydrochloric acid*).
4. **Metabolic Enzyme (CYP450) Elimination:**
   * Filters **55 Cytochrome P450 enzymes** (CYP3A4, CYP2D6, CYP2C9, etc.) from target connectivity graphs. This eliminates false pharmacokinetic interactions where two drugs merely compete for hepatic metabolism rather than demonstrating synergistic target engagement.

### 4.2 Search Strategies
SynThera provides three selectable combinatorial exploration algorithms:

#### A. Beam Search (Default: $B=5$)
* **Algorithm:** Maintains a priority queue of width $B$ representing the top-performing partial combinations.
* At each step, expands candidate pairs, computes $V(\text{pair})$, prunes all states below rank $B$, and continues exploration.
* **Characteristics:** Balances combinatorial exploration breadth with low latency ($<2.5$ seconds for candidate pools of 50 drugs).

#### B. Greedy Search
* **Algorithm:** Iteratively selects the highest-scoring candidate drug that maximizes incremental value $V(\text{pair})$.
* **Characteristics:** Extremely fast ($O(K \cdot N)$), but susceptible to local optima.

#### C. Monte Carlo Tree Search (MCTS) with UCT Exploration
* **Algorithm:** Constructs an exploration tree where nodes represent candidate drug subsets.
* Selection is governed by the Upper Confidence bounds applied to Trees (UCT) formula:
  $$\text{UCT}(s, a) = Q(s, a) + c_{\text{puct}} \cdot P(s, a) \cdot \frac{\sqrt{N(s)}}{1 + N(s, a)}$$
* Evaluates non-obvious synergistic pairs through stochastic rollouts and backpropagation.

---

## 5. Multi-Objective Value Function $V(\text{pair})$ & Toxicity Layer

### 5.1 Formulation of $V(\text{pair})$
Raw synergy probability $p_{\text{synergy}}$ is clinically insufficient; an efficacious combination that causes lethal hepatic toxicity or severe target redundancy is not viable. SynThera ranks combinations using a multi-objective composite objective:

$$V(\text{pair}) = w_{\text{synergy}} \cdot p_{\text{synergy}} - w_{\text{toxicity}} \cdot \text{toxicity\_penalty}(\text{pair}) - w_{\text{redundancy}} \cdot \text{redundancy\_penalty}(\text{pair})$$

#### Default Parameterization
* $w_{\text{synergy}} = 1.0$
* $w_{\text{toxicity}} = 0.35$
* $w_{\text{redundancy}} = 0.10$

### 5.2 Toxicity Penalty Formulation
The toxicity penalty combines biomedical knowledge graph edges from PrimeKG with empirical side-effect frequencies from SIDER 4.1:

$$\text{toxicity\_penalty} = \alpha_{\text{ddi}} \cdot \text{ddi\_risk} + \alpha_{\text{se}} \cdot \text{se\_risk}$$

where:
* $\alpha_{\text{ddi}} = 0.65$ (weight for confirmed adverse drug-drug interaction edges).
* $\alpha_{\text{se}} = 0.35$ (weight for clinical side-effect phenotype overlap).

#### Documented Unknown-Risk Policy
Missing biomedical graph data **must never silently default to $0.0$** (which would falsely imply confirmed safety). SynThera enforces an explicit baseline uncertainty penalty:
* **Confirmed Toxic (`has_known_ddi = True`):** $\text{ddi\_risk} = 1.0$
* **Confirmed Safe (`has_known_ddi = False`):** $\text{ddi\_risk} = 0.0$
* **Unindexed DDI (`has_known_ddi = None`):** $\text{ddi\_risk} = 0.35$ (baseline uncertainty penalty)
* **Indexed Side-Effect Profile:** $\text{se\_risk} = \text{Jaccard overlap of SIDER phenotype strings}$
* **Unindexed Side Effects (`side_effect_overlap = None`):** $\text{se\_risk} = 0.15$ (empirical small-molecule mean)

#### Strict Mathematical Ordering Guarantee
$$\text{Confirmed Safe } (0.00) < \text{Unknown Risk } (0.28) < \text{Confirmed Toxic } (0.70 - 1.00)$$

### 5.3 Redundancy Penalty
Measures target-space overlap in Protein-Protein Interaction (PPI) space using Jaccard target similarity:
$$\text{redundancy\_penalty} = \frac{|T_A \cap T_B|}{|T_A \cup T_B|}$$
Penalizes combinations that bind identical targets without complementary pathway coverage.

### 5.4 Composed Three-Drug Combination Scoring (Phase C1)
Three-drug combination discovery is evaluated strictly as **composed pairwise scores**:

> **Mandatory Universal System Disclaimer:**
> *"We compose pair scores; we do not have DrugComb 3-way synergy labels."*

For a triplet $\{A, B, C\}$:
* **Primary Bottleneck Ranker:**
  $$V_{\text{min}}(A, B, C) = \min\big(V(A, B), V(A, C), V(B, C)\big)$$
* **Secondary Descriptive Aggregate:**
  $$V_{\text{mean}}(A, B, C) = \frac{V(A, B) + V(A, C) + V(B, C)}{3}$$
* **Triple Toxicity Union:**
  $$\text{Tox}_{\text{triple}} = \max\big(\text{Tox}(A, B), \text{Tox}(A, C), \text{Tox}(B, C)\big)$$
* **Adverse DDI Flag:** $\text{True}$ if *any* constituent pair has a confirmed DDI; $\text{False}$ if all pairs are confirmed safe; $\text{None}$ if any pair is unindexed.

### 5.5 Clinical Protocol Nuance & Caveat
Toxicity penalties reflect known adverse-interaction and side-effect-overlap signals from static databases. They do **not** model clinical dose staggering, interval scheduling, or rescue therapies.
* *Example Reference Case:* In Glioblastoma (`T98G`), the triplet **Procarbazine + Carmustine + Vincristine** (PCV regimen analog) receives a high toxicity penalty ($0.7276$) because all three constituent pairs carry confirmed DDI edges (severe additive myelosuppression and neurotoxicity).
* SynThera demotes this combination to **#80 of 120** in Glioblastoma discovery. This flags the combination for **clinical scrutiny**, reflecting the strict monitoring and interval scheduling required in hospital administration.

---

## 6. Explainability, Graph Attribution & In-Silico Faithfulness

### 6.1 Subgraph Extraction & Input-Gradient Edge Attribution
To explain why a combination is predicted as synergistic, SynThera extracts a 2-hop local ego-network around (Drug A, Drug B, Disease, Targets) using `torch_geometric.loader.NeighborLoader`.

Rather than using black-box post-hoc surrogates, SynThera computes **Input-Gradient Edge Saliency**:
$$\text{importance}(e) = \|\nabla_{x_{\text{src}}} p_{\text{predicted\_class}}\|_2$$

1. Sets `requires_grad=True` on the input drug feature tensors in the local subgraph.
2. Performs a forward pass to calculate class probabilities.
3. Computes the gradient of the predicted synergy probability with respect to the node feature representations.
4. Scores each knowledge graph edge by the L2-norm of the gradient at the source node.
5. Ranks all edges and extracts the top-$K$ most influential interactions (e.g., target binding, downstream pathway signaling).

### 6.2 In-Silico Faithfulness Verification Protocols
An explanation is only clinically valuable if it accurately reflects the model's actual internal decision-making. SynThera implements real-time in-silico ablation experiments:

#### A. Sufficiency Evaluation
Evaluates the model using **only** the isolated top-$K$ attribution edge subgraph $G_{\text{attr}}$:
$$\text{Sufficiency} = \frac{p(\text{synergy} \mid G_{\text{attr}})}{p(\text{synergy} \mid G_{\text{full}})} \times 100\%$$
* High sufficiency ($>80\%$) confirms that the extracted biological subgraph contains almost all information necessary to sustain the prediction.

#### B. Necessity Evaluation
Evaluates the model after **ablating (removing)** the top-$K$ attribution edges from the full graph:
$$\text{Necessity} = \frac{p(\text{synergy} \mid G_{\text{full}}) - p(\text{synergy} \mid G_{\text{full}} \setminus G_{\text{attr}})}{p(\text{synergy} \mid G_{\text{full}})} \times 100\%$$
* Significant necessity drop confirms that the identified edges are indispensable to the synergy prediction.

#### C. Binary Faithfulness Verdict
An explanation is certified as **Faithful** (`explanation_faithful = True`) if:
1. Original prediction probability $p_{\text{synergy}} \ge 0.50$.
2. Predicted class remains unchanged under the isolated subgraph.
3. $\text{Sufficiency} \ge 80\%$.
4. $\text{Necessity} \ge 0.5\%$.

---

## 7. Counterfactual Diagnostic "Why Not?" Reasoning Engine

### 7.1 Objective
When researchers run discovery for a cancer (e.g., Glioblastoma), they frequently ask:
* *"Why wasn't Drug X included in the top combinations?"*
* *"Why is Temozolomide ranked above Carmustine?"*

Instead of returning ungrounded LLM text, SynThera executes a **deterministic 4-stage diagnostic pipeline** (`src/why_not.py`).

### 7.2 Diagnostic Decision Pipeline
1. **Excipient / Formulation Check:**
   * Detects if Drug X is an inactive ingredient, preservative, or solvent (e.g., Zinc chloride, Sodium chloride).
   * *Verdict:* Excluded as non-therapeutic formulation agent.
2. **Knowledge Graph Connectivity Check:**
   * Verifies if Drug X has documented target binding, indication, or phenotypic edges connected to the queried disease in PrimeKG.
   * *Verdict:* Excluded due to absence of direct or downstream disease connectivity.
3. **Metabolic Enzyme (CYP) Interaction Check:**
   * Determines if Drug X was filtered out because its only interactions are non-therapeutic CYP450 metabolic bindings.
4. **GNN Quantitative Score & Beam Pruning Evaluation:**
   * If Drug X passed all heuristic filters, the system executes real-time inference on Drug X paired with candidate partners.
   * Compares its score $V(\text{pair})$, synergy probability $p_{\text{synergy}}$, toxicity penalty, and beam rank against the cut-off threshold of the top candidates.

### 7.3 Rule-Based Natural Language Intent Parser
Uses high-precision regex parsers to interpret user intent without stochastic LLM latency:
* `parse_why_not_intent(question)`: maps queries to `why_not`, `compare`, or `ranked_below`.

---

## 8. Real-Time Retrieve-Then-Cite PubMed RAG Engine

### 8.1 Retrieval Protocol (`src/literature.py`)
SynThera integrates directly with the **NCBI Entrez E-Utilities API** to retrieve and ground clinical literature in real time:

1. **Mechanism Term Extraction:**
   * Extracts only verified gene/protein and pathway terms identified in the top attribution subgraph. Unrelated diseases and non-cancer indications are strictly filtered.
2. **Multi-Tier Query Construction:**
   * **Tier 1 (High Precision):**
     `("{Drug A}"[Title/Abstract] AND "{Drug B}"[Title/Abstract]) AND ("{Disease}" OR "{Target Gene}")`
   * **Tier 2 (Pair Combination):**
     `("{Drug A}"[Title/Abstract] AND "{Drug B}"[Title/Abstract])`
   * **Tier 3 (Single-Drug Monotherapy Baseline):**
     `("{Drug A}"[Title/Abstract] AND "{Disease}"[Title/Abstract])`
3. **ESearch & EFetch Medline Parsing:**
   * Fetches full PubMed XML records (`title`, `authors`, `journal`, `pubdate`, `abstract`, `doi`).
4. **Honest Evidence Classification:**
   * **`combination`:** Both drug names (or verified clinical synonyms) appear directly in the title or abstract.
   * **`single_drug`:** Exactly one of the drugs appears with the disease.
   * **`weak` / `related`:** Pathway or target overlap without direct co-administration.
5. **Rate Limiting & Thread-Safe Caching:**
   * Respects NCBI rate limits ($3\text{ req/s}$ anonymous, $10\text{ req/s}$ with `NCBI_API_KEY`).
   * LRU in-memory cache with TTL prevents redundant HTTP overhead.

---

## 9. Strictly Grounded Tool-Calling Conversational Assistant

### 9.1 Zero-Hallucination Architectural Policy (`app/chat.py`)
The conversational assistant in SynThera is designed for clinical and scientific research where generative hallucinations are impermissible.

* **OpenRouter Gateway:** Powered by OpenAI-compatible tool-calling endpoints. By default, routes to `openrouter/free` (e.g. `google/gemini-2.0-flash-exp:free`) providing **$0.00 cost / zero token bill**.
* **Bounded Tool Execution:** The assistant can only acquire facts by executing 4 core deterministic tools:
  1. `predict_pair(drug_a, drug_b, cell_line)`
  2. `search_combinations(disease, cell_line, inspect_top_k)`
  3. `why_not(disease, cell_line, drug_name)`
  4. `get_literature(drug_a, drug_b, target_or_pathway)`
* **Loop Prevention:** Maximum 4 tool calls per user turn.
* **Strict Literal Grounding:** The system prompt forbids introducing external biological mechanisms, genes, or pathways from pretrained weights. Every biological claim must appear verbatim in the tool return payload.

### 9.2 Step H Claim-Level Literal Grounding Evaluation Suite (`src/eval_chat.py`)
SynThera includes an automated verification test harness that audits assistant responses for literal claim-level compliance:
* **Test 1 (Standard Query):** Validates probability vectors and exact PubMed PMIDs.
* **Test 2 (Discovery Query):** Verifies top-ranked combination names, scores, and disease targets.
* **Test 3 (Why-Not Query):** Confirms exact diagnostic exclusion reasons (e.g. Zinc chloride excipient filter).
* **Test 4 (Mechanistic Grounding):** Enforces that mechanistic explanations contain **zero** ungrounded biological terms not present in the tool return.
* **Benchmark Score:** **100% (4/4 tests passed)** with 0 ungrounded biological claims.

---

## 10. REST API Specification & Service Architecture

The FastAPI backend (`app/main.py`) exposes high-performance asynchronous endpoints:

| Endpoint | Method | Input Parameters | Key Output Fields |
|---|---|---|---|
| `/health` | `GET` | None | `status`, `device`, `model_loaded`, `uptime` |
| `/drugs` | `GET` | None | `drugs`: List of `{id: DrugBankID, name: DrugName}` |
| `/cell-lines` | `GET` | None | `cell_lines`: List of indexed cancer cell lines |
| `/predict` | `POST` | `drug_a`, `drug_b`, `cell_line`, `disease` (optional) | `p_synergy`, `p_additive`, `p_antagonism`, `top_edges`, `faithfulness`, `supporting_literature` |
| `/search` | `POST` | `disease`, `cell_line`, `search_method`, `top_k`, `max_candidates` | `top_combinations`: List of ranked pairs with $V(\text{pair})$, toxicity, and candidate pool metrics |
| `/predict-triple` | `POST` | `drug_a`, `drug_b`, `drug_c`, `cell_line` | `aggregate_min`, `aggregate_mean`, `triple_toxicity_penalty`, `has_known_ddi`, `bottleneck_pair` |
| `/search-triple` | `POST` | `disease`, `cell_line`, `top_k`, `max_candidates` | Ranked three-drug combinations with universal composition disclaimer |
| `/why-not` | `POST` | `disease`, `cell_line`, `question`, `drug_x` | `status`, `category`, `reason`, `diagnostic_details`, `alternatives` |
| `/chat/analysis` | `POST` | `message`, `conversation_history`, `context` | `response`, `tool_calls`, `conversation_history` |

---

## 11. Frontend User Interface & Interaction Design

The frontend application (`frontend/`) is engineered for progressive technical disclosure:

### 11.1 Key Modules & Pages
1. **Discover Page (`DiscoverPage.tsx`):**
   * Disease and cell-line selection dropdowns.
   * Search method toggles (Beam Search, Greedy Search, MCTS).
   * Filter controls for candidate pool size, toxicity penalty threshold, and target redundancy weighting.
   * Ranked combination cards displaying $V(\text{pair})$, synergy probability bars, and adverse DDI risk flags.
2. **Analysis Page (`AnalysisPage.tsx`):**
   * **Prediction Breakdown:** Primary synergy classification badge, calibrated probability breakdown (Synergy, Additive, Antagonism).
   * **Interactive Knowledge Subgraph:** Visualizes 2-hop local PrimeKG topology using Cytoscape / Canvas, highlighting drug-target bindings, pathways, and phenotypic associations.
   * **Toxicity & Safety Profile (`ToxicityCard.tsx`):** Displays composite toxicity penalty, SIDER adverse event Jaccard overlap, and PrimeKG DDI interaction status.
   * **Faithfulness & Explainability (`FaithfulnessCard.tsx`):** Sufficiency and necessity ablation gauges certifying explanation reliability.
   * **Peer-Reviewed Evidence (`LiteratureSection.tsx`):** PubMed citation cards with direct PMID links, evidence tier tags, and abstract snippets.
   * **Research Chat Panel (`AnalysisChatPanel.tsx`):** Terminal-style conversational interface interacting directly with the grounded LLM agent.
3. **Evidence Page (`EvidencePage.tsx`):**
   * Curated repository of clinical trial citations, DrugComb reference datasets, and experimental protocols.
4. **Knowledge Graph Explorer (`KnowledgeGraphPage.tsx`):**
   * Global interactive explorer for browsing PrimeKG entity nodes and relational edges.

---

## 12. Benchmark Evaluations & Scientific Protocols

### 12.1 Experimental Benchmark Results
Extensive cross-validation and holdout evaluations across 37,778 test pairs:

| Evaluation Protocol | Test Split Description | Test AUROC | Test AUPR | Baseline AUPR |
|---|---|:---:|:---:|:---:|
| **Cold-Drug Split (Ours)** | **Leave-Drugs-Out ($D_{\text{train}} \cap D_{\text{test}} = \emptyset$)** | **0.64** | **0.44** | ~0.16 (Random) |
| *-- Unilateral Cold Subset* | Exactly one drug unseen during training | 0.65 | 0.45 | ~0.16 |
| *-- Bilateral Cold Subset* | Neither drug seen anywhere in training | 0.62 | 0.41 | ~0.16 |
| **Standard Random Split** | Transductive Pair Split (Data Leakage Setting) | **0.87** | **0.78** | ~0.16 |

### 12.2 Model Architecture Comparisons
Evaluated on the strict Bilateral Cold-Drug holdout set:
* **Random Guessing:** $\text{AUROC} = 0.50$, $\text{AUPR} = 0.16$
* **Marginal Promiscuity Baseline:** $\text{AUROC} = 0.52$, $\text{AUPR} = 0.18$
* **Chemical Morgan Fingerprint MLP:** $\text{AUROC} = 0.56$, $\text{AUPR} = 0.24$
* **SynThera Heterogeneous Graph Transformer (HGT):** $\text{AUROC} = \mathbf{0.64}$, $\text{AUPR} = \mathbf{0.44}$

### 12.3 Key Scientific Takeaways
1. Graph topological message passing across PrimeKG provides strong inductive bias, allowing the model to predict synergistic interactions even for novel, completely unseen chemical structures.
2. Grounded, in-silico ablated explanations bridge the gap between black-box deep learning and actionable clinical hypotheses in oncology.
