import csv
import re

with open("data/processed/cell_line_metadata.csv", "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    rows = list(reader)

NON_CANCER_KEYWORDS = {
    "epilepsy", "seizure", "alzheimer", "parkinson", "dementia", "huntington",
    "diabetes", "hypertension", "schizophrenia", "depression", "bipolar",
    "asthma", "arthritis", "rheumatoid", "multiple sclerosis", "lupus",
    "crohn", "colitis", "hepatitis", "cirrhosis", "atherosclerosis",
    "obesity", "hyperlipidemia", "anemia", "heart failure", "stroke",
    "glaucoma", "macular degeneration", "osteoporosis", "infection", "sepsis",
    "malaria", "tuberculosis", "pneumonia", "covid", "hiv", "cystic fibrosis"
}

GENERIC_CANCER_WORDS = {
    "cancer", "carcinoma", "adenocarcinoma", "neoplasm", "neoplasms",
    "tumor", "tumour", "tumors", "tumours", "malignant", "malignancy",
    "sarcoma", "lymphoma", "leukemia", "leukaemia", "myeloma", "disease"
}

# Stop words
STOP_WORDS = {"of", "the", "and", "in", "a", "an", "for", "with", "to", "type", "cell", "cells"}

def score_cell_line(row, query):
    q = query.lower().strip()
    # Check non-cancer explicitly
    for nc in NON_CANCER_KEYWORDS:
        if re.search(r"\b" + re.escape(nc) + r"\b", q):
            # Unless explicitly combined with cancer words
            if not any(cw in q for cw in ["cancer", "carcinoma", "neoplasm", "tumor", "tumour", "melanoma", "sarcoma"]):
                return 0, []

    q_tokens = [w for w in re.findall(r"\w+", q) if w not in STOP_WORDS]
    if not q_tokens:
        return 0, []

    tissue = row["tissue"].lower()
    cancer_type = row["cancer_type"].lower()
    keywords = row["keywords"].lower()
    cl_name = row["cell_line_name"].lower()

    score = 0
    matched_reasons = []

    # Check full query substring in tissue, cancer_type, or keywords
    if len(q_tokens) > 1 and q in keywords:
        score += 30
        matched_reasons.append(f"full phrase '{q}' in keywords")
    elif len(q_tokens) > 1 and q in cancer_type:
        score += 30
        matched_reasons.append(f"full phrase '{q}' in cancer_type")

    # Check individual tokens
    for token in q_tokens:
        # Check tissue match (highest biological specificity)
        if re.search(r"\b" + re.escape(token), tissue):
            score += 25
            matched_reasons.append(f"token '{token}' in tissue ({row['tissue']})")
        # Check cancer_type match
        elif re.search(r"\b" + re.escape(token), cancer_type):
            pts = 15 if token not in GENERIC_CANCER_WORDS else 3
            score += pts
            matched_reasons.append(f"token '{token}' in cancer_type (+{pts})")
        # Check keywords match
        elif re.search(r"\b" + re.escape(token), keywords):
            pts = 10 if token not in GENERIC_CANCER_WORDS else 2
            score += pts
            matched_reasons.append(f"token '{token}' in keywords (+{pts})")

    return score, matched_reasons

test_queries = [
    "glioblastoma",
    "colorectal carcinoma",
    "prostate adenocarcinoma",
    "pancreatic cancer",
    "renal cell carcinoma",
    "epilepsy",
    "Alzheimer's disease"
]

for tq in test_queries:
    scores = []
    for r in rows:
        sc, reasons = score_cell_line(r, tq)
        if sc > 0:
            scores.append((r["cell_line_name"], r["tissue"], r["cancer_type"], sc, reasons))
    scores.sort(key=lambda x: -x[3])
    print(f"\n=======================================================")
    print(f"QUERY: '{tq}' -> {len(scores)} cell lines with score > 0")
    print(f"=======================================================")
    if scores:
        max_sc = scores[0][3]
        print(f"Max score: {max_sc}")
        # Top tier: score >= max_sc * 0.6 or top 10
        top_tier = [s for s in scores if s[3] >= max_sc * 0.6][:12]
        print(f"Top tier ({len(top_tier)} lines):")
        for s in top_tier:
            print(f"  {s[0]} ({s[1]} | {s[2]}): score={s[3]} | {s[4]}")
    else:
        print("  NO MATCHES (Cleanly rejected)")
