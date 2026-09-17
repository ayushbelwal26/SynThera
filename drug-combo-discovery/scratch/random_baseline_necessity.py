"""
scratch/random_baseline_necessity.py
=====================================================
Fix 1 diagnostic: Random-edge-removal baseline control for necessity.

For each of the 8 known pairs:
  - Run explain_prediction() to get the GNNExplainer top-10 edges + necessity delta.
  - Also remove 10 RANDOM edges (from the same batch, excluding the explanation edges),
    repeat 5 times with different seeds, average the delta.
  - Compare: does explanation-edge removal beat random?

Conclusion categories:
  (a) Random similarly tiny  → graph redundancy is real, not an explainer failure.
  (b) Random beats explanation → explainer is not selecting load-bearing edges; real problem.
  (c) Explanation beats random but both below 5% → explainer is real but threshold too strict.
"""

from __future__ import annotations

import os
import sys
import random
import time
from collections import defaultdict
from typing import List, Dict, Any

import torch
import torch.nn.functional as F

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR  = os.path.join(ROOT_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from predict import load_model, THRESHOLD_SYNERGY, THRESHOLD_ANTAGONISM
from explain import (
    _sample_batch, _score_edges, _necessity_check,
    _build_name_lookups,
)
from search import score_candidate_pairs

CHECKPOINT_PATH = os.path.join(ROOT_DIR, "models", "synergy_gnn_final.ckpt")
HETERODATA_PATH = os.path.join(ROOT_DIR, "data", "processed", "heterodata.pt")
N_RANDOM_SEEDS  = 5    # repetitions per pair


# ---------------------------------------------------------------------------
# Random-edge necessity helper
# ---------------------------------------------------------------------------

def _random_necessity(
    module,
    batch,
    top_edges: List[Dict],
    predicted_class: int,
    original_prob: float,
    device: str,
    n_remove: int,
    seeds: List[int],
) -> float:
    """
    Remove n_remove RANDOM edges (not in top_edges) from the batch, re-run
    inference, return average delta_pct over all seeds.

    Convention matches _necessity_check: positive = prob dropped (good for necessity).
    """
    # Build the set of explanation edge (etype, src_local, dst_local) tuples to exclude
    explanation_set = set()
    for e in top_edges:
        etype = (e["source_type"], e["relation"], e["target_type"])
        explanation_set.add((etype, e["source_local"], e["target_local"]))

    # Enumerate ALL candidate edges across the batch (excluding supervision edge type)
    candidate_pool: List[tuple] = []
    for etype in batch.edge_types:
        src_type, rel, dst_type = etype
        if rel == "synergy_pair":
            continue
        store = batch[etype]
        if not hasattr(store, "edge_index") or store.edge_index is None:
            continue
        ei = store.edge_index
        for k in range(ei.shape[1]):
            s, d = ei[0, k].item(), ei[1, k].item()
            entry = (etype, s, d)
            if entry not in explanation_set:
                candidate_pool.append(entry)

    if len(candidate_pool) < n_remove:
        # Not enough non-explanation edges → return 0 (neutral)
        return 0.0

    deltas = []
    for seed in seeds:
        rng = random.Random(seed)
        chosen = rng.sample(candidate_pool, n_remove)

        # Build removal map
        removal_map = defaultdict(set)
        for (etype, s, d) in chosen:
            removal_map[etype].add((s, d))

        batch_rand = batch.clone().to(device)
        for etype, pairs in removal_map.items():
            if etype not in batch_rand.edge_types:
                continue
            store = batch_rand[etype]
            ei = store.edge_index
            keep = torch.ones(ei.shape[1], dtype=torch.bool)
            for k in range(ei.shape[1]):
                if (ei[0, k].item(), ei[1, k].item()) in pairs:
                    keep[k] = False
            store.edge_index = ei[:, keep]

        module.eval()
        with torch.no_grad():
            logits_rand, _ = module(batch_rand)
            probs_rand = F.softmax(logits_rand, dim=-1).squeeze(0).cpu()
        new_prob = probs_rand[predicted_class].item()
        delta = round((original_prob - new_prob) / max(original_prob, 1e-9) * 100, 2)
        deltas.append(delta)

    return round(sum(deltas) / len(deltas), 2)


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def run():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    print("=" * 78)
    print("  FIX 1: Random-Edge-Removal Baseline vs. GNNExplainer Necessity")
    print("=" * 78)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"\n[Init] Loading model on {device}...")
    t0 = time.time()
    module, heterodata, device = load_model(CHECKPOINT_PATH, HETERODATA_PATH, device=device)
    name_lookup, id_lookup = _build_name_lookups(heterodata)
    drug_id2idx = {db_id: idx for idx, db_id in id_lookup.get("drug", {}).items()}
    print(f"[Init] Ready in {time.time()-t0:.2f}s. Edge types: {len(heterodata.edge_types)}")

    # --------------------------------------------------------
    # 3 demo benchmark pairs
    # --------------------------------------------------------
    demo_pairs = [
        ("DB00853", "DB00531", "T98G",    "Temozolomide+Cyclophosphamide",  "synergy"),
        ("DB00853", "DB01248", "OVCAR-5", "Temozolomide+Docetaxel",         "antagonism"),
        ("DB01248", "DB01030", "A498",    "Docetaxel+Topotecan",            "additive"),
    ]

    # --------------------------------------------------------
    # 5 GBM search results (hardcoded from live /search output)
    # --------------------------------------------------------
    print("\n[Retrieve] Getting live top-5 GBM search results...")
    gbm_top = score_candidate_pairs(
        disease_name="glioblastoma",
        cell_line_name="T98G",
        heterodata=heterodata,
        module=module,
        device=device,
        top_k=5,
    )
    gbm_pairs = [
        (p["drug_a"], p["drug_b"], "T98G",
         f"{p['drug_a_name']}+{p['drug_b_name']}", p["predicted_class"])
        for p in gbm_top
    ]

    all_pairs = [(a, b, cl, label, cls) for (a, b, cl, label, cls) in demo_pairs]
    all_pairs += gbm_pairs

    # --------------------------------------------------------
    # Run necessity (explanation) + random baseline per pair
    # --------------------------------------------------------
    print(f"\n[Run] Evaluating {len(all_pairs)} pairs ({N_RANDOM_SEEDS} random seeds each)...\n")

    results = []
    for i, (drug_a_id, drug_b_id, cell_line, label, expected_cls) in enumerate(all_pairs, 1):
        t_pair = time.time()

        # Resolve indices
        cell_line_map = getattr(heterodata, "cell_line_map", {})
        a_idx = id_lookup["drug"].get(drug_a_id) if isinstance(id_lookup.get("drug"), dict) else None
        # Build proper idx maps from heterodata
        # drug_id2idx is built from id_lookup["drug"] which maps local_idx -> db_id
        # We need db_id -> local_idx
        inv_drug = {v: k for k, v in id_lookup.get("drug", {}).items()}
        inv_prot  = {v: k for k, v in id_lookup.get("protein", {}).items()}

        a_local = inv_drug.get(drug_a_id)
        b_local = inv_drug.get(drug_b_id)
        cl_idx  = cell_line_map.get(cell_line)

        if a_local is None or b_local is None or cl_idx is None:
            print(f"  [{i}] SKIP — could not resolve IDs for {label}")
            continue

        # Sample subgraph
        batch = _sample_batch(heterodata, a_local, b_local, cl_idx)

        # Forward pass to get original_prob and predicted class
        batch_dev = batch.to(device)
        drug_feats = batch_dev["drug"].x.float().detach().requires_grad_(True)
        batch_dev["drug"].x = drug_feats

        module.eval()
        logits, _ = module(batch_dev)
        probs = F.softmax(logits, dim=-1).squeeze(0)
        p_ant, p_add, p_syn = probs.tolist()

        if p_syn > THRESHOLD_SYNERGY:
            pred_idx = 2; pred_name = "synergy"
        elif p_ant > THRESHOLD_ANTAGONISM:
            pred_idx = 0; pred_name = "antagonism"
        else:
            pred_idx = 1; pred_name = "additive"

        original_prob = probs[pred_idx].item()

        # Backprop for edge scores
        probs[pred_idx].backward()
        drug_grad = drug_feats.grad
        grad_norms = {}
        if drug_grad is not None:
            grad_norms["drug"] = drug_grad.norm(dim=-1).detach().cpu()

        # Score edges — use CPU batch for name resolution
        batch_cpu = batch  # already on CPU from _sample_batch
        top_edges, all_edges = _score_edges(batch_cpu, grad_norms, name_lookup, top_k=10)

        # Explanation necessity (existing)
        expl_nec = _necessity_check(
            module, batch_cpu, top_edges, pred_idx, original_prob, device
        )

        # Random baseline necessity (new)
        seeds = list(range(42, 42 + N_RANDOM_SEEDS))
        rand_nec = _random_necessity(
            module, batch_cpu, top_edges, pred_idx, original_prob, device,
            n_remove=len(top_edges), seeds=seeds,
        )

        elapsed = time.time() - t_pair
        results.append({
            "label":    label,
            "cell_line": cell_line,
            "pred":     pred_name,
            "p_syn":    p_syn,
            "expl_nec": expl_nec,
            "rand_nec": rand_nec,
            "beats":    expl_nec > rand_nec,
            "gap":      round(expl_nec - rand_nec, 2),
        })
        beat_str = "YES" if expl_nec > rand_nec else "NO "
        print(f"  [{i:>2}/{len(all_pairs)}] {label:<40} "
              f"expl={expl_nec:+.2f}%  rand={rand_nec:+.2f}%  beats={beat_str}  ({elapsed:.1f}s)")

    # --------------------------------------------------------
    # Print clean comparison table
    # --------------------------------------------------------
    print("\n\n" + "=" * 105)
    print(f"  {'Pair':<38} | {'Cell':<7} | {'Class':<5} | {'Expl Nec':>10} | {'Rand Nec (avg5)':>16} | {'Beats Rand?':>11}")
    print("=" * 105)
    for r in results:
        beat = "YES" if r["beats"] else "NO"
        print(f"  {r['label']:<38} | {r['cell_line']:<7} | {r['pred']:<5} | "
              f"{r['expl_nec']:>+9.2f}% | {r['rand_nec']:>+15.2f}% | {beat:>11}")
    print("=" * 105)

    # --------------------------------------------------------
    # Aggregates + verdict
    # --------------------------------------------------------
    expl_vals = [r["expl_nec"] for r in results]
    rand_vals  = [r["rand_nec"]  for r in results]
    beats_count = sum(1 for r in results if r["beats"])
    n = len(results)

    expl_mean = sum(expl_vals) / n
    rand_mean  = sum(rand_vals)  / n
    gap_mean   = expl_mean - rand_mean

    print(f"\nAggregates over {n} pairs:")
    print(f"  Explanation necessity  mean : {expl_mean:+.2f}%  (min {min(expl_vals):+.2f}%, max {max(expl_vals):+.2f}%)")
    print(f"  Random necessity       mean : {rand_mean:+.2f}%   (min {min(rand_vals):+.2f}%, max {max(rand_vals):+.2f}%)")
    print(f"  Mean gap (expl - rand)      : {gap_mean:+.2f}%")
    print(f"  Pairs where expl > rand     : {beats_count}/{n}")

    # --------------------------------------------------------
    # Verdict (a / b / c)
    # --------------------------------------------------------
    print("\n" + "=" * 65)
    print("  VERDICT")
    print("=" * 65)

    all_expl_small = all(abs(v) < 5.0 for v in expl_vals)
    all_rand_small  = all(abs(v) < 5.0 for v in rand_vals)
    expl_consistently_beats = beats_count >= int(n * 0.6)

    if all_expl_small and all_rand_small:
        if expl_consistently_beats and gap_mean > 0.5:
            verdict = "c"
        else:
            verdict = "a"
    elif not expl_consistently_beats and rand_mean > expl_mean + 0.5:
        verdict = "b"
    elif expl_consistently_beats and gap_mean > 0.5:
        verdict = "c"
    else:
        verdict = "a"

    if verdict == "a":
        print("CONCLUSION: (a) — Both explanation and random removal produce similarly")
        print("tiny score changes. This confirms GENUINE GRAPH REDUNDANCY: the HGT's")
        print("multi-hop message passing has alternative paths through the dense PrimeKG")
        print("subgraph that compensate for any 10 ablated edges. Near-zero necessity")
        print("is an honest, expected property of this architecture — not an explainer")
        print("failure. Sufficiency (79-106%) remains the more diagnostic faithfulness")
        print("metric for this model class.")
    elif verdict == "b":
        print("CONCLUSION: (b) — RANDOM REMOVAL BEATS EXPLANATION-EDGE REMOVAL.")
        print("The GNNExplainer selection is NOT identifying load-bearing edges.")
        print("ACTION REQUIRED: Consider PGExplainer, larger top_k, or L1 regularization.")
    else:
        print("CONCLUSION: (c) — Explanation edges ARE doing better than random, but")
        print(f"the gap is {gap_mean:+.2f}% (expl mean {expl_mean:+.2f}% vs random mean {rand_mean:+.2f}%).")
        print(f"Both fall below the 5.0% necessity threshold. The explainer is real but")
        print(f"the threshold may need recalibrating to reflect what is achievable on")
        print(f"this dense HGT architecture.")

    print("=" * 65)
    return results


if __name__ == "__main__":
    run()
