# SynThera: Explainable Drug Combination Discovery

SynThera is an end-to-end artificial intelligence platform for discovering and explaining synergistic drug combinations in oncology. It couples a Heterogeneous Graph Transformer (HGT) trained on the PrimeKG biomedical knowledge graph and DrugComb experimental synergy labels with gradient-based mechanistic attribution, real in-silico faithfulness ablation, PubMed literature retrieval, and an interactive web interface.

---

## Benchmark Headline Performance

| Metric | Score | Evaluation Setting |
|---|:---:|---|
| **Test AUROC** | **0.64** | Cold-Drug Split (Leave-Drugs-Out) |
| **Test AUPR** | **0.44** | Cold-Drug Split (Random Prevalence Baseline: ~0.16) |

### Why This Benchmark is Scientifically Honest
In drug synergy literature, standard random pair splitting causes massive data leakage: if Drug A is seen with Drug B during training, a model in test predicting (Drug A, Drug C) simply exploits marginal single-drug promiscuity, producing artificially inflated AUROC scores ($>0.85$) that fail during wet-lab validation.

SynThera enforces a **cold-drug split (leave-drugs-out)**:
* A designated 15% of drugs are strictly held out and **completely absent** from all training pairs (disjoint drug pools: $D_{\text{train}} \cap D_{\text{test}} = \emptyset$).
* Any pair containing a held-out drug is assigned to the test set. Across the 37,778 test pairs:
  * **Unilateral cold pairs (~29,282 pairs):** Exactly one drug was unseen during training.
  * **Bilateral cold pairs (~8,496 pairs):** Neither drug appeared anywhere in any training combination (the strictest inductive subset).
* Achieving **0.64 AUROC** and **0.44 AUPR** on the full cold-drug test split represents true, generalizable out-of-distribution inference across the heterogeneous biological graph.

---

## Architecture Overview

1. **Stage 1: Candidate Generation & Biological Filtering (`src/search.py`)**
   Traverses PrimeKG to find direct disease indications and target-overlap proteins. Denies non-drug biological entities, excipients, solvents, and elemental minerals via `is_valid_therapeutic_candidate()`, and excludes 55 cytochrome P450 (CYP) metabolic enzymes to eliminate pharmacokinetic false positives.
2. **Stage 2: GNN-Driven Combination Scoring (`src/search.py`, `src/model.py`)**
   Evaluates candidate drug pairs in cell-line contexts using Beam Search, Greedy Search, or Monte Carlo Tree Search (MCTS) with Upper Confidence bounds applied to Trees (UCT). Scored directly by the trained `SynergyGNN` model without heuristic overrides.
3. **Stage 3: Biological Explanations & Faithfulness (`src/explain.py`)**
   Extracts lightweight local 2-hop subgraphs with PyTorch Geometric `NeighborLoader` without copying the multi-hundred-megabyte graph. Computes gradient attribution to identify load-bearing biological paths, tests faithfulness via in-silico necessity/sufficiency edge ablations, and retrieves corroborating peer-reviewed citations via PubMed RAG (`src/literature.py`).
4. **Interactive Interfaces**
   * **FastAPI Backend (`app/main.py`)**: High-throughput REST API.
   * **React / Vite Frontend (`frontend/`)**: Modern UI featuring animated interaction graphs, confidence breakdowns, and diagnostic tools.

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

---

## Environment Variables

Configure optional environment variables in your environment or a `.env` file:

| Variable | Default | Description |
|---|---|---|
| `PORT` | `7860` | Port for FastAPI server. |
| `NCBI_API_KEY` | *None* | **Recommended for production.** Setting a personal NCBI API key increases PubMed E-Utilities rate limits from 3 requests/sec to 10 requests/sec. |
| `OPENROUTER_API_KEY` | *None* | **Required for Analysis chat assistant.** API key for OpenRouter (OpenAI-compatible API). OpenRouter bills per-token across whatever model is selected. |
| `OPENROUTER_MODEL` | `openrouter/free` | Model string to route via OpenRouter. Defaults to `openrouter/free` which routes to free tool-calling models at $0.00 cost (zero token bill). |
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
.venv\Scripts\activate

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

In a new terminal:
```bash
cd SynThera/drug-combo-discovery/frontend
npm install
npm run dev
```
Open your browser at `http://localhost:5173`.

---

## CLI Combination Discovery

Run the combination discovery pipeline directly from the command line:

```bash
cd drug-combo-discovery
python src/search.py --disease glioblastoma --cell-line T98G --max-candidates 20 --top-k 5
```

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

**Example Verdict:**
```json
{
  "drug_x": "Zinc chloride",
  "category": "filtered_non_therapeutic",
  "verdict": "Zinc chloride was filtered out upstream because it is an inorganic salt / dietary supplement, not a plausible therapeutic antineoplastic agent."
}
```

---

## Directory Structure

```text
SynThera/
├── README.md                          # Root setup and documentation
├── drug-combo-discovery/
│   ├── README.md                      # Project reference documentation
│   ├── Dockerfile                     # Container definition for API backend
│   ├── requirements.txt               # Backend Python dependencies
│   ├── app/
│   │   └── main.py                    # FastAPI application and endpoint handlers
│   ├── src/
│   │   ├── model.py                   # SynergyGNN / HGT neural network architecture
│   │   ├── search.py                  # Candidate discovery, Beam Search, & MCTS
│   │   ├── explain.py                 # Graph attribution & faithfulness ablations
│   │   ├── literature.py              # PubMed E-Utilities RAG retrieval
│   │   ├── why_not.py                 # Grounded diagnostic reasoning agent
│   │   ├── cell_line_mapping.py       # Disease-to-cell-line mapping logic
│   │   ├── build_heterodata.py        # Graph assembly pipeline
│   │   ├── train.py                   # Lightning training script
│   │   └── predict.py                 # CLI inference utility
│   ├── lightning_logs/
│   │   └── version_8/                 # Checkpoint logs with final benchmark metrics
│   └── frontend/
│       ├── package.json               # React/Vite dependencies
│       ├── vite.config.ts             # Vite configuration and proxy rules
│       └── src/                       # React components and Tailwind CSS UI
```