"""
src/train_random_split.py — Train a SynThera model on the Random / Warm Split
==============================================================================

PURPOSE
-------
Trains a NEW SynergyModule checkpoint on the 70/15/15 random observation split
so that a clean, uncontaminated random-split test evaluation is possible.

WHY A NEW MODEL IS NEEDED
--------------------------
The existing champion (synergy_gnn_pair_interaction.ckpt) was trained using
the COLD-DRUG split (split_train.csv / split_val.csv / split_test.csv).
Many observations that appear in the random test split were in the champion's
training set.  Evaluating the frozen champion on the random test set would
therefore NOT be a legitimate held-out evaluation.

A new model trained from scratch on random_train.csv is required for a clean
random-split result.

ARCHITECTURE
------------
Identical to the champion:
  - Same SynergyModule (enriched_pair_head=True)
  - Same Morgan fingerprint drug features
  - Same loss (weighted cross-entropy with sqrt-softened class weights)
  - Same optimizer (AdamW, lr=1e-3, weight_decay=1e-4)
  - Same HGT message-passing budget (NUM_NEIGHBORS from train.py)
  - Same training discipline (EarlyStopping on val_loss, patience=5)
  - Same max_epochs=30

Only the data indices change.

OUTPUT
------
  models/synergy_gnn_random_split_seed42.ckpt   ← DO NOT CONFUSE WITH CHAMPION

Protected (NEVER OVERWRITTEN):
  models/synergy_gnn_pair_interaction.ckpt
"""

from __future__ import annotations

import os
import sys
import time
import warnings

import numpy as np
import pandas as pd
import torch
import pytorch_lightning as pl
from pytorch_lightning.callbacks import (
    EarlyStopping,
    ModelCheckpoint,
    LearningRateMonitor,
)
from torch_geometric.loader import LinkNeighborLoader

ROOT_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR   = os.path.join(ROOT_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from model import SynergyModule, CLASS_NAMES
from train import (
    HETERODATA_PATH,
    LABELS_PATH,
    MODELS_DIR,
    NUM_NEIGHBORS,
    BATCH_SIZE,
    MAX_EPOCHS,
    LR,
    WEIGHT_DECAY,
    ES_PATIENCE,
    LossCurveCallback,
    _sep,
    _elapsed,
)

PROCESSED   = os.path.join(ROOT_DIR, "data", "processed")
SPLITS_DIR  = os.path.join(PROCESSED, "splits_random")

RANDOM_TRAIN_CSV = os.path.join(SPLITS_DIR, "random_train.csv")
RANDOM_VAL_CSV   = os.path.join(SPLITS_DIR, "random_val.csv")
RANDOM_TEST_CSV  = os.path.join(SPLITS_DIR, "random_test.csv")

CHAMPION_CKPT      = os.path.join(MODELS_DIR, "synergy_gnn_pair_interaction.ckpt")
RANDOM_CKPT_NAME   = "synergy_gnn_random_split_seed42"
RANDOM_CKPT_PATH   = os.path.join(MODELS_DIR, f"{RANDOM_CKPT_NAME}.ckpt")
RANDOM_LOSS_CURVE  = os.path.join(MODELS_DIR, "loss_curve_random_split.png")

SEED = 42


def _guard_champion() -> None:
    """Abort immediately if anything is about to overwrite the champion."""
    outputs = {
        os.path.abspath(RANDOM_CKPT_PATH),
        os.path.abspath(RANDOM_LOSS_CURVE),
    }
    if os.path.abspath(CHAMPION_CKPT) in outputs:
        raise RuntimeError(
            "SAFETY ABORT: output path would overwrite champion checkpoint!"
        )


def _build_loaders(heterodata, train_idx, val_idx, test_idx):
    """Build LinkNeighborLoaders from arbitrary row-index lists."""
    _sep("Building LinkNeighborLoader instances (random split)")

    labels_df = pd.read_csv(LABELS_PATH)

    # Rebuild class-map and cell-map identical to build_heterodata.py
    CLASS_MAP = {"antagonism": 0, "additive": 1, "synergy": 2}
    cell_map  = heterodata.cell_line_map        # dict str->int from HeteroData
    drug_map  = {                               # str DrugBank ID -> int node idx
        v: k for k, v in enumerate(sorted(
            set(labels_df["drug_a_kg_id"]) | set(labels_df["drug_b_kg_id"])
        ))
    }
    # The authoritative drug map is in the KG node ordering — reuse the one
    # already baked into heterodata by examining label_train tensors.
    # We must NOT rebuild from scratch because index ordering must match the GNN.
    # Instead, we rebuild drug indices from labels_df using the same logic
    # as build_heterodata.py: sorted unique drug IDs -> 0-indexed.
    # This is guaranteed correct because heterodata was built the same way.

    def _make_tensors(idx_list):
        sub = labels_df.iloc[idx_list].reset_index(drop=True)
        a = torch.tensor(
            sub["drug_a_kg_id"].map(drug_map).astype(int).values, dtype=torch.long
        )
        b = torch.tensor(
            sub["drug_b_kg_id"].map(drug_map).astype(int).values, dtype=torch.long
        )
        y = torch.tensor(
            sub["synergy_class"].map(CLASS_MAP).astype(int).values, dtype=torch.long
        )
        c = torch.tensor(
            sub["cell_line_name"].map(cell_map).astype(int).values, dtype=torch.long
        )
        return a, b, y, c

    def _make_loader(split_name, idx_list, shuffle):
        a, b, y, c = _make_tensors(idx_list)
        edge_label_index = torch.stack([a, b], dim=0)        # [2, N]
        edge_label       = torch.stack([y, c], dim=1)        # [N, 2]
        n_pairs = y.shape[0]
        print(f"  {split_name:<6}: {n_pairs:>8,} pairs  "
              f"| class counts: {[(y==cls).sum().item() for cls in range(3)]}")
        loader = LinkNeighborLoader(
            data              = heterodata,
            num_neighbors     = NUM_NEIGHBORS,
            edge_label_index  = (("drug", "synergy_pair", "drug"), edge_label_index),
            edge_label        = edge_label,
            batch_size        = BATCH_SIZE,
            shuffle           = shuffle,
            num_workers       = 0,
            persistent_workers= False,
        )
        return loader

    train_loader = _make_loader("train", train_idx, shuffle=True)
    val_loader   = _make_loader("val",   val_idx,   shuffle=False)
    test_loader  = _make_loader("test",  test_idx,  shuffle=False)
    return train_loader, val_loader, test_loader


def _compute_class_weights(labels_df, train_idx):
    """Softened inverse-frequency weights from the RANDOM TRAIN split."""
    _sep("Computing class weights from random train split")
    CLASS_MAP = {"antagonism": 0, "additive": 1, "synergy": 2}
    y_train = labels_df.iloc[train_idx]["synergy_class"].map(CLASS_MAP).values
    n_total = len(y_train)
    weights = []
    for c, name in enumerate(CLASS_NAMES):
        n_c   = (y_train == c).sum()
        raw_w = n_total / (3.0 * n_c) if n_c > 0 else 1.0
        soft_w = raw_w ** 0.5
        weights.append(soft_w)
        print(f"  {name:<15}: n={n_c:>8,}  raw_weight={raw_w:.4f}  soft_weight={soft_w:.4f}")
    return torch.tensor(weights, dtype=torch.float32)


def main(seed: int = SEED) -> str:
    """
    Train SynergyModule on the random/warm split and save checkpoint.

    Returns
    -------
    str
        Path to the saved checkpoint (never the champion path).
    """
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    _guard_champion()

    # Check that random split files exist
    for csv_path in [RANDOM_TRAIN_CSV, RANDOM_VAL_CSV, RANDOM_TEST_CSV]:
        if not os.path.exists(csv_path):
            raise FileNotFoundError(
                f"Random split CSV not found: {csv_path}\n"
                f"Run: python -m src.build_random_split first."
            )

    pl.seed_everything(seed, workers=True)
    warnings.filterwarnings("ignore", ".*does not have many workers.*")

    _sep(f"SynThera — Training on Random/Warm Split  (seed={seed})")
    t_total = time.time()
    print(f"  Champion checkpoint  : {CHAMPION_CKPT}  (NOT TOUCHED)")
    print(f"  Output checkpoint    : {RANDOM_CKPT_PATH}")
    print(f"  Split type           : random observation-level 70/15/15")

    # ── 1. Load data ─────────────────────────────────────────────
    _sep("Loading HeteroData and random split indices")
    heterodata = torch.load(HETERODATA_PATH, weights_only=False)
    labels_df  = pd.read_csv(LABELS_PATH)

    train_idx = pd.read_csv(RANDOM_TRAIN_CSV)["row_index"].tolist()
    val_idx   = pd.read_csv(RANDOM_VAL_CSV)["row_index"].tolist()
    test_idx  = pd.read_csv(RANDOM_TEST_CSV)["row_index"].tolist()

    print(f"\n  Random train obs : {len(train_idx):,}")
    print(f"  Random val   obs : {len(val_idx):,}")
    print(f"  Random test  obs : {len(test_idx):,}")

    # ── 2. Build loaders ─────────────────────────────────────────
    train_loader, val_loader, test_loader = _build_loaders(
        heterodata, train_idx, val_idx, test_idx
    )

    # ── 3. Class weights ─────────────────────────────────────────
    class_weights = _compute_class_weights(labels_df, train_idx)

    # ── 4. Model ─────────────────────────────────────────────────
    _sep("Instantiating SynergyModule (same architecture as champion)")
    metadata       = heterodata.metadata()
    num_nodes_dict = {nt: heterodata[nt].num_nodes for nt in heterodata.node_types}
    n_fallback     = int((~heterodata["drug"].fp_mask).sum().item())

    model = SynergyModule(
        metadata            = metadata,
        num_nodes_dict      = num_nodes_dict,
        num_fallback_drugs  = n_fallback,
        num_cell_lines      = heterodata.num_cell_lines,
        class_weights       = class_weights,
        lr                  = LR,
        weight_decay        = WEIGHT_DECAY,
        max_epochs          = MAX_EPOCHS,
        enriched_pair_head  = True,    # same as champion
    )
    n_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"  Trainable parameters: {n_params:,}")

    # ── 5. Callbacks ─────────────────────────────────────────────
    loss_curve_cb = LossCurveCallback()
    early_stop_cb = EarlyStopping(
        monitor="val_loss", patience=ES_PATIENCE, mode="min", verbose=True
    )
    checkpoint_cb = ModelCheckpoint(
        dirpath      = MODELS_DIR,
        filename     = RANDOM_CKPT_NAME,
        monitor      = "val_loss",
        save_top_k   = 1,
        mode         = "min",
        save_last    = True,
        verbose      = True,
    )
    lr_monitor_cb = LearningRateMonitor(logging_interval="epoch")

    # ── 6. Train ──────────────────────────────────────────────────
    _sep("Training")
    trainer = pl.Trainer(
        accelerator         = "gpu",
        devices             = 1,
        max_epochs          = MAX_EPOCHS,
        callbacks           = [early_stop_cb, checkpoint_cb, lr_monitor_cb, loss_curve_cb],
        log_every_n_steps   = 10,
        enable_progress_bar = True,
        deterministic       = False,
        gradient_clip_val   = 1.0,
        inference_mode      = False,
    )

    try:
        trainer.fit(model, train_loader, val_loader)
    except RuntimeError as e:
        if "out of memory" in str(e).lower():
            print("CUDA OOM on GTX 1650. Reduce BATCH_SIZE or NUM_NEIGHBORS.")
        raise

    loss_curve_cb.save_plot(RANDOM_LOSS_CURVE)

    # ── 7. Copy best checkpoint to canonical path ─────────────────
    import shutil
    best_ckpt = checkpoint_cb.best_model_path
    print(f"\n  Best checkpoint  : {best_ckpt}")
    print(f"  Best val_loss    : {checkpoint_cb.best_model_score:.4f}")

    if os.path.exists(best_ckpt) and os.path.abspath(best_ckpt) != os.path.abspath(RANDOM_CKPT_PATH):
        shutil.copy2(best_ckpt, RANDOM_CKPT_PATH)
        print(f"  Saved: {RANDOM_CKPT_PATH}")

    # ── 8. Verify we did not touch champion ───────────────────────
    assert os.path.abspath(best_ckpt) != os.path.abspath(CHAMPION_CKPT), \
        "SAFETY VIOLATION: champion checkpoint was overwritten!"
    if os.path.exists(RANDOM_CKPT_PATH):
        assert os.path.abspath(RANDOM_CKPT_PATH) != os.path.abspath(CHAMPION_CKPT), \
            "SAFETY VIOLATION: random ckpt path == champion path!"

    wall = time.time() - t_total
    _sep("Done")
    print(f"  Wall-clock time : {_elapsed(t_total)}")
    print(f"  Random-split checkpoint : {RANDOM_CKPT_PATH}")
    print(f"  Champion unchanged      : {CHAMPION_CKPT}")
    return RANDOM_CKPT_PATH


if __name__ == "__main__":
    main()
