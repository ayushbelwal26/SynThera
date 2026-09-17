import pandas as pd
import re

df = pd.read_csv("data/processed/cell_line_metadata.csv")
print("Total cell lines:", len(df))

# Check words across fields
for query in ["colorectal carcinoma", "prostate adenocarcinoma", "pancreatic cancer", "epilepsy"]:
    tokens = set(re.findall(r"\w+", query.lower()))
    matches = []
    for _, row in df.iterrows():
        text = f"{row['cell_line_name']} {row['tissue']} {row['cancer_type']} {row['lineage']} {row['keywords']}".lower()
        matched_tokens = [t for t in tokens if t in text]
        if matched_tokens:
            matches.append((row["cell_line_name"], row["tissue"], row["cancer_type"], matched_tokens))
    print(f"\nQuery: '{query}' -> {len(matches)} matches")
    for m in matches[:5]:
        print("  ", m)
