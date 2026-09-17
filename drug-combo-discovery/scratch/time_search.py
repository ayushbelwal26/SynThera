import urllib.request
import json
import time

payload = {
    'disease': 'glioblastoma',
    'cell_line': 'T98G',
    'max_candidates': 15,
    'top_k': 5
}
req = urllib.request.Request(
    'http://localhost:8000/search',
    data=json.dumps(payload).encode(),
    headers={'Content-Type': 'application/json'}
)

print("Sending /search request for glioblastoma @ T98G (max_candidates=15, top_k=5)...")
t0 = time.perf_counter()
res = urllib.request.urlopen(req)
raw = res.read().decode()
elapsed = time.perf_counter() - t0

body = json.loads(raw)
print(f"STATUS: {res.status}")
print(f"ELAPSED TIME: {elapsed:.2f} seconds")
print(f"Candidate pool size: {body.get('candidate_pool_size')}")
print(f"Top-K results returned: {len(body.get('results', []))}")
for i, r in enumerate(body.get('results', []), 1):
    da = r.get('drug_a_name')
    db = r.get('drug_b_name')
    cls = r.get('predicted_class')
    score = r.get('score')
    nec = r.get('necessity_delta_pct')
    suf = r.get('sufficiency_retained_pct')
    print(f"  {i}. {da} x {db}: {cls} (score: {score:.4f}) | necessity: {nec}% | sufficiency: {suf}%")
