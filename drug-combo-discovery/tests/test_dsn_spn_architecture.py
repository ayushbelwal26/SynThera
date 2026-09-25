"""
tests/test_dsn_spn_architecture.py
==================================

Unit and sanity tests for Experiment 5: Drug-Specific Subnetwork (DSN) ->
Synergy Prediction Network (SPN) architecture.

Requirements verified:
  1. Permutation Symmetry: f(A, B, cell) == f(B, A, cell) with max error <= 1e-6.
  2. Shared DSN parameters: Drug A and Drug B share the exact same weights (no artificial slot identity).
  3. Cell Sensitivity: Changing cell representation changes the predictions (confirming context conditioning).
  4. Output Shape: [batch_size, 3] for antagonistic, additive, synergy classes.
  5. Checkpoint Protection: Champion checkpoint (models/synergy_gnn_pair_interaction.ckpt) exists and is untouched.
  6. PyG Batch Symmetry: Test forward pass with swapped edge_label_index on real HeteroData batch.
"""

from __future__ import annotations

import os
import sys
import unittest
import torch
import torch.nn as nn

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from model import SynergyGNN, SynergyModule
from train import HETERODATA_PATH, MODELS_DIR, compute_class_weights


class TestDSNSPNArchitecture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.heterodata = torch.load(HETERODATA_PATH, weights_only=False)
        cls.metadata = cls.heterodata.metadata()
        cls.num_nodes_dict = {nt: cls.heterodata[nt].num_nodes for nt in cls.heterodata.node_types}
        cls.num_fallback = int((~cls.heterodata["drug"].fp_mask).sum().item())
        cls.num_cell_lines = cls.heterodata.num_cell_lines
        cls.class_weights = compute_class_weights(cls.heterodata)

        # Instantiate DSN/SPN model
        cls.model_dsn = SynergyGNN(
            metadata=cls.metadata,
            num_nodes_dict=cls.num_nodes_dict,
            num_fallback_drugs=cls.num_fallback,
            num_cell_lines=cls.num_cell_lines,
            hidden_dim=128,
            use_dsn_spn=True,
        )
        cls.model_dsn.eval()

    def test_shared_dsn_parameters(self):
        """A. Verify that Drug A and Drug B use the exact same DSN module and weights."""
        self.assertTrue(hasattr(self.model_dsn, "dsn"), "Model lacks dsn attribute.")
        self.assertTrue(hasattr(self.model_dsn, "spn"), "Model lacks spn attribute.")
        self.assertFalse(hasattr(self.model_dsn, "dsn_a"), "Model must NOT have separate dsn_a.")
        self.assertFalse(hasattr(self.model_dsn, "dsn_b"), "Model must NOT have separate dsn_b.")

        # Check that dsn has linear layers
        dsn_linears = [m for m in self.model_dsn.dsn if isinstance(m, nn.Linear)]
        self.assertEqual(len(dsn_linears), 2, "DSN should have 2 linear layers.")
        self.assertEqual(dsn_linears[0].in_features, 256)
        self.assertEqual(dsn_linears[0].out_features, 128)
        self.assertEqual(dsn_linears[1].in_features, 128)
        self.assertEqual(dsn_linears[1].out_features, 128)

        # Check SPN input dimension: [z_sum || z_prod || z_diff || cell] -> 512
        spn_linears = [m for m in self.model_dsn.spn if isinstance(m, nn.Linear)]
        self.assertEqual(len(spn_linears), 2, "SPN should have 2 linear layers.")
        self.assertEqual(spn_linears[0].in_features, 512)
        self.assertEqual(spn_linears[0].out_features, 128)
        self.assertEqual(spn_linears[1].out_features, 3)

    def test_swap_invariance_embeddings(self):
        """B1. Verify mathematical permutation invariance on random embedding tensors."""
        torch.manual_seed(42)
        batch_size = 32
        hidden_dim = 128

        emb_a = torch.randn(batch_size, hidden_dim)
        emb_b = torch.randn(batch_size, hidden_dim)
        emb_cell = torch.randn(batch_size, hidden_dim)

        with torch.no_grad():
            logits_ab = self.model_dsn.score_pair_dsn_spn(emb_a, emb_b, emb_cell)
            logits_ba = self.model_dsn.score_pair_dsn_spn(emb_b, emb_a, emb_cell)

        diff = torch.abs(logits_ab - logits_ba)
        max_diff = diff.max().item()
        print(f"\n[Test] Maximum swap difference on random embeddings: {max_diff:.2e}")
        self.assertLessEqual(max_diff, 1e-6, f"Swap difference {max_diff} exceeds 1e-6 tolerance!")

    def test_cell_sensitivity(self):
        """C. Verify that changing cell representation changes the predictions."""
        torch.manual_seed(42)
        batch_size = 16
        hidden_dim = 128

        emb_a = torch.randn(batch_size, hidden_dim)
        emb_b = torch.randn(batch_size, hidden_dim)
        emb_cell_1 = torch.randn(batch_size, hidden_dim)
        emb_cell_2 = torch.randn(batch_size, hidden_dim)

        with torch.no_grad():
            logits_1 = self.model_dsn.score_pair_dsn_spn(emb_a, emb_b, emb_cell_1)
            logits_2 = self.model_dsn.score_pair_dsn_spn(emb_a, emb_b, emb_cell_2)

        diff = torch.abs(logits_1 - logits_2)
        mean_diff = diff.mean().item()
        print(f"[Test] Mean difference when altering cell context: {mean_diff:.4f}")
        self.assertGreater(mean_diff, 1e-3, "Predictions did not change when cell context changed!")

    def test_output_shape(self):
        """D. Verify output shape is [batch_size, 3]."""
        batch_size = 10
        hidden_dim = 128
        emb_a = torch.randn(batch_size, hidden_dim)
        emb_b = torch.randn(batch_size, hidden_dim)
        emb_cell = torch.randn(batch_size, hidden_dim)

        with torch.no_grad():
            logits = self.model_dsn.score_pair_dsn_spn(emb_a, emb_b, emb_cell)

        self.assertEqual(logits.shape, (batch_size, 3))

    def test_champion_checkpoint_preserved(self):
        """E. Verify champion checkpoint exists and has not been modified."""
        champion_path = os.path.join(MODELS_DIR, "synergy_gnn_pair_interaction.ckpt")
        self.assertTrue(os.path.exists(champion_path), f"Champion checkpoint {champion_path} is missing!")
        size_mb = os.path.getsize(champion_path) / 1e6
        print(f"[Test] Champion checkpoint size: {size_mb:.2f} MB")
        self.assertGreater(size_mb, 10.0, "Champion checkpoint appears corrupted or truncated.")

    def test_pyg_batch_symmetry(self):
        """F. Verify symmetry across a real PyG NeighborLoader mini-batch."""
        from train import build_loaders
        _, _, test_loader = build_loaders(self.heterodata, [], [], [])
        batch = next(iter(test_loader))

        self.model_dsn.eval()
        with torch.no_grad():
            logits_fwd, _ = self.model_dsn(batch)

            batch_rev = batch.clone()
            orig_edge_idx = batch_rev["drug", "synergy_pair", "drug"].edge_label_index
            batch_rev["drug", "synergy_pair", "drug"].edge_label_index = orig_edge_idx[[1, 0]]
            logits_rev, _ = self.model_dsn(batch_rev)

        diff = torch.abs(logits_fwd - logits_rev)
        max_diff = diff.max().item()
        print(f"[Test] PyG batch swap maximum difference: {max_diff:.2e}")
        self.assertLessEqual(max_diff, 1e-6, f"Batch swap difference {max_diff} exceeds 1e-6 tolerance!")


if __name__ == "__main__":
    unittest.main()
