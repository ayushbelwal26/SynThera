"""
build_kg.py — Filtered PrimeKG Knowledge Graph Builder
=======================================================

PURPOSE
-------
Loads the raw PrimeKG edge list, filters it down to the biomedical
sub-schema relevant to drug-combination discovery, builds a NetworkX
MultiDiGraph, and saves outputs for downstream GNN training.

⚠️  CRITICAL LEAKAGE WARNING — drug_drug RELATION  ⚠️
------------------------------------------------------
PrimeKG contains a 'drug_drug' relation (display name: 'synergistic
interaction').  This relation is RETAINED in the filtered graph as a
STRUCTURAL SIGNAL ONLY — it encodes known drug-drug interaction topology
from DrugBank and other KB sources, and that topology is useful context
for the GNN.

However, this relation MUST NEVER be used as a training label or
prediction target.  Our actual synergy label is DrugComb's
'synergy_loewe' score, which is experimentally derived and represents a
quantitative, cell-line-specific synergy measurement.  PrimeKG's
drug_drug edges represent a qualitatively different concept (known
pharmacological interactions / co-occurrence in KB) and are NOT a
superset or proxy of experimental synergy.

Using drug_drug edges as labels — or allowing them to leak into the
message-passing neighbourhood during label-generation — would
constitute data leakage and will produce an inflated, non-reproducible
model.

Concretely: when you construct the training, validation, and test
splits for drug-pair synergy prediction, mask out (or remove) all
drug_drug edges between any (drug_A, drug_B) pair whose synergy_loewe
label is being used for evaluation, to prevent the GNN from trivially
memorising KB co-occurrence as a proxy label.
"""

import os
import sys
import time
import pickle

import pandas as pd
import networkx as nx

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(ROOT, "data", "raw")
PROCESSED_DIR = os.path.join(ROOT, "data", "processed")

PRIMEKG_RAW = os.path.join(RAW_DIR, "primekg_raw.csv")

OUT_GRAPH = os.path.join(PROCESSED_DIR, "primekg_filtered.gpickle")
OUT_NODES = os.path.join(PROCESSED_DIR, "primekg_nodes.csv")
OUT_EDGES = os.path.join(PROCESSED_DIR, "primekg_edges.csv")
OUT_DRUGS = os.path.join(PROCESSED_DIR, "primekg_drugs.csv")

# ---------------------------------------------------------------------------
# Schema configuration — single place to change if schema evolves
# ---------------------------------------------------------------------------
KEEP_NODE_TYPES = {"drug", "gene/protein", "pathway", "disease"}

KEEP_RELATIONS = {
    "drug_protein",      # drug → protein target/carrier/enzyme/transporter
    "drug_effect",       # drug → phenotype/side-effect
    "protein_protein",   # PPI
    "pathway_protein",   # gene membership in pathway
    "disease_protein",   # disease–gene association
    "disease_disease",   # disease ontology hierarchy
    "indication",        # drug indicated for disease
    "contraindication",  # drug contraindicated for disease
    "off-label use",     # drug used off-label for disease
    # ⚠️  LEAKAGE WARNING — see module docstring.
    # drug_drug is kept as STRUCTURAL SIGNAL ONLY.
    # It must NEVER be used as a training label or prediction target.
    "drug_drug",
}

# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _sep(title: str = "") -> None:
    print("\n" + "=" * 68)
    if title:
        print(f"  {title}")
        print("=" * 68)


def _elapsed(t0: float) -> str:
    secs = time.time() - t0
    return f"{secs:.1f}s" if secs < 60 else f"{secs / 60:.1f}m"


# ---------------------------------------------------------------------------
# Step 1 — Load raw PrimeKG
# ---------------------------------------------------------------------------

def load_primekg(path: str) -> pd.DataFrame:
    _sep("Step 1 — Loading raw PrimeKG")
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"PrimeKG raw file not found at:\n  {path}\n"
            "Download it from https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/IXA7BM"
        )
    t0 = time.time()
    print(f"  Reading: {path}")
    df = pd.read_csv(path, low_memory=False)
    print(f"  Loaded:  {len(df):,} edges x {df.shape[1]} columns in {_elapsed(t0)}")
    print(f"  Columns: {df.columns.tolist()}")
    return df


# ---------------------------------------------------------------------------
# Step 2 & 3 — Filter nodes and edges
# ---------------------------------------------------------------------------

def filter_graph(df: pd.DataFrame) -> pd.DataFrame:
    _sep("Step 2 & 3 — Filtering node types and edge relations")
    n_raw = len(df)

    # 2. Keep only rows where BOTH endpoints are in the allowed node type set
    both_kept = df["x_type"].isin(KEEP_NODE_TYPES) & df["y_type"].isin(KEEP_NODE_TYPES)
    df_node = df[both_kept].copy()
    print(f"  After node-type filter:     {len(df_node):,} / {n_raw:,} edges retained "
          f"({100 * len(df_node) / n_raw:.1f}%)")

    # 3. Keep only the target relations
    df_edge = df_node[df_node["relation"].isin(KEEP_RELATIONS)].copy()
    print(f"  After relation filter:      {len(df_edge):,} / {len(df_node):,} edges retained "
          f"({100 * len(df_edge) / len(df_node):.1f}%)")

    # Sanity-check: make sure no unexpected relations slipped through
    found_rels = set(df_edge["relation"].unique())
    unexpected = found_rels - KEEP_RELATIONS
    if unexpected:
        print(f"  ⚠ Unexpected relations present (review KEEP_RELATIONS): {unexpected}")
    else:
        print(f"  ✓ All retained relations match KEEP_RELATIONS exactly.")

    return df_edge


# ---------------------------------------------------------------------------
# Step 4 — Build NetworkX MultiDiGraph
# ---------------------------------------------------------------------------

def build_graph(df: pd.DataFrame) -> nx.MultiDiGraph:
    _sep("Step 4 — Building NetworkX MultiDiGraph")
    t0 = time.time()
    G = nx.MultiDiGraph()

    print(f"  Adding nodes ...")
    # Collect all unique nodes from both x and y sides
    x_nodes = df[["x_id", "x_name", "x_type", "x_source"]].rename(
        columns={"x_id": "id", "x_name": "name", "x_type": "node_type", "x_source": "source"}
    )
    y_nodes = df[["y_id", "y_name", "y_type", "y_source"]].rename(
        columns={"y_id": "id", "y_name": "name", "y_type": "node_type", "y_source": "source"}
    )
    all_nodes = (
        pd.concat([x_nodes, y_nodes])
        .drop_duplicates(subset=["id"])
        .reset_index(drop=True)
    )

    for _, row in all_nodes.iterrows():
        G.add_node(
            row["id"],
            name=row["name"],
            node_type=row["node_type"],
            source=row["source"],
        )

    print(f"  Adding edges ...")
    for _, row in df.iterrows():
        # ⚠️  drug_drug is added as a structural edge only — NOT a label.
        #    See module-level docstring for the full leakage warning.
        G.add_edge(
            row["x_id"],
            row["y_id"],
            relation=row["relation"],
            display_relation=row["display_relation"],
        )

    print(f"  Graph built in {_elapsed(t0)}: "
          f"{G.number_of_nodes():,} nodes, {G.number_of_edges():,} edges")
    return G, all_nodes


# ---------------------------------------------------------------------------
# Step 5 — Summary statistics
# ---------------------------------------------------------------------------

def print_summary(G: nx.MultiDiGraph, df: pd.DataFrame, all_nodes: pd.DataFrame) -> None:
    _sep("Step 5 — Filtered Graph Summary")

    print("\n  Node counts by type:")
    type_counts = all_nodes["node_type"].value_counts()
    for ntype, cnt in type_counts.items():
        print(f"    {ntype:<22} : {cnt:>8,} nodes")
    print(f"    {'TOTAL':<22} : {all_nodes.shape[0]:>8,} nodes")

    print("\n  Edge counts by relation (retained):")
    rel_counts = df["relation"].value_counts()
    for rel, cnt in rel_counts.items():
        warning = "  ← ⚠ STRUCTURAL ONLY — not a synergy label" if rel == "drug_drug" else ""
        print(f"    {rel:<28} : {cnt:>9,} edges{warning}")
    print(f"    {'TOTAL':<28} : {len(df):>9,} edges")


# ---------------------------------------------------------------------------
# Step 6 — Save graph, node list, edge list
# ---------------------------------------------------------------------------

def save_outputs(G: nx.MultiDiGraph, df: pd.DataFrame, all_nodes: pd.DataFrame) -> None:
    _sep("Step 6 — Saving outputs to data/processed/")
    os.makedirs(PROCESSED_DIR, exist_ok=True)

    # 6a. Save NetworkX graph as gpickle
    t0 = time.time()
    with open(OUT_GRAPH, "wb") as f:
        pickle.dump(G, f, protocol=pickle.HIGHEST_PROTOCOL)
    print(f"  Saved graph pickle:   {OUT_GRAPH}  ({_elapsed(t0)})")

    # 6b. Save node list CSV
    t0 = time.time()
    all_nodes[["id", "name", "node_type", "source"]].to_csv(OUT_NODES, index=False)
    print(f"  Saved node list:      {OUT_NODES}  ({all_nodes.shape[0]:,} rows, {_elapsed(t0)})")

    # 6c. Save edge list CSV
    t0 = time.time()
    edge_out = df[["x_id", "y_id", "relation", "display_relation", "x_name", "y_name",
                   "x_type", "y_type"]].copy()
    edge_out.columns = ["source", "target", "relation", "display_relation",
                        "source_name", "target_name", "source_type", "target_type"]
    edge_out.to_csv(OUT_EDGES, index=False)
    print(f"  Saved edge list:      {OUT_EDGES}  ({edge_out.shape[0]:,} rows, {_elapsed(t0)})")


# ---------------------------------------------------------------------------
# Step 7 — Save drug lookup table for name-matching against DrugComb
# ---------------------------------------------------------------------------

def save_drug_lookup(all_nodes: pd.DataFrame) -> None:
    _sep("Step 7 — Saving drug node lookup table")
    drug_nodes = (
        all_nodes[all_nodes["node_type"] == "drug"][["id", "name", "source"]]
        .drop_duplicates(subset=["id"])
        .sort_values("id")
        .reset_index(drop=True)
    )
    drug_nodes.columns = ["drugbank_id", "drug_name", "source"]
    drug_nodes.to_csv(OUT_DRUGS, index=False)
    print(f"  Saved drug lookup:    {OUT_DRUGS}  ({len(drug_nodes):,} unique drugs)")
    print(f"\n  Sample (first 10):")
    print(drug_nodes.head(10).to_string(index=False))
    print(f"\n  NOTE: These drug names will be used for fuzzy/exact name-matching")
    print(f"  against DrugComb's drug_row / drug_col string identifiers in the")
    print(f"  next preprocessing phase.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    _sep("PrimeKG Knowledge Graph Builder")
    print(f"  Root directory : {ROOT}")
    print(f"  Input          : {PRIMEKG_RAW}")
    print(f"  Output dir     : {PROCESSED_DIR}")
    print(f"\n  Kept node types : {sorted(KEEP_NODE_TYPES)}")
    print(f"  Kept relations  : {sorted(KEEP_RELATIONS)}")

    t_total = time.time()

    df_raw = load_primekg(PRIMEKG_RAW)
    df_filtered = filter_graph(df_raw)

    # Release raw dataframe memory before building graph
    del df_raw

    G, all_nodes = build_graph(df_filtered)
    print_summary(G, df_filtered, all_nodes)
    save_outputs(G, df_filtered, all_nodes)
    save_drug_lookup(all_nodes)

    _sep("Done")
    print(f"  Total wall-clock time: {_elapsed(t_total)}")
    print(f"\n  Output files:")
    for path in [OUT_GRAPH, OUT_NODES, OUT_EDGES, OUT_DRUGS]:
        size_mb = os.path.getsize(path) / 1e6
        print(f"    {os.path.basename(path):<35} {size_mb:>8.1f} MB")


if __name__ == "__main__":
    main()
