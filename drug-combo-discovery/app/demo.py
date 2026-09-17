"""
=============================================================================
SynThera — Explainable Drug Combination Discovery (Streamlit Demo)
=============================================================================

Interactive web dashboard calling the SynThera FastAPI backend (http://localhost:8000).
Provides synergy prediction with biologically grounded explanations, dual faithfulness
metrics, and interactive PyVis heterogeneous subgraph visualization.
=============================================================================
"""

import os
import sys
from typing import Any, Dict, List, Optional, Tuple

import requests
import streamlit as st
import streamlit.components.v1 as components
from pyvis.network import Network

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from cell_line_mapping import (
    get_relevant_cell_lines,
    get_cell_line_info,
    is_cell_line_relevant,
)

# ---------------------------------------------------------------------------
# Page Configuration & Global Styling
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Explainable Drug Combination Discovery",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for distance-readable presentation (large fonts, clear contrast)
st.markdown(
    """
    <style>
    /* Global typography & spacing */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1280px;
    }
    
    /* Main titles */
    .main-title {
        font-size: 2.5rem !important;
        font-weight: 800 !important;
        color: #0f172a !important;
        margin-bottom: 0.25rem !important;
        letter-spacing: -0.02em;
    }
    
    .subtitle {
        font-size: 1.25rem !important;
        color: #475569 !important;
        margin-bottom: 1.75rem !important;
        font-weight: 400 !important;
        line-height: 1.5 !important;
    }

    /* Prediction badge styling */
    .badge-synergy {
        display: inline-flex;
        align-items: center;
        gap: 16px;
        background-color: #ecfdf5;
        border: 2.5px solid #10b981;
        border-radius: 12px;
        padding: 14px 28px;
        margin-bottom: 1.25rem;
    }
    .badge-synergy .badge-title {
        font-size: 1.9rem;
        font-weight: 800;
        color: #047857;
        letter-spacing: 0.05em;
    }
    .badge-synergy .badge-prob {
        font-size: 1.45rem;
        font-weight: 700;
        color: #065f46;
    }

    .badge-antagonism {
        display: inline-flex;
        align-items: center;
        gap: 16px;
        background-color: #fef2f2;
        border: 2.5px solid #ef4444;
        border-radius: 12px;
        padding: 14px 28px;
        margin-bottom: 1.25rem;
    }
    .badge-antagonism .badge-title {
        font-size: 1.9rem;
        font-weight: 800;
        color: #b91c1c;
        letter-spacing: 0.05em;
    }
    .badge-antagonism .badge-prob {
        font-size: 1.45rem;
        font-weight: 700;
        color: #991b1b;
    }

    .badge-additive {
        display: inline-flex;
        align-items: center;
        gap: 16px;
        background-color: #fffbeb;
        border: 2.5px solid #f59e0b;
        border-radius: 12px;
        padding: 14px 28px;
        margin-bottom: 1.25rem;
    }
    .badge-additive .badge-title {
        font-size: 1.9rem;
        font-weight: 800;
        color: #b45309;
        letter-spacing: 0.05em;
    }
    .badge-additive .badge-prob {
        font-size: 1.45rem;
        font-weight: 700;
        color: #92400e;
    }

    /* Explanation callout box */
    .explanation-box {
        background: #f8fafc;
        border-radius: 10px;
        padding: 22px 26px;
        margin-bottom: 1.25rem;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.04);
    }
    .explanation-heading {
        font-size: 1.15rem;
        font-weight: 700;
        color: #1e293b;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .explanation-text {
        font-size: 1.25rem !important;
        line-height: 1.65 !important;
        color: #0f172a !important;
        font-weight: 500 !important;
        margin: 0 !important;
    }

    /* Faithfulness caption */
    .faithfulness-caption {
        font-size: 1.05rem;
        color: #475569;
        background: #f1f5f9;
        padding: 10px 18px;
        border-radius: 8px;
        margin-bottom: 0.75rem;
        display: inline-block;
        font-weight: 500;
        border: 1px solid #e2e8f0;
    }

    /* Supporting Literature section */
    .literature-section {
        margin-bottom: 1.5rem;
        padding: 10px 16px;
        border-radius: 8px;
        background: #f8fafc;
        border: 1px solid #e2e8f0;
    }
    .literature-heading {
        font-size: 0.85rem;
        font-weight: 700;
        color: #64748b;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        margin-bottom: 6px;
    }
    .literature-item {
        font-size: 0.9rem;
        line-height: 1.5;
        color: #334155;
        margin-bottom: 4px;
    }
    .literature-item a {
        color: #2563eb;
        text-decoration: none;
        font-weight: 500;
    }
    .literature-item a:hover {
        text-decoration: underline;
    }
    .literature-meta {
        color: #64748b;
        font-size: 0.82rem;
    }
    .literature-empty {
        font-size: 0.88rem;
        color: #94a3b8;
        font-style: italic;
    }

    .legend-container {
        display: flex;
        gap: 16px;
        align-items: center;
        margin-bottom: 10px;
        font-size: 0.95rem;
        font-weight: 600;
    }
    .legend-item {
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
    .legend-dot {
        width: 13px;
        height: 13px;
        border-radius: 50%;
        display: inline-block;
    }

    /* Evidence Tier Badges */
    .tier-badge-direct {
        background-color: #dcfce7;
        color: #15803d;
        border: 1.5px solid #86efac;
        padding: 4px 12px;
        border-radius: 6px;
        font-size: 0.85rem;
        font-weight: 700;
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }
    .tier-badge-mixed {
        background-color: #fef9c3;
        color: #a16207;
        border: 1.5px solid #fde047;
        padding: 4px 12px;
        border-radius: 6px;
        font-size: 0.85rem;
        font-weight: 700;
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }
    .tier-badge-indirect {
        background-color: #f1f5f9;
        color: #475569;
        border: 1.5px solid #cbd5e1;
        padding: 4px 12px;
        border-radius: 6px;
        font-size: 0.85rem;
        font-weight: 700;
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }
    .ood-warning-badge {
        background-color: #fff7ed;
        color: #c2410c;
        border: 1.5px solid #ffedd5;
        padding: 4px 12px;
        border-radius: 6px;
        font-size: 0.82rem;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }

    /* Search Result Card Container */
    .search-card {
        background: #ffffff;
        border: 1.5px solid #e2e8f0;
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    .search-card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
        flex-wrap: wrap;
        gap: 10px;
    }
    .search-card-title {
        font-size: 1.35rem;
        font-weight: 800;
        color: #0f172a;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# API Configuration & Backend Connectors
# ---------------------------------------------------------------------------
API_BASE_URL = os.environ.get("SYNTHERA_API_URL", "http://127.0.0.1:8000")


def check_backend_health() -> Tuple[bool, str]:
    """Check whether FastAPI backend is responsive."""
    for attempt in range(2):
        try:
            r = requests.get(f"{API_BASE_URL}/health", timeout=5)
            if r.status_code == 200:
                return True, "ok"
            return False, f"Backend returned HTTP {r.status_code}"
        except requests.exceptions.RequestException as e:
            if attempt == 0:
                continue
            return False, str(e)
    return False, "Backend connection timeout"


@st.cache_data(ttl=3600)
def load_catalog_data() -> Tuple[List[Dict[str, str]], List[str]]:
    """Fetch all available drugs and cell lines from FastAPI."""
    r_drugs = requests.get(f"{API_BASE_URL}/drugs", timeout=20)
    r_drugs.raise_for_status()
    drugs = r_drugs.json()

    r_cells = requests.get(f"{API_BASE_URL}/cell-lines", timeout=20)
    r_cells.raise_for_status()
    cell_lines = r_cells.json()

    return drugs, cell_lines


def query_prediction(drug_a: str, drug_b: str, cell_line: str) -> Optional[Dict[str, Any]]:
    """Call backend /predict endpoint."""
    payload = {
        "drug_a": drug_a,
        "drug_b": drug_b,
        "cell_line": cell_line,
    }
    r = requests.post(f"{API_BASE_URL}/predict", json=payload, timeout=45)
    if r.status_code == 200:
        return r.json()
    elif r.status_code == 404:
        st.error(f"❌ **Entity Not Found:** {r.json().get('detail', 'Unknown error')}")
        return None
    else:
        st.error(f"❌ **Inference Error (HTTP {r.status_code}):** {r.text}")
        return None


def query_search(disease: str, cell_line: str, max_candidates: int = 20, top_k: int = 5) -> Optional[Dict[str, Any]]:
    """Call backend /search endpoint."""
    payload = {
        "disease": disease,
        "cell_line": cell_line,
        "max_candidates": max_candidates,
        "top_k": top_k,
    }
    try:
        r = requests.post(f"{API_BASE_URL}/search", json=payload, timeout=120)
        if r.status_code == 200:
            return r.json()
        elif r.status_code == 404:
            st.error(f"❌ **Disease or Cell Line Error:** {r.json().get('detail', 'Unknown error')}")
            return None
        else:
            st.error(f"❌ **Search Error (HTTP {r.status_code}):** {r.text}")
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"❌ **Connection Error:** Could not reach FastAPI backend: {e}")
        return None


def render_literature_html(lit_refs: List[Dict[str, Any]]) -> str:
    """Render HTML component for PubMed supporting literature citations."""
    if lit_refs:
        lit_items_html = ""
        for ref in lit_refs:
            title       = ref.get("title", "").strip()
            url         = ref.get("url", "#")
            year        = ref.get("year", "")
            first_auth  = ref.get("first_author", "")
            pmid        = ref.get("pmid", "")
            meta_parts  = [p for p in [first_auth, year, f"PMID {pmid}"] if p]
            meta_str    = " &middot; ".join(meta_parts)
            lit_items_html += (
                f'<div class="literature-item">'
                f'<a href="{url}" target="_blank" rel="noopener noreferrer">{title}</a>'
                f'<br><span class="literature-meta">{meta_str}</span>'
                f'</div>'
            )
        return (
            f'<div class="literature-section">'
            f'<div class="literature-heading">📄 Supporting Literature</div>'
            f'{lit_items_html}'
            f'</div>'
        )
    else:
        return (
            '<div class="literature-section">'
            '<div class="literature-heading">📄 Supporting Literature</div>'
            '<span class="literature-empty">No directly matching literature found for this mechanism.</span>'
            '</div>'
        )


# ---------------------------------------------------------------------------
# PyVis Subgraph Visualizer (Coherent, Stabilized Topology)
# ---------------------------------------------------------------------------
NODE_COLORS = {
    "drug": "#2563eb",         # Royal Blue
    "gene/protein": "#f97316", # Warm Orange
    "protein": "#f97316",
    "disease": "#10b981",      # Emerald Green
    "pathway": "#8b5cf6",      # Royal Purple
}


def build_pyvis_graph(
    top_edges: List[Dict[str, Any]],
    drug_a_name: str,
    drug_b_name: str,
    predicted_class: str = "synergy",
    prob: float = 0.0,
) -> str:
    """
    Generate interactive VisJS HTML string from top explanation edges.
    Guarantees a coherent, fully connected graph by:
    1. Anchoring both Drug A and Drug B as central hubs.
    2. Linking Drug A and Drug B via the candidate combination interaction edge.
    3. Stabilizing the physics simulation so nodes arrive in balanced equilibrium
       without drift or isolated strays.
    """
    net = Network(
        height="450px",
        width="100%",
        bgcolor="#f8fafc",
        font_color="#0f172a",
        directed=False,
    )

    # ForceAtlas2-based physics configuration with stabilization to keep hubs close together
    net.set_options("""
    {
      "physics": {
        "solver": "forceAtlas2Based",
        "forceAtlas2Based": {
          "gravitationalConstant": -55,
          "centralGravity": 0.04,
          "springLength": 110,
          "springConstant": 0.09,
          "damping": 0.88,
          "avoidOverlap": 0.6
        },
        "stabilization": {
          "enabled": true,
          "iterations": 400,
          "updateInterval": 25
        }
      },
      "interaction": {
        "hover": true,
        "zoomView": true,
        "dragNodes": true,
        "navigationButtons": false
      }
    }
    """)

    drug_names_lower = {drug_a_name.lower(), drug_b_name.lower()}

    # 1. Primary Hubs: Add both candidate drugs anchored adjacent in center
    net.add_node(
        drug_a_name,
        label=drug_a_name,
        color="#2563eb",
        size=34,
        title=f"Drug: {drug_a_name}",
        borderWidth=3,
        borderColor="#1d4ed8",
        font={"size": 14, "face": "Inter, sans-serif", "color": "#0f172a"},
        x=-35,
        y=0,
    )
    net.add_node(
        drug_b_name,
        label=drug_b_name,
        color="#2563eb",
        size=34,
        title=f"Drug: {drug_b_name}",
        borderWidth=3,
        borderColor="#1d4ed8",
        font={"size": 14, "face": "Inter, sans-serif", "color": "#0f172a"},
        x=35,
        y=0,
    )

    # 2. Add central candidate combination link between Drug A and Drug B
    # Short length (50) and high width (5.0) binds the two drug hubs tightly into a single cohesive nucleus
    combo_color = (
        "#10b981" if predicted_class.lower() == "synergy"
        else ("#ef4444" if predicted_class.lower() == "antagonism" else "#f59e0b")
    )
    net.add_edge(
        drug_a_name,
        drug_b_name,
        label=f"Combination ({predicted_class.capitalize()})",
        title=f"Candidate Pair: {drug_a_name} + {drug_b_name}<br>Predicted Interaction: {predicted_class.upper()} ({prob * 100:.1f}%)",
        color=combo_color,
        width=5.0,
        dashes=[6, 4],
        length=50,
        font={"size": 11, "color": combo_color, "align": "middle"},
    )

    added_nodes = {drug_a_name, drug_b_name}

    # 3. Add explanation relational edges radiating outward
    for edge in top_edges:
        src = str(edge.get("source", "")).strip()
        tgt = str(edge.get("target", "")).strip()
        rel = str(edge.get("relation", "interaction")).strip()
        imp = float(edge.get("importance", 0.0))

        if not src or not tgt:
            continue

        src_type = str(edge.get("source_type", "")).lower()
        tgt_type = str(edge.get("target_type", "")).lower()

        # Fallback type inference if missing
        if not src_type:
            if src.lower() in drug_names_lower:
                src_type = "drug"
            elif rel in ("drug_protein", "protein_protein", "pathway_protein"):
                src_type = "gene/protein"
            elif rel in ("indication", "off-label use", "contraindication", "disease_disease"):
                src_type = "disease"
            else:
                src_type = "gene/protein"

        if not tgt_type:
            if tgt.lower() in drug_names_lower:
                tgt_type = "drug"
            elif rel in ("drug_protein", "protein_protein"):
                tgt_type = "gene/protein"
            elif rel in ("indication", "off-label use", "contraindication"):
                tgt_type = "disease"
            else:
                tgt_type = "gene/protein"

        # Add source node
        if src not in added_nodes:
            is_drug = (src_type == "drug" or src.lower() in drug_names_lower)
            color = NODE_COLORS["drug"] if is_drug else NODE_COLORS.get(src_type, "#64748b")
            size = 32 if is_drug else 20
            net.add_node(
                src,
                label=src,
                color=color,
                size=size,
                title=f"Type: {src_type.capitalize()}<br>{src}",
                font={"size": 13 if is_drug else 11, "face": "Inter, sans-serif"},
            )
            added_nodes.add(src)

        # Add target node
        if tgt not in added_nodes:
            is_drug = (tgt_type == "drug" or tgt.lower() in drug_names_lower)
            color = NODE_COLORS["drug"] if is_drug else NODE_COLORS.get(tgt_type, "#64748b")
            size = 32 if is_drug else 20
            net.add_node(
                tgt,
                label=tgt,
                color=color,
                size=size,
                title=f"Type: {tgt_type.capitalize()}<br>{tgt}",
                font={"size": 13 if is_drug else 11, "face": "Inter, sans-serif"},
            )
            added_nodes.add(tgt)

        # Add edge with radiating length (135)
        edge_width = max(1.8, min(5.0, 1.5 + imp * 5.0))
        net.add_edge(
            src,
            tgt,
            title=f"Relation: {rel}<br>Importance: {imp:.4f}",
            label=rel,
            color="#94a3b8",
            width=edge_width,
            length=135,
            font={"size": 10, "color": "#64748b", "align": "middle"},
        )

    return net.generate_html()


# ---------------------------------------------------------------------------
# Main Application Flow
# ---------------------------------------------------------------------------
def main():
    import time
    t0 = time.time()
    print(f"[TIMING demo.py] 0.00s: Entering main()", flush=True)

    # 1. Health check & error handling
    is_healthy, health_msg = check_backend_health()
    print(f"[TIMING demo.py] {time.time()-t0:.2f}s: Health check complete (ok={is_healthy})", flush=True)
    if not is_healthy:
        st.error(
            "⚠️ **Backend Service Unreachable**\n\n"
            f"Could not connect to the SynThera FastAPI server at `{API_BASE_URL}`.\n\n"
            "**To launch the backend, open a terminal and run:**\n"
            "```bash\n"
            "uvicorn app.main:app --reload --host 0.0.0.0 --port 8000\n"
            "```\n\n"
            f"*Technical error details:* `{health_msg}`"
        )
        st.stop()

    # 2. Load catalog data
    with st.spinner("Connecting to knowledge graph and loading drug catalogs..."):
        drugs_catalog, cell_lines_catalog = load_catalog_data()
    print(f"[TIMING demo.py] {time.time()-t0:.2f}s: Catalog loaded ({len(drugs_catalog)} drugs, {len(cell_lines_catalog)} cells)", flush=True)

    # Build unique option labels: "DrugName (DrugBankID)"
    drug_labels = [f"{d['name']} ({d['id']})" for d in drugs_catalog]
    id_to_label = {d["id"]: f"{d['name']} ({d['id']})" for d in drugs_catalog}
    label_to_id = {f"{d['name']} ({d['id']})": d["id"] for d in drugs_catalog}

    # 3. Header Section
    st.markdown('<div class="main-title">Explainable Drug Combination Discovery</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="subtitle">AI-powered synergy prediction for drug-resistant conditions, with biologically grounded explanations.</div>',
        unsafe_allow_html=True,
    )

    # 4. Session State Initialization
    if "widget_drug_a" not in st.session_state:
        st.session_state["widget_drug_a"] = id_to_label.get("DB00853", drug_labels[0])
    if "widget_drug_b" not in st.session_state:
        st.session_state["widget_drug_b"] = id_to_label.get("DB00531", drug_labels[1])
    if "widget_cell_line" not in st.session_state:
        st.session_state["widget_cell_line"] = "T98G" if "T98G" in cell_lines_catalog else cell_lines_catalog[0]
    if "curr_drug_a" not in st.session_state:
        st.session_state["curr_drug_a"] = st.session_state["widget_drug_a"]
    if "curr_drug_b" not in st.session_state:
        st.session_state["curr_drug_b"] = st.session_state["widget_drug_b"]
    if "curr_cell_line" not in st.session_state:
        st.session_state["curr_cell_line"] = st.session_state["widget_cell_line"]
    if "prediction_result" not in st.session_state:
        st.session_state["prediction_result"] = None

    # 5. Sidebar: Locked Demo Trio (Direct Session State Setter with st.rerun)
    st.sidebar.markdown("### 🎯 Verified Demo Combinations")
    st.sidebar.caption("Click any locked oncology benchmark pair to auto-fill and run prediction:")

    btn_synergy = st.sidebar.button(
        "🟢 Synergy: Temozolomide + Cyclophosphamide (T98G)",
        use_container_width=True,
    )
    btn_antagonism = st.sidebar.button(
        "🔴 Antagonism: Temozolomide + Docetaxel (OVCAR-5)",
        use_container_width=True,
    )
    btn_additive = st.sidebar.button(
        "🟡 Additive: Docetaxel + Topotecan (A498)",
        use_container_width=True,
    )

    if btn_synergy:
        lbl_a = id_to_label["DB00853"]
        lbl_b = id_to_label["DB00531"]
        cl = "T98G"
        print(f"[DEBUG demo.py] Synergy Clicked -> Setting Drug A='{lbl_a}', Drug B='{lbl_b}', Cell Line='{cl}'", flush=True)
        st.session_state["curr_drug_a"] = lbl_a
        st.session_state["curr_drug_b"] = lbl_b
        st.session_state["curr_cell_line"] = cl
        st.session_state["widget_drug_a"] = lbl_a
        st.session_state["widget_drug_b"] = lbl_b
        st.session_state["widget_cell_line"] = cl
        st.session_state["trigger_predict"] = True
        st.rerun()

    if btn_antagonism:
        lbl_a = id_to_label["DB00853"]
        lbl_b = id_to_label["DB01248"]
        cl = "OVCAR-5"
        print(f"[DEBUG demo.py] Antagonism Clicked -> Setting Drug A='{lbl_a}', Drug B='{lbl_b}', Cell Line='{cl}'", flush=True)
        st.session_state["curr_drug_a"] = lbl_a
        st.session_state["curr_drug_b"] = lbl_b
        st.session_state["curr_cell_line"] = cl
        st.session_state["widget_drug_a"] = lbl_a
        st.session_state["widget_drug_b"] = lbl_b
        st.session_state["widget_cell_line"] = cl
        st.session_state["trigger_predict"] = True
        st.rerun()

    if btn_additive:
        lbl_a = id_to_label["DB01248"]
        lbl_b = id_to_label["DB01030"]
        cl = "A498"
        print(f"[DEBUG demo.py] Additive Clicked -> Setting Drug A='{lbl_a}', Drug B='{lbl_b}', Cell Line='{cl}'", flush=True)
        st.session_state["curr_drug_a"] = lbl_a
        st.session_state["curr_drug_b"] = lbl_b
        st.session_state["curr_cell_line"] = cl
        st.session_state["widget_drug_a"] = lbl_a
        st.session_state["widget_drug_b"] = lbl_b
        st.session_state["widget_cell_line"] = cl
        st.session_state["trigger_predict"] = True
        st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔬 Architecture & Data")
    st.sidebar.markdown(
        """
        - **Model:** 2-Layer Heterogeneous Graph Transformer (HGT)
        - **Knowledge Graph:** PrimeKG (129k nodes, 4.05M biological edges)
        - **Context:** Cancer cell-line transcriptional embedding (80 lines)
        - **Explainability:** Attentive gradient importance + Dual faithfulness (Necessity & Sufficiency)
        """
    )

    # 6. Main Tabs: Predict a Pair vs Discover Combinations
    tab_predict, tab_search = st.tabs(["🔮 Predict a Pair", "🔎 Discover Combinations"])

    with tab_predict:
        st.markdown("### 🧪 Select Candidate Combination")
        col1, col2, col3 = st.columns([1.2, 1.2, 0.9])

        with col1:
            drug_a_selection = st.selectbox(
                "Drug A",
                options=drug_labels,
                key="widget_drug_a",
                help="Select first therapeutic agent (search by brand/generic name or DrugBank ID)",
            )
            st.session_state["curr_drug_a"] = drug_a_selection

        with col2:
            drug_b_selection = st.selectbox(
                "Drug B",
                options=drug_labels,
                key="widget_drug_b",
                help="Select second therapeutic agent (search by brand/generic name or DrugBank ID)",
            )
            st.session_state["curr_drug_b"] = drug_b_selection

        with col3:
            cell_line_selection = st.selectbox(
                "Cell Line Context",
                options=cell_lines_catalog,
                key="widget_cell_line",
                help="Select cancer cell line context",
            )
            st.session_state["curr_cell_line"] = cell_line_selection

        print(f"[DEBUG demo.py] Rendered Dropdowns -> Drug A: '{drug_a_selection}', Drug B: '{drug_b_selection}', Cell Line: '{cell_line_selection}'", flush=True)

        # Action Button
        predict_clicked = st.button("🔮 Predict Combination & Explain", type="primary", use_container_width=True)

        # Check if prediction should run (either button clicked or sidebar triggered)
        should_run = predict_clicked or st.session_state.get("trigger_predict", False)
        if should_run:
            st.session_state["trigger_predict"] = False
            drug_a_id = label_to_id.get(drug_a_selection)
            drug_b_id = label_to_id.get(drug_b_selection)

            with st.spinner("Extracting 2-hop biological subgraph & evaluating interaction..."):
                res = query_prediction(drug_a_id, drug_b_id, cell_line_selection)
                if res:
                    st.session_state["prediction_result"] = res

        # Render Results for Predict tab
        res = st.session_state.get("prediction_result")
        if res:
            st.markdown("---")
            pred_class = res.get("predicted_class", "").lower()
            p_syn = res.get("p_synergy", 0.0)
            p_add = res.get("p_additive", 0.0)
            p_ant = res.get("p_antagonism", 0.0)

            # A. Large Color-Coded Badge
            if pred_class == "synergy":
                badge_html = f"""
                <div class="badge-synergy">
                    <span class="badge-title">🟢 SYNERGY</span>
                    <span class="badge-prob">Confidence: {p_syn * 100:.1f}%</span>
                </div>
                """
                accent_color = "#10b981"
            elif pred_class == "antagonism":
                badge_html = f"""
                <div class="badge-antagonism">
                    <span class="badge-title">🔴 ANTAGONISM</span>
                    <span class="badge-prob">Confidence: {p_ant * 100:.1f}%</span>
                </div>
                """
                accent_color = "#ef4444"
            else:
                badge_html = f"""
                <div class="badge-additive">
                    <span class="badge-title">🟡 ADDITIVE</span>
                    <span class="badge-prob">Confidence: {p_add * 100:.1f}%</span>
                </div>
                """
                accent_color = "#f59e0b"

            st.markdown(badge_html, unsafe_allow_html=True)

            # B. Mechanistic Explanation in Highlighted Box
            explanation_text = res.get("explanation_text", "No explanation available.")
            explanation_html = f"""
            <div class="explanation-box" style="border-left: 6px solid {accent_color};">
                <div class="explanation-heading">🧬 Mechanistic Biological Rationale</div>
                <p class="explanation-text">{explanation_text}</p>
            </div>
            """
            st.markdown(explanation_html, unsafe_allow_html=True)

            # C. Faithfulness Caption
            nec_delta = res.get("necessity_delta_pct", 0.0)
            suf_pct = res.get("sufficiency_retained_pct", 0.0)
            suf_pres = res.get("sufficiency_class_preserved", False)
            pres_label = "Yes" if suf_pres else "No"

            faithfulness_html = f"""
            <div class="faithfulness-caption">
                🔬 <strong>Faithfulness:</strong> &nbsp;
                Necessity: <strong>{nec_delta:+.1f}%</strong> (prob drop when top edges ablated) &nbsp;|&nbsp;
                Sufficiency: <strong>{suf_pct:.1f}%</strong> (original confidence retained with top edges only) &nbsp;
                (class preserved: <strong>{pres_label}</strong>)
            </div>
            """
            st.markdown(faithfulness_html, unsafe_allow_html=True)

            # D. Supporting Literature
            st.markdown(render_literature_html(res.get("supporting_literature", [])), unsafe_allow_html=True)

            # E. Probability breakdown pills
            st.caption(
                f"**Full Distribution:** p(Synergy) = `{p_syn:.3f}` &nbsp;|&nbsp; "
                f"p(Additive) = `{p_add:.3f}` &nbsp;|&nbsp; "
                f"p(Antagonism) = `{p_ant:.3f}` &nbsp;|&nbsp; "
                f"Response: `{'Cached (sub-ms)' if res.get('cached') else 'Computed'}`"
            )

            # F. Interactive PyVis Subgraph Visualization
            top_edges = res.get("top_edges", [])
            if top_edges:
                st.markdown("#### 🕸️ Biological Subgraph & Load-Bearing Relational Edges")
                st.markdown(
                    """
                    <div class="legend-container">
                        <span class="legend-item"><span class="legend-dot" style="background:#2563eb;"></span> Drug</span>
                        <span class="legend-item"><span class="legend-dot" style="background:#f97316;"></span> Gene / Protein</span>
                        <span class="legend-item"><span class="legend-dot" style="background:#10b981;"></span> Disease</span>
                        <span class="legend-item"><span class="legend-dot" style="background:#8b5cf6;"></span> Pathway</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                primary_prob = p_syn if pred_class == "synergy" else (p_ant if pred_class == "antagonism" else p_add)
                graph_html = build_pyvis_graph(
                    top_edges=top_edges,
                    drug_a_name=res.get("drug_a_name", drug_a_selection),
                    drug_b_name=res.get("drug_b_name", drug_b_selection),
                    predicted_class=pred_class,
                    prob=primary_prob,
                )
                components.html(graph_html, height=470, scrolling=False)

    # 7. Discover Combinations Tab
    with tab_search:
        st.markdown("### 🔎 Automated Drug Combination Search")
        st.caption("Enter a disease to discover candidate drugs via PrimeKG graph traversal and rank combinations using the Synergy GNN model.")

        scol1, scol2 = st.columns([1.5, 1.0])
        with scol1:
            disease_input = st.text_input(
                "Target Disease",
                value=st.session_state.get("search_disease_val", "glioblastoma"),
                placeholder="e.g. glioblastoma, breast neoplasm, ovarian carcinoma",
                help="Type any disease name to search PrimeKG indications and target overlap",
                key="search_disease_input_field",
            )
            st.session_state["search_disease_val"] = disease_input

        # Disease-aware cell line resolution
        target_disease_clean = disease_input.strip()
        relevant_cell_lines = get_relevant_cell_lines(target_disease_clean) if target_disease_clean else []
        has_cell_line_context = len(relevant_cell_lines) > 0

        with scol2:
            if not has_cell_line_context:
                search_cell_line = st.selectbox(
                    "Cell Line Context",
                    options=["No cancer cell-line context available"],
                    index=0,
                    disabled=True,
                    key="search_cell_line_disabled",
                    help="No cancer cell-line context available for this disease — using knowledge-graph structure only.",
                )
                actual_cell_line = "T98G"  # neutral fallback for backend GNN model
            else:
                other_lines = [c for c in cell_lines_catalog if c not in relevant_cell_lines]

                def make_display_label(c: str) -> str:
                    if c in relevant_cell_lines:
                        info = get_cell_line_info(c)
                        t = info.get("tissue", "") if info else ""
                        return f"⭐ {c} ({t} — Relevant)"
                    return c

                def parse_cell_line_name(opt: str) -> str:
                    cleaned = opt.strip()
                    if cleaned.startswith("⭐"):
                        cleaned = cleaned[1:].strip()
                    return cleaned.split(" (")[0].strip()

                display_options = [make_display_label(c) for c in (relevant_cell_lines + other_lines)]

                # Track previous disease to reset to top relevant line on change
                prev_disease = st.session_state.get("_prev_disease_input", "")
                current_raw = st.session_state.get("search_cell_line_raw")
                if prev_disease != target_disease_clean.lower() or not current_raw or current_raw not in cell_lines_catalog:
                    current_raw = relevant_cell_lines[0]
                    st.session_state["search_cell_line_raw"] = current_raw
                    st.session_state["_prev_disease_input"] = target_disease_clean.lower()

                current_display = make_display_label(current_raw)
                default_idx = display_options.index(current_display) if current_display in display_options else 0

                search_cell_line_display = st.selectbox(
                    "Cell Line Context",
                    options=display_options,
                    index=default_idx,
                    key="search_cell_line_select",
                    help="Target cell lines matching the disease tissue are listed on top with ⭐. Other lines may be selected for exploratory testing.",
                )
                actual_cell_line = parse_cell_line_name(search_cell_line_display)
                st.session_state["search_cell_line_raw"] = actual_cell_line

        # Status / Warning notifications below inputs
        if not has_cell_line_context:
            st.info("ℹ️ No cancer cell-line context available for this disease — using knowledge-graph structure only")
        else:
            if actual_cell_line not in relevant_cell_lines:
                info = get_cell_line_info(actual_cell_line)
                cl_tissue = info.get("tissue", "other tissue") if info else "other tissue"
                st.warning(
                    f"⚠️ Cell line **{actual_cell_line}** ({cl_tissue}) may not be relevant to **{target_disease_clean}**. "
                    "Exploratory mode active."
                )

        btn_search = st.button("🔎 Discover Combinations", type="primary", use_container_width=True, key="btn_discover")

        if btn_search:
            status_box = st.status("Discovering drug combinations and generating explanations...", expanded=True)
            with status_box:
                st.write("🔍 **Step 1:** Traversing PrimeKG graph for disease indications & target overlaps...")
                st.write("⚡ **Step 2:** Scoring candidate pairs with GNN model (fast forward pass)...")
                st.write("🧬 **Step 3:** Computing graph attributions, faithfulness & PubMed citations for top-5...")
                search_res = query_search(target_disease_clean, actual_cell_line, max_candidates=20, top_k=5)
                if search_res:
                    search_res["kg_only"] = not has_cell_line_context
                    status_box.update(label="✅ Combination Search & Explanations Complete!", state="complete", expanded=False)
                    st.session_state["search_result"] = search_res
                else:
                    status_box.update(label="❌ Search Failed — check disease name", state="error", expanded=True)

        s_res = st.session_state.get("search_result")
        if s_res:
            st.markdown("---")
            if s_res.get("kg_only"):
                st.markdown(
                    f"### 🏆 Top Candidate Drug Pairs for **{s_res['disease'].title()}** *(KG Structure Only)* "
                    f"*(Candidate Pool: {s_res.get('candidate_pool_size', 0)} drugs)*"
                )
            else:
                st.markdown(
                    f"### 🏆 Top Candidate Drug Pairs for **{s_res['disease'].title()}** @ **{s_res['cell_line']}** "
                    f"*(Candidate Pool: {s_res.get('candidate_pool_size', 0)} drugs)*"
                )

            results_list = s_res.get("results", [])
            for i, item in enumerate(results_list, 1):
                drug_a = item.get("drug_a_name", item.get("drug_a", ""))
                drug_b = item.get("drug_b_name", item.get("drug_b", ""))
                pair_tier = item.get("pair_tier_name", "both_direct")
                p_syn = item.get("p_synergy", 0.0)
                pred_cls = item.get("predicted_class", "synergy").upper()
                expl_txt = item.get("explanation_text", "")
                nec_delta = item.get("necessity_delta_pct", 0.0)
                suf_pct = item.get("sufficiency_retained_pct", 0.0)
                ood_caveat = item.get("high_confidence_caveat", False)

                # Tier Badge HTML
                if pair_tier == "both_direct":
                    tier_badge = '<span class="tier-badge-direct">🟢 Direct Evidence</span>'
                elif pair_tier == "mixed":
                    tier_badge = '<span class="tier-badge-mixed">🟡 Partial Evidence</span>'
                else:
                    tier_badge = '<span class="tier-badge-indirect">⚪ Speculative</span>'

                ood_badge = (
                    '<span class="ood-warning-badge">⚠️ Unusually high confidence — treat with extra scrutiny</span>'
                    if ood_caveat else ""
                )

                st.markdown(
                    f"""
                    <div class="search-card">
                        <div class="search-card-header">
                            <div>
                                <span class="search-card-title">#{i}. {drug_a} + {drug_b}</span>
                                &nbsp; {tier_badge} {ood_badge}
                            </div>
                            <div>
                                <span class="badge-title" style="font-size:1.1rem; color:#047857; font-weight:800;">{pred_cls}</span>
                                &nbsp; <span style="font-weight:700; color:#065f46; font-size:1.05rem;">{p_syn * 100:.1f}%</span>
                            </div>
                        </div>
                        <div class="explanation-box" style="border-left: 5px solid #10b981; margin-bottom: 10px;">
                            <p class="explanation-text" style="font-size: 1.05rem !important;">{expl_txt}</p>
                        </div>
                        <div class="faithfulness-caption" style="margin-bottom: 10px;">
                            🔬 <strong>Faithfulness:</strong> &nbsp; Necessity: <strong>{nec_delta:+.1f}%</strong> &nbsp;|&nbsp; Sufficiency: <strong>{suf_pct:.1f}%</strong>
                        </div>
                        {render_literature_html(item.get("supporting_literature", []))}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


if __name__ == "__main__":
    main()
