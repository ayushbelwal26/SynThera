import pandas as pd

nodes = pd.read_csv("data/processed/primekg_nodes.csv")
print("Node types:\n", nodes["node_type"].value_counts())

diseases = nodes[nodes["node_type"] == "disease"]
print(f"Total diseases: {len(diseases)}")
print("Sample diseases:\n", diseases["name"].head(20).tolist())

# Check glioblastoma
gbm = diseases[diseases["name"].str.contains("glioblastoma", case=False, na=False)]
print("GBM diseases:\n", gbm[["id", "name"]].head(10))

# Check cancer diseases
cancer = diseases[diseases["name"].str.contains("cancer|carcinoma|sarcoma|melanoma|glioma|lymphoma|leukemia|neoplasm", case=False, na=False)]
print(f"Total cancer-like diseases in PrimeKG: {len(cancer)}")
print("Sample cancer diseases:\n", cancer["name"].head(15).tolist())
