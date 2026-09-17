import sys
import os
sys.path.insert(0, "src")
from search import _load_model_cached
from explain import explain_prediction

m, h, d = _load_model_cached()
res = explain_prediction(
    "DB00853", "DB00531", "T98G",
    module=m, heterodata=h, device=d,
    run_literature=False,
    disease_context="glioblastoma"
)

print("Explanation text:", res["explanation_text"])
print("Top edges:")
for e in res["top_edges"]:
    print(f"  {e.get('source')} ({e.get('source_type')}) -> {e.get('target')} ({e.get('target_type')}) [{e.get('relation')}]")
