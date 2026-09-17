import sys
import os
sys.path.insert(0, "src")

# Configure UTF-8 safe output
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from cell_line_mapping import (
    get_relevant_cell_lines,
    is_cell_line_relevant,
    is_cancer_disease,
    get_cell_line_info
)

print("=" * 65)
print("  TESTING DYNAMIC METADATA CELL LINE MAPPING")
print("=" * 65)

# 1. Test the requested non-hardcoded cancer diseases
test_diseases = [
    ("pancreatic cancer", "Generic / Pancreatic Adenocarcinoma"),
    ("colorectal carcinoma", "Colon / Colorectal"),
    ("prostate adenocarcinoma", "Prostate"),
    ("renal cell carcinoma", "Kidney / Renal"),
    ("cutaneous melanoma", "Skin / Melanoma"),
]

for dis, expected_type in test_diseases:
    lines = get_relevant_cell_lines(dis)
    print(f"\n[Disease] '{dis}' ({expected_type}):")
    print(f"  Count surfaced : {len(lines)}")
    print(f"  Top lines       : {lines[:6]}")
    # pancreatic cancer has no matching tissue in the NCI-60 panel -- must return []
    if dis == "pancreatic cancer":
        assert lines == [], f"Expected [] for {dis} (not in panel), got {lines}"
        print("  ASSERTION PASSED: pancreatic cancer correctly returns [] (tissue absent from panel)")
    else:
        assert len(lines) > 0, f"Expected lines for {dis}, got empty list!"
        is_cancer = is_cancer_disease(dis)
        assert is_cancer is True, f"Expected {dis} to be identified as cancer"

# Specific assertion on colorectal carcinoma
crc_lines = get_relevant_cell_lines("colorectal carcinoma")
assert "HCT116" in crc_lines
assert "HT29" in crc_lines
assert "COLO 205" in crc_lines
assert "786-0" not in crc_lines  # renal line should NOT be in top tier for colorectal!
print("  ASSERTION PASSED: Colorectal carcinoma specifically surfaces colorectal lines!")

# Specific assertion on prostate adenocarcinoma
pros_lines = get_relevant_cell_lines("prostate adenocarcinoma")
assert "PC-3" in pros_lines
assert "DU-145" in pros_lines
assert "VCAP" in pros_lines
assert "A549" not in pros_lines  # lung line should NOT be in top tier for prostate!
print("  ASSERTION PASSED: Prostate adenocarcinoma specifically surfaces prostate lines!")

# Specific assertion on pancreatic cancer — tissue not in panel, should return []
panc_lines = get_relevant_cell_lines("pancreatic cancer")
assert panc_lines == [], f"Pancreatic cancer should return [] (tissue not in NCI-60 panel), got {len(panc_lines)} lines"
assert "A549" not in panc_lines, "Lung line A549 must NOT appear for pancreatic cancer!"
assert "HCT116" not in panc_lines, "CRC line HCT116 must NOT appear for pancreatic cancer!"
print("  ASSERTION PASSED: Pancreatic cancer correctly returns [] — panel has no pancreatic lines!")

# 2. Test Priority Overrides (Glioblastoma)
print("\n[Disease] 'glioblastoma' (Priority Override):")
gbm_lines = get_relevant_cell_lines("glioblastoma")
print(f"  Top lines: {gbm_lines}")
assert gbm_lines[0] == "T98G"
assert gbm_lines[1] == "U251"
print("  ASSERTION PASSED: Glioblastoma priority override preserved!")

# 3. Test Non-Cancer Diseases (Must hit guardrail cleanly)
non_cancer_cases = ["epilepsy", "Alzheimer's disease", "hypertension", "diabetes mellitus"]
print("\n--- Testing Non-Cancer Guardrails ---")
for nc in non_cancer_cases:
    nc_lines = get_relevant_cell_lines(nc)
    print(f"  '{nc}' -> {nc_lines}")
    assert nc_lines == [], f"Expected [] for non-cancer {nc}, got {nc_lines}"
    is_c = is_cancer_disease(nc)
    assert is_c is False, f"Expected {nc} to NOT be cancer"
print("  ASSERTION PASSED: Non-cancer indications cleanly return []!")

# 4. Test is_cell_line_relevant validation and warning messages
print("\n--- Testing is_cell_line_relevant ---")
# Relevant:
ok, msg = is_cell_line_relevant("HCT116", "colorectal carcinoma")
print(f"  HCT116 @ colorectal carcinoma: ok={ok}, msg='{msg}'")
assert ok is True

ok, msg = is_cell_line_relevant("PC-3", "prostate adenocarcinoma")
print(f"  PC-3 @ prostate adenocarcinoma: ok={ok}, msg='{msg}'")
assert ok is True

# Discordant:
ok, msg = is_cell_line_relevant("786-0", "colorectal carcinoma")
print(f"  786-0 @ colorectal carcinoma: ok={ok}, msg='{msg}'")
assert ok is False
assert "Kidney / Renal" in msg

ok, msg = is_cell_line_relevant("A549", "prostate adenocarcinoma")
print(f"  A549 @ prostate adenocarcinoma: ok={ok}, msg='{msg}'")
assert ok is False
assert "Lung" in msg

# Non-cancer:
ok, msg = is_cell_line_relevant("T98G", "epilepsy")
print(f"  T98G @ epilepsy: ok={ok}, msg='{msg}'")
assert ok is False
assert "No cancer cell-line context available" in msg

print("\n" + "=" * 65)
print("  ALL DYNAMIC MAPPING TESTS PASSED SUCCESSFULLY!")
print("=" * 65)
