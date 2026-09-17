def parse_cell_line_name(opt: str) -> str:
    cleaned = opt.strip()
    if cleaned.startswith("⭐"):
        cleaned = cleaned[1:].strip()
    return cleaned.split(" (")[0].strip()

assert parse_cell_line_name("⭐ T98G (CNS / Brain — Relevant)") == "T98G"
assert parse_cell_line_name("⭐ COLO 205 (Colon / Colorectal — Relevant)") == "COLO 205"
assert parse_cell_line_name("⭐ 786-0 (Kidney / Renal — Relevant)") == "786-0"
assert parse_cell_line_name("786-0") == "786-0"
assert parse_cell_line_name("COLO 205") == "COLO 205"
assert parse_cell_line_name("A549") == "A549"
print("All parsing tests passed cleanly!")
