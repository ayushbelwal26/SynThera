"""
join_labels.py — Drug Name Entity Resolution + Synergy Label Construction
==========================================================================

PURPOSE
-------
Bridges DrugComb's plain-name drug identifiers with PrimeKG's DrugBank IDs
using a two-pass name-matching strategy (exact then fuzzy), and produces
the final labeled (drug_a_kg_id, drug_b_kg_id, cell_line, synergy) dataset.

MATCHING STRATEGY
-----------------
1. Normalize both sides: uppercase, strip whitespace, remove common salt-form
   suffixes (hydrochloride, sodium, sulfate, etc.), extract parenthetical codes
   as separate alias candidates.
2. Pass 1 — exact match on normalized name.
3. Pass 2 — rapidfuzz token_sort_ratio >= 90 for remaining unmatched names,
   against the full set of PrimeKG normalized drug names.
4. Unmatched drugs (CAS numbers, internal codes, etc.) are saved separately
   and NOT force-matched.

LABEL SCHEMA
------------
synergy_loewe > 10   → 'synergy'
synergy_loewe < -10  → 'antagonism'
else                 → 'additive'
"""

import os
import re
import sys
import time

import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(ROOT, "data", "raw")
PROCESSED_DIR = os.path.join(ROOT, "data", "processed")

DRUGCOMB_PATH = os.path.join(RAW_DIR, "drugcomb_raw.tsv")
PRIMEKG_DRUGS_PATH = os.path.join(PROCESSED_DIR, "primekg_drugs.csv")

OUT_LABELED = os.path.join(PROCESSED_DIR, "labeled_pairs.csv")
OUT_UNMATCHED = os.path.join(PROCESSED_DIR, "unmatched_drugs.csv")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
FUZZY_THRESHOLD = 97     # rapidfuzz token_sort_ratio cutoff (raised from 90 to remove false positives)
SYNERGY_LO_PCTILE = 15  # percentile below which -> 'antagonism'
SYNERGY_HI_PCTILE = 85  # percentile above which -> 'synergy'

# Salt-form and formulation suffixes to strip before matching.
# Sorted longest-first so multi-word suffixes match before their substrings.
SALT_SUFFIXES = sorted([
    "dihydrochloride", "hydrochloride", "hydrobromide", "hydrofluoride",
    "hydrate", "monohydrate", "dihydrate",
    "sodium", "potassium", "calcium", "magnesium", "lithium",
    "sulfate", "sulphate", "bisulfate", "bisulphate",
    "phosphate", "diphosphate", "triphosphate",
    "chloride", "bromide", "iodide", "fluoride",
    "nitrate", "nitrite", "carbonate", "bicarbonate",
    "acetate", "diacetate", "triacetate",
    "mesylate", "tosylate", "besylate", "maleate",
    "fumarate", "succinate", "tartrate", "citrate", "oxalate",
    "lactate", "gluconate", "malonate",
    "benzoate", "pamoate", "stearate",
    "trifluoroacetate", "hydroxy",
    "hcl", "hbr",
], key=len, reverse=True)

# Pre-compiled regex for salt suffixes and parenthetical codes
_SALT_RE = re.compile(
    r"\b(" + "|".join(re.escape(s) for s in SALT_SUFFIXES) + r")\b",
    re.IGNORECASE,
)
_PAREN_RE = re.compile(r"\(([^)]+)\)")  # captures content inside parens
_WHITESPACE_RE = re.compile(r"\s+")


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _sep(title: str = "") -> None:
    print("\n" + "=" * 68)
    if title:
        print(f"  {title}")
        print("=" * 68)


def _elapsed(t0: float) -> str:
    s = time.time() - t0
    return f"{s:.2f}s" if s < 60 else f"{s/60:.1f}m"


def normalize(name: str) -> str:
    """
    Canonical normalization for matching:
      - uppercase
      - strip salt-form suffixes
      - collapse internal whitespace
      - strip punctuation-only artefacts at ends
    """
    n = name.upper().strip()
    n = _SALT_RE.sub("", n)
    n = _WHITESPACE_RE.sub(" ", n).strip(" ,;-/")
    return n


def extract_aliases(raw_name: str) -> list[str]:
    """
    Returns a list of normalized candidates from one raw drug name:
      - the full normalized name
      - the name with ALL parenthetical sections removed (e.g., "(GDC-0199)")
      - each parenthetical content as a standalone alias (e.g., "GDC-0199")
    Duplicates are removed; all aliases are normalized.
    """
    aliases = []
    # Full normalized name
    full_norm = normalize(raw_name)
    if full_norm:
        aliases.append(full_norm)

    # Find all parenthetical groups
    paren_contents = _PAREN_RE.findall(raw_name)

    # Name with all parens stripped
    no_paren = normalize(_PAREN_RE.sub("", raw_name))
    if no_paren and no_paren != full_norm:
        aliases.append(no_paren)

    # Each paren content as its own alias
    for pc in paren_contents:
        pc_norm = normalize(pc)
        if pc_norm and pc_norm not in aliases:
            aliases.append(pc_norm)

    # Deduplicate while preserving order
    seen, out = set(), []
    for a in aliases:
        if a not in seen and a:
            seen.add(a)
            out.append(a)
    return out


# ---------------------------------------------------------------------------
# Step 1 — Load data
# ---------------------------------------------------------------------------

def load_data():
    _sep("Step 1 — Loading data")

    dc = pd.read_csv(DRUGCOMB_PATH, sep="\t", low_memory=False)
    print(f"  DrugComb: {len(dc):,} rows, columns: {dc.columns.tolist()}")

    pkg = pd.read_csv(PRIMEKG_DRUGS_PATH)
    print(f"  PrimeKG drugs: {len(pkg):,} rows, columns: {pkg.columns.tolist()}")

    return dc, pkg


# ---------------------------------------------------------------------------
# Step 2 — Build normalized lookup for PrimeKG drugs
# ---------------------------------------------------------------------------

def build_pkg_lookup(pkg: pd.DataFrame) -> dict[str, str]:
    """
    Returns {normalized_name -> drugbank_id}.
    Where multiple DrugBank drugs share a normalized name, the first is kept
    (alphabetically by drugbank_id) and a warning is printed.
    """
    _sep("Step 2 — Building PrimeKG normalized name lookup")
    lookup: dict[str, str] = {}
    collisions = 0
    for _, row in pkg.iterrows():
        db_id = row["drugbank_id"]
        raw = row["drug_name"]
        for alias in extract_aliases(raw):
            if alias in lookup:
                collisions += 1
            else:
                lookup[alias] = db_id
    print(f"  PrimeKG entries:         {len(pkg):,}")
    print(f"  Normalized lookup keys:  {len(lookup):,} (collisions skipped: {collisions})")
    if collisions:
        print(f"  [Note] {collisions} alias collision(s) — first DrugBank ID wins per alias.")
    return lookup


# ---------------------------------------------------------------------------
# Step 3 — Collect unique DrugComb drug names and build alias map
# ---------------------------------------------------------------------------

def collect_drugcomb_drugs(dc: pd.DataFrame) -> dict[str, list[str]]:
    """Returns {raw_name -> [alias1, alias2, ...]} for all unique DrugComb drugs."""
    all_raw = set(dc["drug_row"].dropna()) | set(dc["drug_col"].dropna())
    print(f"\n  Unique raw DrugComb drug strings: {len(all_raw):,}")
    return {raw: extract_aliases(raw) for raw in all_raw}


# ---------------------------------------------------------------------------
# Step 4 — Pass 1: Exact match
# ---------------------------------------------------------------------------

def exact_match(
    dc_alias_map: dict[str, list[str]],
    pkg_lookup: dict[str, str],
) -> tuple[dict[str, str], set[str]]:
    """
    Returns:
        matched   : {raw_dc_name -> drugbank_id}
        unmatched : set of raw_dc_names with no exact match
    """
    _sep("Step 3 — Pass 1: Exact match")
    matched: dict[str, str] = {}
    unmatched: set[str] = set()

    for raw, aliases in dc_alias_map.items():
        found = None
        for alias in aliases:
            if alias in pkg_lookup:
                found = pkg_lookup[alias]
                break
        if found:
            matched[raw] = found
        else:
            unmatched.add(raw)

    total = len(dc_alias_map)
    print(f"  Exact matches:   {len(matched):,} / {total:,}  ({100*len(matched)/total:.1f}%)")
    print(f"  Still unmatched: {len(unmatched):,} / {total:,}  ({100*len(unmatched)/total:.1f}%)")
    return matched, unmatched


# ---------------------------------------------------------------------------
# Step 5 — Pass 2: Fuzzy match
# ---------------------------------------------------------------------------

def fuzzy_match(
    unmatched: set[str],
    pkg_lookup: dict[str, str],
    dc_alias_map: dict[str, list[str]],
) -> tuple[dict[str, str], set[str]]:
    """
    For each unmatched DrugComb drug, try rapidfuzz token_sort_ratio >= FUZZY_THRESHOLD
    against every PrimeKG normalized name.

    Returns:
        fuzzy_matched   : {raw_dc_name -> drugbank_id}
        still_unmatched : set of raw_dc_names with no match above threshold
    """
    _sep(f"Step 4 — Pass 2: Fuzzy match (rapidfuzz token_sort_ratio >= {FUZZY_THRESHOLD})")

    try:
        from rapidfuzz import process as rf_process, fuzz as rf_fuzz
        _USE_RAPIDFUZZ = True
        print("  Using: rapidfuzz (C-accelerated)")
    except ImportError:
        import difflib
        _USE_RAPIDFUZZ = False
        print("  Using: difflib SequenceMatcher (install rapidfuzz for ~50x speedup)")

    pkg_names_list = list(pkg_lookup.keys())  # all normalized PrimeKG names

    fuzzy_matched: dict[str, str] = {}
    still_unmatched: set[str] = set()
    fuzzy_details: list[tuple] = []  # (dc_raw, dc_alias, pkg_name, score, db_id)

    t0 = time.time()
    n = len(unmatched)
    for i, raw in enumerate(sorted(unmatched), 1):
        if i % 200 == 0 or i == n:
            print(f"    [{i:>4}/{n}] {_elapsed(t0)} elapsed ...", end="\r", flush=True)

        best_score = 0.0
        best_pkg_name = None
        best_alias = None

        for alias in dc_alias_map[raw]:
            if _USE_RAPIDFUZZ:
                result = rf_process.extractOne(
                    alias,
                    pkg_names_list,
                    scorer=rf_fuzz.token_sort_ratio,
                    score_cutoff=FUZZY_THRESHOLD,
                )
                if result and result[1] > best_score:
                    best_score = result[1]
                    best_pkg_name = result[0]
                    best_alias = alias
            else:
                for pkg_name in pkg_names_list:
                    score = difflib.SequenceMatcher(None, alias, pkg_name).ratio() * 100
                    if score >= FUZZY_THRESHOLD and score > best_score:
                        best_score = score
                        best_pkg_name = pkg_name
                        best_alias = alias

        if best_pkg_name:
            db_id = pkg_lookup[best_pkg_name]
            fuzzy_matched[raw] = db_id
            fuzzy_details.append((raw, best_alias, best_pkg_name, round(best_score, 1), db_id))
        else:
            still_unmatched.add(raw)

    print()  # newline after \r progress
    print(f"\n  Fuzzy matches recovered: {len(fuzzy_matched):,}")
    print(f"  Still unmatched:         {len(still_unmatched):,}")

    # Print sample of 15 fuzzy matches for manual review
    print(f"\n  Sample of up to 15 fuzzy matches (eyeball for sanity):")
    print(f"  {'DrugComb Name':<40}  {'Matched PrimeKG Name':<35}  {'Score':>5}")
    print("  " + "-" * 85)
    for dc_raw, dc_alias, pkg_name, score, db_id in fuzzy_details[:15]:
        alias_note = f" [via: '{dc_alias}']" if dc_alias != normalize(dc_raw) else ""
        print(f"  {dc_raw:<40}  {pkg_name:<35}  {score:>5.1f}{alias_note}")

    return fuzzy_matched, still_unmatched


# ---------------------------------------------------------------------------
# Step 5 — Save unmatched list
# ---------------------------------------------------------------------------

def save_unmatched(still_unmatched: set[str], dc: pd.DataFrame) -> None:
    _sep("Step 5 — Saving unmatched drugs")

    # Classify unmatched: CAS (ddd-dd-d), internal code, or name
    def classify(name: str) -> str:
        if re.fullmatch(r"\d{2,7}-\d{2}-\d", name.strip()):
            return "CAS_number"
        if re.search(r"[A-Z0-9]{4,}-\d{2,}", name):
            return "internal_code"
        if name[0].isdigit():
            return "numeric_start"
        return "name_not_found"

    rows = []
    for raw in sorted(still_unmatched):
        # Count how many DrugComb experiments use this drug
        mask = (dc["drug_row"] == raw) | (dc["drug_col"] == raw)
        n_experiments = mask.sum()
        rows.append({
            "raw_name": raw,
            "category": classify(raw),
            "experiment_count": n_experiments,
        })

    df_unmatched = pd.DataFrame(rows).sort_values(
        ["category", "experiment_count"], ascending=[True, False]
    ).reset_index(drop=True)

    os.makedirs(PROCESSED_DIR, exist_ok=True)
    df_unmatched.to_csv(OUT_UNMATCHED, index=False)
    print(f"  Saved {len(df_unmatched):,} unmatched drugs → {OUT_UNMATCHED}")

    print("\n  Breakdown by category:")
    for cat, cnt in df_unmatched["category"].value_counts().items():
        print(f"    {cat:<22} : {cnt:>4}")

    print("\n  Top 10 unmatched by experiment count (most impactful drops):")
    print(f"  {'Drug Name':<40}  {'Category':<18}  {'Experiments':>11}")
    print("  " + "-" * 74)
    for _, r in df_unmatched.head(10).iterrows():
        print(f"  {r['raw_name']:<40}  {r['category']:<18}  {r['experiment_count']:>11,}")


# ---------------------------------------------------------------------------
# Step 6 — Build labeled dataset
# ---------------------------------------------------------------------------

def build_labeled_dataset(
    dc: pd.DataFrame,
    matched: dict[str, str],
) -> pd.DataFrame:
    _sep("Step 6 — Building labeled drug-pair dataset")

    # Map raw names to DrugBank IDs
    df = dc.copy()
    df["drug_a_kg_id"] = df["drug_row"].map(matched)
    df["drug_b_kg_id"] = df["drug_col"].map(matched)

    # Keep only rows where BOTH drugs mapped
    before = len(df)
    df = df.dropna(subset=["drug_a_kg_id", "drug_b_kg_id"]).copy()
    after = len(df)
    print(f"  Rows before both-drug filter: {before:,}")
    print(f"  Rows after  both-drug filter: {after:,}  (dropped {before - after:,})")

    # Percentile-based class assignment (computed on the filtered, matched dataset)
    lo_cut = df["synergy_loewe"].quantile(SYNERGY_LO_PCTILE / 100)
    hi_cut = df["synergy_loewe"].quantile(SYNERGY_HI_PCTILE / 100)
    print(f"\n  Percentile cutoffs (computed on {after:,} matched rows):")
    print(f"    {SYNERGY_LO_PCTILE}th percentile (antagonism threshold) : {lo_cut:>10.4f}")
    print(f"    {SYNERGY_HI_PCTILE}th percentile (synergy threshold)    : {hi_cut:>10.4f}")

    def synergy_class(score: float) -> str:
        if score >= hi_cut:
            return "synergy"
        if score <= lo_cut:
            return "antagonism"
        return "additive"

    df["synergy_class"] = df["synergy_loewe"].apply(synergy_class)

    # Select and rename output columns
    labeled = df[[
        "drug_a_kg_id", "drug_b_kg_id",
        "drug_row", "drug_col",
        "cell_line_name", "synergy_loewe", "synergy_class",
    ]].reset_index(drop=True)

    # Rename for clarity
    labeled = labeled.rename(columns={
        "drug_row": "drug_a_name",
        "drug_col": "drug_b_name",
    })

    return labeled


# ---------------------------------------------------------------------------
# Step 7 — Class balance report
# ---------------------------------------------------------------------------

def report_class_balance(labeled: pd.DataFrame) -> None:
    _sep("Step 7 — Class balance report")
    total = len(labeled)
    counts = labeled["synergy_class"].value_counts()

    print(f"\n  Total labeled pairs: {total:,}")
    print(f"\n  {'Class':<15}  {'Count':>10}  {'%':>8}")
    print("  " + "-" * 38)
    for cls in ["synergy", "additive", "antagonism"]:
        cnt = counts.get(cls, 0)
        pct = 100 * cnt / total if total else 0
        print(f"  {cls:<15}  {cnt:>10,}  {pct:>7.1f}%")

    majority = counts.index[0]
    majority_pct = 100 * counts.iloc[0] / total
    if majority_pct > 60:
        print(f"\n  ⚠  Class imbalance detected: '{majority}' is {majority_pct:.1f}% of data.")
        print(f"     Consider: class-weighted loss, oversampling minority, or stratified splits.")
    else:
        print(f"\n  ✓  Class distribution looks reasonably balanced.")

    print(f"\n  Unique drug pairs (unordered): "
          f"{labeled[['drug_a_kg_id','drug_b_kg_id']].apply(frozenset, axis=1).nunique():,}")
    print(f"  Unique cell lines:            {labeled['cell_line_name'].nunique():,}")


# ---------------------------------------------------------------------------
# Step 8 — Save labeled dataset
# ---------------------------------------------------------------------------

def save_labeled(labeled: pd.DataFrame) -> None:
    _sep("Step 8 — Saving labeled pairs")
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    labeled.to_csv(OUT_LABELED, index=False)
    print(f"  Saved {len(labeled):,} labeled rows → {OUT_LABELED}")
    print(f"\n  Sample (first 5 rows):")
    print(labeled.head(5).to_string(index=False))


# ---------------------------------------------------------------------------
# Final summary
# ---------------------------------------------------------------------------

def print_summary(
    total_dc_drugs: int,
    n_exact: int,
    n_fuzzy: int,
    n_unmatched: int,
    n_labeled_rows: int,
) -> None:
    _sep("FINAL SUMMARY")
    print(f"\n  {'Metric':<45}  {'Count':>8}")
    print("  " + "-" * 57)
    print(f"  {'Unique drug strings in DrugComb':<45}  {total_dc_drugs:>8,}")
    print(f"  {'Matched — exact (pass 1)':<45}  {n_exact:>8,}  "
          f"({100*n_exact/total_dc_drugs:.1f}%)")
    print(f"  {'Matched — fuzzy ≥90 (pass 2)':<45}  {n_fuzzy:>8,}  "
          f"({100*n_fuzzy/total_dc_drugs:.1f}%)")
    print(f"  {'Total matched':<45}  {n_exact+n_fuzzy:>8,}  "
          f"({100*(n_exact+n_fuzzy)/total_dc_drugs:.1f}%)")
    print(f"  {'Unmatched (saved to unmatched_drugs.csv)':<45}  {n_unmatched:>8,}  "
          f"({100*n_unmatched/total_dc_drugs:.1f}%)")
    print(f"  {'Labeled pair rows (both drugs matched)':<45}  {n_labeled_rows:>8,}")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    _sep("Drug Name Entity Resolution + Label Construction")
    t_total = time.time()

    # Step 1
    dc, pkg = load_data()

    # Step 2
    pkg_lookup = build_pkg_lookup(pkg)

    # Collect all unique DC drugs
    _sep("Step 2b — Collecting unique DrugComb drug names")
    dc_alias_map = collect_drugcomb_drugs(dc)
    total_dc_drugs = len(dc_alias_map)

    # Step 3 — exact match
    exact_matched, unmatched_after_exact = exact_match(dc_alias_map, pkg_lookup)

    # Step 4 — fuzzy match
    fuzzy_matched, still_unmatched = fuzzy_match(
        unmatched_after_exact, pkg_lookup, dc_alias_map
    )

    # Merge all matched
    all_matched: dict[str, str] = {**exact_matched, **fuzzy_matched}

    # Step 5 — save unmatched
    save_unmatched(still_unmatched, dc)

    # Step 6 — build labeled dataset
    labeled = build_labeled_dataset(dc, all_matched)

    # Step 7 — class balance
    report_class_balance(labeled)

    # Step 8 — save
    save_labeled(labeled)

    # Summary
    print_summary(
        total_dc_drugs=total_dc_drugs,
        n_exact=len(exact_matched),
        n_fuzzy=len(fuzzy_matched),
        n_unmatched=len(still_unmatched),
        n_labeled_rows=len(labeled),
    )

    print(f"  Total wall-clock time: {_elapsed(t_total)}")


if __name__ == "__main__":
    main()
