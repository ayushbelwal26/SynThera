import sys
import os
sys.path.insert(0, "src")

from cell_line_mapping import (
    load_cell_line_metadata,
    get_relevant_cell_lines,
    is_cell_line_relevant,
    is_cancer_disease,
    get_cell_line_info
)

print("--- Testing load_cell_line_metadata ---")
meta = load_cell_line_metadata()
print(f"Loaded {len(meta)} cell lines.")
assert len(meta) == 80, f"Expected 80, got {len(meta)}"

print("\n--- Testing get_relevant_cell_lines ---")
gbm_lines = get_relevant_cell_lines("glioblastoma")
print("glioblastoma:", gbm_lines)
assert "T98G" in gbm_lines
assert "U251" in gbm_lines
assert "786-0" not in gbm_lines

breast_lines = get_relevant_cell_lines("breast neoplasm")
print("breast neoplasm:", breast_lines)
assert "MCF7" in breast_lines
assert "MDA-MB-231" in breast_lines

lung_lines = get_relevant_cell_lines("lung adenocarcinoma")
print("lung adenocarcinoma:", lung_lines)
assert "A549" in lung_lines

epilepsy_lines = get_relevant_cell_lines("epilepsy")
print("epilepsy:", epilepsy_lines)
assert epilepsy_lines == [], f"Expected empty list for epilepsy, got {epilepsy_lines}"

alz_lines = get_relevant_cell_lines("Alzheimer's disease")
print("Alzheimer's disease:", alz_lines)
assert alz_lines == [], f"Expected empty list for Alzheimer's, got {alz_lines}"

print("\n--- Testing is_cell_line_relevant ---")
ok, msg = is_cell_line_relevant("T98G", "glioblastoma")
print(f"T98G @ glioblastoma: ok={ok}, msg='{msg}'")
assert ok is True

ok, msg = is_cell_line_relevant("786-0", "glioblastoma")
print(f"786-0 @ glioblastoma: ok={ok}, msg='{msg}'")
assert ok is False
assert "Kidney / Renal" in msg

ok, msg = is_cell_line_relevant("T98G", "epilepsy")
print(f"T98G @ epilepsy: ok={ok}, msg='{msg}'")
assert ok is False
assert "No cancer cell-line context available" in msg

print("\nAll unit checks passed successfully!")
