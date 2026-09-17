"""
model.py — Heterogeneous Graph Transformer for Drug-Combination Synergy Prediction
====================================================================================

ARCHITECTURE
------------
1. Node Input Features / Embeddings
   - drug (FP path, ~7,122 nodes): real 2048-bit Morgan fingerprint (float32)
     projected to hidden_dim via Linear(2048 → 128).
   - drug (fallback path, ~824 biologics): nn.Embedding(N_fallback, 128) —
     a small learnable embedding for drugs without a SMILES entry.
     Routing is controlled per-node by the boolean fp_mask stored in HeteroData.
   - gene/protein: nn.Embedding(19585, 64)  →  Linear(64 → 128)
   - pathway:      nn.Embedding(2020,  64)  →  Linear(64 → 128)
   - disease:      nn.Embedding(11250, 64)  →  Linear(64 → 128)

2. HGT Encoder — 2 × HGTConv(hidden_dim, hidden_dim, metadata, heads=4)
   with ELU activation and LayerNorm after each layer.
   The drug_drug relation is used for message passing (structural signal)
   but its edges are NEVER used as supervision labels.

3. Pair Scorer — MLP head on the concatenated embeddings of both drugs:
   [hidden_dim × 2] → hidden_dim → 3 classes (antagonism / additive / synergy)

LIGHTNING MODULE
----------------
SynergyModule wraps SynergyGNN in a pl.LightningModule.
- Loss: weighted cross-entropy (weights passed from train class frequencies)
- Optimiser: AdamW with CosineAnnealingLR
- Tracks: train_loss, val_loss (used for early stopping and checkpointing)
- test_step collects logits/labels for AUROC / AUPR / confusion matrix in
  on_test_epoch_end
"""

from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import pytorch_lightning as pl
from torch_geometric.nn import HGTConv
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    confusion_matrix,
)

# ─────────────────────────────────────────────────────────────────
# Constants — single source of truth for all hyper-parameters
# ─────────────────────────────────────────────────────────────────
HIDDEN_DIM = 128       # unified hidden dimension after projection
NUM_HEADS  = 4         # HGT multi-head attention heads
NUM_LAYERS = 2         # number of HGT conv layers (v2 2-hop configuration)
DROPOUT    = 0.3       # dropout applied after embedding projection and in MLP

# Morgan fingerprint dimension (radius=2, nBits=2048 — must match build_heterodata.py)
FP_DIM = 2048

# Input feature dimensions per node type.
# drug: handled specially — FP nodes use FP_DIM (2048), fallback nodes use HIDDEN_DIM (128)
#       (both are projected to HIDDEN_DIM inside _build_x_dict).
# Other types use a learnable embedding of these dims, then project to HIDDEN_DIM.
EMB_DIMS: dict[str, int] = {
    "drug":         FP_DIM,   # raw Morgan FP dim (2048); fallback uses separate Embedding
    "gene/protein":  64,
    "pathway":       64,
    "disease":       64,
}

# Integer class encoding used everywhere: 0=antagonism, 1=additive, 2=synergy
CLASS_NAMES = ["antagonism", "additive", "synergy"]

# Cell-line embedding dimension (projected to hidden_dim before concatenation)
NUM_CELL_LINE_DIM = 64

# ─────────────────────────────────────────────────────────────────
# Focal loss helper
# ─────────────────────────────────────────────────────────────────

def focal_loss(
    logits: torch.Tensor,
    labels: torch.Tensor,
    alpha: torch.Tensor | None = None,
    gamma: float = 2.0,
) -> torch.Tensor:
    """
    Multi-class focal loss (Lin et al., 2017).

    FL(p_t) = -alpha_t * (1 - p_t)^gamma * log(p_t)

    Args
    ----
    logits : [N, C]  raw (unnormalised) class scores
    labels : [N]     integer class indices 0..C-1
    alpha  : [C]     per-class weight (same softened inv-freq weights as before,
                     now used as focal alpha rather than CE weights)
    gamma  : float   focusing exponent; 2.0 is the standard value

    Returns
    -------
    Scalar mean focal loss over the batch.
    """
    log_probs  = F.log_softmax(logits, dim=-1)          # [N, C]
    probs      = log_probs.exp()                         # [N, C]

    # Gather the log-prob and prob for the true class of each sample
    log_pt = log_probs.gather(1, labels.unsqueeze(1)).squeeze(1)   # [N]
    pt     = probs.gather(1, labels.unsqueeze(1)).squeeze(1)       # [N]

    focal_term = (1.0 - pt) ** gamma                    # [N]  — down-weights easy examples
    loss = -focal_term * log_pt                          # [N]

    if alpha is not None:
        alpha_t = alpha[labels]                          # [N]
        loss = alpha_t * loss

    return loss.mean()

# ─────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────

def _safe_key(node_type: str) -> str:
    """Convert a node-type string to a valid Python identifier for ModuleDict keys."""
    return node_type.replace("/", "_").replace(" ", "_").replace("-", "_")


# ─────────────────────────────────────────────────────────────────
# Core GNN (pure nn.Module — no Lightning)
# ─────────────────────────────────────────────────────────────────

class SynergyGNN(nn.Module):
    """
    HGT encoder + pair-scorer MLP.

    Args
    ----
    metadata        : (node_types, edge_types) from heterodata.metadata()
    num_nodes_dict  : {node_type -> int} total nodes per type in full graph
    hidden_dim      : unified hidden dimension after input projection
    num_heads       : HGT attention heads
    dropout         : dropout rate
    """

    def __init__(
        self,
        metadata: tuple,
        num_nodes_dict: dict[str, int],
        num_fallback_drugs: int,
        num_cell_lines: int,
        num_layers: int = 2,
        hidden_dim: int = HIDDEN_DIM,
        num_heads: int  = NUM_HEADS,
        dropout: float  = DROPOUT,
    ) -> None:
        super().__init__()

        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.dropout    = nn.Dropout(dropout)
        node_types = metadata[0]

        # ── Drug: hybrid feature module ───────────────────────────
        # FP path  : Linear(FP_DIM → hidden_dim) — applied to real fingerprint rows
        # Fallback : nn.Embedding(N_fallback, hidden_dim) — for biologics with no FP
        self.drug_fp_proj = nn.Linear(FP_DIM, hidden_dim, bias=False)
        nn.init.xavier_uniform_(self.drug_fp_proj.weight)

        self.drug_fallback_emb = nn.Embedding(num_fallback_drugs, hidden_dim)
        nn.init.xavier_uniform_(self.drug_fallback_emb.weight)

        # ── Non-drug: learnable embedding tables ──────────────────
        self.emb_tables = nn.ModuleDict()
        self.input_proj = nn.ModuleDict()
        for ntype in node_types:
            if ntype == "drug":
                continue  # handled separately above
            key = _safe_key(ntype)
            n   = num_nodes_dict[ntype]
            d   = EMB_DIMS.get(ntype, 64)
            self.emb_tables[key] = nn.Embedding(n, d)
            nn.init.xavier_uniform_(self.emb_tables[key].weight)
            # Projection to hidden_dim
            self.input_proj[key] = (
                nn.Linear(d, hidden_dim, bias=False)
                if d != hidden_dim else nn.Identity()
            )

        # ── HGT convolutional layers ───────────────────────────────
        self.convs = nn.ModuleList([
            HGTConv(hidden_dim, hidden_dim, metadata, heads=num_heads)
            for _ in range(num_layers)
        ])

        # ── Per-layer, per-node-type LayerNorm ────────────────────
        self.layer_norms = nn.ModuleList([
            nn.ModuleDict({
                _safe_key(ntype): nn.LayerNorm(hidden_dim)
                for ntype in node_types
            })
            for _ in range(num_layers)
        ])

        # ── Cell-line context embedding ────────────────────────────
        # Learned embedding per cell line, projected to hidden_dim.
        # Concatenated with (emb_a, emb_b) before the scorer MLP.
        self.cell_line_emb  = nn.Embedding(num_cell_lines, NUM_CELL_LINE_DIM)
        self.cell_line_proj = nn.Linear(NUM_CELL_LINE_DIM, hidden_dim, bias=False)
        nn.init.xavier_uniform_(self.cell_line_emb.weight)
        nn.init.xavier_uniform_(self.cell_line_proj.weight)

        # ── Pair-scorer MLP ───────────────────────────────────────
        # Input: cat(emb_A, emb_B, emb_cell)  ->  [3 * hidden_dim]
        self.scorer = nn.Sequential(
            nn.Linear(hidden_dim * 3, hidden_dim),
            nn.ELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, 3),       # 3 classes
        )

    # ─────────────────────────────────────────────────────────────
    # Forward helpers
    # ─────────────────────────────────────────────────────────────

    def _build_x_dict(self, batch) -> dict[str, torch.Tensor]:
        """
        Build per-node-type feature tensors projected to hidden_dim.

        Drug nodes use a hybrid two-path approach keyed by fallback_lookup:
          fallback_lookup[i] == -1  →  node i has a real 2048-bit Morgan FP
          fallback_lookup[i] >= 0   →  node i is a fallback (biologic); value
                                        is its row index in drug_fallback_emb.

        PyG's NeighborLoader slices fallback_lookup, fp_mask and x all with the
        same batch-local drug node indices, so they are always consistent here.

          • FP path    : fp_feats[fp_mask]  →  drug_fp_proj  →  [N_fp_batch, 128]
          • Fallback   : drug_fallback_emb(fallback_lookup[fb_mask])  →  [N_fb_batch, 128]

        Non-drug types: integer index → nn.Embedding → Linear projection.
        """
        x_dict: dict[str, torch.Tensor] = {}

        for ntype in batch.node_types:
            store = batch[ntype]

            if ntype == "drug":
                fp_feats        = store.x               # float32 [N_batch_drug, FP_DIM=2048]
                fallback_lookup = store.fallback_lookup  # long    [N_batch_drug] -1 or 0..K-1
                # fp_mask is also available and consistent, but we derive from
                # fallback_lookup so there's a single source of truth per batch.
                fp_mask = (fallback_lookup < 0)   # True where node has a real FP
                fb_mask = (fallback_lookup >= 0)  # True where node is a fallback biologic

                n_drug = fp_feats.shape[0]
                out = torch.zeros(
                    n_drug, self.hidden_dim,
                    dtype=torch.float32,
                    device=fp_feats.device,
                )

                # FP path: project real 2048-bit fingerprints → 128 dims
                if fp_mask.any():
                    out[fp_mask] = self.drug_fp_proj(fp_feats[fp_mask])

                # Fallback path: look up batch-local fallback rows in the embedding table
                if fb_mask.any():
                    fb_row_indices = fallback_lookup[fb_mask]   # correct rows in Embedding(K, 128)
                    out[fb_mask] = self.drug_fallback_emb(fb_row_indices.to(fp_feats.device))

                x_dict[ntype] = self.dropout(out)

            else:
                key  = _safe_key(ntype)
                idx  = store.x          # global node IDs [N_local]
                emb  = self.emb_tables[key](idx)
                proj = self.input_proj[key](emb)
                x_dict[ntype] = self.dropout(proj)

        return x_dict

    def _build_edge_index_dict(self, batch) -> dict[tuple, torch.Tensor]:
        """
        Collect edge_index tensors for all message-passing edge types.
        Excludes the 'synergy_pair' supervision edge type so it is never
        used for neighbourhood aggregation.
        """
        ei_dict: dict[tuple, torch.Tensor] = {}
        for etype in batch.edge_types:
            _, rel, _ = etype
            if rel == "synergy_pair":
                continue
            store = batch[etype]
            if hasattr(store, "edge_index") and store.edge_index is not None:
                ei_dict[etype] = store.edge_index
        return ei_dict

    # ─────────────────────────────────────────────────────────────
    # Encode: run HGT to get node embeddings
    # ─────────────────────────────────────────────────────────────

    def encode(self, batch) -> dict[str, torch.Tensor]:
        x_dict = self._build_x_dict(batch)
        ei_dict = self._build_edge_index_dict(batch)

        for layer_idx, conv in enumerate(self.convs):
            norms = self.layer_norms[layer_idx]
            x_dict_new = conv(x_dict, ei_dict)
            # Post-conv: ELU + LayerNorm, fall back to pre-conv embedding if a
            # node type had no incoming edges (HGTConv returns None for it).
            x_dict = {
                ntype: F.elu(norms[_safe_key(ntype)](x_dict_new[ntype]))
                if (ntype in x_dict_new and x_dict_new[ntype] is not None)
                else x_dict[ntype]
                for ntype in x_dict
            }

        return x_dict

    # ─────────────────────────────────────────────────────────────
    # Score a batch of drug pairs
    # ─────────────────────────────────────────────────────────────

    def forward(self, batch) -> tuple[torch.Tensor, torch.Tensor]:
        """
        Returns
        -------
        logits  : [num_pairs, 3]   raw class scores
        labels  : [num_pairs]      ground-truth integer class (0/1/2)

        edge_label is a [num_pairs, 2] int64 tensor packed by train.py:
            col 0 = synergy class label (0/1/2)
            col 1 = cell-line integer ID
        """
        x_dict = self.encode(batch)

        pair_store = batch["drug", "synergy_pair", "drug"]
        src_local  = pair_store.edge_label_index[0]   # local drug indices in this batch
        dst_local  = pair_store.edge_label_index[1]

        # Unpack the 2-column edge_label
        packed     = pair_store.edge_label            # [num_pairs, 2]
        labels     = packed[:, 0]                     # synergy class  int64
        cell_ids   = packed[:, 1]                     # cell-line ID   int64

        drug_embs  = x_dict["drug"]                   # [N_drug_local, hidden_dim]
        emb_a      = drug_embs[src_local]
        emb_b      = drug_embs[dst_local]

        # Cell-line embedding
        emb_cell   = self.dropout(
            self.cell_line_proj(
                self.cell_line_emb(cell_ids.to(emb_a.device))
            )
        )                                             # [num_pairs, hidden_dim]

        pair_emb   = torch.cat([emb_a, emb_b, emb_cell], dim=-1)  # [num_pairs, 3*hidden_dim]
        logits     = self.scorer(pair_emb)                          # [num_pairs, 3]

        return logits, labels


# ─────────────────────────────────────────────────────────────────
# Lightning Module
# ─────────────────────────────────────────────────────────────────

class SynergyModule(pl.LightningModule):
    """
    PyTorch Lightning wrapper around SynergyGNN.

    Args
    ----
    metadata        : HeteroData metadata (node_types, edge_types)
    num_nodes_dict  : {node_type -> total node count}
    class_weights   : optional [3] float tensor for weighted CE loss
    lr              : learning rate for AdamW
    weight_decay    : L2 regularisation
    max_epochs      : used to configure CosineAnnealingLR
    """

    def __init__(
        self,
        metadata: tuple,
        num_nodes_dict: dict[str, int],
        num_fallback_drugs: int,
        num_cell_lines: int,
        num_layers: int      = 2,
        class_weights: torch.Tensor | None = None,
        lr: float            = 1e-3,
        weight_decay: float  = 1e-4,
        max_epochs: int      = 30,
        hidden_dim: int      = HIDDEN_DIM,
        num_heads: int       = NUM_HEADS,
        dropout: float       = DROPOUT,
    ) -> None:
        super().__init__()
        self.save_hyperparameters(ignore=["class_weights"])

        self.model = SynergyGNN(
            metadata           = metadata,
            num_nodes_dict     = num_nodes_dict,
            num_fallback_drugs = num_fallback_drugs,
            num_cell_lines     = num_cell_lines,
            num_layers         = num_layers,
            hidden_dim         = hidden_dim,
            num_heads          = num_heads,
            dropout            = dropout,
        )

        # Register class weights as buffer (moves to GPU with the module)
        if class_weights is not None:
            self.register_buffer("class_weights", class_weights.float())
        else:
            self.register_buffer("class_weights", None)

        # Collectors for test-epoch metrics (cleared each test epoch)
        self._test_logits: list[torch.Tensor] = []
        self._test_labels: list[torch.Tensor] = []

    # ─────────────────────────────────────────────────────────────
    # Forward
    # ─────────────────────────────────────────────────────────────

    def forward(self, batch):
        return self.model(batch)

    # ─────────────────────────────────────────────────────────────
    # Shared step
    # ─────────────────────────────────────────────────────────────

    def _shared_step(self, batch) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        logits, labels = self(batch)
        if logits.shape[0] == 0:
            # Empty mini-batch (can happen if no pairs have both drugs sampled)
            dummy_loss = torch.tensor(0.0, requires_grad=True, device=logits.device)
            return dummy_loss, logits, labels

        # Class-weighted cross-entropy loss (using softened sqrt class weights)
        loss = F.cross_entropy(logits, labels, weight=self.class_weights)
        return loss, logits, labels

    # ─────────────────────────────────────────────────────────────
    # Train / Val / Test steps
    # ─────────────────────────────────────────────────────────────

    def training_step(self, batch, batch_idx):
        loss, _, _ = self._shared_step(batch)
        self.log("train_loss", loss,
                 on_step=True, on_epoch=True, prog_bar=True, batch_size=256)
        return loss

    def validation_step(self, batch, batch_idx):
        loss, _, _ = self._shared_step(batch)
        self.log("val_loss", loss,
                 on_step=False, on_epoch=True, prog_bar=True, batch_size=256)
        return loss

    def test_step(self, batch, batch_idx):
        loss, logits, labels = self._shared_step(batch)
        self.log("test_loss", loss, on_step=False, on_epoch=True, batch_size=256)
        if logits.shape[0] > 0:
            self._test_logits.append(logits.detach().cpu())
            self._test_labels.append(labels.detach().cpu())

    def on_test_epoch_end(self) -> None:
        if not self._test_logits:
            print("  [WARNING] No test predictions collected.")
            return

        all_logits = torch.cat(self._test_logits)   # [N_test, 3]
        all_labels = torch.cat(self._test_labels)   # [N_test]
        self._test_logits.clear()
        self._test_labels.clear()

        probs      = F.softmax(all_logits, dim=-1).numpy()  # [N_test, 3]
        labels_np  = all_labels.numpy()
        preds_np   = all_logits.argmax(dim=-1).numpy()

        # ── Macro AUROC ───────────────────────────────────────────
        try:
            auroc = roc_auc_score(labels_np, probs, multi_class="ovr", average="macro")
        except ValueError as e:
            auroc = float("nan")
            print(f"  [WARNING] AUROC computation failed: {e}")

        # ── Macro AUPR (per-class, then average) ─────────────────
        aupr_per_class = []
        for c in range(3):
            binary_labels = (labels_np == c).astype(int)
            try:
                ap = average_precision_score(binary_labels, probs[:, c])
                aupr_per_class.append(ap)
            except ValueError:
                aupr_per_class.append(float("nan"))
        aupr = float(np.nanmean(aupr_per_class))

        # ── Confusion matrix ──────────────────────────────────────
        cm = confusion_matrix(labels_np, preds_np, labels=[0, 1, 2])

        # ── Log scalar metrics ────────────────────────────────────
        self.log("test_auroc", auroc)
        self.log("test_aupr",  aupr)

        # ── Print results ─────────────────────────────────────────
        sep = "=" * 60
        print(f"\n{sep}")
        print("  TEST RESULTS")
        print(sep)
        print(f"  Macro AUROC : {auroc:.4f}")
        print(f"  Macro AUPR  : {aupr:.4f}")
        print(f"\n  Per-class AUPR:")
        for i, (cls, ap) in enumerate(zip(CLASS_NAMES, aupr_per_class)):
            print(f"    {cls:<15}: {ap:.4f}")
        print(f"\n  Confusion Matrix  (rows=true, cols=pred):")
        print(f"  Classes: {CLASS_NAMES}")
        print(f"  {cm}")
        print(sep)

        if not np.isnan(auroc) and auroc < 0.65:
            print(
                f"\n  [WARNING] Test macro AUROC ({auroc:.4f}) is below 0.65.\n"
                f"  This may indicate insufficient training, a data issue, or that\n"
                f"  the cold-drug split is genuinely very hard (expected on small datasets).\n"
                f"  Consider: more epochs, lower LR, more HGT layers, or node features."
            )

    # ─────────────────────────────────────────────────────────────
    # Optimiser + scheduler
    # ─────────────────────────────────────────────────────────────

    def configure_optimizers(self):
        opt = torch.optim.AdamW(
            self.parameters(),
            lr           = self.hparams.lr,
            weight_decay = self.hparams.weight_decay,
        )
        sched = torch.optim.lr_scheduler.CosineAnnealingLR(
            opt,
            T_max  = self.hparams.max_epochs,
            eta_min = self.hparams.lr * 0.01,
        )
        return {
            "optimizer": opt,
            "lr_scheduler": {
                "scheduler": sched,
                "monitor":   "val_loss",
                "interval":  "epoch",
            },
        }
