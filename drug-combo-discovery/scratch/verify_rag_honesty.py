import urllib.request
import json

def call_predict(drug_a, drug_b, cell_line, disease):
    payload = {
        "drug_a": drug_a,
        "drug_b": drug_b,
        "cell_line": cell_line,
        "disease": disease,
    }
    req = urllib.request.Request(
        "http://127.0.0.1:8000/predict",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

print("=" * 70)
print("1. Testing Temozolomide (DB00853) + Cyclophosphamide (DB00531) + T98G + glioblastoma")
print("=" * 70)
res1 = call_predict("DB00853", "DB00531", "T98G", "glioblastoma")
lit1 = res1.get("literature", {})
print("query_used:", lit1.get("query_used"))
print("Total citations:", len(lit1.get("citations", [])))
for i, c in enumerate(lit1.get("citations", []), 1):
    pmid = c.get("pmid")
    ev_type = c.get("evidence_type")
    reason = c.get("match_reason")
    title = c.get("title", "")
    snippet = c.get("snippet", "")
    # Check via efetch full title + abstract
    import sys
    sys.path.insert(0, "src")
    from literature import _efetch_xml
    art = _efetch_xml([pmid])[0] if pmid else {}
    full_text = (art.get("title", "") + " " + art.get("abstract", "")).lower()
    tmz_in_title_or_abstract = ("temozolomide" in full_text or "tmz" in full_text)
    ctx_in_title_or_abstract = ("cyclophosphamide" in full_text or "ctx" in full_text)
    print(f"\n[Citation {i}] PMID: {pmid}")
    print(f"  Title: {title}")
    print(f"  evidence_type: {ev_type}")
    print(f"  match_reason: {reason}")
    print(f"  temozolomide in title/abstract: {tmz_in_title_or_abstract}")
    print(f"  cyclophosphamide in title/abstract: {ctx_in_title_or_abstract}")
    print(f"  url: {c.get('url')}")

print("\n" + "=" * 70)
print("2. Testing Procarbazine (DB01168) + Carmustine (DB00262) + T98G + glioblastoma")
print("=" * 70)
res2 = call_predict("DB01168", "DB00262", "T98G", "glioblastoma")
lit2 = res2.get("literature", {})
print("query_used:", lit2.get("query_used"))
print("Total citations:", len(lit2.get("citations", [])))
for i, c in enumerate(lit2.get("citations", []), 1):
    pmid = c.get("pmid")
    ev_type = c.get("evidence_type")
    reason = c.get("match_reason")
    title = c.get("title", "")
    print(f"\n[Citation {i}] PMID: {pmid}")
    print(f"  Title: {title}")
    print(f"  evidence_type: {ev_type}")
    print(f"  match_reason: {reason}")
    print(f"  url: {c.get('url')}")
