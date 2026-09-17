import time
import json
import urllib.request

t0 = time.time()
payload = {
    "disease": "glioblastoma",
    "cell_line": "T98G",
    "max_candidates": 15,
    "top_k": 3,
    "search_method": "beam",
    "beam_width": 5,
    "inspect_top_k": 0,
}

req = urllib.request.Request(
    "http://127.0.0.1:8000/search",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
)

resp = urllib.request.urlopen(req)
data = json.loads(resp.read().decode("utf-8"))
wall_clock_time = time.time() - t0

print(f"Wall-clock search time: {wall_clock_time:.2f}s")
print(f"Search Method: {data.get('search_method')}")
print(f"Beam Width: {data.get('beam_width')}")
print(f"Candidate Pool Size: {data.get('candidate_pool_size')}")
print(f"Max Candidates Scored: {data.get('max_candidates_scored')}")
print(f"Results Count: {len(data.get('results', []))}")
print("\n--- TOP HITS ---")
for i, h in enumerate(data.get("results", []), 1):
    print(
        f"#{h.get('rank', i)}: {h['drug_a_name']} ({h['drug_a']}) + {h['drug_b_name']} ({h['drug_b']}) | "
        f"score={h['score']:.4f} (p_syn={h['p_synergy']:.4f}, p_add={h['p_additive']:.4f}, p_ant={h['p_antagonism']:.4f}) | "
        f"pred={h['predicted_class']} | faithfulness={h.get('faithfulness')}"
    )

# Now test inspect /predict on the top hit
top_hit = data["results"][0]
print(f"\n--- INSPECTING TOP HIT #1 ({top_hit['drug_a']} + {top_hit['drug_b']} @ {data['cell_line']}) ---")
t_pred0 = time.time()
predict_payload = {
    "drug_a": top_hit["drug_a"],
    "drug_b": top_hit["drug_b"],
    "cell_line": data["cell_line"],
    "disease": data["disease"],
}
pred_req = urllib.request.Request(
    "http://127.0.0.1:8000/predict",
    data=json.dumps(predict_payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
)
pred_resp = urllib.request.urlopen(pred_req)
pred_data = json.loads(pred_resp.read().decode("utf-8"))
pred_time = time.time() - t_pred0

print(f"Wall-clock inspect /predict time: {pred_time:.2f}s")
print(f"Predicted class: {pred_data.get('predicted_class')}")
print(f"Score: {pred_data.get('score')}")
print(f"Sufficiency retained: {pred_data.get('sufficiency_retained_pct')}%")
print(f"Necessity delta: {pred_data.get('necessity_delta_pct')}%")
print(f"Faithfulness object: {json.dumps(pred_data.get('faithfulness'), indent=2)}")
