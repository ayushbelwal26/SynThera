# SynThera: Explainable Drug Combination Discovery

SynThera is an end-to-end artificial intelligence platform for discovering, ranking, and mechanistically explaining synergistic drug combinations in oncology. It couples a Heterogeneous Graph Transformer (HGT) trained on the PrimeKG biomedical knowledge graph and DrugComb experimental synergy labels with gradient-based mechanistic attribution, in-silico faithfulness ablation, real-time PubMed literature retrieval, a strictly grounded tool-calling conversational assistant, and an interactive web interface.

---

## Key Capabilities

* **Heterogeneous Graph Transformer (`src/model.py`)**: Multi-relational GNN operating across 10 node types and 24 edge types from PrimeKG, enriched with 2048-bit Morgan chemical fingerprints and cell-line gene expression profiles.
* **Cold-Drug Generalization (Leave-Drugs-Out)**: Enforces disjoint training/test drug sets ($D_{\text{train}} \cap D_{\text{test}} = \emptyset$) to prevent single-drug promiscuity data leakage and ensure real-world wet-lab transferability.
* **In-Silico Faithfulness & Attribution (`src/explain.py`)**: Computes Integrated Gradients attribution over 2-hop local subgraphs, quantifying explanation necessity and sufficiency via real-time subgraph edge ablations.
* **Counterfactual Diagnostic 'Why Not?' Reasoning (`src/why_not.py`)**: Evaluates why candidate drugs were omitted, filtered by therapeutic heuristics, or outranked by the GNN search beam.
* **Real-Time Literature Retrieval (`src/literature.py`)**: Integrates NCBI PubMed E-Utilities RAG to automatically query, rank, and cite peer-reviewed clinical studies supporting discovered combinations.
* **Strictly Grounded Tool-Calling Analysis Chat (`app/chat.py`)**: Conversational LLM assistant powered by OpenRouter (supporting free zero-cost models or any provider) that operates under a zero-hallucination policy—stating only biological and mechanistic claims returned directly by core tools.
* **Interactive Web Platform (`frontend/`)**: Modern React + TypeScript + Tailwind CSS dashboard featuring interactive interaction networks, confidence gauges, and diagnostic tools.

---

## Scientific Benchmarks & Evaluation

### Benchmark Headline Performance

| Metric | Score | Evaluation Protocol | Dataset / Split |
|---|:---:|---|---|
| **Test AUROC** | **0.64** | Cold-Drug Split (Leave-Drugs-Out) | 37,778 Test Pairs (Disjoint Drug Pools) |
| **Test AUPR** | **0.44** | Cold-Drug Split (Random Baseline: ~0.16) | 37,778 Test Pairs |
| **Random Split AUROC** | **0.87** | Standard Random Split (Data Leakage Setting) | Transductive Pair Split |
| **Chat Grounding Accuracy** | **100% (4/4)** | Claim-Level Literal Grounding Suite | Zero Ungrounded Biological Entities |

### Why Cold-Drug Splitting Matters
In standard drug combination literature, random pair splitting causes massive data leakage: if Drug A is seen with Drug B during training, evaluating (Drug A, Drug C) in test simply exploits marginal single-drug promiscuity. This produces artificially inflated AUROC scores ($>0.85$) that fail wet-lab validation.

SynThera strictly enforces a **cold-drug split (leave-drugs-out)**:
* A designated 15% of drugs are held out and **completely absent** from all training combinations ($D_{\text{train}} \cap D_{\text{test}} = \emptyset$).
* Test pairs include:
  * **Unilateral cold pairs (~29,282 pairs):** Exactly one drug was unseen during training.
  * **Bilateral cold pairs (~8,496 pairs):** Neither drug appeared anywhere in any training combination (the strictest inductive subset).
* Achieving **0.64 AUROC** and **0.44 AUPR** under strict cold evaluation reflects genuine inductive generalization across biomedical knowledge networks.
* Detailed benchmarks, comparison against MLP baselines, DSN/SPN experiments, and similarity distributions are documented in [`docs/`](file:///drug-combo-discovery/docs/).

---

## Architecture Overview

```
                      +---------------------------------------+
                      |   PrimeKG Knowledge Graph + DrugComb  |
                      +---------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
| Stage 1: Candidate Generation & Filtering (src/search.py)                         |
| - Traverses PrimeKG indications and target overlap proteins                       |
| - Eliminates excipients, solvents, and non-therapeutic minerals                   |
| - Filters 55 CYP metabolic enzymes to prevent false pharmacokinetic positives     |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
| Stage 2: Combination Scoring & Search (src/search.py, src/model.py)              |
| - Heterogeneous Graph Transformer (SynergyGNN) evaluates candidate pairs          |
| - Search strategies: Beam Search, Greedy Search, or MCTS with UCT exploration     |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
| Stage 3: Attribution, Faithfulness & Literature (src/explain.py, src/literature.py)|
| - Computes gradient saliency over 2-hop local subgraphs via NeighborLoader       |
| - In-silico necessity and sufficiency edge ablations verify explanation fidelity  |
| - PubMed E-Utilities RAG retrieves peer-reviewed clinical citations               |
+-----------------------------------------------------------------------------------+
                                          |
                     +--------------------+--------------------+
                     v                                         v
+-----------------------------------------+   +-------------------------------------+
| Stage 4: Grounded LLM Chat (app/chat.py)|   | Stage 5: React Web UI (frontend/)   |
| - OpenRouter tool-calling agent         |   | - Pair Discovery & Indication Search|
| - Strictly bounded to 4 core tools      |   | - Dynamic graph visualization       |
| - Claim-level literal grounding         |   | - Real-time conversational panel    |
+-----------------------------------------+   +-------------------------------------+
```

---

## Environment Variables

Configure optional environment variables in your environment or a `.env` file in `drug-combo-discovery/.env`:

| Variable | Default | Description |
|---|---|---|
| `PORT` | `7860` | Port for FastAPI backend server. |
| `NCBI_API_KEY` | *None* | **Recommended for production.** Setting a personal NCBI key increases PubMed API rate limits from 3 req/s to 10 req/s. |
| `OPENROUTER_API_KEY` | *None* | **Required for Analysis Chat Assistant.** API key for OpenRouter (OpenAI-compatible). If omitted, chat gracefully uses deterministic offline fallback. |
| `OPENROUTER_MODEL` | `openrouter/free` | Model routed via OpenRouter. Defaults to `openrouter/free` which uses free tool-calling models at $0.00 cost (zero token bill). |
| `VITE_API_BASE_URL` | `http://localhost:7860` | Base URL used by the frontend to communicate with the backend. |

---

## Quickstart: Clone & Run Fresh

### 1. Prerequisites
* **Python 3.10 or 3.11**
* **Node.js 18+** & `npm`
* Git

### 2. Backend Installation & Startup

```bash
# 1. Clone repository
git clone https://github.com/ayushbelwal26/SynThera.git
cd SynThera/drug-combo-discovery

# 2. Create and activate Python virtual environment
python -m venv .venv
# On Linux/macOS:
source .venv/bin/activate
# On Windows:
.\.venv\Scripts\activate

# 3. Install PyTorch and PyG dependencies
pip install --upgrade pip
pip install torch==2.6.0+cpu --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
pip install pyg_lib -f https://data.pyg.org/whl/torch-2.6.0+cpu.html

# 4. Start FastAPI server
uvicorn app.main:app --host 0.0.0.0 --port 7860
```
Backend API docs will be live at: `http://localhost:7860/docs`

### 3. Frontend Installation & Startup

In a separate terminal:
```bash
cd SynThera/drug-combo-discovery/frontend
npm install
npm run dev
```
Open your browser at `http://localhost:5173`.

---

## OpenAPI / REST Usage Examples

### 1. Predict Synergy & Generate Explanation (`POST /predict`)
Predicts calibrated synergy probability, extracts attribution subgraphs, runs in-silico faithfulness verification, and retrieves literature:

```bash
curl -X POST http://localhost:7860/predict \
  -H "Content-Type: application/json" \
  -d '{
    "drug_a": "DB00853",
    "drug_b": "DB00531",
    "cell_line": "T98G",
    "disease": "glioblastoma"
  }'
```

**Example Response Summary:**
```json
{
  "drug_a": "DB00853",
  "drug_a_name": "Temozolomide",
  "drug_b": "DB00531",
  "drug_b_name": "Cyclophosphamide",
  "cell_line": "T98G",
  "predicted_class": "synergy",
  "score": 0.7196,
  "p_synergy": 0.7196,
  "p_additive": 0.2766,
  "p_antagonism": 0.0038,
  "top_edges": [
    {
      "source": "Temozolomide",
      "relation": "indication",
      "target": "brain glioblastoma",
      "importance": 0.6716
    }
  ],
  "faithfulness": {
    "original_score": 0.7196,
    "original_class": "synergy",
    "sufficiency": 96.5,
    "necessity": 1.0,
    "explanation_faithful": true,
    "rationale": "The isolated 10-edge attribution subgraph retains 96.5% of original confidence with predicted class preserved."
  },
  "explanation_text": "Temozolomide is indicated for brain glioblastoma...",
  "supporting_literature": [
    {
      "pmid": "18483314",
      "title": "Phase II trial of temozolomide and cyclophosphamide...",
      "url": "https://pubmed.ncbi.nlm.nih.gov/18483314/"
    }
  ]
}
```

### 2. Disease-Driven Candidate Search (`POST /search`)
Discovers candidate drugs, evaluates pairs with GNN beam/MCTS search, and returns top combination candidates with explanations:

```bash
curl -X POST http://localhost:7860/search \
  -H "Content-Type: application/json" \
  -d '{
    "disease": "glioblastoma",
    "cell_line": "T98G",
    "max_candidates": 20,
    "top_k": 5,
    "search_method": "beam",
    "beam_width": 5,
    "inspect_top_k": 0
  }'
```

### 3. Diagnostic 'Why Not?' Reasoning (`POST /why-not`)
Analyzes why an expected drug was absent, filtered out, or outranked:

```bash
curl -X POST http://localhost:7860/why-not \
  -H "Content-Type: application/json" \
  -d '{
    "disease": "glioblastoma",
    "cell_line": "T98G",
    "question": "Why not Zinc chloride?",
    "drug_x": "Zinc chloride",
    "search_method": "beam"
  }'
```

### 4. Strictly Grounded Analysis Chat (`POST /chat/analysis`)
Interacts with the tool-calling assistant on the Analysis page. The assistant executes tools (`predict_pair`, `search_combinations`, `why_not`, `get_literature`) and bounds every claim strictly to returned tool data:

```bash
curl -X POST http://localhost:7860/chat/analysis \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is the predicted synergy between Temozolomide and Carmustine in T98G, and what literature supports it?",
    "conversation_history": [],
    "context": {
      "drug_a": "Temozolomide",
      "drug_b": "Carmustine",
      "cell_line": "T98G",
      "disease": "glioblastoma"
    }
  }'
```

**Example Response Summary:**
```json
{
  "response": "According to the synergy prediction tool, Temozolomide and Carmustine in cell line T98G are predicted as synergy with a probability of 0.8804 (additive: 0.1180, antagonism: 0.0016). Published literature includes 'Phase I/II trial of temozolomide and carmustine in recurrent glioblastoma' (PMID: 15309322).",
  "tool_calls": [
    {
      "tool": "predict_pair",
      "args": {
        "drug_a": "Temozolomide",
        "drug_b": "Carmustine",
        "cell_line": "T98G"
      }
    },
    {
      "tool": "get_literature",
      "args": {
        "drug_a": "Temozolomide",
        "drug_b": "Carmustine"
      }
    }
  ],
  "conversation_history": [ ... ]
}
```

---

## Running Evaluations & Tests

Run the comprehensive unit test and benchmark suites:

```bash
cd drug-combo-discovery

# Run core unit tests
pytest tests/

# Run the Step H Claim-Level Literal Grounding Chat Evaluation Suite
python src/eval_chat.py

# Run leave-drug-out cold-split benchmark evaluation
python src/eval_splits.py

# Run paper evaluation protocols and baseline comparison
python src/eval_paper_splits.py
```

---

## Directory Structure

```text
SynThera/
├── README.md                                  # Root setup and platform documentation
├── drug-combo-discovery/
│   ├── README.md                              # Package reference documentation
│   ├── Dockerfile                             # Container definition for API backend
│   ├── requirements.txt                       # Backend Python dependencies
│   ├── app/
│   │   ├── main.py                            # FastAPI application and route endpoints
│   │   └── chat.py                            # Grounded OpenRouter tool-calling assistant
│   ├── src/
│   │   ├── model.py                           # SynergyGNN / HGT neural network architecture
│   │   ├── search.py                          # Candidate discovery, Beam Search, & MCTS
│   │   ├── explain.py                         # Graph attribution & faithfulness ablations
│   │   ├── literature.py                      # PubMed E-Utilities RAG retrieval
│   │   ├── why_not.py                         # Grounded diagnostic reasoning agent
│   │   ├── eval_chat.py                       # Claim-level literal chat grounding evaluator
│   │   ├── eval_splits.py                     # Cold-drug split evaluation pipeline
│   │   ├── eval_paper_splits.py               # Benchmark split replication protocols
│   │   ├── familiarity.py                     # Training-set similarity distribution analysis
│   │   ├── baselines/                         # Baseline models (MLP, Random, Promiscuity)
│   │   ├── cell_line_mapping.py               # Disease-to-cell-line mapping logic
│   │   ├── build_heterodata.py                # PrimeKG graph assembly pipeline
│   │   └── train.py                           # Lightning training script
│   ├── docs/
│   │   ├── analysis_chat_openrouter.md        # Chat evaluation report & verified transcripts
│   │   ├── experiment_5_dsn_spn.md            # DSN / SPN architecture benchmark results
│   │   ├── experiment_6_strict_bilateral.md   # Strict bilateral cold-split analysis
│   │   ├── experiment_7_random_warm_split.md  # Random split comparison documentation
│   │   └── paper_evaluation_protocols.md      # Scientific benchmarking protocols
│   ├── tests/
│   │   ├── test_predict_triple.py             # Inference unit tests
│   │   ├── test_baseline.py                   # Baseline tests
│   │   ├── test_familiarity.py                # Similarity score tests
│   │   └── test_dsn_spn_architecture.py       # Architecture unit tests
│   └── frontend/
│       ├── package.json                       # React/Vite dependencies
│       ├── vite.config.ts                     # Vite configuration and proxy rules
│       └── src/
│           ├── pages/
│           │   ├── AnalysisPage.tsx           # Prediction, attribution, & chat UI
│           │   ├── DiscoverPage.tsx           # Targeted pair & unbiased search UI
│           │   └── KnowledgeGraphPage.tsx     # Interactive PrimeKG explorer
│           ├── components/
│           │   ├── analysis/                  # Toxicity, graph, and AnalysisChatPanel
│           │   └── discover/                  # Pair search controls & result cards
│           └── services/
│               └── api.ts                     # Type-safe API client wrappers
```

---

## Artifact Handling

To keep the git repository lightweight and fast to clone, large binary model checkpoints and processed graphs are **not committed to git** and are excluded via `.gitignore`:

* `data/processed/heterodata.pt` (~175 MB): HeteroData graph containing PrimeKG nodes and 2048-bit Morgan drug fingerprints.
* `models/synergy_gnn_final.ckpt` (~30 MB): Final PyTorch Lightning model weights.
* `data/processed/primekg_nodes.csv` (~1 MB): Global node metadata and name lookups.
* `data/processed/labeled_pairs.csv` (~3 MB): Experimental synergy labels from DrugComb.
* `data/processed/cell_line_metadata.csv`: Cancer cell line disease mappings.

### Rebuilding Artifacts from Scratch (Optional)
If rebuilding the dataset and training from raw data:
```bash
cd drug-combo-discovery
# Build processed HeteroData graph with Morgan fingerprints
python src/build_heterodata.py
# Train SynergyGNN with cold-drug splitting
python src/train.py
```