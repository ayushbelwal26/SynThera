import urllib.request
import json

def post_json(url, data):
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode('utf-8'))

print("=== 1. Why not Temozolomide? ===")
status, res1 = post_json('http://127.0.0.1:8000/why-not', {
    'disease': 'glioblastoma',
    'cell_line': 'T98G',
    'question': 'Why not Temozolomide?'
})
print(f"Status: {status}")
print(json.dumps(res1, indent=2))

print("\n=== 2. Why not Zinc chloride? ===")
status, res2 = post_json('http://127.0.0.1:8000/why-not', {
    'disease': 'glioblastoma',
    'cell_line': 'T98G',
    'question': 'Why not Zinc chloride?'
})
print(f"Status: {status}")
print(json.dumps(res2, indent=2))

print("\n=== 3. What's the weather? ===")
status, res3 = post_json('http://127.0.0.1:8000/why-not', {
    'disease': 'glioblastoma',
    'cell_line': 'T98G',
    'question': "What's the weather?"
})
print(f"Status: {status}")
print(json.dumps(res3, indent=2))

print("\n=== 4. POST /search (search_method=beam) ===")
status, res4 = post_json('http://127.0.0.1:8000/search', {
    'disease': 'glioblastoma',
    'cell_line': 'T98G',
    'search_method': 'beam',
    'top_k': 3
})
print(f"Status: {status}")
print(f"Candidate pool: {res4.get('candidate_pool_size')}")
print(f"Results count: {len(res4.get('results', []))}")
if res4.get('results'):
    top = res4['results'][0]
    print(f"Top 1: {top['drug_a_name']} + {top['drug_b_name']} | score={top['score']} | class={top['predicted_class']}")
    print(f"Top 1 faithfulness: {top.get('faithfulness')}")

print("\n=== 5. POST /predict (unchanged check) ===")
status, res5 = post_json('http://127.0.0.1:8000/predict', {
    'drug_a': 'DB00853',
    'drug_b': 'DB00515',
    'cell_line': 'T98G'
})
print(f"Status: {status}")
print(f"Predict {res5.get('drug_a_name')} + {res5.get('drug_b_name')}: score={res5.get('score')} | class={res5.get('predicted_class')}")
print(f"Faithfulness present: {'faithfulness' in res5 and res5['faithfulness'] is not None}")
