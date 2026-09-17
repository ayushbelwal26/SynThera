import sys
import os

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from streamlit.testing.v1 import AppTest

print("Initializing AppTest for app/demo.py...")
at = AppTest.from_file("../app/demo.py", default_timeout=60)
at.run()

print(f"Run completed. Exceptions count: {len(at.exception)}")
if at.exception:
    for ex in at.exception:
        print("EXCEPTION:", ex.value)
    sys.exit(1)

disease_input = at.get("text_input")[0]

# 1. Test 'colorectal carcinoma'
print("\n--- Testing 'colorectal carcinoma' ---")
disease_input.input("colorectal carcinoma").run()

search_sb = at.get("selectbox")[-1]
print(f"Disabled: {search_sb.disabled}, Selected value: '{search_sb.value}'")
assert search_sb.disabled is False, "Dropdown should NOT be disabled for colorectal carcinoma!"
assert "COLO 205" in search_sb.value or "HCT116" in search_sb.value or "Colon / Colorectal" in search_sb.value
assert not any("No cancer cell-line context available" in ib.value for ib in at.info)
print("ASSERTION PASSED: 'colorectal carcinoma' surfaces colorectal cell lines dynamically!")

# 2. Test 'prostate adenocarcinoma'
print("\n--- Testing 'prostate adenocarcinoma' ---")
disease_input.input("prostate adenocarcinoma").run()

search_sb = at.get("selectbox")[-1]
print(f"Disabled: {search_sb.disabled}, Selected value: '{search_sb.value}'")
assert search_sb.disabled is False, "Dropdown should NOT be disabled for prostate adenocarcinoma!"
assert "PC-3" in search_sb.value or "Prostate" in search_sb.value
assert not any("No cancer cell-line context available" in ib.value for ib in at.info)
print("ASSERTION PASSED: 'prostate adenocarcinoma' surfaces prostate cell lines dynamically!")

# 3. Test 'pancreatic cancer'
print("\n--- Testing 'pancreatic cancer' ---")
disease_input.input("pancreatic cancer").run()

search_sb = at.get("selectbox")[-1]
print(f"Disabled: {search_sb.disabled}, Selected value: '{search_sb.value}'")
assert search_sb.disabled is False, "Dropdown should NOT be disabled for pancreatic cancer!"
assert not any("No cancer cell-line context available" in ib.value for ib in at.info), "Should NOT hit the guardrail for pancreatic cancer!"
print("ASSERTION PASSED: 'pancreatic cancer' surfaces cancer cell lines and avoids guardrail!")

# 4. Test 'epilepsy' (Non-cancer guardrail)
print("\n--- Testing 'epilepsy' (Non-cancer) ---")
disease_input.input("epilepsy").run()

search_sb = at.get("selectbox")[-1]
print(f"Disabled: {search_sb.disabled}, Selected value: '{search_sb.value}'")
assert search_sb.disabled is True, "Dropdown SHOULD be disabled for epilepsy!"
assert any("No cancer cell-line context available" in ib.value for ib in at.info), "Expected guardrail banner for epilepsy!"
print("ASSERTION PASSED: 'epilepsy' cleanly triggers non-cancer guardrail!")

print("\n" + "=" * 65)
print("  ALL STREAMLIT APPTEST VERIFICATIONS PASSED!")
print("=" * 65)
