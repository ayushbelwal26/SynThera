"""
fetch_chemberta.py
==================
Extracts 768-dimensional molecular embeddings for all drugs with valid SMILES
using the pretrained ChemBERTa model ("seyonec/ChemBERTa-zinc-base-v1") from HuggingFace.

Outputs:
  - data/processed/drug_chemberta_embeddings.pt   (PyTorch dictionary for fast binary loading)
  - data/processed/drug_chemberta_embeddings.csv  (CSV format: drugbank_id, name, dim_0..dim_767)
"""

import os
import sys
import time
import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModel

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_DIR = os.path.join(ROOT, "data", "processed")
INPUT_CSV = os.path.join(PROCESSED_DIR, "drug_smiles_fingerprints.csv")
OUTPUT_PT = os.path.join(PROCESSED_DIR, "drug_chemberta_embeddings.pt")
OUTPUT_CSV = os.path.join(PROCESSED_DIR, "drug_chemberta_embeddings.csv")

MODEL_NAME = "seyonec/ChemBERTa-zinc-base-v1"
BATCH_SIZE = 64
MAX_LENGTH = 512
EMB_DIM = 768


def mean_pooling(model_output, attention_mask: torch.Tensor) -> torch.Tensor:
    """Mean-pools token embeddings using the attention mask."""
    token_embeddings = model_output[0]  # [B, seq_len, 768]
    input_mask_expanded = (
        attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    )
    sum_embeddings = torch.sum(token_embeddings * input_mask_expanded, dim=1)
    sum_mask = torch.clamp(input_mask_expanded.sum(dim=1), min=1e-9)
    return sum_embeddings / sum_mask


def main():
    t_start = time.time()
    print("=" * 70)
    print("  EXTRACTING ChemBERTa EMBEDDINGS (seyonec/ChemBERTa-zinc-base-v1)")
    print("=" * 70)

    # 1. Load input SMILES
    if not os.path.exists(INPUT_CSV):
        raise FileNotFoundError(f"Input file not found: {INPUT_CSV}")

    df = pd.read_csv(INPUT_CSV, dtype=str)
    # Filter rows with non-empty SMILES
    valid_mask = df["smiles"].notna() & (df["smiles"].str.strip() != "")
    df_valid = df[valid_mask].reset_index(drop=True)
    total_drugs = len(df_valid)
    print(f"  Loaded {len(df):,} total drug records from {os.path.basename(INPUT_CSV)}")
    print(f"  Found {total_drugs:,} drugs with valid SMILES strings")

    # 2. Load model and tokenizer
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"\n  Loading ChemBERTa from '{MODEL_NAME}' on {device}...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModel.from_pretrained(MODEL_NAME)
    model.to(device)
    model.eval()
    print(f"  Model loaded successfully. Embedding dimension: {EMB_DIM}")

    # 3. Batch inference
    print(f"\n  Extracting embeddings in batches of {BATCH_SIZE} on {device}...")
    all_embeddings = []
    all_drugbank_ids = []
    all_names = []

    num_batches = (total_drugs + BATCH_SIZE - 1) // BATCH_SIZE

    for b_idx in range(num_batches):
        start_idx = b_idx * BATCH_SIZE
        end_idx = min(start_idx + BATCH_SIZE, total_drugs)
        batch_slice = df_valid.iloc[start_idx:end_idx]

        smiles_list = batch_slice["smiles"].tolist()
        db_ids = batch_slice["drugbank_id"].tolist()
        names = batch_slice["name"].tolist()

        inputs = tokenizer(
            smiles_list,
            padding=True,
            truncation=True,
            max_length=MAX_LENGTH,
            return_tensors="pt",
        ).to(device)

        with torch.no_grad():
            outputs = model(**inputs)
            emb = mean_pooling(outputs, inputs["attention_mask"]).cpu()  # [B, 768]

        all_embeddings.append(emb)
        all_drugbank_ids.extend(db_ids)
        all_names.extend(names)

        # Progress every 1000 drugs
        if end_idx % 1000 < BATCH_SIZE or end_idx == total_drugs:
            elapsed = time.time() - t_start
            print(
                f"  [{end_idx:>5}/{total_drugs:,}] drugs processed  "
                f"({end_idx / total_drugs * 100:>5.1f}%)  "
                f"| Elapsed: {elapsed:.1f}s  "
                f"| Speed: {end_idx / max(elapsed, 0.01):.1f} drugs/s"
            )

    full_tensor = torch.cat(all_embeddings, dim=0)  # [total_drugs, 768]
    assert full_tensor.shape == (total_drugs, EMB_DIM), (
        f"Shape mismatch: {full_tensor.shape} != ({total_drugs}, {EMB_DIM})"
    )

    # 4. Save PyTorch tensor format (.pt) for fast binary loading
    print(f"\n  Saving PyTorch checkpoint to {OUTPUT_PT}...")
    torch.save(
        {
            "drugbank_id": all_drugbank_ids,
            "name": all_names,
            "embeddings": full_tensor,  # float32 [7122, 768]
        },
        OUTPUT_PT,
    )
    pt_size_mb = os.path.getsize(OUTPUT_PT) / 1e6
    print(f"  Saved {OUTPUT_PT} ({pt_size_mb:.2f} MB)")

    # 5. Save CSV format as requested
    print(f"\n  Saving CSV to {OUTPUT_CSV}...")
    emb_cols = [f"dim_{i}" for i in range(EMB_DIM)]
    emb_df = pd.DataFrame(full_tensor.numpy(), columns=emb_cols)
    emb_df.insert(0, "name", all_names)
    emb_df.insert(0, "drugbank_id", all_drugbank_ids)
    emb_df.to_csv(OUTPUT_CSV, index=False)
    csv_size_mb = os.path.getsize(OUTPUT_CSV) / 1e6
    print(f"  Saved {OUTPUT_CSV} ({csv_size_mb:.2f} MB)")

    # 6. Final summary
    total_time = time.time() - t_start
    print("\n" + "=" * 70)
    print("  COMPLETION SUMMARY")
    print("=" * 70)
    print(f"  Total drugs processed : {total_drugs:,}")
    print(f"  Embedding shape       : {tuple(full_tensor.shape)}")
    print(f"  Total wall-clock time : {total_time:.2f}s ({total_time / 60:.2f} min)")
    print(f"  Throughput            : {total_drugs / total_time:.1f} drugs/sec")
    print("=" * 70)


if __name__ == "__main__":
    main()
