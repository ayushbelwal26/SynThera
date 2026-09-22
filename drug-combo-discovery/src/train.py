"""
train.py — Mini-Batch Training Pipeline for Drug Synergy GNN
==============================================================

OVERVIEW
--------
1.  Load heterodata.pt (PyG HeteroData) and the cold-drug split indices.
2.  Build three LinkNeighborLoader instances (train / val / test) that
    sample local subgraphs around drug-pair endpoints for mini-batch HGT.
3.  Compute class weights from the training split for weighted CE loss.
4.  Train SynergyModule with PyTorch Lightning:
      - Early stopping on val_loss (patience=5)
      - Best checkpoint saved to models/
      - Max 30 epochs
5.  Load best checkpoint, run test evaluation (AUROC / AUPR / confusion matrix).
6.  Save loss-curve PNG to models/loss_curve.png.

HARDWARE NOTE (GTX 1650, 4 GB VRAM)
------------------------------------
Mini-batch training is MANDATORY — the full graph (40 K nodes, 3.6 M edges)
does not fit in 4 GB VRAM when storing activations for backpropagation.

LinkNeighborLoader seeds on drug pairs and samples at most NUM_NEIGHBORS
edges per hop per relation type. Conservative per-type budgets are used
(especially for drug_drug which has 2.67 M edges).

If you hit a CUDA OOM error:
  1. Reduce BATCH_SIZE (try 128 or 64).
  2. Reduce NUM_NEIGHBORS (halve the values below).
  3. Reduce HIDDEN_DIM in model.py from 128 to 64.
  Do NOT silently fall back to CPU — that would make training take hours
  and mask a real hardware bottleneck. Instead, report the OOM here.
"""

from __future__ import annotations

import os
import sys
import time
import warnings
import traceback

import numpy as np
import pandas as pd
import torch
import matplotlib
matplotlib.use("Agg")          # headless backend — no display required
import matplotlib.pyplot as plt

import pytorch_lightning as pl
from pytorch_lightning.callbacks import (
    EarlyStopping,
    ModelCheckpoint,
    LearningRateMonitor,
)
from torch_geometric.loader import LinkNeighborLoader

# Local imports
sys.path.insert(0, os.path.dirname(__file__))
from model import SynergyModule, CLASS_NAMES

# ─────────────────────────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────────────────────────
ROOT       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED  = os.path.join(ROOT, "data", "processed")
MODELS_DIR = os.path.join(ROOT, "models")

HETERODATA_PATH  = os.path.join(PROCESSED, "heterodata.pt")
LABELS_PATH      = os.path.join(PROCESSED, "labeled_pairs.csv")
SPLIT_TRAIN_PATH = os.path.join(PROCESSED, "split_train.csv")
SPLIT_VAL_PATH   = os.path.join(PROCESSED, "split_val.csv")
# Headline MUST use this cold-drug split; also report bilateral-subset AUROC/AUPR as the stricter inductive metric.
SPLIT_TEST_PATH  = os.path.join(PROCESSED, "split_test.csv")
LOSS_CURVE_PATH  = os.path.join(MODELS_DIR, "loss_curve.png")

# ─────────────────────────────────────────────────────────────────
# Training hyper-parameters
# ─────────────────────────────────────────────────────────────────
SEED         = 42
BATCH_SIZE   = 256     # drug pairs per mini-batch -> reduce to 128/64 if OOM
MAX_EPOCHS   = 30      # v2 setting
LR           = 1e-3    # v2 setting
WEIGHT_DECAY = 1e-4
ES_PATIENCE  = 5       # v2 setting: 5 epochs patience on val_loss

# Neighbor sampling budget per hop per edge type.
# ⚠ Keep drug_drug very low (2.67 M edges total) to avoid OOM.
# Halve all values if you still hit OOM after reducing BATCH_SIZE.
NUM_NEIGHBORS: dict[tuple, list[int]] = {
    ("drug",         "drug_drug",        "drug"):         [4,  2],
    ("drug",         "drug_protein",     "gene/protein"): [12, 6],
    ("gene/protein", "drug_protein",     "drug"):         [12, 6],
    ("drug",         "indication",       "disease"):      [10, 5],
    ("disease",      "indication",       "drug"):         [10, 5],
    ("drug",         "contraindication", "disease"):      [10, 5],
    ("disease",      "contraindication", "drug"):         [10, 5],
    ("drug",         "off-label use",    "disease"):       [6,  3],
    ("disease",      "off-label use",    "drug"):          [6,  3],
    ("gene/protein", "protein_protein",  "gene/protein"): [10, 5],
    ("disease",      "disease_protein",  "gene/protein"): [8,  4],
    ("gene/protein", "disease_protein",  "disease"):      [8,  4],
    ("disease",      "disease_disease",  "disease"):      [5,  3],
    ("gene/protein", "pathway_protein",  "pathway"):      [5,  3],
    ("pathway",      "pathway_protein",  "gene/protein"): [5,  3],
}


# ─────────────────────────────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────────────────────────────

def _sep(title: str = "") -> None:
    print("\n" + "=" * 66)
    if title:
        print(f"  {title}")
        print("=" * 66)


def _elapsed(t0: float) -> str:
    s = time.time() - t0
    return f"{s:.1f}s" if s < 60 else f"{s/60:.1f}m"


# ─────────────────────────────────────────────────────────────────
# Loss-curve callback
# ─────────────────────────────────────────────────────────────────

class LossCurveCallback(pl.Callback):
    """Collects epoch-level train and val losses for offline plotting."""

    def __init__(self):
        super().__init__()
        self.train_losses: list[float] = []
        self.val_losses:   list[float] = []

    def on_train_epoch_end(self, trainer, pl_module):
        val = trainer.callback_metrics.get("train_loss_epoch")
        if val is not None:
            self.train_losses.append(float(val))

    def on_validation_epoch_end(self, trainer, pl_module):
        val = trainer.callback_metrics.get("val_loss")
        if val is not None:
            self.val_losses.append(float(val))

    def save_plot(self, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        fig, ax = plt.subplots(figsize=(10, 5))
        epochs = range(1, len(self.train_losses) + 1)
        ax.plot(epochs, self.train_losses, "b-o", markersize=4, label="Train Loss")
        val_epochs = range(1, len(self.val_losses) + 1)
        ax.plot(val_epochs, self.val_losses, "r-o", markersize=4, label="Val Loss")
        ax.set_xlabel("Epoch")
        ax.set_ylabel("Cross-Entropy Loss")
        ax.set_title("SynergyGNN — Training & Validation Loss")
        ax.legend()
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig(path, dpi=150)
        plt.close(fig)
        print(f"  Loss curve saved → {path}")


# ─────────────────────────────────────────────────────────────────
# Data loading
# ─────────────────────────────────────────────────────────────────

def load_data():
    _sep("Loading HeteroData and split indices")

    heterodata = torch.load(HETERODATA_PATH, weights_only=False)
    print(f"  Loaded heterodata.pt")
    print(f"  Node types : {heterodata.node_types}")
    print(f"  Edge types : {len(heterodata.edge_types)} types")

    labels_df  = pd.read_csv(LABELS_PATH)

    train_idx = pd.read_csv(SPLIT_TRAIN_PATH)["row_index"].tolist()
    val_idx   = pd.read_csv(SPLIT_VAL_PATH)["row_index"].tolist()
    test_idx  = pd.read_csv(SPLIT_TEST_PATH)["row_index"].tolist()

    print(f"\n  Labeled pairs  : {len(labels_df):,}")
    print(f"  Train idx      : {len(train_idx):,}")
    print(f"  Val   idx      : {len(val_idx):,}")
    print(f"  Test  idx      : {len(test_idx):,}")

    return heterodata, labels_df, train_idx, val_idx, test_idx


# ─────────────────────────────────────────────────────────────────
# Build LinkNeighborLoader for each split
# ─────────────────────────────────────────────────────────────────

def build_loaders(
    heterodata,
    train_idx: list[int],
    val_idx:   list[int],
    test_idx:  list[int],
) -> tuple:
    """
    Retrieves pre-built label tensors from heterodata (stored by build_heterodata.py)
    and wraps them in LinkNeighborLoader instances that sample local HGT subgraphs
    around each drug pair's endpoints.

    The supervision edge type ('drug', 'synergy_pair', 'drug') is NOT present in
    heterodata's regular edge types -- it exists only as edge_label_index / edge_label
    inside each mini-batch, so it is never used for message passing.

    Cell-line context is carried as a second column in edge_label:
        edge_label[:, 0]  = synergy class (0/1/2)
        edge_label[:, 1]  = cell-line integer ID
    Both columns are unpacked in model.forward().
    """
    _sep("Building LinkNeighborLoader instances")

    def _get_split_tensors(split_name: str):
        a    = getattr(heterodata, f"label_{split_name}_drug_a")
        b    = getattr(heterodata, f"label_{split_name}_drug_b")
        y    = getattr(heterodata, f"label_{split_name}_y")
        cell = getattr(heterodata, f"label_{split_name}_cell")
        return a, b, y, cell

    def _make_loader(split_name: str, shuffle: bool) -> LinkNeighborLoader:
        drug_a, drug_b, y, cell = _get_split_tensors(split_name)
        edge_label_index = torch.stack([drug_a, drug_b], dim=0)   # [2, N]
        # Pack synergy class + cell-line id into a single [N, 2] tensor.
        # LinkNeighborLoader preserves arbitrary edge_label shapes.
        edge_label = torch.stack([y, cell], dim=1)                 # [N, 2]  int64

        n_pairs = y.shape[0]
        print(f"  {split_name:<6}: {n_pairs:>8,} pairs  "
              f"| class counts: {[(y==c).sum().item() for c in range(3)]}")

        loader = LinkNeighborLoader(
            data                  = heterodata,
            num_neighbors         = NUM_NEIGHBORS,
            edge_label_index      = (("drug", "synergy_pair", "drug"), edge_label_index),
            edge_label            = edge_label,
            batch_size            = BATCH_SIZE,
            shuffle               = shuffle,
            num_workers           = 0,     # Windows: must be 0
            persistent_workers    = False,
        )
        return loader

    train_loader = _make_loader("train", shuffle=True)
    val_loader   = _make_loader("val",   shuffle=False)
    test_loader  = _make_loader("test",  shuffle=False)

    return train_loader, val_loader, test_loader


# ─────────────────────────────────────────────────────────────────
# Class weights (from training split)
# ─────────────────────────────────────────────────────────────────

def compute_class_weights(heterodata) -> torch.Tensor:
    """
    Softened inverse-frequency class weights: weight_c = sqrt(N_total / (3 * N_c)).
    Using the square root of the raw inverse frequency softens the correction,
    reducing over-prediction of minority classes at the cost of the majority class recall.
    """
    _sep("Computing class weights from training split")
    y_train = getattr(heterodata, "label_train_y")
    n_total = len(y_train)
    weights = []
    for c in range(3):
        n_c      = (y_train == c).sum().item()
        raw_w    = n_total / (3.0 * n_c) if n_c > 0 else 1.0
        soft_w   = raw_w ** 0.5              # sqrt softening
        weights.append(soft_w)
        print(f"  {CLASS_NAMES[c]:<15}: n={n_c:>8,}  raw_weight={raw_w:.4f}  soft_weight={soft_w:.4f}")

    return torch.tensor(weights, dtype=torch.float32)


# ─────────────────────────────────────────────────────────────────
# Run B Regularized Module (Training Loop Only)
# ─────────────────────────────────────────────────────────────────

class RegularizedSynergyModule(SynergyModule):
    """
    Subclass of SynergyModule for Run B drug-level regularization during training:
    1. Fingerprint bit dropout: randomly zero out 10% of each drug's 2048-bit Morgan FP bits
       before projection, resampled every batch. Off at eval/inference.
    2. Drug-edge masking: for a random 15% of drugs in each training batch, drop a random
       half of that drug's non-drug-drug graph edges (target/indication edges) before message passing,
       resampled every batch. Off at eval/inference.
    Architecture, head (384-dim simple concat), and forward pass remain identical to baseline.
    """
    def __init__(
        self,
        *args,
        fp_dropout: float = 0.10,
        drug_mask_frac: float = 0.15,
        edge_drop_frac: float = 0.50,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.fp_dropout = fp_dropout
        self.drug_mask_frac = drug_mask_frac
        self.edge_drop_frac = edge_drop_frac

    def training_step(self, batch, batch_idx):
        # 1. Fingerprint bit dropout: randomly zero out 10% of each drug's 2048-bit Morgan FP bits
        if self.fp_dropout > 0 and hasattr(batch["drug"], "x") and batch["drug"].x is not None:
            bit_keep_mask = (torch.rand_like(batch["drug"].x) >= self.fp_dropout).float()
            batch["drug"].x = batch["drug"].x * bit_keep_mask

        # 2. Drug-edge masking: for random 15% of drugs, drop a random half of non-drug-drug edges
        if self.drug_mask_frac > 0 and self.edge_drop_frac > 0:
            n_drugs = batch["drug"].num_nodes
            dev = batch["drug"].x.device if hasattr(batch["drug"], "x") and batch["drug"].x is not None else None
            is_selected_drugs = torch.rand(n_drugs, device=dev) < self.drug_mask_frac

            for etype in batch.edge_types:
                src_type, rel, dst_type = etype
                # non-drug-drug graph edges involving drug (target / indication / disease edges)
                if src_type == "drug" and dst_type != "drug":
                    drug_idx = batch[etype].edge_index[0]
                elif dst_type == "drug" and src_type != "drug":
                    drug_idx = batch[etype].edge_index[1]
                else:
                    continue

                orig_edges = batch[etype].edge_index.size(1)
                if orig_edges == 0:
                    continue
                selected_edges = is_selected_drugs[drug_idx]
                drop_mask = selected_edges & (torch.rand(orig_edges, device=batch[etype].edge_index.device) < self.edge_drop_frac)
                batch[etype].edge_index = batch[etype].edge_index[:, ~drop_mask]

        return super().training_step(batch, batch_idx)


# ─────────────────────────────────────────────────────────────────
# Main training routine
# ─────────────────────────────────────────────────────────────────

def main(
    run_name: str = "synergy_gnn_runA",
    seed: int = SEED,
    save_all_epochs: bool = False,
    checkpoint_dir: str = MODELS_DIR,
    use_regularization: bool = False,
    use_target_features: bool = False,
    fp_dropout: float = 0.10,
    drug_mask_frac: float = 0.15,
    edge_drop_frac: float = 0.50,
) -> tuple[str, float]:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    # If run_name starts with runB or flags set, enable regularization
    if "runB" in run_name or "run_b" in run_name.lower():
        use_regularization = True
    if "runC" in run_name or "run_c" in run_name.lower():
        use_target_features = True

    pl.seed_everything(seed, workers=True)
    os.makedirs(checkpoint_dir, exist_ok=True)
    warnings.filterwarnings("ignore", ".*does not have many workers.*")

    reg_desc = f" (Regularized Run B: fp_drop={fp_dropout}, drug_mask={drug_mask_frac}, edge_drop={edge_drop_frac})" if use_regularization else ""
    target_desc = " (Target Features Run C active: 4 hand-crafted PPI features)" if use_target_features else ""
    _sep(f"SynergyGNN — Training ({run_name}, seed={seed}){reg_desc}{target_desc}")
    t_total = time.time()

    # ── 1. Load data ──────────────────────────────────────────────
    heterodata, labels_df, train_idx, val_idx, test_idx = load_data()

    # ── 2. Build loaders ─────────────────────────────────────────
    train_loader, val_loader, test_loader = build_loaders(
        heterodata, train_idx, val_idx, test_idx
    )

    # ── 3. Class weights ─────────────────────────────────────────
    class_weights = compute_class_weights(heterodata)

    # ── 4. Instantiate model ─────────────────────────────────────
    _sep("Instantiating SynergyModule")

    # Build metadata from the actual edge types in heterodata
    # (excludes synergy_pair — it's only added at loader time)
    metadata = heterodata.metadata()
    num_nodes_dict = {
        ntype: heterodata[ntype].num_nodes
        for ntype in heterodata.node_types
    }
    print(f"  Metadata: {len(metadata[0])} node types, {len(metadata[1])} edge types")
    print(f"  Node counts: {num_nodes_dict}")

    module_cls = RegularizedSynergyModule if use_regularization else SynergyModule
    extra_kwargs = (
        dict(fp_dropout=fp_dropout, drug_mask_frac=drug_mask_frac, edge_drop_frac=edge_drop_frac)
        if use_regularization
        else {}
    )

    model = module_cls(
        metadata           = metadata,
        num_nodes_dict     = num_nodes_dict,
        num_fallback_drugs = int((~heterodata["drug"].fp_mask).sum().item()),
        num_cell_lines     = heterodata.num_cell_lines,
        class_weights      = class_weights,
        lr                 = LR,
        weight_decay       = WEIGHT_DECAY,
        max_epochs         = MAX_EPOCHS,
        enriched_pair_head = False,  # keep baseline architecture (384-dim simple concat)
        use_target_features = use_target_features,
        **extra_kwargs,
    )

    n_fp       = int(heterodata["drug"].fp_mask.sum().item())
    n_fallback = heterodata["drug"].num_nodes - n_fp
    print(f"  Drug embedded nodes: {n_fp:,}  (Morgan FP 2048 -> Linear(2048->128))")
    print(f"  Drug fallback nodes: {n_fallback:,}  (trainable ID emb disabled in forward pass)")
    print(f"  Cell lines         : {heterodata.num_cell_lines}  (learnable Embedding(N, 64) -> scorer)")
    if use_regularization:
        print(f"  [Run B Active] Drug FP bit dropout: {fp_dropout:.0%}")
        print(f"  [Run B Active] Drug edge masking  : {drug_mask_frac:.0%} drugs, {edge_drop_frac:.0%} non-drug edges dropped")

    n_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"  Trainable parameters: {n_params:,}")

    # ── 5. Callbacks ─────────────────────────────────────────────
    loss_curve_cb = LossCurveCallback()

    early_stop_cb = EarlyStopping(
        monitor   = "val_loss",
        patience  = ES_PATIENCE,
        mode      = "min",
        verbose   = True,
    )

    if save_all_epochs:
        checkpoint_cb = ModelCheckpoint(
            dirpath          = checkpoint_dir,
            filename         = f"seed{seed}_epoch{{epoch}}",
            monitor          = "val_loss",
            save_top_k       = -1,   # save every epoch
            save_last        = False,
            verbose          = True,
        )
    else:
        checkpoint_cb = ModelCheckpoint(
            dirpath          = checkpoint_dir,
            filename         = run_name,
            monitor          = "val_loss",
            save_top_k       = 1,
            mode             = "min",
            save_last        = True,
            verbose          = True,
        )

    lr_monitor_cb = LearningRateMonitor(logging_interval="epoch")

    # ── 6. Trainer ────────────────────────────────────────────────
    _sep("Training")
    print(f"  run_name     = {run_name}")
    print(f"  batch_size   = {BATCH_SIZE}")
    print(f"  max_epochs   = {MAX_EPOCHS}")
    print(f"  early_stop   = {ES_PATIENCE} epochs patience on val_loss")
    print(f"  accelerator  = gpu  (GTX 1650, 4 GB VRAM)")
    print(f"  num_neighbors (per hop, key types):")
    for k, v in list(NUM_NEIGHBORS.items())[:5]:
        print(f"    {str(k):<52} {v}")
    print(f"    ... and {len(NUM_NEIGHBORS) - 5} more types")

    trainer = pl.Trainer(
        accelerator     = "gpu",
        devices         = 1,
        max_epochs      = MAX_EPOCHS,
        callbacks       = [early_stop_cb, checkpoint_cb, lr_monitor_cb, loss_curve_cb],
        log_every_n_steps = 10,
        enable_progress_bar = True,
        deterministic   = False,    # True would slow HGT attention significantly
        gradient_clip_val = 1.0,    # clip gradients to prevent instability
        inference_mode  = False,    # PyG neighbor_sampler requires no_grad rather than inference_mode
    )

    try:
        trainer.fit(model, train_loader, val_loader)
    except RuntimeError as e:
        if "CUDA out of memory" in str(e) or "out of memory" in str(e).lower():
            print(
                "\n" + "!" * 66 + "\n"
                "  CUDA OUT OF MEMORY detected on GTX 1650.\n"
                "  Hardware is the bottleneck. Suggested fixes (in order):\n"
                "    1. Reduce BATCH_SIZE from 256 to 128 (halves activation memory)\n"
                "    2. Halve all NUM_NEIGHBORS values\n"
                "    3. Reduce HIDDEN_DIM in model.py from 128 to 64\n"
                "  Do NOT fall back to CPU training — it will be ~50x slower.\n"
                + "!" * 66
            )
            raise
        raise

    # Normalize checkpoint names if save_all_epochs is active
    if save_all_epochs:
        import glob
        for f in glob.glob(os.path.join(checkpoint_dir, f"seed{seed}_*.ckpt")):
            new_f = f.replace("epochepoch=", "epoch").replace("epoch=", "epoch")
            if new_f != f:
                try:
                    os.replace(f, new_f)
                except Exception:
                    pass

    # ── 7. Loss curve ─────────────────────────────────────────────
    loss_curve_cb.save_plot(LOSS_CURVE_PATH)

    # ── 8. Test evaluation ────────────────────────────────────────
    _sep("Test Evaluation — loading best checkpoint")
    best_ckpt = checkpoint_cb.best_model_path
    if save_all_epochs and best_ckpt:
        best_ckpt = best_ckpt.replace("epochepoch=", "epoch").replace("epoch=", "epoch")
    print(f"  Best checkpoint : {best_ckpt}")
    print(f"  Best val_loss   : {checkpoint_cb.best_model_score:.4f}")

    # Copy to target checkpoint path e.g. models/synergy_gnn_runA.ckpt (if not save_all_epochs)
    if not save_all_epochs:
        target_ckpt = os.path.join(checkpoint_dir, f"{run_name}.ckpt")
        if os.path.exists(best_ckpt) and os.path.abspath(best_ckpt) != os.path.abspath(target_ckpt):
            import shutil
            shutil.copy2(best_ckpt, target_ckpt)
            print(f"  Saved run checkpoint: {target_ckpt}")

    best_model = SynergyModule.load_from_checkpoint(
        best_ckpt,
        metadata           = metadata,
        num_nodes_dict     = num_nodes_dict,
        num_fallback_drugs = int((~heterodata["drug"].fp_mask).sum().item()),
        num_cell_lines     = heterodata.num_cell_lines,
        class_weights      = class_weights,
    )

    trainer.test(best_model, test_loader)

    wall_clock = time.time() - t_total
    _sep("Done")
    print(f"  Total wall-clock time : {_elapsed(t_total)}")
    print(f"\n  Artifacts saved to {MODELS_DIR}/:")
    for fname in sorted(os.listdir(MODELS_DIR)):
        fpath = os.path.join(MODELS_DIR, fname)
        if os.path.isfile(fpath):
            size_mb = os.path.getsize(fpath) / 1e6
            print(f"    {fname:<40}  {size_mb:>7.2f} MB")

    saved_path = target_ckpt if not save_all_epochs else best_ckpt
    return saved_path, wall_clock



# ─────────────────────────────────────────────────────────────────
# Test split subset evaluation helper
# ─────────────────────────────────────────────────────────────────
def evaluate_split_subsets(
    ckpt_path: str = os.path.join(MODELS_DIR, "synergy_gnn_final.ckpt"),
    heterodata_path: str = HETERODATA_PATH,
):
    """
    Evaluates test set predictions across:
      1. Full cold-drug test (headline)
      2. Bilateral cold-drug test (strictest subset: neither drug in train)
      3. Unilateral cold-drug test (exactly one drug in train)
    """
    from eval_splits import evaluate_cold_split_subsets
    return evaluate_cold_split_subsets(ckpt_path=ckpt_path, heterodata_path=heterodata_path)


if __name__ == "__main__":
    if "--help" in sys.argv or "-h" in sys.argv:
        print("Usage: python src/train.py [--run-name NAME] [--seed INT] [--eval-subsets] [--use-regularization]")
        print("  --run-name NAME       : Name for checkpoint (default: synergy_gnn_runA)")
        print("  --seed INT            : Random seed for training (default: 42)")
        print("  --use-regularization  : Enable Run B drug-level regularization")
        print("  --eval-subsets        : Evaluate checkpoint across full test, bilateral, and unilateral subsets")
        sys.exit(0)
    elif "--eval-subsets" in sys.argv:
        ckpt_arg = None
        for i, a in enumerate(sys.argv):
            if a == "--ckpt" and i + 1 < len(sys.argv):
                ckpt_arg = sys.argv[i + 1]
        evaluate_split_subsets(ckpt_path=ckpt_arg) if ckpt_arg else evaluate_split_subsets()
    else:
        run_name = "synergy_gnn_runA"
        seed = SEED
        save_all = "--save-all-epochs" in sys.argv
        ckpt_dir = MODELS_DIR
        use_reg = "--use-regularization" in sys.argv or "--run-B" in sys.argv
        use_target = "--use-target-features" in sys.argv or "--run-C" in sys.argv
        for i, a in enumerate(sys.argv):
            if a == "--run-name" and i + 1 < len(sys.argv):
                run_name = sys.argv[i + 1]
            if a == "--seed" and i + 1 < len(sys.argv):
                seed = int(sys.argv[i + 1])
            if a == "--checkpoint-dir" and i + 1 < len(sys.argv):
                ckpt_dir = sys.argv[i + 1]
        main(
            run_name=run_name,
            seed=seed,
            save_all_epochs=save_all,
            checkpoint_dir=ckpt_dir,
            use_regularization=use_reg,
            use_target_features=use_target,
        )

