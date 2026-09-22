"""
Pre-processes and caches toxicity and DDI data sources for fast O(1) runtime lookup:
1. SIDER 4.1 side-effect profiles joined to DrugBank IDs via PubChem CIDs & drug names.
2. PrimeKG DDI edge network (2.67M edges) joined to DrugBank IDs.

Outputs:
  - data/processed/sider_side_effects.json
  - data/processed/primekg_ddi_pairs.pt
  - data/processed/primekg_ddi_drugs.json
  - data/processed/toxicity_coverage_stats.json
"""

import os
import gzip
import json
import urllib.request
import pandas as pd
import torch

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT_DIR, "data")
RAW_DIR = os.path.join(DATA_DIR, "raw")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")

SIDER_RAW_GZ = os.path.join(RAW_DIR, "sider_raw.tsv.gz")
SIDER_NAMES_TSV = os.path.join(RAW_DIR, "sider_drug_names.tsv")
PRIMEKG_EDGES_CSV = os.path.join(PROCESSED_DIR, "primekg_edges.csv")
PRIMEKG_DRUGS_CSV = os.path.join(PROCESSED_DIR, "primekg_drugs.csv")
FINGERPRINTS_CSV = os.path.join(PROCESSED_DIR, "drug_smiles_fingerprints.csv")
LABELED_PAIRS_CSV = os.path.join(PROCESSED_DIR, "labeled_pairs.csv")

OUT_SIDER_JSON = os.path.join(PROCESSED_DIR, "sider_side_effects.json")
OUT_DDI_PT = os.path.join(PROCESSED_DIR, "primekg_ddi_pairs.pt")
OUT_DDI_DRUGS_JSON = os.path.join(PROCESSED_DIR, "primekg_ddi_drugs.json")
OUT_STATS_JSON = os.path.join(PROCESSED_DIR, "toxicity_coverage_stats.json")


def ensure_sider_drug_names():
    if os.path.exists(SIDER_NAMES_TSV):
        return
    print("Downloading official SIDER drug_names.tsv...")
    url = "http://sideeffects.embl.de/media/download/drug_names.tsv"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SynThera/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read()
        with open(SIDER_NAMES_TSV, "wb") as f:
            f.write(content)
        print(f"Saved SIDER drug names to {SIDER_NAMES_TSV}")
    except Exception as e:
        print(f"Warning: Could not download SIDER drug names ({e}). Will proceed with CID mapping.")


def parse_sider():
    if os.path.exists(OUT_SIDER_JSON):
        print(f"Loading cached SIDER profiles from {OUT_SIDER_JSON}...")
        with open(OUT_SIDER_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {k: set(v) for k, v in data.items()}

    print("Parsing SIDER side effect profiles...")
    ensure_sider_drug_names()

    # 1. Parse SIDER drug_names.tsv if present: STITCH CID -> set of drug names
    stitch_to_names = {}
    name_to_stitch = {}
    if os.path.exists(SIDER_NAMES_TSV):
        with open(SIDER_NAMES_TSV, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                parts = line.strip().split("\t")
                if len(parts) >= 2:
                    cid_str, name = parts[0], parts[1].strip().lower()
                    stitch_to_names.setdefault(cid_str, set()).add(name)
                    name_to_stitch[name] = cid_str

    # 2. Parse sider_raw.tsv.gz (meddra_all_se.tsv)
    # Schema: flat_id, stereo_id, umls_concept, concept_type, meddra_concept, se_name
    pubchem_to_se = {}
    stitch_to_se = {}

    with gzip.open(SIDER_RAW_GZ, "rt", encoding="utf-8", errors="ignore") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) < 6:
                continue
            c_flat, c_stereo, se_name = parts[0], parts[1], parts[5]

            # Save under raw STITCH IDs
            stitch_to_se.setdefault(c_flat, set()).add(se_name)
            stitch_to_se.setdefault(c_stereo, set()).add(se_name)

            # Convert to numeric PubChem CID
            for c in (c_flat, c_stereo):
                try:
                    val = int(c.replace("CID", ""))
                    pub_id = val - 100000000 if val >= 100000000 else val
                    pubchem_to_se.setdefault(pub_id, set()).add(se_name)
                except ValueError:
                    pass

    # Map name directly to side effects
    name_to_se = {}
    for stitch_id, names in stitch_to_names.items():
        effects = stitch_to_se.get(stitch_id)
        if effects:
            for n in names:
                name_to_se.setdefault(n, set()).update(effects)

    print(f"  SIDER: {len(pubchem_to_se):,} unique PubChem CIDs with side effects")
    print(f"  SIDER: {len(name_to_se):,} unique drug names with side effects")

    # 3. Join to PrimeKG DrugBank IDs
    print("Joining SIDER profiles to PrimeKG drugs...")
    fps_df = pd.read_csv(FINGERPRINTS_CSV, usecols=["drugbank_id", "name", "cid"])
    fps_df = fps_df.dropna(subset=["drugbank_id"])

    drugs_df = pd.read_csv(PRIMEKG_DRUGS_CSV)
    drug_names_map = dict(zip(drugs_df["drugbank_id"], drugs_df["drug_name"].astype(str).str.lower()))

    db_to_effects = {}
    matched_by_cid = 0
    matched_by_name = 0

    for _, row in fps_df.iterrows():
        db_id = str(row["drugbank_id"])
        cid_val = row["cid"]
        matched = False

        # Attempt 1: PubChem CID match
        if pd.notna(cid_val):
            try:
                cid_int = int(cid_val)
                if cid_int in pubchem_to_se:
                    db_to_effects[db_id] = pubchem_to_se[cid_int]
                    matched_by_cid += 1
                    matched = True
            except ValueError:
                pass

        # Attempt 2: Drug name match if not matched by CID
        if not matched:
            drug_name = drug_names_map.get(db_id, "").strip().lower()
            if drug_name and drug_name in name_to_se:
                db_to_effects[db_id] = name_to_se[drug_name]
                matched_by_name += 1
                matched = True

    # Also check remaining drugs in primekg_drugs.csv
    for db_id, drug_name in drug_names_map.items():
        if db_id not in db_to_effects:
            d_name = drug_name.strip().lower()
            if d_name and d_name in name_to_se:
                db_to_effects[db_id] = name_to_se[d_name]
                matched_by_name += 1

    print(f"  Total PrimeKG drugs mapped to SIDER: {len(db_to_effects):,} "
          f"(CID matches: {matched_by_cid:,}, Name matches: {matched_by_name:,})")

    # Convert sets to sorted lists for JSON serialization
    serializable = {k: sorted(list(v)) for k, v in db_to_effects.items()}
    with open(OUT_SIDER_JSON, "w", encoding="utf-8") as f:
        json.dump(serializable, f)
    print(f"  Saved SIDER cache -> {OUT_SIDER_JSON} ({os.path.getsize(OUT_SIDER_JSON)/(1024*1024):.2f} MB)")

    return db_to_effects


def parse_primekg_ddi():
    if os.path.exists(OUT_DDI_PT) and os.path.exists(OUT_DDI_DRUGS_JSON):
        print(f"Loading cached DDI pairs from {OUT_DDI_PT}...")
        ddi_pairs = torch.load(OUT_DDI_PT, weights_only=False)
        with open(OUT_DDI_DRUGS_JSON, "r", encoding="utf-8") as f:
            ddi_drugs = set(json.load(f))
        return ddi_pairs, ddi_drugs

    print("\nParsing PrimeKG DDI edge network...")
    # Read only drug_drug relation from primekg_edges.csv
    edges_iter = pd.read_csv(
        PRIMEKG_EDGES_CSV,
        chunksize=250000,
        usecols=["source", "target", "relation"],
        low_memory=False,
    )

    ddi_pairs = set()
    ddi_drugs = set()
    total_edges = 0

    for chunk in edges_iter:
        sub = chunk[chunk["relation"] == "drug_drug"]
        if len(sub) == 0:
            continue
        total_edges += len(sub)
        srcs = sub["source"].astype(str).values
        dsts = sub["target"].astype(str).values

        for s, d in zip(srcs, dsts):
            ddi_drugs.add(s)
            ddi_drugs.add(d)
            if s <= d:
                ddi_pairs.add((s, d))
            else:
                ddi_pairs.add((d, s))

    print(f"  Total raw drug_drug edges scanned: {total_edges:,}")
    print(f"  Total canonical undirected DDI pairs: {len(ddi_pairs):,}")
    print(f"  Total unique drugs in DDI network: {len(ddi_drugs):,}")

    # Save pairs as torch tensor or serialized set
    # Using torch.save for fast native binary loading
    torch.save(ddi_pairs, OUT_DDI_PT)
    print(f"  Saved DDI pairs -> {OUT_DDI_PT} ({os.path.getsize(OUT_DDI_PT)/(1024*1024):.2f} MB)")

    with open(OUT_DDI_DRUGS_JSON, "w", encoding="utf-8") as f:
        json.dump(sorted(list(ddi_drugs)), f)
    print(f"  Saved DDI drug universe -> {OUT_DDI_DRUGS_JSON}")

    return ddi_pairs, ddi_drugs


def compute_coverage_statistics(sider_effects: dict, ddi_pairs: set, ddi_drugs: set):
    print("\nComputing comprehensive coverage statistics...")
    primekg_drugs_df = pd.read_csv(PRIMEKG_DRUGS_CSV)
    total_primekg_drugs = len(primekg_drugs_df)
    primekg_drug_ids = set(primekg_drugs_df["drugbank_id"])

    labeled_pairs_df = pd.read_csv(LABELED_PAIRS_CSV)
    total_pairs = len(labeled_pairs_df)
    synergy_drugs = set(labeled_pairs_df["drug_a_kg_id"]).union(set(labeled_pairs_df["drug_b_kg_id"]))
    total_synergy_drugs = len(synergy_drugs)

    # 1. Drug-level coverage
    pk_sider_covered = len(primekg_drug_ids & set(sider_effects.keys()))
    pk_ddi_covered = len(primekg_drug_ids & ddi_drugs)
    pk_both_covered = len(primekg_drug_ids & set(sider_effects.keys()) & ddi_drugs)

    syn_sider_covered = len(synergy_drugs & set(sider_effects.keys()))
    syn_ddi_covered = len(synergy_drugs & ddi_drugs)
    syn_both_covered = len(synergy_drugs & set(sider_effects.keys()) & ddi_drugs)

    # 2. Pair-level coverage across all 151,264 synergy pairs
    a_drugs = labeled_pairs_df["drug_a_kg_id"].astype(str).values
    b_drugs = labeled_pairs_df["drug_b_kg_id"].astype(str).values

    sider_set = set(sider_effects.keys())

    sider_pair_coverage = 0
    ddi_pair_known = 0
    ddi_universe_coverage = 0

    for a, b in zip(a_drugs, b_drugs):
        # SIDER coverage: both drugs have side effects
        if a in sider_set and b in sider_set:
            sider_pair_coverage += 1

        # DDI status: is canonical pair in DDI graph?
        pair_key = (a, b) if a <= b else (b, a)
        if pair_key in ddi_pairs:
            ddi_pair_known += 1

        # DDI universe coverage: are both drugs tracked in DDI network?
        if a in ddi_drugs and b in ddi_drugs:
            ddi_universe_coverage += 1

    stats = {
        "primekg_total_drugs": total_primekg_drugs,
        "primekg_sider_covered": pk_sider_covered,
        "primekg_sider_pct": pk_sider_covered / total_primekg_drugs * 100,
        "primekg_ddi_covered": pk_ddi_covered,
        "primekg_ddi_pct": pk_ddi_covered / total_primekg_drugs * 100,
        "primekg_both_covered": pk_both_covered,
        "primekg_both_pct": pk_both_covered / total_primekg_drugs * 100,

        "synergy_total_drugs": total_synergy_drugs,
        "synergy_sider_covered": syn_sider_covered,
        "synergy_sider_pct": syn_sider_covered / total_synergy_drugs * 100,
        "synergy_ddi_covered": syn_ddi_covered,
        "synergy_ddi_pct": syn_ddi_covered / total_synergy_drugs * 100,
        "synergy_both_covered": syn_both_covered,
        "synergy_both_pct": syn_both_covered / total_synergy_drugs * 100,

        "synergy_total_pairs": total_pairs,
        "pairs_with_sider_overlap": sider_pair_coverage,
        "pairs_with_sider_overlap_pct": sider_pair_coverage / total_pairs * 100,
        "pairs_with_known_ddi": ddi_pair_known,
        "pairs_with_known_ddi_pct": ddi_pair_known / total_pairs * 100,
        "pairs_in_ddi_universe": ddi_universe_coverage,
        "pairs_in_ddi_universe_pct": ddi_universe_coverage / total_pairs * 100,
    }

    with open(OUT_STATS_JSON, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    print("\n" + "=" * 75)
    print("  TOXICITY & DDI SIGNAL LAYER COVERAGE REPORT")
    print("=" * 75)
    print(f"Total PrimeKG Drugs: {total_primekg_drugs:,}")
    print(f"  |-- SIDER Profile:    {pk_sider_covered:>5,} ({stats['primekg_sider_pct']:5.1f}%)")
    print(f"  |-- DDI Network:      {pk_ddi_covered:>5,} ({stats['primekg_ddi_pct']:5.1f}%)")
    print(f"  \\-- Both Sources:     {pk_both_covered:>5,} ({stats['primekg_both_pct']:5.1f}%)")
    print(f"\nSynergy Dataset Drugs ({total_synergy_drugs:,} unique in labeled_pairs):")
    print(f"  |-- SIDER Profile:    {syn_sider_covered:>5,} ({stats['synergy_sider_pct']:5.1f}%)")
    print(f"  |-- DDI Network:      {syn_ddi_covered:>5,} ({stats['synergy_ddi_pct']:5.1f}%)")
    print(f"  \\-- Both Sources:     {syn_both_covered:>5,} ({stats['synergy_both_pct']:5.1f}%)")
    print(f"\nSynergy Pairs ({total_pairs:,} total in labeled_pairs):")
    print(f"  |-- SIDER Overlap Available: {sider_pair_coverage:>7,} ({stats['pairs_with_sider_overlap_pct']:5.1f}%)")
    print(f"  |-- Known DDI Flagged (True):{ddi_pair_known:>7,} ({stats['pairs_with_known_ddi_pct']:5.1f}%)")
    print(f"  \\-- In DDI Universe (Known): {ddi_universe_coverage:>7,} ({stats['pairs_in_ddi_universe_pct']:5.1f}%)")
    print("=" * 75)

    return stats


def main():
    sider_effects = parse_sider()
    ddi_pairs, ddi_drugs = parse_primekg_ddi()
    compute_coverage_statistics(sider_effects, ddi_pairs, ddi_drugs)
    print("\nToxicity caching completed successfully!")


if __name__ == "__main__":
    main()
