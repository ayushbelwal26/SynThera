"""
src/target_features.py
======================
Feature Engineering for Run C: Hand-crafted target-complementarity features.

Features for each drug pair (A, B) using ONLY PrimeKG relations in heterodata.pt:
1. target_shortest_path: shortest-path distance in PPI between A's and B's target proteins
   (min over all target pairs, capped at 6.0 for disconnected).
2. disconnected: binary flag (1.0 if disconnected or either drug has 0 targets, 0.0 otherwise).
3. target_jaccard: Jaccard similarity of A's and B's target proteins' direct PPI neighborhoods.
4. shared_pathway_or_disease: binary flag (1.0 if A's and B's targets share >= 1 pathway or disease).

Normalized using TRAIN-set statistics only.
"""

import os
import sys
import time
from collections import defaultdict
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import shortest_path
import torch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED = os.path.join(ROOT, "data", "processed")
HETERODATA_PATH = os.path.join(PROCESSED, "heterodata.pt")
OUT_PARQUET = os.path.join(PROCESSED, "target_complementarity_features.parquet")
OUT_TENSOR_PT = os.path.join(PROCESSED, "target_complementarity_lookup.pt")


def compute_target_features():
    t0 = time.time()
    print("=" * 80)
    print("  STEP 1: PRECOMPUTING TARGET-COMPLEMENTARITY FEATURES")
    print("=" * 80)

    print("Loading heterodata.pt...")
    heterodata = torch.load(HETERODATA_PATH, weights_only=False)

    # 1. Build PPI adjacency
    ppi_edge_index = heterodata["gene/protein", "protein_protein", "gene/protein"].edge_index.numpy()
    n_proteins = heterodata["gene/protein"].num_nodes
    ppi_data = np.ones(ppi_edge_index.shape[1], dtype=np.float32)
    ppi_adj = csr_matrix((ppi_data, (ppi_edge_index[0], ppi_edge_index[1])), shape=(n_proteins, n_proteins))

    # PPI adjacency neighbor sets for Jaccard
    print("Building direct PPI neighbor sets for all proteins...")
    ppi_neighbors = defaultdict(set)
    for u, v in zip(ppi_edge_index[0], ppi_edge_index[1]):
        u, v = int(u), int(v)
        ppi_neighbors[u].add(v)
        ppi_neighbors[v].add(u)

    # 2. Drug-target mappings
    dt_edge_index = heterodata["drug", "drug_protein", "gene/protein"].edge_index.numpy()
    drug_to_targets = defaultdict(set)
    for d, p in zip(dt_edge_index[0], dt_edge_index[1]):
        drug_to_targets[int(d)].add(int(p))

    # 3. Protein to pathway and disease mappings
    prot_to_pathways = defaultdict(set)
    if ("gene/protein", "pathway_protein", "pathway") in heterodata.edge_types:
        pw_edges = heterodata["gene/protein", "pathway_protein", "pathway"].edge_index.numpy()
        for p, pw in zip(pw_edges[0], pw_edges[1]):
            prot_to_pathways[int(p)].add(int(pw))

    prot_to_diseases = defaultdict(set)
    if ("gene/protein", "disease_protein", "disease") in heterodata.edge_types:
        dis_edges = heterodata["gene/protein", "disease_protein", "disease"].edge_index.numpy()
        for p, dis in zip(dis_edges[0], dis_edges[1]):
            prot_to_diseases[int(p)].add(int(dis))

    # All unique target proteins
    all_target_proteins = sorted(list(set(dt_edge_index[1])))
    prot_to_row = {p: i for i, p in enumerate(all_target_proteins)}
    print(f"Total target proteins: {len(all_target_proteins):,} / {n_proteins:,}")

    # Compute all-pairs shortest paths from all target proteins
    print("Computing shortest paths in PPI subgraph for target proteins...")
    t_sp0 = time.time()
    sp_matrix = shortest_path(ppi_adj, directed=False, indices=all_target_proteins)
    print(f"Shortest paths computed in {time.time() - t_sp0:.2f}s (matrix shape {sp_matrix.shape})")

    # Drugs that appear in any labeled pair
    train_a = heterodata.label_train_drug_a.numpy()
    train_b = heterodata.label_train_drug_b.numpy()
    val_a = heterodata.label_val_drug_a.numpy()
    val_b = heterodata.label_val_drug_b.numpy()
    test_a = heterodata.label_test_drug_a.numpy()
    test_b = heterodata.label_test_drug_b.numpy()

    all_pairs_a = np.concatenate([train_a, val_a, test_a])
    all_pairs_b = np.concatenate([train_b, val_b, test_b])
    unique_pairs = set(zip(all_pairs_a, all_pairs_b))
    print(f"Unique directed drug pairs across all splits: {len(unique_pairs):,}")

    # Pre-aggregate drug-level target neighborhood and pathway/disease sets
    all_unique_drugs = sorted(list(set(all_pairs_a) | set(all_pairs_b)))
    drug_to_compact = {d: i for i, d in enumerate(all_unique_drugs)}
    n_drugs = len(all_unique_drugs)
    print(f"Unique drugs across all splits: {n_drugs:,}")

    drug_ppi_interactors = {}
    drug_pathways_diseases = {}
    for d in all_unique_drugs:
        targets = drug_to_targets.get(d, set())
        # Union of direct PPI interactors
        interactors = set()
        for t in targets:
            interactors.update(ppi_neighbors.get(t, set()))
            interactors.add(t)  # include target itself
        drug_ppi_interactors[d] = interactors

        # Union of pathways and diseases
        pw_dis = set()
        for t in targets:
            for pw in prot_to_pathways.get(t, set()):
                pw_dis.add(("pathway", pw))
            for dis in prot_to_diseases.get(t, set()):
                pw_dis.add(("disease", dis))
        drug_pathways_diseases[d] = pw_dis

    # Compute features for each unique pair
    print("Computing 4 target-complementarity features for all unique drug pairs...")
    pair_features = {}
    
    for a, b in unique_pairs:
        targets_a = drug_to_targets.get(a, set())
        targets_b = drug_to_targets.get(b, set())

        # 1 & 2: Shortest path and Disconnected flag
        if not targets_a or not targets_b:
            sp_dist = 6.0
            disc = 1.0
        else:
            min_d = np.inf
            for ta in targets_a:
                row_idx = prot_to_row[ta]
                for tb in targets_b:
                    d_val = sp_matrix[row_idx, tb]
                    if d_val < min_d:
                        min_d = d_val
            if np.isinf(min_d):
                sp_dist = 6.0
                disc = 1.0
            else:
                sp_dist = float(min(min_d, 6.0))
                disc = 0.0

        # 3: Target Jaccard similarity of PPI neighborhoods
        ia = drug_ppi_interactors[a]
        ib = drug_ppi_interactors[b]
        union_i = ia | ib
        if not union_i:
            jaccard = 0.0
        else:
            jaccard = float(len(ia & ib) / len(union_i))

        # 4: Shared pathway or disease flag
        sa = drug_pathways_diseases[a]
        sb = drug_pathways_diseases[b]
        shared_flag = 1.0 if len(sa & sb) > 0 else 0.0

        pair_features[(a, b)] = (sp_dist, disc, jaccard, shared_flag)
        # Symmetrical pair
        pair_features[(b, a)] = (sp_dist, disc, jaccard, shared_flag)

    t_precompute = time.time() - t0
    print(f"Precomputation for all {len(pair_features):,} directed pairs completed in {t_precompute:.2f}s ({t_precompute/60:.2f} min)")

    # 4. Compute TRAIN-set statistics for normalization
    print("\nComputing normalization statistics using TRAIN-set pairs only...")
    train_feats = np.array([pair_features[(a, b)] for a, b in zip(train_a, train_b)], dtype=np.float32)
    train_mean = np.mean(train_feats, axis=0)
    train_std = np.std(train_feats, axis=0)
    # Avoid zero division
    train_std[train_std < 1e-6] = 1.0

    print("Train Set Statistics (N = {:,}):".format(len(train_a)))
    names = ["target_shortest_path", "disconnected", "target_jaccard", "shared_pathway_or_disease"]
    for i, name in enumerate(names):
        print(f"  {name:<28}: mean = {train_mean[i]:.4f}, std = {train_std[i]:.4f}")

    # Build 2D lookup tensor of shape [n_drugs, n_drugs, 4] for compact indexed lookup
    # compact index maps drug global id -> compact id
    lookup_matrix = np.zeros((n_drugs, n_drugs, 4), dtype=np.float32)
    default_feat = np.array([6.0, 1.0, 0.0, 0.0], dtype=np.float32)
    default_norm = (default_feat - train_mean) / train_std

    for (a, b), raw_f in pair_features.items():
        if a in drug_to_compact and b in drug_to_compact:
            idx_a = drug_to_compact[a]
            idx_b = drug_to_compact[b]
            norm_f = (np.array(raw_f, dtype=np.float32) - train_mean) / train_std
            lookup_matrix[idx_a, idx_b] = norm_f

    # Create global drug lookup array [7946] mapping global_id -> compact_id
    n_global_drugs = heterodata["drug"].num_nodes
    global_to_compact = np.full((n_global_drugs,), -1, dtype=np.int64)
    for g_id, c_id in drug_to_compact.items():
        global_to_compact[g_id] = c_id

    # Save to disk
    torch.save({
        "lookup_matrix": torch.from_numpy(lookup_matrix),
        "global_to_compact": torch.from_numpy(global_to_compact),
        "default_norm": torch.from_numpy(default_norm),
        "train_mean": torch.from_numpy(train_mean),
        "train_std": torch.from_numpy(train_std),
        "feature_names": names,
        "precompute_seconds": t_precompute,
    }, OUT_TENSOR_PT)
    print(f"Saved lookup tensor to: {OUT_TENSOR_PT} ({os.path.getsize(OUT_TENSOR_PT)/1e6:.2f} MB)")

    # Also save DataFrame / parquet for auditing
    df_rows = []
    for (a, b), f in pair_features.items():
        df_rows.append({
            "drug_a": a,
            "drug_b": b,
            "target_shortest_path": f[0],
            "disconnected": f[1],
            "target_jaccard": f[2],
            "shared_pathway_or_disease": f[3],
        })
    df_feats = pd.DataFrame(df_rows)
    df_feats.to_parquet(OUT_PARQUET, index=False)
    print(f"Saved parquet to: {OUT_PARQUET} ({os.path.getsize(OUT_PARQUET)/1e6:.2f} MB)")

    return {
        "precompute_seconds": t_precompute,
        "train_mean": train_mean,
        "train_std": train_std,
        "n_pairs": len(pair_features),
    }


if __name__ == "__main__":
    compute_target_features()
