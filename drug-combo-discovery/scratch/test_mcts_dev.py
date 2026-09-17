import time
import math
import torch
import torch.nn.functional as F
from torch_geometric.loader import LinkNeighborLoader
import sys
sys.path.insert(0, "src")
from search import (
    _load_model_cached,
    find_candidate_drugs,
    is_valid_therapeutic_candidate,
    _HIGH_CONFIDENCE_THRESHOLD,
)
from predict import (
    _get_node_maps,
    THRESHOLD_SYNERGY,
    THRESHOLD_ANTAGONISM,
)

module, heterodata, device = _load_model_cached()
node_maps = _get_node_maps(heterodata)
drug_id2idx = node_maps["drug"]
cell_idx = heterodata.cell_line_map["T98G"]

candidates = find_candidate_drugs("glioblastoma", heterodata=heterodata, node_maps=node_maps, max_candidates=10)
candidates = [c for c in candidates if is_valid_therapeutic_candidate(c["drug_name"], c["drug_id"])]
print(f"Candidates pool size: {len(candidates)}: {[c['drug_name'] for c in candidates]}")

def run_mcts_test(n_sims=40, mcts_c=1.414, time_budget=10.0):
    torch.manual_seed(42)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(42)

    pair_cache = {}
    pair_visits = {}
    cache_hits = 0
    n_pairs_scored = 0

    def score_single_pair(d_a, d_b):
        nonlocal n_pairs_scored
        a_idx = drug_id2idx[d_a]
        b_idx = drug_id2idx[d_b]
        data_work = heterodata.clone()
        edge_index = torch.tensor([[a_idx], [b_idx]], dtype=torch.long)
        dummy_label = torch.tensor([[0, cell_idx]], dtype=torch.long)

        data_work["drug", "synergy_pair", "drug"].edge_index = edge_index
        data_work["drug", "synergy_pair", "drug"].edge_label_index = edge_index
        data_work["drug", "synergy_pair", "drug"].edge_label = dummy_label

        num_neighbors = {
            et: ([0, 0] if et == ("drug", "synergy_pair", "drug") else [5, 3])
            for et in data_work.edge_types
        }
        loader = LinkNeighborLoader(
            data=data_work,
            num_neighbors=num_neighbors,
            edge_label_index=(("drug", "synergy_pair", "drug"), edge_index),
            edge_label=dummy_label,
            batch_size=1,
            shuffle=False,
        )
        module.eval()
        with torch.no_grad():
            batch = next(iter(loader)).to(device)
            logits, _ = module(batch)
            probs = F.softmax(logits, dim=-1)[0].tolist()

        n_pairs_scored += 1
        p_ant, p_add, p_syn = probs
        if p_syn > THRESHOLD_SYNERGY:
            pred = "synergy"
        elif p_ant > THRESHOLD_ANTAGONISM:
            pred = "antagonism"
        else:
            pred = "additive"

        return {
            "p_antagonism": p_ant,
            "p_additive": p_add,
            "p_synergy": p_syn,
            "predicted_class": pred,
        }

    class MCTSNode:
        def __init__(self, drug_id=None, parent=None, depth=0):
            self.drug_id = drug_id
            self.parent = parent
            self.depth = depth
            self.children = {}
            self.visits = 0
            self.total_value = 0.0

        @property
        def q_value(self):
            return self.total_value / self.visits if self.visits > 0 else 0.0

    cand_ids = [c["drug_id"] for c in candidates]
    cand_by_id = {c["drug_id"]: c for c in candidates}
    root = MCTSNode(depth=0)

    start_time = time.time()
    truncated = False
    sims_done = 0

    for sim in range(n_sims):
        if time.time() - start_time >= time_budget:
            truncated = True
            break

        # 1. Selection
        curr = root
        # At depth 0 (Root)
        unvisited_roots = [d for d in cand_ids if d not in curr.children]
        if unvisited_roots:
            pick_d = unvisited_roots[0]
            child = MCTSNode(drug_id=pick_d, parent=curr, depth=1)
            curr.children[pick_d] = child
            curr = child
        else:
            # Select root child with max UCT
            log_n = math.log(max(curr.visits, 1))
            best_uct = -1e9
            best_child = None
            for d in cand_ids:
                ch = curr.children[d]
                uct = ch.q_value + mcts_c * math.sqrt(log_n / max(ch.visits, 1))
                if uct > best_uct or (uct == best_uct and (best_child is None or d < best_child.drug_id)):
                    best_uct = uct
                    best_child = ch
            curr = best_child

        # At depth 1 (choose partner)
        d_a = curr.drug_id
        partner_cands = [d for d in cand_ids if d != d_a]
        unvisited_partners = [d for d in partner_cands if d not in curr.children]
        if unvisited_partners:
            pick_p = unvisited_partners[0]
            child = MCTSNode(drug_id=pick_p, parent=curr, depth=2)
            curr.children[pick_p] = child
            curr = child
        else:
            log_n = math.log(max(curr.visits, 1))
            best_uct = -1e9
            best_child = None
            for p in partner_cands:
                ch = curr.children[p]
                uct = ch.q_value + mcts_c * math.sqrt(log_n / max(ch.visits, 1))
                if uct > best_uct or (uct == best_uct and (best_child is None or p < best_child.drug_id)):
                    best_uct = uct
                    best_child = ch
            curr = best_child

        # 2. Terminal state (d_a, d_b)
        d_b = curr.drug_id
        pair_key = (min(d_a, d_b), max(d_a, d_b))
        pair_visits[pair_key] = pair_visits.get(pair_key, 0) + 1

        if pair_key in pair_cache:
            eval_res = pair_cache[pair_key]
            cache_hits += 1
        else:
            eval_res = score_single_pair(d_a, d_b)
            pair_cache[pair_key] = eval_res

        v = eval_res["p_synergy"]

        # 3. Backprop
        node = curr
        while node is not None:
            node.visits += 1
            node.total_value += v
            node = node.parent

        sims_done += 1

    elapsed = time.time() - start_time
    print(f"\nMCTS finished in {elapsed:.2f}s: {sims_done} sims, {n_pairs_scored} scored, {cache_hits} cache hits, truncated={truncated}")

    # Build results
    scored_pairs = []
    for pair_key, eval_res in pair_cache.items():
        da_id, db_id = pair_key
        p_syn = eval_res["p_synergy"]
        ca = cand_by_id[da_id]
        cb = cand_by_id[db_id]
        scored_pairs.append({
            "drug_a": da_id,
            "drug_a_name": ca["drug_name"],
            "drug_b": db_id,
            "drug_b_name": cb["drug_name"],
            "score": round(p_syn, 4),
            "p_synergy": round(p_syn, 4),
            "mcts_visits": pair_visits.get(pair_key, 1),
            "predicted_class": eval_res["predicted_class"],
        })

    scored_pairs.sort(key=lambda x: (-x["p_synergy"], x["drug_a"], x["drug_b"]))
    print("\nTop 5 MCTS pairs:")
    for i, p in enumerate(scored_pairs[:5], 1):
        print(f"  #{i}: {p['drug_a_name']} ({p['drug_a']}) + {p['drug_b_name']} ({p['drug_b']}) | p_syn={p['p_synergy']} | visits={p['mcts_visits']}")

run_mcts_test(n_sims=30, mcts_c=1.414, time_budget=10.0)
