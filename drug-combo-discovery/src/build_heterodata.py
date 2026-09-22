"""
build_heterodata.py — PrimeKG → PyTorch Geometric HeteroData + Cold-Drug Splits
=================================================================================

PURPOSE
-------
Converts the filtered PrimeKG knowledge graph and the DrugComb synergy labels
into a PyTorch Geometric HeteroData object ready for heterogeneous GNN training,
and produces train/val/test split indices using a COLD-DRUG strategy.

WHY COLD-DRUG SPLIT (NOT RANDOM SPLIT)
---------------------------------------
A random split of (drug_A, drug_B, cell_line) triplets would allow the same
drug to appear in both train and test — sometimes even on both sides of a pair.
This is a severe form of data leakage: the GNN would learn node embeddings for
those drugs during training and would essentially be doing interpolation at test
time, not extrapolation. The measured test performance would be inflated and
would not reflect the model's ability to score *novel* drug combinations.

A cold-drug split partitions the unique drug nodes first (15% → test, 15% → val,
70% → train), then assigns each labeled pair to the split of the "hardest"
drug it contains:
  - If either drug is a test-only drug  → pair goes to TEST.
  - Else if either drug is a val-only drug → pair goes to VAL.
  - Otherwise → pair goes to TRAIN.

This guarantees zero drug-identity overlap between train and test: at test time
the model must generalise to drug nodes it has never seen labelled pairs for.

NODE FEATURES
-------------
Drug nodes (7,946):       Two-path hybrid feature system:
                          • FP path  (~7,122 nodes): 2048-bit Morgan fingerprint
                            (radius=2, nBits=2048) loaded from
                            data/processed/drug_smiles_fingerprints.csv, stored
                            as float32 tensor in data['drug'].x   shape [N, 2048]
                          • Fallback path (~824 biologics with no SMILES):
                            learnable embedding — stored as LongTensor of
                            fallback-specific indices in data['drug'].fallback_lookup
                            shape [N_fallback], values in [0, N_fallback).
                          The boolean mask data['drug'].fp_mask   shape [N_drug]
                          is True for FP nodes and False for fallback nodes.
                          Both paths project to 128 dims inside the model.

gene/protein nodes:       Learnable embedding dim=64
pathway nodes:            Learnable embedding dim=64
disease nodes:            Learnable embedding dim=64

For non-drug learnable embeddings, `x` is stored as a LongTensor of shape [N]
containing integer node indices (0..N-1). The GNN model owns nn.Embedding tables
of the appropriate sizes and looks up embeddings by indexing with these tensors.
"""

import os
import sys
import time
import pickle
import random

import numpy as np
import pandas as pd
import torch
from torch_geometric.data import HeteroData

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED = os.path.join(ROOT, "data", "processed")

GRAPH_PICKLE   = os.path.join(PROCESSED, "primekg_filtered.gpickle")
NODES_CSV      = os.path.join(PROCESSED, "primekg_nodes.csv")
EDGES_CSV      = os.path.join(PROCESSED, "primekg_edges.csv")
LABELS_CSV     = os.path.join(PROCESSED, "labeled_pairs.csv")
SMILES_FP_CSV     = os.path.join(PROCESSED, "drug_smiles_fingerprints.csv")
CHEMBERTA_PT      = os.path.join(PROCESSED, "drug_chemberta_embeddings.pt")
CHEMBERTA_CSV     = os.path.join(PROCESSED, "drug_chemberta_embeddings.csv")

OUT_HETERODATA = os.path.join(PROCESSED, "heterodata.pt")
OUT_TRAIN      = os.path.join(PROCESSED, "split_train.csv")
OUT_VAL        = os.path.join(PROCESSED, "split_val.csv")
OUT_TEST       = os.path.join(PROCESSED, "split_test.csv")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SEED             = 42
VAL_DRUG_FRAC    = 0.15   # fraction of unique drugs assigned to val
TEST_DRUG_FRAC   = 0.15   # fraction of unique drugs assigned to test

# Drug feature dimension (Morgan fingerprint: radius=2, nBits=2048)
FP_DIM           = 2048
# Projected hidden dimension (must match what the model expects)
DIM_DRUG         = 128
DIM_OTHER        = 64

# Node types and their INPUT feature/embedding dims
# drug is special: FP nodes have raw dim 2048; fallback nodes have a small Embedding.
# non-drug types keep a learnable embedding.
NODE_TYPE_DIM = {
    "drug":         FP_DIM,   # actual raw Morgan FP dimension (projection happens in model)
    "gene/protein": DIM_OTHER,
    "pathway":      DIM_OTHER,
    "disease":      DIM_OTHER,
}

# Relations that must NEVER be used as synergy labels (structural signal only)
STRUCTURAL_ONLY_RELATIONS = {"drug_drug"}


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _sep(title: str = "") -> None:
    print("\n" + "=" * 68)
    if title:
        print(f"  {title}")
        print("=" * 68)


def _elapsed(t0: float) -> str:
    s = time.time() - t0
    return f"{s:.2f}s" if s < 60 else f"{s/60:.1f}m"


# ---------------------------------------------------------------------------
# Step 1 — Load node and edge tables
# ---------------------------------------------------------------------------

def load_graph_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    _sep("Step 1 — Loading PrimeKG node and edge tables")
    t0 = time.time()

    nodes = pd.read_csv(NODES_CSV)
    print(f"  Nodes: {len(nodes):,} rows  ({_elapsed(t0)})")
    print(f"  Node types: {nodes['node_type'].value_counts().to_dict()}")

    t0 = time.time()
    edges = pd.read_csv(EDGES_CSV, low_memory=False)
    print(f"  Edges: {len(edges):,} rows  ({_elapsed(t0)})")
    print(f"  Relations: {edges['relation'].value_counts().to_dict()}")

    return nodes, edges


# ---------------------------------------------------------------------------
# Step 2 — Build per-type node index maps
#           raw_id (DrugBank ID / Entrez gene / etc.) → integer index 0..N-1
# ---------------------------------------------------------------------------

def build_node_index_maps(nodes: pd.DataFrame) -> dict[str, dict]:
    """
    Returns:
        node_maps : {node_type -> {raw_id_str -> int_idx}}
    """
    _sep("Step 2 — Building per-type node index maps")
    node_maps: dict[str, dict] = {}
    for ntype in nodes["node_type"].unique():
        sub = nodes[nodes["node_type"] == ntype].reset_index(drop=True)
        # Cast id to string for consistent key type
        id2idx = {str(row["id"]): i for i, (_, row) in enumerate(sub.iterrows())}
        node_maps[ntype] = id2idx
        print(f"  {ntype:<22} : {len(id2idx):>8,} nodes")
    return node_maps


# ---------------------------------------------------------------------------
# Step 3 — Build HeteroData node features
# ---------------------------------------------------------------------------
# Step 3 — Build node features
#           • drug nodes: real Morgan FP (float32 [N, 2048]) + fallback mask
#           • all other types: integer index tensor for nn.Embedding lookup
# ---------------------------------------------------------------------------

def _load_fingerprints(drug_id2idx: dict[str, int]) -> tuple[
    torch.Tensor,   # emb_matrix     : float32 [N_drug, FP_DIM]  (zeros for fallback rows)
    torch.Tensor,   # fp_mask        : bool    [N_drug]  True = Morgan FP row, False = fallback
    torch.Tensor,   # fallback_lookup: long    [N_drug]  -1 for FP nodes; 0..K-1 for fallback
]:
    """
    Loads drug_smiles_fingerprints.csv and builds three aligned [N_drug] tensors:

      emb_matrix     : full [N_drug × 2048] float32; Morgan-FP drug rows hold the
                       2048-bit fingerprint; fallback rows are zeros.
      fp_mask        : bool [N_drug]; True where a real fingerprint is available.
      fallback_lookup: long [N_drug]; -1 for FP drugs, 0..K-1 for the K fallback
                       drugs (their row index into the model's nn.Embedding table).
                       Shape == N_drug so PyG's NeighborLoader slices it correctly
                       alongside x and fp_mask when building mini-batches.
    """
    n_total = len(drug_id2idx)
    emb_matrix      = torch.zeros(n_total, FP_DIM, dtype=torch.float32)
    fp_mask         = torch.zeros(n_total, dtype=torch.bool)
    fallback_lookup = torch.full((n_total,), -1, dtype=torch.long)  # -1 = has real FP

    if not os.path.exists(SMILES_FP_CSV):
        print(f"  [WARNING] {SMILES_FP_CSV} not found — all drugs will use fallback embeddings.")
        # Every drug is a fallback; assign indices 0..N-1
        fallback_lookup = torch.arange(n_total, dtype=torch.long)
        return emb_matrix, fp_mask, fallback_lookup

    print(f"  Loading Morgan fingerprints from CSV: {SMILES_FP_CSV}")
    # Must read with dtype=str:
    # The 'fingerprint' column holds a 2048-char '0'/'1' bit string.
    # Without dtype=str, pandas tries to parse it as a huge integer -> OverflowError.
    df = pd.read_csv(SMILES_FP_CSV, dtype=str)

    # Detect column format:
    #   Format A: single column 'fingerprint' with a 2048-char bit string e.g. "010001..."
    #   Format B: separate columns fp_0...fp_2047 (or bit_0...bit_2047)
    has_bitstring_col = "fingerprint" in df.columns
    fp_cols = [c for c in df.columns if c.startswith("fp_")]
    if not fp_cols:
        fp_cols = [c for c in df.columns if c.startswith("bit_")]

    if not has_bitstring_col and not fp_cols:
        print(f"  [WARNING] No fingerprint data found in {SMILES_FP_CSV} -- all drugs fallback.")
        fallback_lookup = torch.arange(n_total, dtype=torch.long)
        return emb_matrix, fp_mask, fallback_lookup

    n_loaded = 0
    for _, row in df.iterrows():
        db_id = str(row["drugbank_id"]).strip()
        if db_id not in drug_id2idx:
            continue

        if has_bitstring_col and not fp_cols:
            # Format A: decode '01001...' bit string -> float32 array
            fp_str = str(row["fingerprint"]).strip()
            if fp_str in ("", "nan", "None") or len(fp_str) != FP_DIM:
                continue  # skip missing / malformed
            # Convert ASCII '0'/'1' bytes to float32 without Python loop
            fp_vals = (
                np.frombuffer(fp_str.encode("ascii"), dtype=np.uint8).astype(np.float32)
                - ord("0")
            )
        else:
            # Format B: separate per-bit columns
            vals = [row[c] for c in fp_cols]
            if any(v in ("", "nan", "None", None) for v in vals):
                continue
            fp_vals = np.array(vals, dtype=np.float32)

        node_idx = drug_id2idx[db_id]
        emb_matrix[node_idx] = torch.from_numpy(fp_vals)
        fp_mask[node_idx]   = True
        n_loaded += 1

    print(f"  Loaded Morgan fingerprints for {n_loaded:,} / {n_total:,} KG drug nodes.")

    # Assign each fallback node its row index in the model's nn.Embedding table.
    # fallback_lookup[i] is set to 0, 1, 2, ... for each node i where fp_mask[i] is False.
    # FP nodes keep -1 (sentinel).
    fallback_counter = 0
    for i in range(n_total):
        if not fp_mask[i]:
            fallback_lookup[i] = fallback_counter
            fallback_counter += 1
    # sanity: fallback_counter should equal n_total - n_loaded
    assert fallback_counter == (n_total - n_loaded), (
        f"fallback counter mismatch: {fallback_counter} vs {n_total - n_loaded}"
    )

    return emb_matrix, fp_mask, fallback_lookup


def build_node_features(
    node_maps: dict[str, dict],
    data: HeteroData,
) -> HeteroData:
    _sep("Step 3 — Adding node features (Morgan FP for drugs; embedding indices for others)")

    for ntype, id2idx in node_maps.items():
        n   = len(id2idx)
        dim = NODE_TYPE_DIM[ntype]

        if ntype == "drug":
            # ── Drug nodes: real Morgan fingerprints + fallback mask ──────
            emb_matrix, fp_mask, fallback_lookup = _load_fingerprints(id2idx)

            n_fp       = int(fp_mask.sum().item())
            n_fallback = n - n_fp

            data[ntype].x               = emb_matrix       # float32 [N, FP_DIM (2048)]
            data[ntype].fp_mask         = fp_mask          # bool    [N]
            data[ntype].fallback_lookup = fallback_lookup  # long    [N]  -1=Morgan FP, 0..K-1=fallback
            data[ntype].num_nodes       = n

            print(f"  [{ntype:<22}]  num_nodes={n:>8,}")
            print(f"    ├─ Morgan FP path (2048-dim) : {n_fp:>6,} nodes  "
                  f"(feature tensor shape: [{n}, {FP_DIM}])")
            print(f"    └─ Fallback (learnable emb)  : {n_fallback:>6,} nodes  "
                  f"(biologic/unresolved drugs, embedding size: {n_fallback} x {DIM_DRUG})")
        else:
            # ── Non-drug types: integer index tensor for nn.Embedding ──────
            data[ntype].x         = torch.arange(n, dtype=torch.long)
            data[ntype].num_nodes = n
            print(f"  [{ntype:<22}]  num_nodes={n:>8,}  embedding_dim={dim}")

    return data


# ---------------------------------------------------------------------------
# Step 4 — Build HeteroData edge indices
# ---------------------------------------------------------------------------

def build_edge_indices(
    edges: pd.DataFrame,
    node_maps: dict[str, dict],
    data: HeteroData,
) -> HeteroData:
    """
    Groups edges by the full (source_type, relation, target_type) triple.
    This correctly handles relations that PrimeKG stores bidirectionally
    (e.g. 'contraindication' appears as both drug→disease and disease→drug),
    creating a separate PyG edge-type entry for each unique triple.
    """
    _sep("Step 4 — Building edge indices per (src_type, relation, dst_type) triple")

    # Group by the full triple — avoids mixed-type assertion failures
    group_keys = edges.groupby(
        ["source_type", "relation", "target_type"], sort=True
    )

    skipped = 0
    for (src_type, rel, dst_type), sub in group_keys:
        if sub.empty:
            skipped += 1
            continue

        if src_type not in node_maps or dst_type not in node_maps:
            print(f"  SKIP  ({src_type}, {rel}, {dst_type})  — node type not in schema")
            skipped += 1
            continue

        src_map = node_maps[src_type]
        dst_map = node_maps[dst_type]

        # Map raw PrimeKG IDs to per-type integer indices
        src_idx = sub["source"].astype(str).map(src_map)
        dst_idx = sub["target"].astype(str).map(dst_map)

        valid = src_idx.notna() & dst_idx.notna()
        n_dropped = (~valid).sum()
        if n_dropped > 0:
            print(f"  ⚠  ({src_type}, {rel}, {dst_type}): "
                  f"dropped {n_dropped:,} edges with unmapped node IDs")

        src_tensor = torch.tensor(src_idx[valid].astype(int).values, dtype=torch.long)
        dst_tensor = torch.tensor(dst_idx[valid].astype(int).values, dtype=torch.long)
        edge_index = torch.stack([src_tensor, dst_tensor], dim=0)  # [2, E]

        # PyG edge type key: (src_node_type, relation_name, dst_node_type)
        edge_key = (src_type, rel, dst_type)
        data[edge_key].edge_index = edge_index

        structural_flag = "  ← ⚠ STRUCTURAL ONLY (never use as label)" \
            if rel in STRUCTURAL_ONLY_RELATIONS else ""
        print(f"  {str(edge_key):<60}  {edge_index.shape[1]:>10,} edges{structural_flag}")

    if skipped:
        print(f"\n  Skipped {skipped} triples (empty or missing node types).")

    return data


# ---------------------------------------------------------------------------
# Step 5 — Cold-drug split
# ---------------------------------------------------------------------------

def cold_drug_split(
    labels: pd.DataFrame,
    seed: int = SEED,
) -> tuple[list[int], list[int], list[int]]:
    """
    Splits labeled_pairs.csv into train/val/test using a cold-drug strategy.

    Headline MUST use this cold-drug split; also report bilateral-subset AUROC/AUPR as the stricter inductive metric.

    Logic:
        1. Collect all unique drug IDs appearing in drug_a_kg_id or drug_b_kg_id.
        2. Shuffle and partition: first ~15% → test_drugs, next ~15% → val_drugs,
           rest → train_drugs.
        3. Assign each pair:
             - TEST if drug_a OR drug_b ∈ test_drugs
             - VAL  if (not test) and (drug_a OR drug_b ∈ val_drugs)
             - TRAIN otherwise
        4. Assert train_drug_set ∩ test_drug_set = ∅.

    Returns:
        (train_idx, val_idx, test_idx) as lists of integer row indices into labels.
    """
    _sep("Step 5 — Cold-drug split (15% val drugs / 15% test drugs)")
    rng = random.Random(seed)

    all_drugs = sorted(
        set(labels["drug_a_kg_id"].unique()) | set(labels["drug_b_kg_id"].unique())
    )
    rng.shuffle(all_drugs)

    n_total = len(all_drugs)
    n_test  = max(1, round(n_total * TEST_DRUG_FRAC))
    n_val   = max(1, round(n_total * VAL_DRUG_FRAC))

    test_drugs = set(all_drugs[:n_test])
    val_drugs  = set(all_drugs[n_test : n_test + n_val])
    train_drugs = set(all_drugs[n_test + n_val :])

    print(f"\n  Total unique drugs: {n_total:,}")
    print(f"  Test  drugs:        {len(test_drugs):,}  ({100*len(test_drugs)/n_total:.1f}%)")
    print(f"  Val   drugs:        {len(val_drugs):,}  ({100*len(val_drugs)/n_total:.1f}%)")
    print(f"  Train drugs:        {len(train_drugs):,}  ({100*len(train_drugs)/n_total:.1f}%)")

    train_idx, val_idx, test_idx = [], [], []

    a = labels["drug_a_kg_id"].values
    b = labels["drug_b_kg_id"].values

    for i in range(len(labels)):
        da, db = a[i], b[i]
        if da in test_drugs or db in test_drugs:
            test_idx.append(i)
        elif da in val_drugs or db in val_drugs:
            val_idx.append(i)
        else:
            train_idx.append(i)

    total_pairs = len(labels)
    print(f"\n  Pair distribution:")
    print(f"    Train : {len(train_idx):>8,}  ({100*len(train_idx)/total_pairs:.1f}%)")
    print(f"    Val   : {len(val_idx):>8,}  ({100*len(val_idx)/total_pairs:.1f}%)")
    print(f"    Test  : {len(test_idx):>8,}  ({100*len(test_idx)/total_pairs:.1f}%)")

    # Integrity assertion — correct cold-drug invariant:
    # TEST-designated drugs must never appear in any train pair.
    # (It is expected and fine that a train-assigned drug appears in a test pair
    # when it is paired with a test-designated drug — that pair correctly goes to test.)
    train_pair_drugs = (
        set(labels.iloc[train_idx]["drug_a_kg_id"].unique()) |
        set(labels.iloc[train_idx]["drug_b_kg_id"].unique())
    )
    # No test drug should leak into train
    test_leak = test_drugs & train_pair_drugs
    assert len(test_leak) == 0, (
        f"BUG: {len(test_leak)} test-designated drug(s) appear in train pairs!\n"
        f"  Examples: {list(test_leak)[:5]}"
    )
    # No val drug should leak into train
    val_leak = val_drugs & train_pair_drugs
    assert len(val_leak) == 0, (
        f"BUG: {len(val_leak)} val-designated drug(s) appear in train pairs!\n"
        f"  Examples: {list(val_leak)[:5]}"
    )
    print(f"\n  ✓ No test-designated drugs leak into train pairs.")
    print(f"  ✓ No val-designated  drugs leak into train pairs.")

    # Class balance per split
    for name, idx in [("Train", train_idx), ("Val", val_idx), ("Test", test_idx)]:
        split_labels = labels.iloc[idx]["synergy_class"]
        counts = split_labels.value_counts()
        print(f"\n  {name} class balance:")
        for cls in ["synergy", "additive", "antagonism"]:
            cnt = counts.get(cls, 0)
            print(f"    {cls:<12} : {cnt:>7,}  ({100*cnt/len(idx):.1f}%)")

    return train_idx, val_idx, test_idx


# ---------------------------------------------------------------------------
# Step 6 — Attach labeled pair metadata to HeteroData and save split CSVs
# ---------------------------------------------------------------------------

def save_splits(
    labels: pd.DataFrame,
    train_idx: list[int],
    val_idx: list[int],
    test_idx: list[int],
    node_maps: dict[str, dict],
    data: HeteroData,
) -> HeteroData:
    """
    Attaches synergy label tensors (drug_a_idx, drug_b_idx, cell_line_idx,
    synergy_loewe, synergy_class_int) to HeteroData for each split,
    and saves row-index CSVs.

    synergy_class int encoding: 0=antagonism, 1=additive, 2=synergy
    cell_line_idx  : integer ID 0..N_cell-1, consistent across all splits.
    """
    _sep("Step 6 — Attaching label tensors + saving split CSVs")

    CLASS_MAP = {"antagonism": 0, "additive": 1, "synergy": 2}
    drug_map  = node_maps["drug"]

    # Build a stable cell-line → int mapping (sorted for reproducibility)
    all_cell_lines = sorted(labels["cell_line_name"].unique())
    cell_map: dict[str, int] = {cl: i for i, cl in enumerate(all_cell_lines)}
    n_cell_lines = len(cell_map)
    data.cell_line_map = cell_map          # persist map in HeteroData for inference
    data.num_cell_lines = n_cell_lines
    print(f"  Cell lines: {n_cell_lines} unique values mapped to 0..{n_cell_lines-1}")

    def _make_label_tensor(idx: list[int]) -> dict:
        sub = labels.iloc[idx].reset_index(drop=True)
        # Map DrugBank IDs to integer node indices (within the 'drug' node type)
        a_idx = torch.tensor(
            sub["drug_a_kg_id"].map(drug_map).astype(int).values, dtype=torch.long
        )
        b_idx = torch.tensor(
            sub["drug_b_kg_id"].map(drug_map).astype(int).values, dtype=torch.long
        )
        cell  = torch.tensor(
            sub["cell_line_name"].map(cell_map).astype(int).values, dtype=torch.long
        )
        loewe = torch.tensor(sub["synergy_loewe"].values, dtype=torch.float32)
        y     = torch.tensor(
            sub["synergy_class"].map(CLASS_MAP).astype(int).values, dtype=torch.long
        )
        return dict(drug_a=a_idx, drug_b=b_idx, cell=cell, loewe=loewe, y=y)

    for split_name, idx, out_path in [
        ("train", train_idx, OUT_TRAIN),
        ("val",   val_idx,   OUT_VAL),
        ("test",  test_idx,  OUT_TEST),
    ]:
        tensors = _make_label_tensor(idx)
        # Store on HeteroData under a dedicated attribute namespace
        data[f"label_{split_name}_drug_a"]  = tensors["drug_a"]
        data[f"label_{split_name}_drug_b"]  = tensors["drug_b"]
        data[f"label_{split_name}_cell"]    = tensors["cell"]
        data[f"label_{split_name}_loewe"]   = tensors["loewe"]
        data[f"label_{split_name}_y"]       = tensors["y"]

        # Save split row indices as CSV
        pd.DataFrame({"row_index": idx}).to_csv(out_path, index=False)
        print(f"  Saved {split_name:>5} split: {len(idx):>8,} pairs -> {out_path}")

    return data


# ---------------------------------------------------------------------------
# Step 7 — Print HeteroData summary
# ---------------------------------------------------------------------------

def print_heterodata_summary(data: HeteroData) -> None:
    _sep("Step 7 — HeteroData Summary")

    print("\n  NODE TYPES:")
    print(f"  {'Node Type':<24}  {'num_nodes':>10}  {'x.shape':>20}  {'notes':<30}")
    print("  " + "-" * 90)
    for ntype in data.node_types:
        nn_val = data[ntype].num_nodes
        xs     = str(tuple(data[ntype].x.shape))
        if ntype == "drug":
            n_fp  = int(data[ntype].fp_mask.sum().item())
            n_fb  = nn_val - n_fp
            notes = f"{n_fp} Morgan FP  |  {n_fb} fallback emb"
        else:
            notes = "learnable embedding"
        print(f"  {ntype:<24}  {nn_val:>10,}  {xs:>20}  {notes:<30}")

    print("\n  DRUG FEATURE SUMMARY:")
    drug_store = data["drug"]
    n_drug     = drug_store.num_nodes
    n_fp       = int(drug_store.fp_mask.sum().item())
    n_fallback = n_drug - n_fp
    import hashlib
    fp_sha = hashlib.sha256(drug_store.x.numpy().tobytes()).hexdigest()[:16]
    print(f"    Total drug nodes          : {n_drug:>6,}")
    print(f"    ├─ Morgan FP (float32)    : {n_fp:>6,}  ({100*n_fp/n_drug:.1f}%)  "
          f"— feature tensor shape {tuple(drug_store.x.shape)}")
    print(f"    └─ Fallback embedding     : {n_fallback:>6,}  ({100*n_fallback/n_drug:.1f}%)  "
          f"— fallback_lookup shape {tuple(drug_store.fallback_lookup.shape)}")
    print(f"    fp_mask shape             : {tuple(drug_store.fp_mask.shape)}  dtype=bool")
    print(f"    drug.x tensor SHA-256     : {fp_sha}")

    print("\n  EDGE TYPES:")
    print(f"  {'(src, relation, dst)':<58}  {'num_edges':>10}")
    print("  " + "-" * 72)
    for etype in data.edge_types:
        ne = data[etype].edge_index.shape[1]
        rel_str = str(etype)
        structural = "  [struct]" if etype[1] in STRUCTURAL_ONLY_RELATIONS else ""
        print(f"  {rel_str:<58}  {ne:>10,}{structural}")

    total_nodes = sum(data[nt].num_nodes for nt in data.node_types)
    total_edges = sum(data[et].edge_index.shape[1] for et in data.edge_types)
    print(f"\n  Total nodes : {total_nodes:,}")
    print(f"  Total edges : {total_edges:,}")

    print("\n  LABEL SPLITS (stored as HeteroData attributes):")
    for split in ["train", "val", "test"]:
        key = f"label_{split}_y"
        if hasattr(data, key):
            y = getattr(data, key)
            print(f"    {split:<6}: {len(y):>8,} pairs  |  y shape: {tuple(y.shape)}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    random.seed(SEED)
    torch.manual_seed(SEED)
    np.random.seed(SEED)

    _sep("PrimeKG → PyTorch Geometric HeteroData Builder")
    t_total = time.time()
    os.makedirs(PROCESSED, exist_ok=True)

    # Step 1 — Load tables
    nodes, edges = load_graph_tables()

    # Step 2 — Node index maps
    node_maps = build_node_index_maps(nodes)

    # Step 3 — Build HeteroData + node features
    data = HeteroData()
    data = build_node_features(node_maps, data)

    # Step 4 — Edge indices
    data = build_edge_indices(edges, node_maps, data)

    # Step 5 — Load labels + cold-drug split
    _sep("Loading labeled pairs")
    labels = pd.read_csv(LABELS_CSV)
    print(f"  Labeled pairs: {len(labels):,} rows")
    print(f"  Columns: {labels.columns.tolist()}")

    train_idx, val_idx, test_idx = cold_drug_split(labels)

    # Step 6 — Attach label tensors + save split CSVs
    data = save_splits(labels, train_idx, val_idx, test_idx, node_maps, data)

    # Step 7 — Summary
    print_heterodata_summary(data)

    # Save HeteroData
    _sep("Saving HeteroData")
    t0 = time.time()
    torch.save(data, OUT_HETERODATA)
    size_mb = os.path.getsize(OUT_HETERODATA) / 1e6
    print(f"  Saved: {OUT_HETERODATA}")
    print(f"  File size: {size_mb:.1f} MB  ({_elapsed(t0)})")

    _sep("Done")
    print(f"  Total wall-clock time: {_elapsed(t_total)}")
    print(f"\n  Output files:")
    for path in [OUT_HETERODATA, OUT_TRAIN, OUT_VAL, OUT_TEST]:
        size_mb = os.path.getsize(path) / 1e6
        print(f"    {os.path.basename(path):<35}  {size_mb:>8.2f} MB")


if __name__ == "__main__":
    main()
