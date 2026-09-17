import sys
sys.path.insert(0, "src")
import json
from search import _load_model_cached
from why_not import analyze_why_not, parse_why_not_intent
from predict import _get_node_maps
from explain import _build_name_lookups

module, heterodata, device = _load_model_cached()
name_lookup, id_lookup = _build_name_lookups(heterodata)
drug_id2idx = _get_node_maps(heterodata).get("drug", {})

drug_list = []
drug_alias_map = {}
seen = set()
for idx, db_id in id_lookup.get("drug", {}).items():
    name = name_lookup.get("drug", {}).get(idx, db_id)
    if db_id in drug_id2idx and db_id not in seen:
        seen.add(db_id)
        drug_list.append({"id": db_id, "name": name})
        drug_alias_map[db_id.lower()] = db_id
        drug_alias_map[name.lower()] = db_id

print(f"Loaded {len(drug_list)} drugs in alias map.")

# Test 1: Unsupported question
print("\n--- TEST 1: Unsupported Question ---")
res1 = analyze_why_not(
    disease_name="glioblastoma",
    cell_line_name="T98G",
    question="What's the weather?",
    drug_alias_map=drug_alias_map,
    drug_list=drug_list,
    heterodata=heterodata,
    module=module,
    device=device,
)
print(json.dumps(res1, indent=2))

# Test 2: Filtered Zinc chloride
print("\n--- TEST 2: Filtered Zinc chloride ---")
res2 = analyze_why_not(
    disease_name="glioblastoma",
    cell_line_name="T98G",
    question="Why not Zinc chloride?",
    drug_alias_map=drug_alias_map,
    drug_list=drug_list,
    heterodata=heterodata,
    module=module,
    device=device,
)
print(json.dumps(res2, indent=2))

# Test 3: Unknown drug
print("\n--- TEST 3: Unknown Drug ---")
res3 = analyze_why_not(
    disease_name="glioblastoma",
    cell_line_name="T98G",
    question="Why not FakeDrugXYZ?",
    drug_alias_map=drug_alias_map,
    drug_list=drug_list,
    heterodata=heterodata,
    module=module,
    device=device,
)
print(json.dumps(res3, indent=2))

# Test 4: Temozolomide on glioblastoma / T98G
print("\n--- TEST 4: Temozolomide on glioblastoma / T98G ---")
res4 = analyze_why_not(
    disease_name="glioblastoma",
    cell_line_name="T98G",
    question="Why not Temozolomide?",
    drug_alias_map=drug_alias_map,
    drug_list=drug_list,
    heterodata=heterodata,
    module=module,
    device=device,
    run_literature=True,
)
print(json.dumps(res4, indent=2))
