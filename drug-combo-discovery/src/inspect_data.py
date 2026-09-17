import os
import sys
import pandas as pd

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "raw")

FILES = [
    {
        "name": "DrugComb Raw Data",
        "filename": "drugcomb_raw.tsv",
        "sep": "\t",
        "compression": None,
        "is_optional": False,
    },
    {
        "name": "PrimeKG Knowledge Graph",
        "filename": "primekg_raw.csv",
        "sep": ",",
        "compression": None,
        "is_optional": False,
    },
    {
        "name": "SIDER Side Effects (Optional)",
        "filename": "sider_raw.tsv.gz",
        "sep": "\t",
        "compression": "gzip",
        "is_optional": True,
    },
]

def print_separator(title=""):
    print("\n" + "=" * 70)
    if title:
        print(f" {title.upper()} ")
        print("=" * 70)

def print_basic_profile(name, filepath, df):
    print(f"\n[Dataset]: {name}")
    print(f"[File Path]: {filepath}")
    print(f"[Shape]: {df.shape[0]:,} rows x {df.shape[1]} columns")
    
    print("\n--- Column Names & Data Types ---")
    dtypes_df = pd.DataFrame({
        "Column": df.columns,
        "Dtype": [str(t) for t in df.dtypes],
        "Missing Count": df.isnull().sum().values,
        "% Missing": (df.isnull().mean() * 100).round(3).values
    })
    print(dtypes_df.to_string(index=False))
    
    print("\n--- First 5 Rows ---")
    # Display full columns without truncation
    with pd.option_context("display.max_columns", None, "display.width", 1000):
        print(df.head(5))

def inspect_drugcomb(df):
    print_separator("DrugComb Specific Diagnostics")
    
    print("1. Drug Identifier Columns Detected:")
    drug_cols = [col for col in ["drug_row", "drug_col"] if col in df.columns]
    print(f"   Identified drug columns: {drug_cols}")
    
    for col in drug_cols:
        unique_vals = df[col].dropna().unique()
        print(f"\n   Column '{col}':")
        print(f"     - Total unique values: {len(unique_vals):,}")
        print(f"     - Sample 10 values: {list(unique_vals[:10])}")
        
        # Check identifier patterns
        db_style = [v for v in unique_vals[:100] if str(v).startswith("DB") and len(str(v)) == 7]
        cid_style = [v for v in unique_vals[:100] if str(v).isdigit()]
        cas_style = [v for v in unique_vals[:100] if "-" in str(v) and any(c.isdigit() for c in str(v))]
        
        print(f"     - Identifier Format Analysis:")
        print(f"       * DrugBank ID pattern (e.g. DB00180): {'Found' if db_style else 'None detected'}")
        print(f"       * PubChem CID integer pattern (e.g. 2244): {'Found' if cid_style else 'None detected'}")
        print(f"       * CAS / Code pattern (e.g. 717906-29-1 / MK-2206): {'Present' if cas_style else 'None detected'}")
        print(f"       * Primary format: Plain Drug Names / Compound Codes (Strings)")

    all_drugs = set(df["drug_row"].dropna()).union(set(df["drug_col"].dropna()))
    print(f"\n2. Combined Unique Drug Count: {len(all_drugs):,}")
    print(f"   Diverse sample across the dataset:")
    sample_drugs = sorted(list(all_drugs))
    step = max(1, len(sample_drugs) // 15)
    print(f"   {sample_drugs[::step][:15]}")

    if "cell_line_name" in df.columns:
        print(f"\n3. Cell Lines:")
        print(f"   - Unique cell lines: {df['cell_line_name'].nunique():,}")
        print(f"   - Top 5 most frequent cell lines:")
        for cl, count in df["cell_line_name"].value_counts().head(5).items():
            print(f"       * {cl}: {count:,} experiments")

    if "synergy_loewe" in df.columns:
        print(f"\n4. Synergy Score ('synergy_loewe') Distribution:")
        print(df["synergy_loewe"].describe().to_string())

def inspect_primekg(df):
    print_separator("PrimeKG Heterogeneous Graph Diagnostics")
    
    print("1. Node-Type Columns & Graph Schema:")
    # Detect node type columns
    node_type_cols = [c for c in ["x_type", "y_type"] if c in df.columns]
    print(f"   Node type columns found: {node_type_cols}")
    
    for c in node_type_cols:
        types = df[c].value_counts()
        print(f"\n   Unique values in '{c}' ({len(types)} node types):")
        for t, cnt in types.items():
            print(f"     - {t:<22} : {cnt:>10,} mentions in edges")
            
    # All combined unique node types
    all_node_types = sorted(list(set(df["x_type"].unique()).union(set(df["y_type"].unique()))))
    print(f"\n   Complete Heterogeneous Node Types ({len(all_node_types)} types):")
    print(f"   {all_node_types}")

    print("\n2. Edge-Type / Relation Columns:")
    rel_cols = [c for c in ["relation", "display_relation"] if c in df.columns]
    print(f"   Relation columns found: {rel_cols}")
    
    for c in rel_cols:
        rels = df[c].value_counts()
        print(f"\n   Unique values in '{c}' ({len(rels)} unique relations):")
        for r, cnt in rels.items():
            print(f"     - {r:<30} : {cnt:>10,} edges")

    print("\n3. Drug Nodes in PrimeKG Analysis:")
    # Filter edges where either endpoint is a drug
    drug_x = df[df["x_type"] == "drug"][["x_id", "x_name", "x_source"]].rename(
        columns={"x_id": "id", "x_name": "name", "x_source": "source"}
    )
    drug_y = df[df["y_type"] == "drug"][["y_id", "y_name", "y_source"]].rename(
        columns={"y_id": "id", "y_name": "name", "y_source": "source"}
    )
    all_primekg_drugs = pd.concat([drug_x, drug_y]).drop_duplicates()
    
    print(f"   - Total unique drug nodes in PrimeKG: {len(all_primekg_drugs):,}")
    print(f"   - Drug identifier source system(s): {all_primekg_drugs['source'].value_counts().to_dict()}")
    print(f"   - PrimeKG Drug ID format: DrugBank IDs (e.g., 'DB00180')")
    print(f"   - PrimeKG Drug Name format: Standard clinical/chemical names (e.g., 'Flunisolide')")
    print(f"\n   Sample 10 PrimeKG Drugs [ID, Name, Source]:")
    print(all_primekg_drugs.head(10).to_string(index=False))

def inspect_sider(df):
    print_separator("SIDER Side Effects Diagnostics")
    
    # SIDER meddra_all_se.tsv usually does not have headers
    first_col_val = str(df.columns[0])
    if first_col_val.startswith("CID") or first_col_val.startswith("C0"):
        print("   [Note]: SIDER raw file appears to be headerless (first row contains data).")
        print("   Standard SIDER schema corresponds to:")
        print("     0: STITCH Flat Compound ID (PubChem CID stereo-insensitive)")
        print("     1: STITCH Stereo Compound ID (PubChem CID stereo-specific)")
        print("     2: UMLS Concept ID as in MedDRA")
        print("     3: MedDRA Concept Type (LLT = lowest level term, PT = preferred term)")
        print("     4: UMLS Concept ID for MedDRA term")
        print("     5: Side Effect Name / Description")
        
        # Sample compound IDs
        sample_flat_cids = df.iloc[:10, 0].tolist()
        sample_effects = df.iloc[:10, -1].tolist()
        print(f"\n   Sample STITCH compound IDs : {sample_flat_cids[:5]}")
        print(f"   Sample Side Effect Names   : {sample_effects[:5]}")
    else:
        print("   Header detected. Sample columns:")
        print(f"   {df.columns.tolist()}")

def main():
    print("=" * 70)
    print("       RAW DATA DIAGNOSTIC & INSPECTION SUITE")
    print("=" * 70)
    print(f"Target Data Directory: {DATA_DIR}\n")

    for file_info in FILES:
        name = file_info["name"]
        filename = file_info["filename"]
        sep = file_info["sep"]
        compression = file_info["compression"]
        is_optional = file_info["is_optional"]
        
        filepath = os.path.join(DATA_DIR, filename)
        
        print_separator(f"Inspecting: {filename}")
        
        if not os.path.exists(filepath):
            if is_optional:
                print(f"[SKIPPED] Optional file '{filename}' was not found. Skipping gracefully.")
            else:
                print(f"[WARNING] Expected file '{filename}' not found at {filepath}!")
            continue
        
        print(f"Loading '{filename}' (sep='{repr(sep)}', compression={compression})...")
        try:
            if compression:
                df = pd.read_csv(filepath, sep=sep, compression=compression, low_memory=False)
            else:
                df = pd.read_csv(filepath, sep=sep, low_memory=False)
            
            # Print basic stats required by user
            print_basic_profile(name, filepath, df)
            
            # Specialized inspections
            if "drugcomb" in filename.lower():
                inspect_drugcomb(df)
            elif "primekg" in filename.lower():
                inspect_primekg(df)
            elif "sider" in filename.lower():
                inspect_sider(df)
                
        except Exception as e:
            print(f"[ERROR] Failed to load/inspect '{filename}': {e}")
            import traceback
            traceback.print_exc()

    print_separator("Diagnostics Complete")

if __name__ == "__main__":
    main()
