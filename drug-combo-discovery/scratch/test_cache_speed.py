import time
import sys
sys.path.insert(0, "src")
from search import _load_model_cached, find_candidate_drugs, is_valid_therapeutic_candidate
from predict import _get_node_maps
import torch
import torch.nn.functional as F
from torch_geometric.loader import LinkNeighborLoader

module, heterodata, device = _load_model_cached()
node_maps = _get_node_maps(heterodata)
drug_id2idx = node_maps["drug"]
cell_idx = heterodata.cell_line_map["T98G"]

candidates = find_candidate_drugs("glioblastoma", heterodata=heterodata, node_maps=node_maps, max_candidates=10)
candidates = [c for c in candidates if is_valid_therapeutic_candidate(c["drug_name"], c["drug_id"])]

pair_cache = {}

def score_pairs_batch(pair_tuples):
    uncached = [p for p in pair_tuples if p not in pair_cache and (p[1], p[0]) not in pair_cache]
    if not uncached:
        return [pair_cache.get(p, pair_cache.get((p[1], p[0]))) for p in pair_tuples]
    
    n = len(uncached)
    a_indices = [drug_id2idx[p[0]] for p in uncached]
    b_indices = [drug_id2idx[p[1]] for p in uncached]
    
    data_work = heterodata.clone()
    edge_index = torch.tensor([a_indices, b_indices], dtype=torch.long)
    dummy_label = torch.tensor([[0, cell_idx]] * n, dtype=torch.long)
    
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
        batch_size=32,
        shuffle=False,
    )
    module.eval()
    all_logits = []
    with torch.no_grad():
        for batch in loader:
            batch = batch.to(device)
            logits, _ = module(batch)
            all_logits.append(logits.cpu())
    all_logits = torch.cat(all_logits, dim=0)
    all_probs = F.softmax(all_logits, dim=-1).tolist()
    
    for p, probs in zip(uncached, all_probs):
        pair_cache[p] = probs
        pair_cache[(p[1], p[0])] = probs
        
    return [pair_cache.get(p, pair_cache.get((p[1], p[0]))) for p in pair_tuples]

# Test 30 calls
t0 = time.time()
for i in range(5):
    for j in range(i+1, min(len(candidates), 5)):
        p = (candidates[i]["drug_id"], candidates[j]["drug_id"])
        res = score_pairs_batch([p])
t1 = time.time()
print(f"10 individual pair scores took: {t1 - t0:.2f}s")

# Now repeat same 10 pairs (cache test)
t2 = time.time()
for i in range(5):
    for j in range(i+1, min(len(candidates), 5)):
        p = (candidates[i]["drug_id"], candidates[j]["drug_id"])
        res = score_pairs_batch([p])
t3 = time.time()
print(f"10 cached pair lookups took: {(t3 - t2)*1000:.3f}ms")
