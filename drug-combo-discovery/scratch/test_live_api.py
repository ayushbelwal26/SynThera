import json
import urllib.request

def test_search():
    payload = {
        "disease": "glioblastoma",
        "cell_line": "T98G",
        "top_k": 3,
        "search_method": "beam",
        "beam_width": 3
    }
    req = urllib.request.Request(
        "http://127.0.0.1:8000/search",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    print("Keys:", list(data.keys()))
    print("Full response preview:", json.dumps(data, indent=2)[:500])
    print(f"Total returned results: {len(data.get('results', []))}")
    for p in data.get("results", []):
        print(f"  Rank #{p.get('rank')}: {p.get('drug_a_name')} ({p.get('drug_a')}) + {p.get('drug_b_name')} ({p.get('drug_b')})")
        print(f"    p_synergy: {p.get('p_synergy')}")
        print(f"    literature: {p.get('literature')}")
        print(f"    supporting_literature: {p.get('supporting_literature')}")
        print(f"    faithfulness: {p.get('faithfulness')}")

if __name__ == "__main__":
    test_search()
