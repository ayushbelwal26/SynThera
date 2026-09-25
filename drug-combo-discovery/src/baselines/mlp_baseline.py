"""
src/baselines/mlp_baseline.py
=============================
Feedforward MLP Baseline for Drug Synergy Prediction (DeepSynergy-Style).
Phase B2 / Group 2 Item 4 Implementation.

Architecture:
- Input: Concatenation of [Morgan fingerprint A (2048-bit), Morgan fingerprint B (2048-bit), cell-line embedding (64-dim)] -> total 4,160-dim.
- Feedforward MLP:
    Linear(4160 -> 512) -> LayerNorm(512) -> ReLU -> Dropout(0.2)
    Linear(512 -> 256)  -> LayerNorm(256) -> ReLU -> Dropout(0.2)
    Linear(256 -> 128)  -> LayerNorm(128) -> ReLU -> Dropout(0.2)
    Linear(128 -> 3)    -> 3-class logits (0: antagonism, 1: additive, 2: synergy)
- Symmetrized inference:
    Averages probabilities from forward (A, B, C) and reverse (B, A, C) orderings.
"""

from __future__ import annotations
import torch
import torch.nn as nn
import torch.nn.functional as F


class DeepSynergyMLP(nn.Module):
    """
    DeepSynergy-style feedforward neural network operating purely on chemical fingerprints
    and cell-line context (without graph message passing or topological PPI edges).
    """

    def __init__(
        self,
        fp_dim: int = 2048,
        num_cell_lines: int = 80,
        cell_dim: int = 64,
        hidden_dims: list[int] = [512, 256, 128],
        dropout: float = 0.2,
        num_classes: int = 3,
    ):
        super().__init__()
        self.fp_dim = fp_dim
        self.cell_dim = cell_dim
        self.num_classes = num_classes

        # Learnable cell line embedding
        self.cell_embedding = nn.Embedding(num_cell_lines, cell_dim)

        in_dim = fp_dim * 2 + cell_dim
        layers = []
        curr_dim = in_dim
        for h_dim in hidden_dims:
            layers.append(nn.Linear(curr_dim, h_dim))
            layers.append(nn.LayerNorm(h_dim))
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(dropout))
            curr_dim = h_dim

        self.backbone = nn.Sequential(*layers)
        self.classifier = nn.Linear(curr_dim, num_classes)

    def forward(
        self,
        fp_a: torch.Tensor,
        fp_b: torch.Tensor,
        cell_idx: torch.Tensor,
    ) -> torch.Tensor:
        """
        Forward pass for a specific drug pair ordering (A, B, C).
        """
        c_emb = self.cell_embedding(cell_idx)
        x = torch.cat([fp_a, fp_b, c_emb], dim=-1)
        h = self.backbone(x)
        logits = self.classifier(h)
        return logits

    def forward_symmetric(
        self,
        fp_a: torch.Tensor,
        fp_b: torch.Tensor,
        cell_idx: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """
        Symmetric forward pass: evaluates both (A, B, C) and (B, A, C),
        returning the averaged softmax probabilities and averaged logits.
        """
        logits_fwd = self.forward(fp_a, fp_b, cell_idx)
        logits_rev = self.forward(fp_b, fp_a, cell_idx)

        probs_fwd = F.softmax(logits_fwd, dim=-1)
        probs_rev = F.softmax(logits_rev, dim=-1)
        probs_sym = (probs_fwd + probs_rev) / 2.0
        logits_sym = (logits_fwd + logits_rev) / 2.0

        return probs_sym, logits_sym
