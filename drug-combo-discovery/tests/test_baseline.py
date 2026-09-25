"""
tests/test_baseline.py
======================
Unit and regression tests for DeepSynergy-style MLP baseline.
Phase B2 / Group 2 Item 4.
"""

import os
import sys
import unittest
import torch

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from baselines.mlp_baseline import DeepSynergyMLP
from baselines.train_baseline import BASELINES_DIR


class TestDeepSynergyBaseline(unittest.TestCase):
    def setUp(self):
        self.device = torch.device("cpu")
        self.model = DeepSynergyMLP(
            fp_dim=2048,
            num_cell_lines=80,
            cell_dim=64,
            hidden_dims=[128, 64],
            dropout=0.1,
            num_classes=3,
        ).to(self.device)

    def test_forward_pass_shape(self):
        batch_size = 4
        fp_a = torch.randn(batch_size, 2048)
        fp_b = torch.randn(batch_size, 2048)
        cell_idx = torch.tensor([0, 5, 12, 79], dtype=torch.long)

        logits = self.model(fp_a, fp_b, cell_idx)
        self.assertEqual(logits.shape, (batch_size, 3))

    def test_symmetric_inference_property(self):
        """
        Verify that forward_symmetric satisfies P(A, B, C) == P(B, A, C)
        and probabilities sum to 1.
        """
        self.model.eval()
        batch_size = 3
        fp_a = torch.randn(batch_size, 2048)
        fp_b = torch.randn(batch_size, 2048)
        cell_idx = torch.tensor([1, 10, 42], dtype=torch.long)

        probs_fwd, _ = self.model.forward_symmetric(fp_a, fp_b, cell_idx)
        probs_rev, _ = self.model.forward_symmetric(fp_b, fp_a, cell_idx)

        # Symmetry test
        self.assertTrue(torch.allclose(probs_fwd, probs_rev, atol=1e-6))

        # Probability distribution test
        sums = probs_fwd.sum(dim=-1)
        self.assertTrue(torch.allclose(sums, torch.ones_like(sums), atol=1e-5))

    def test_checkpoints_exist(self):
        """
        Verify trained baseline checkpoints exist in models/baselines.
        """
        cold_ckpt = os.path.join(BASELINES_DIR, "mlp_cold.pt")
        warm_ckpt = os.path.join(BASELINES_DIR, "mlp_warm_random.pt")

        self.assertTrue(os.path.exists(cold_ckpt), f"Missing {cold_ckpt}")
        self.assertTrue(os.path.exists(warm_ckpt), f"Missing {warm_ckpt}")

        # Test loading
        state_cold = torch.load(cold_ckpt, map_location="cpu")
        self.assertIn("model_state_dict", state_cold)
        self.assertIn("val_loss", state_cold)

        state_warm = torch.load(warm_ckpt, map_location="cpu")
        self.assertIn("model_state_dict", state_warm)
        self.assertIn("val_loss", state_warm)


if __name__ == "__main__":
    unittest.main()
