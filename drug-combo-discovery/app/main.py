"""
=============================================================================
SynThera Drug Synergy & Explainability API
=============================================================================

FastAPI service wrapping the production Synergy GNN model (synergy_gnn_final.ckpt)
and the biological explanation pipeline (src/explain.py).

Example curl commands:

1. Health check:
   curl -X GET http://localhost:8000/health

2. Get list of all available drugs:
   curl -X GET http://localhost:8000/drugs

3. Get list of all available cell lines:
   curl -X GET http://localhost:8000/cell-lines

4. Predict synergy & generate biological explanation (by DrugBank ID):
   curl -X POST http://localhost:8000/predict \
        -H "Content-Type: application/json" \
        -d "{\"drug_a\": \"DB00853\", \"drug_b\": \"DB00531\", \"cell_line\": \"T98G\"}"

5. Predict synergy & generate biological explanation (by Drug Name):
   curl -X POST http://localhost:8000/predict \
        -H "Content-Type: application/json" \
        -d "{\"drug_a\": \"Temozolomide\", \"drug_b\": \"Cyclophosphamide\", \"cell_line\": \"T98G\"}"
=============================================================================
"""

import os
import sys
from typing import Any, Dict, List, Optional, Tuple

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Ensure project root and src/ are in Python path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from predict import load_model, _get_node_maps
from explain import explain_prediction, _build_name_lookups
from search import (
    find_candidate_drugs,
    score_candidate_pairs,
    beam_search_combinations,
    get_full_explanations_for_top_k,
)
from cell_line_mapping import get_relevant_cell_lines, is_cancer_disease

# File paths
CHECKPOINT_PATH = os.path.join(ROOT_DIR, "models", "synergy_gnn_final.ckpt")
HETERODATA_PATH = os.path.join(ROOT_DIR, "data", "processed", "heterodata.pt")
LABELED_PAIRS_PATH = os.path.join(ROOT_DIR, "data", "processed", "labeled_pairs.csv")

# ---------------------------------------------------------------------------
# Global in-memory state & cache
# ---------------------------------------------------------------------------
MODULE = None
HETERODATA = None
DEVICE = "cpu"

DRUG_LIST: List[Dict[str, str]] = []
DRUG_ALIAS_MAP: Dict[str, str] = {}         # alias.lower() -> canonical DrugBank ID
CELL_LINE_LIST: List[str] = []
CELL_LINE_ALIAS_MAP: Dict[str, str] = {}    # name.lower() -> canonical cell line name

PREDICTION_CACHE: Dict[Tuple[Tuple[str, str], str], Dict[str, Any]] = {}


def _initialize_app_state():
    """Load model, heterodata, build alias maps, and prepare dropdown lists."""
    global MODULE, HETERODATA, DEVICE
    global DRUG_LIST, DRUG_ALIAS_MAP, CELL_LINE_LIST, CELL_LINE_ALIAS_MAP

    print("=" * 65)
    print("  Initializing SynThera FastAPI Service...")
    print("=" * 65)

    # 1. Load GNN model and HeteroData
    MODULE, HETERODATA, DEVICE = load_model(CHECKPOINT_PATH, HETERODATA_PATH)

    # 2. Build name lookups from PrimeKG
    name_lookup, id_lookup = _build_name_lookups(HETERODATA)
    drug_id2idx = _get_node_maps(HETERODATA).get("drug", {})

    # 3. Build drug list and drug alias map
    seen_drugs = set()
    drugs = []
    drug_alias = {}

    for idx, db_id in id_lookup.get("drug", {}).items():
        name = name_lookup.get("drug", {}).get(idx, db_id)
        if db_id in drug_id2idx and db_id not in seen_drugs:
            seen_drugs.add(db_id)
            drugs.append({"id": db_id, "name": name})
            drug_alias[db_id.lower()] = db_id
            drug_alias[name.lower()] = db_id

    # Also incorporate any aliases from labeled_pairs.csv (e.g. all-caps names)
    if os.path.exists(LABELED_PAIRS_PATH):
        try:
            import pandas as pd
            df_labels = pd.read_csv(LABELED_PAIRS_PATH, usecols=["drug_a_kg_id", "drug_a_name", "drug_b_kg_id", "drug_b_name"])
            for _, row in df_labels.iterrows():
                da_id = str(row["drug_a_kg_id"])
                da_name = str(row["drug_a_name"])
                db_id = str(row["drug_b_kg_id"])
                db_name = str(row["drug_b_name"])

                if da_id in seen_drugs and da_name:
                    drug_alias[da_name.lower()] = da_id
                if db_id in seen_drugs and db_name:
                    drug_alias[db_name.lower()] = db_id
        except Exception as e:
            print(f"  [warn] Could not load labeled_pairs aliases: {e}")

    drugs.sort(key=lambda x: x["name"].lower())
    DRUG_LIST = drugs
    DRUG_ALIAS_MAP = drug_alias
    print(f"  [init] Indexed {len(DRUG_LIST)} unique drugs with {len(DRUG_ALIAS_MAP)} alias keys.")

    # 4. Build cell line list and alias map
    cell_line_map = getattr(HETERODATA, "cell_line_map", {})
    cell_lines = sorted(list(cell_line_map.keys()))
    cell_alias = {cl.lower(): cl for cl in cell_lines}

    CELL_LINE_LIST = cell_lines
    CELL_LINE_ALIAS_MAP = cell_alias
    print(f"  [init] Indexed {len(CELL_LINE_LIST)} cell lines.")
    print("  [init] Service initialization complete.")
    print("=" * 65)


# Run initialization immediately at module load time (meets "ONCE at startup, module-level" requirement)
_initialize_app_state()


# ---------------------------------------------------------------------------
# FastAPI Application & Lifespan
# ---------------------------------------------------------------------------

app = FastAPI(
    title="SynThera Drug Synergy & Explainability API",
    description="Explainable Graph Neural Network (HGT) for anticancer drug combination synergy prediction.",
    version="1.0.0",
)

# Enable CORS for all origins (ideal for hackathon frontend / local dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request & Response Schemas
# ---------------------------------------------------------------------------

class PredictRequest(BaseModel):
    drug_a: str = Field(..., description="Drug A name (e.g. 'Temozolomide') or DrugBank ID (e.g. 'DB00853')")
    drug_b: str = Field(..., description="Drug B name (e.g. 'Cyclophosphamide') or DrugBank ID (e.g. 'DB00531')")
    cell_line: str = Field(..., description="Cell line name (e.g. 'T98G', 'A549', 'OVCAR-5')")
    disease: Optional[str] = Field(None, description="Target disease context (e.g. 'glioblastoma')")

    model_config = {
        "json_schema_extra": {
            "example": {
                "drug_a": "Temozolomide",
                "drug_b": "Cyclophosphamide",
                "cell_line": "T98G",
                "disease": "glioblastoma",
            }
        }
    }


class SearchRequest(BaseModel):
    disease: str = Field(..., description="Target disease name (e.g. 'glioblastoma')")
    cell_line: str = Field(..., description="Target cell line name (e.g. 'T98G')")
    max_candidates: int = Field(20, description="Maximum candidate drugs to discover from PrimeKG")
    top_k: int = Field(5, description="Number of top-scoring candidate pairs to return")
    search_method: str = Field("beam", description="Search strategy: 'beam' (default), 'greedy', or 'mcts'. Beam expands top-B anchors greedily; MCTS uses Upper Confidence bounds applied to Trees (UCT) to balance exploration and exploitation across candidate combinations.")
    beam_width: int = Field(5, description="Beam width B for state-space expansion (used when search_method='beam')")
    n_simulations: int = Field(50, description="Number of MCTS simulations/rollouts to run (used when search_method='mcts')")
    mcts_c: float = Field(1.414, description="UCT exploration constant balancing exploitation of high-scoring pairs vs exploration of unvisited branches (used when search_method='mcts')")
    time_budget_sec: float = Field(15.0, description="Hard wall-clock timeout in seconds for MCTS search (returns best pairs found so far if reached)")
    inspect_top_k: int = Field(0, description="Optional number of top hits (0-3) to run in-silico faithfulness ablation on")

    model_config = {
        "json_schema_extra": {
            "example": {
                "disease": "glioblastoma",
                "cell_line": "T98G",
                "max_candidates": 20,
                "top_k": 5,
                "search_method": "beam",
                "beam_width": 5,
                "n_simulations": 50,
                "mcts_c": 1.414,
                "time_budget_sec": 15.0,
                "inspect_top_k": 0,
            }
        }
    }


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@app.get("/health", summary="Service Health Check")
def health_check() -> Dict[str, Any]:
    """
    Check service health, confirming model and knowledge graph are loaded
    and reporting the active compute device (CPU/CUDA).
    """
    return {
        "status": "ok",
        "model_loaded": MODULE is not None and HETERODATA is not None,
        "device": str(DEVICE),
        "total_drugs": len(DRUG_LIST),
        "total_cell_lines": len(CELL_LINE_LIST),
        "cache_entries": len(PREDICTION_CACHE),
    }


@app.get("/drugs", summary="List Available Drugs")
def get_drugs() -> List[Dict[str, str]]:
    """
    Return all drug names and DrugBank IDs available in the PrimeKG graph
    for populating frontend search and dropdown menus.
    """
    return DRUG_LIST


@app.get("/cell-lines", summary="List Available Cell Lines")
def get_cell_lines(disease: Optional[str] = None) -> List[str]:
    """
    Return all available cancer cell line names, or filter by disease indication
    using cell_line_mapping.py dynamic relevance logic.
    """
    if disease and disease.strip():
        relevant = get_relevant_cell_lines(disease.strip())
        available_set = set(CELL_LINE_LIST)
        return [cl for cl in relevant if cl in available_set]
    return CELL_LINE_LIST


@app.post("/predict", summary="Predict Synergy and Generate Biological Explanation")
def predict(request: PredictRequest) -> Dict[str, Any]:
    """
    Predict synergy, additive, or antagonism interaction for a drug pair in a given
    cell line context, returning calibrated probabilities, mechanistic explanations,
    top load-bearing edges, and a real in-silico faithfulness ablation object.

    The returned `faithfulness` dictionary contains:
      - `original_score` (float): Unablated probability on predicted class.
      - `original_class` (str): Calibrated interaction class ('synergy', 'additive', 'antagonism').
      - `ablated_score` (float): Probability on predicted class after ablating top-K edges.
      - `ablated_class` (str): Predicted class on the ablated graph.
      - `sufficiency` (float): % of original confidence retained on isolated subgraph:
        formula: `(p_suf / p_orig) * 100%`.
      - `necessity` (float): % probability drop when top-K edges are ablated:
        formula: `((p_orig - p_abl) / p_orig) * 100%`.
      - `explanation_faithful` (bool): True if sufficiency >= 70.0% with class preserved.
      - `rationale` (str): One-sentence scientific rationale for the verification verdict.
      - `k_edges_ablated` (int): Number of load-bearing edges ablated (default: 10).
      - `error` (str | None): Explicit error string if an edge case prevents ablation.
    """
    drug_a_raw = request.drug_a.strip()
    drug_b_raw = request.drug_b.strip()
    cell_line_raw = request.cell_line.strip()

    # 1. Resolve Drug A (case-insensitive lookup on ID or Name)
    drug_a_id = DRUG_ALIAS_MAP.get(drug_a_raw.lower())
    if not drug_a_id:
        raise HTTPException(
            status_code=404,
            detail=f"Drug '{drug_a_raw}' not found in knowledge graph. Please check /drugs for available compounds.",
        )

    # 2. Resolve Drug B (case-insensitive lookup on ID or Name)
    drug_b_id = DRUG_ALIAS_MAP.get(drug_b_raw.lower())
    if not drug_b_id:
        raise HTTPException(
            status_code=404,
            detail=f"Drug '{drug_b_raw}' not found in knowledge graph. Please check /drugs for available compounds.",
        )

    # 3. Resolve Cell Line (case-insensitive lookup)
    canonical_cell_line = CELL_LINE_ALIAS_MAP.get(cell_line_raw.lower())
    if not canonical_cell_line:
        raise HTTPException(
            status_code=404,
            detail=f"Cell line '{cell_line_raw}' not found in knowledge graph. Please check /cell-lines for available lines.",
        )

    disease_raw = request.disease.strip() if request.disease else None

    # 4. Check in-memory cache (symmetric on drug order, with disease context)
    cache_key = (tuple(sorted([drug_a_id, drug_b_id])), canonical_cell_line, (disease_raw or "").lower())
    if cache_key in PREDICTION_CACHE:
        cached_result = dict(PREDICTION_CACHE[cache_key])
        cached_result["cached"] = True
        return cached_result

    # 5. Run inference and explanation pipeline (with real in-silico ablation and literature RAG)
    try:
        result = explain_prediction(
            drug_a_id=drug_a_id,
            drug_b_id=drug_b_id,
            cell_line_name=canonical_cell_line,
            module=MODULE,
            heterodata=HETERODATA,
            device=DEVICE,
            run_faithfulness=True,
            run_literature=True,
            disease_context=disease_raw,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Inference error while explaining prediction: {str(e)}",
        )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    # 6. Store in cache
    result["cached"] = False
    PREDICTION_CACHE[cache_key] = result

    return result


@app.post("/search", summary="Discover and Score Candidate Drug Combinations for a Disease")
def search_combinations(request: SearchRequest) -> Dict[str, Any]:
    """
    Given a target disease name and cell line context, discover candidate drugs via PrimeKG,
    score candidate pairs using the trained Synergy GNN model, and generate biologically grounded
    explanations for top hits.

    MCTS vs. Beam Search:
    Beam Search expands a fixed width of top-B candidate anchor drugs deterministically and
    greedily scores their partner space in batched passes. In contrast, Monte Carlo Tree Search
    (MCTS) models combination discovery as a sequential decision tree (Depth 0: root -> Depth 1:
    choose drug A -> Depth 2: choose partner drug B != A). MCTS utilizes Upper Confidence bounds
    applied to Trees (UCT) with exploration constant c to dynamically balance exploiting known
    high-synergy drug clusters against exploring under-sampled candidate drugs, evaluating terminal
    pairs directly with the trained SynergyGNN value function while caching pair evaluations.
    """
    disease_raw = request.disease.strip()
    cell_line_raw = request.cell_line.strip()

    # 1. Resolve Cell Line (case-insensitive)
    canonical_cell_line = CELL_LINE_ALIAS_MAP.get(cell_line_raw.lower())
    if not canonical_cell_line:
        sample_cls = CELL_LINE_LIST[:8]
        raise HTTPException(
            status_code=404,
            detail=f"Cell line '{cell_line_raw}' not found in knowledge graph. Available cell lines include: {sample_cls} (total {len(CELL_LINE_LIST)}).",
        )

    # 2. Find Candidate Drugs for Disease
    candidates = find_candidate_drugs(
        disease_name=disease_raw,
        heterodata=HETERODATA,
        max_candidates=request.max_candidates,
    )

    if not candidates:
        raise HTTPException(
            status_code=404,
            detail=f"Disease '{disease_raw}' could not be resolved to any node in PrimeKG knowledge graph. Please verify the disease name.",
        )

    # 3. Score Candidate Pairs using Beam/Greedy/MCTS Search
    try:
        top_pairs, search_meta = beam_search_combinations(
            disease_name=disease_raw,
            cell_line_name=canonical_cell_line,
            heterodata=HETERODATA,
            module=MODULE,
            device=DEVICE,
            max_candidate_drugs=request.max_candidates,
            beam_width=request.beam_width,
            top_k=request.top_k,
            search_method=request.search_method,
            n_simulations=request.n_simulations,
            mcts_c=request.mcts_c,
            time_budget_sec=request.time_budget_sec,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error while scoring candidate pairs: {str(e)}",
        )

    # 4. Generate Full Explanations for Top-K Pairs
    try:
        explanations = get_full_explanations_for_top_k(
            top_k_pairs=top_pairs,
            cell_line_name=canonical_cell_line,
            module=MODULE,
            heterodata=HETERODATA,
            device=DEVICE,
            inspect_top_k=request.inspect_top_k,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error while generating explanations for top candidate pairs: {str(e)}",
        )

    return {
        "disease": disease_raw,
        "cell_line": canonical_cell_line,
        "search_method": search_meta.get("search_method", request.search_method),
        "beam_width": search_meta.get("beam_width", request.beam_width),
        "candidate_pool_size": search_meta.get("candidate_pool_size", len(candidates)),
        "max_candidates_scored": search_meta.get("max_candidates_scored", len(top_pairs)),
        "n_simulations": search_meta.get("n_simulations"),
        "n_pairs_scored": search_meta.get("n_pairs_scored"),
        "truncated": search_meta.get("truncated", False),
        "results": explanations,
    }


# ---------------------------------------------------------------------------
# Local development runner
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
