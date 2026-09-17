import requests
import json
import sys

BASE_URL = "http://127.0.0.1:8000"

print("=" * 65)
print("  VERIFYING SYNTHERA REAL FAITHFULNESS ABLATION PIPELINE")
print("=" * 65)

# 1. Test POST /predict with real in-silico ablation
print("\n[1] Testing POST /predict for Temozolomide (DB00853) x Cyclophosphamide (DB00531) @ T98G...")
payload = {
    "drug_a": "DB00853",
    "drug_b": "DB00531",
    "cell_line": "T98G",
    "disease": "glioblastoma"
}

resp = requests.post(f"{BASE_URL}/predict", json=payload, timeout=60)
print(f"Status Code: {resp.status_code}")
assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
data = resp.json()

print("\n--- Raw /predict Faithfulness Object ---")
f = data.get("faithfulness")
print(json.dumps(f, indent=2))

assert f is not None, "Expected 'faithfulness' object in response!"
assert "original_score" in f, "Missing original_score"
assert "ablated_score" in f, "Missing ablated_score"
assert "sufficiency" in f, "Missing sufficiency"
assert "necessity" in f, "Missing necessity"
assert "explanation_faithful" in f, "Missing explanation_faithful"
assert "rationale" in f, "Missing rationale"
assert "k_edges_ablated" in f, "Missing k_edges_ablated"

print("\n--- Key Metrics ---")
print(f"  original_score       : {f['original_score']} ({f.get('original_class')})")
print(f"  ablated_score        : {f['ablated_score']} ({f.get('ablated_class')})")
print(f"  sufficiency          : {f['sufficiency']}%")
print(f"  necessity            : {f['necessity']}%")
print(f"  explanation_faithful : {f['explanation_faithful']}")
print(f"  rationale            : {f['rationale']}")
print(f"  k_edges_ablated      : {f['k_edges_ablated']}")

# 2. Test GET /cell-lines
print("\n[2] Testing GET /cell-lines...")
cl_resp = requests.get(f"{BASE_URL}/cell-lines?disease=glioblastoma", timeout=10)
print(f"Status Code: {cl_resp.status_code}")
assert cl_resp.status_code == 200
cl_lines = cl_resp.json()
print(f"Glioblastoma cell lines returned ({len(cl_lines)}): {cl_lines[:5]}")
assert "T98G" in cl_lines
assert "U251" in cl_lines

# 3. Test POST /search disclosure (faithfulness not computed during batch search)
print("\n[3] Testing POST /search disclosure...")
s_payload = {
    "disease": "glioblastoma",
    "cell_line": "T98G",
    "max_candidates": 10,
    "top_k": 2
}
s_resp = requests.post(f"{BASE_URL}/search", json=s_payload, timeout=60)
print(f"Status Code: {s_resp.status_code}")
assert s_resp.status_code == 200
s_data = s_resp.json()
assert "results" in s_data
top_pair = s_data["results"][0]
print(f"Top discovered pair: {top_pair['drug_a_name']} x {top_pair['drug_b_name']}")
print(f"Top pair faithfulness in batch search: {top_pair.get('faithfulness')} (Correct: omitted during batch search)")
assert top_pair.get("faithfulness") is None, "Batch search must omit faithfulness ablation!"

print("\n" + "=" * 65)
print("  ALL REAL ABLATION & API ACCEPTANCE CHECKS PASSED!")
print("=" * 65)
