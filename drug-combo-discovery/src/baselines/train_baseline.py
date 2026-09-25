"""
src/baselines/train_baseline.py
===============================
Training pipeline for the DeepSynergy-style MLP baseline.
Trains models separately on:
  1. Cold-drug split (split_train.csv, split_val.csv)
  2. Warm-random split (splits_extra/warm_random_train.csv, splits_extra/warm_random_val.csv)

Uses the exact same class-weighting formula as train.py:
  weight_c = sqrt(N_total / (3 * N_c))
"""

from __future__ import annotations

import os
import sys
import time
import argparse
from typing import Dict, Tuple

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC_DIR = os.path.join(ROOT_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from baselines.mlp_baseline import DeepSynergyMLP

PROCESSED_DIR = os.path.join(ROOT_DIR, "data", "processed")
SPLITS_EXTRA_DIR = os.path.join(PROCESSED_DIR, "splits_extra")
HETERODATA_PATH = os.path.join(PROCESSED_DIR, "heterodata.pt")
LABELS_PATH = os.path.join(PROCESSED_DIR, "labeled_pairs.csv")
NODES_PATH = os.path.join(PROCESSED_DIR, "primekg_nodes.csv")
BASELINES_DIR = os.path.join(ROOT_DIR, "models", "baselines")
os.makedirs(BASELINES_DIR, exist_ok=True)

CLASS_MAP = {"antagonism": 0, "additive": 1, "synergy": 2}


class PairDataset(Dataset):
    """
    Dataset storing pre-indexed drug fingerprint references and cell-line IDs.
    """

    def __init__(
        self,
        pairs_df: pd.DataFrame,
        drug_fps: torch.Tensor,
        drug_map: Dict[str, int],
        cell_map: Dict[str, int],
    ):
        super().__init__()
        self.drug_fps = drug_fps

        a_indices = pairs_df["drug_a_kg_id"].astype(str).map(drug_map).astype(int).values
        b_indices = pairs_df["drug_b_kg_id"].astype(str).map(drug_map).astype(int).values
        c_indices = pairs_df["cell_line_name"].map(cell_map).astype(int).values
        y_indices = pairs_df["synergy_class"].map(CLASS_MAP).astype(int).values

        self.a_indices = torch.tensor(a_indices, dtype=torch.long)
        self.b_indices = torch.tensor(b_indices, dtype=torch.long)
        self.c_indices = torch.tensor(c_indices, dtype=torch.long)
        self.labels = torch.tensor(y_indices, dtype=torch.long)

    def __len__(self) -> int:
        return len(self.labels)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        fp_a = self.drug_fps[self.a_indices[idx]]
        fp_b = self.drug_fps[self.b_indices[idx]]
        cell_idx = self.c_indices[idx]
        label = self.labels[idx]
        return fp_a, fp_b, cell_idx, label


def load_data_and_features():
    print(f"[1/4] Loading HeteroData from {HETERODATA_PATH}...")
    heterodata = torch.load(HETERODATA_PATH, weights_only=False)
    drug_fps = heterodata["drug"].x.clone().detach().to(dtype=torch.float32)

    print("Building drug ID and cell line index maps...")
    nodes = pd.read_csv(NODES_PATH)
    drug_sub = nodes[nodes["node_type"] == "drug"].reset_index(drop=True)
    drug_map = {str(row["id"]): i for i, (_, row) in enumerate(drug_sub.iterrows())}
    cell_map = heterodata.cell_line_map

    labels_df = pd.read_csv(LABELS_PATH)
    print(f"Loaded {len(labels_df):,} total labeled pairs.")

    return drug_fps, drug_map, cell_map, labels_df


def get_split_indices(split_type: str) -> Tuple[list[int], list[int], list[int]]:
    if split_type == "cold":
        train_path = os.path.join(PROCESSED_DIR, "split_train.csv")
        val_path = os.path.join(PROCESSED_DIR, "split_val.csv")
        test_path = os.path.join(PROCESSED_DIR, "split_test.csv")
    elif split_type == "warm_random":
        train_path = os.path.join(SPLITS_EXTRA_DIR, "warm_random_train.csv")
        val_path = os.path.join(SPLITS_EXTRA_DIR, "warm_random_val.csv")
        test_path = os.path.join(SPLITS_EXTRA_DIR, "warm_random_test.csv")
    else:
        raise ValueError(f"Unknown split_type: {split_type}")

    train_idx = pd.read_csv(train_path)["row_index"].tolist()
    val_idx = pd.read_csv(val_path)["row_index"].tolist()
    test_idx = pd.read_csv(test_path)["row_index"].tolist()
    return train_idx, val_idx, test_idx


def compute_soft_class_weights(labels_series: pd.Series) -> torch.Tensor:
    """
    Computes soft class weights: weight_c = sqrt(N_total / (3 * N_c)), matching train.py.
    """
    y = labels_series.map(CLASS_MAP).values
    n_total = float(len(y))
    weights = [
        np.sqrt(n_total / (3.0 * float((y == c).sum())))
        for c in range(3)
    ]
    return torch.tensor(weights, dtype=torch.float32)


def train_mlp_baseline(
    split_type: str = "cold",
    batch_size: int = 512,
    max_epochs: int = 30,
    lr: float = 1e-3,
    weight_decay: float = 1e-4,
    es_patience: int = 5,
    seed: int = 42,
    device: str | None = None,
) -> str:
    """
    Trains DeepSynergyMLP on the specified split and saves the best checkpoint.
    """
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    device_obj = torch.device(device)

    torch.manual_seed(seed)
    np.random.seed(seed)

    print("=" * 80)
    print(f"TRAINING DEEPSYNERGY MLP BASELINE (Split: {split_type.upper()}) on {device}")
    print("=" * 80)

    drug_fps, drug_map, cell_map, labels_df = load_data_and_features()
    train_idx, val_idx, test_idx = get_split_indices(split_type)

    train_df = labels_df.iloc[train_idx].reset_index(drop=True)
    val_df = labels_df.iloc[val_idx].reset_index(drop=True)
    test_df = labels_df.iloc[test_idx].reset_index(drop=True)

    class_weights = compute_soft_class_weights(train_df["synergy_class"]).to(device_obj)
    print(f"Computed soft class weights: {class_weights.tolist()}")

    train_ds = PairDataset(train_df, drug_fps, drug_map, cell_map)
    val_ds = PairDataset(val_df, drug_fps, drug_map, cell_map)

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, pin_memory=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, pin_memory=True)

    model = DeepSynergyMLP(
        fp_dim=2048,
        num_cell_lines=len(cell_map),
        cell_dim=64,
        hidden_dims=[512, 256, 128],
        dropout=0.2,
        num_classes=3,
    ).to(device_obj)

    criterion = nn.CrossEntropyLoss(weight=class_weights)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min", factor=0.5, patience=2, min_lr=1e-5
    )

    best_val_loss = float("inf")
    best_epoch = 0
    patience_counter = 0
    checkpoint_path = os.path.join(BASELINES_DIR, f"mlp_{split_type}.pt")

    t_start = time.time()
    for epoch in range(1, max_epochs + 1):
        model.train()
        train_loss_sum = 0.0
        n_train = 0

        for fp_a, fp_b, cell_idx, label in train_loader:
            fp_a = fp_a.to(device_obj, non_blocking=True)
            fp_b = fp_b.to(device_obj, non_blocking=True)
            cell_idx = cell_idx.to(device_obj, non_blocking=True)
            label = label.to(device_obj, non_blocking=True)

            optimizer.zero_grad()
            # Random symmetric order swap data augmentation during training
            if torch.rand(1).item() > 0.5:
                logits = model(fp_b, fp_a, cell_idx)
            else:
                logits = model(fp_a, fp_b, cell_idx)

            loss = criterion(logits, label)
            loss.backward()
            optimizer.step()

            train_loss_sum += loss.item() * len(label)
            n_train += len(label)

        train_loss = train_loss_sum / n_train

        # Validation pass
        model.eval()
        val_loss_sum = 0.0
        n_val = 0
        with torch.no_grad():
            for fp_a, fp_b, cell_idx, label in val_loader:
                fp_a = fp_a.to(device_obj, non_blocking=True)
                fp_b = fp_b.to(device_obj, non_blocking=True)
                cell_idx = cell_idx.to(device_obj, non_blocking=True)
                label = label.to(device_obj, non_blocking=True)

                # Symmetric prediction during validation
                probs_sym, logits_sym = model.forward_symmetric(fp_a, fp_b, cell_idx)
                loss = criterion(logits_sym, label)
                val_loss_sum += loss.item() * len(label)
                n_val += len(label)

        val_loss = val_loss_sum / n_val
        scheduler.step(val_loss)

        print(
            f"Epoch {epoch:02d}/{max_epochs:02d} | "
            f"Train Loss: {train_loss:.4f} | "
            f"Val Loss: {val_loss:.4f} | "
            f"LR: {optimizer.param_groups[0]['lr']:.2e}"
        )

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_epoch = epoch
            patience_counter = 0
            torch.save(
                {
                    "epoch": epoch,
                    "model_state_dict": model.state_dict(),
                    "optimizer_state_dict": optimizer.state_dict(),
                    "val_loss": val_loss,
                    "class_weights": class_weights.cpu(),
                    "split_type": split_type,
                    "seed": seed,
                },
                checkpoint_path,
            )
        else:
            patience_counter += 1
            if patience_counter >= es_patience:
                print(f"Early stopping triggered at epoch {epoch}. Best epoch was {best_epoch} (Val Loss: {best_val_loss:.4f}).")
                break

    print(f"Training complete in {time.time() - t_start:.2f}s. Checkpoint saved to: {checkpoint_path}")
    return checkpoint_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train DeepSynergy-style MLP baseline")
    parser.add_argument("--split", type=str, default="both", choices=["cold", "warm_random", "both"])
    parser.add_argument("--batch-size", type=int, default=512)
    parser.add_argument("--max-epochs", type=int, default=30)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    splits = ["cold", "warm_random"] if args.split == "both" else [args.split]
    for sp in splits:
        train_mlp_baseline(
            split_type=sp,
            batch_size=args.batch_size,
            max_epochs=args.max_epochs,
            seed=args.seed,
        )
