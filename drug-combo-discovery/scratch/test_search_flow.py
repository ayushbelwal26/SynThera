import sys
import os

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from streamlit.testing.v1 import AppTest

print("Initializing AppTest for discovery search test...")
at = AppTest.from_file("../app/demo.py", default_timeout=60)
at.run()

# Click Discover Combinations button (the primary button in tab_search)
# In app/demo.py, button keys are: btn_synergy, btn_antagonism, btn_additive (sidebar), predict_clicked, btn_discover
btn_discover = [b for b in at.button if b.key == "btn_discover"][0]
print(f"Clicking discover combinations button (key='{btn_discover.key}', label='{btn_discover.label}')...")
btn_discover.click().run()

print(f"Post-search run completed. Exceptions count: {len(at.exception)}")
if at.exception:
    for ex in at.exception:
        print("EXCEPTION:", ex.value)
    sys.exit(1)

# Check session state
s_res = at.session_state["search_result"]
print("Search result in session state:", bool(s_res))
if s_res:
    print(f"Disease: {s_res['disease']}, Cell Line: {s_res['cell_line']}, Results count: {len(s_res.get('results', []))}")
    for i, r in enumerate(s_res.get("results", []), 1):
        print(f"  #{i}: {r['drug_a_name']} + {r['drug_b_name']} | p_syn={r['p_synergy']:.4f}")

assert s_res is not None
assert len(s_res.get("results", [])) == 5
print("\nDISCOVERY SEARCH APPTEST VERIFIED SUCCESSFULLY!")
