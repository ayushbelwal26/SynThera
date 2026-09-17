import time
import torch
import torch.nn.functional as F
from torch_geometric.loader import LinkNeighborLoader
import sys
sys.path.insert(0, "src")
from search import _load_model_cached, find_candidate_drugs, is_valid_therapeutic_candidate
from predict import _get_node_maps

module, heterodata, device = _load_model_cached()
node_maps = _get_node_maps(heterodata)
drug_id2idx = node_maps["drug"]
cell_idx = heterodata.cell_line_map["T98G"]

candidates = find_candidate_drugs("glioblastoma", heterodata=heterodata, node_maps=node_maps, max_candidates=15)
candidates = [c for c in candidates if is_valid_therapeutic_candidate(c["drug_name"], c["drug_id"])]
print(f"Candidates pool size: {len(candidates)}")

def score_pairs_batch(pair_tuples):
    # pair_tuples: list of (drug_a_id, drug_b_id)
    n = len(pair_tuples)
    a_indices = [drug_id2idx[p[0]] for p in pair_tuples]
    b_indices = [drug_id2idx[p[1]] for p in pair_tuples]
    
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
    return all_probs

# Benchmark 1 pair
t0 = time.time()
res1 = score_pairs_batch([(candidates[0]["drug_id"], candidates[1]["drug_id"])])
t1 = time.time()
print(f"Scoring 1 pair took: {(t1 - t0)*1000:.1f}ms -> probs: {res1[0]}")

# Benchmark 10 pairs
sample_pairs = []
for i in range(min(5, len(candidates))):
    for j in range(i+1, min(5, len(candidates))):
        sample_pairs.append((candidates[i]["drug_id"], candidates[j]["drug_id"]))
t0 = time.time()
res10 = score_pairs_batch(sample_pairs)
t2 = time.time()
print(f"Scoring {len(sample_pairs)} pairs took: {(t2 - t0)*1000:.1f}ms ({(t2 - t0)*1000/len(sample_pairs):.1f}ms/pair)")
