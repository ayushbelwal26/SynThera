import urllib.request
import json
import time

def run_search(payload):
    req = urllib.request.Request(
        "http://127.0.0.1:8000/search",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    t0 = time.time()
    with urllib.request.urlopen(req) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    elapsed = time.time() - t0
    return body, elapsed

print("=== RUNNING BEAM SEARCH ===")
beam_payload = {
    "disease": "glioblastoma",
    "cell_line": "T98G",
    "max_candidates": 15,
    "top_k": 3,
    "search_method": "beam",
    "beam_width": 5,
}
beam_resp, beam_sec = run_search(beam_payload)
print(f"Beam wall-clock: {beam_sec:.3f}s")
print(f"Beam metadata: method={beam_resp.get('search_method')}, pool={beam_resp.get('candidate_pool_size')}, scored={beam_resp.get('max_candidates_scored')}")
for r in beam_resp.get("results", []):
    print(f"  #{r.get('rank')}: {r.get('drug_a_name')} ({r.get('drug_a')}) + {r.get('drug_b_name')} ({r.get('drug_b')}) | score={r.get('score')} | pred={r.get('predicted_class')} | faithfulness={r.get('faithfulness')}")

print("\n=== RUNNING MCTS SEARCH ===")
mcts_payload = {
    "disease": "glioblastoma",
    "cell_line": "T98G",
    "max_candidates": 15,
    "top_k": 3,
    "search_method": "mcts",
    "n_simulations": 50,
    "mcts_c": 1.414,
    "time_budget_sec": 15.0,
}
mcts_resp, mcts_sec = run_search(mcts_payload)
print(f"MCTS wall-clock: {mcts_sec:.3f}s")
print(f"MCTS metadata: method={mcts_resp.get('search_method')}, n_simulations={mcts_resp.get('n_simulations')}, n_pairs_scored={mcts_resp.get('n_pairs_scored')}, truncated={mcts_resp.get('truncated')}")
for r in mcts_resp.get("results", []):
    print(f"  #{r.get('rank')}: {r.get('drug_a_name')} ({r.get('drug_a')}) + {r.get('drug_b_name')} ({r.get('drug_b')}) | score={r.get('score')} | pred={r.get('predicted_class')} | visits={r.get('mcts_visits')} | faithfulness={r.get('faithfulness')}")

# Also test Inspect on MCTS hit #1
hit1 = mcts_resp.get("results", [])[0]
print(f"\n=== RUNNING INSPECT /predict ON MCTS HIT #1: {hit1.get('drug_a_name')} + {hit1.get('drug_b_name')} ===")
predict_payload = {
    "drug_a": hit1.get("drug_a"),
    "drug_b": hit1.get("drug_b"),
    "cell_line": "T98G",
    "disease": "glioblastoma"
}
req = urllib.request.Request(
    "http://127.0.0.1:8000/predict",
    data=json.dumps(predict_payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST"
)
t0 = time.time()
with urllib.request.urlopen(req) as resp:
    pred_body = json.loads(resp.read().decode("utf-8"))
pred_elapsed = time.time() - t0
print(f"Inspect elapsed: {pred_elapsed:.3f}s")
print(f"Inspect faithfulness: {pred_body.get('faithfulness')}")
print(f"Inspect literature citations count: {len(pred_body.get('supporting_literature', []))}")
if pred_body.get("supporting_literature"):
    c0 = pred_body["supporting_literature"][0]
    print(f"Citation #1: PMID {c0.get('pmid')} - {c0.get('title')}")
