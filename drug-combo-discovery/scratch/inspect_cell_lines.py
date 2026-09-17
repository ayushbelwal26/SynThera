import pandas as pd
import torch

print("--- Checking drugcomb_raw.tsv ---")
try:
    df_raw = pd.read_csv("data/raw/drugcomb_raw.tsv", sep="\t", nrows=5)
    print("drugcomb_raw columns:", df_raw.columns.tolist())
    print("Sample row:\n", df_raw.iloc[0].to_dict())
except Exception as e:
    print("drugcomb_raw error:", e)

print("\n--- Checking labeled_pairs.csv ---")
try:
    df_labeled = pd.read_csv("data/processed/labeled_pairs.csv", nrows=5)
    print("labeled_pairs columns:", df_labeled.columns.tolist())
    print("Sample row:\n", df_labeled.iloc[0].to_dict())
except Exception as e:
    print("labeled_pairs error:", e)

print("\n--- Checking heterodata.pt cell_line_map ---")
try:
    data = torch.load("data/processed/heterodata.pt", map_location="cpu", weights_only=False)
    print("heterodata keys:", dir(data))
    if hasattr(data, "cell_line_map"):
        print(f"cell_line_map count: {len(data.cell_line_map)}")
        sample_cls = list(data.cell_line_map.keys())[:15]
        print("Sample cell lines in cell_line_map:", sample_cls)
except Exception as e:
    print("heterodata error:", e)

print("\n--- Checking primekg_nodes.csv for disease types/nodes ---")
try:
    nodes = pd.read_csv("data/processed/primekg_nodes.csv", nrows=10)
    print("primekg_nodes columns:", nodes.columns.tolist())
    nodes_all = pd.read_csv("data/processed/primekg_nodes.csv")
    print("Node types:", nodes_all["type"].value_counts().to_dict() if "type" in nodes_all.columns else "no type col")
    if "type" in nodes_all.columns:
        diseases = nodes_all[nodes_all["type"] == "disease"]
        print(f"Total disease nodes: {len(diseases)}")
        print("Sample diseases:", diseases["name"].head(10).tolist() if "name" in diseases.columns else "no name col")
except Exception as e:
    print("primekg_nodes error:", e)
