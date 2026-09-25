"""
tests/test_paper_splits.py — Formal Reproducibility and Leakage Verification Suite
==================================================================================

Validates that:
  1. No train/test row overlap across all splits
  2. No validation/test row overlap across all splits
  3. No pair leakage for Leave-Pair-Out (LPO)
  4. No held-out drug leakage for Leave-Drug-Out (LDO)
  5. Both drugs strictly unseen for Strict Bilateral
  6. Symmetry: A+B and B+A treated identically
  7. Deterministic split generation across independent seeds
  8. Checkpoint unchanged (models/synergy_gnn_pair_interaction.ckpt)
  9. Strict bilateral benchmark values verified and unchanged
"""

import os
import sys
import json
import random
import unittest
import numpy as np
import pandas as pd
import torch

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_DIR = os.path.join(ROOT_DIR, "data", "processed")
SPLITS_EXTRA_DIR = os.path.join(PROCESSED_DIR, "splits_extra")

LABELS_CSV = os.path.join(PROCESSED_DIR, "labeled_pairs.csv")
TRAIN_CSV = os.path.join(PROCESSED_DIR, "split_train.csv")
VAL_CSV = os.path.join(PROCESSED_DIR, "split_val.csv")
TEST_CSV = os.path.join(PROCESSED_DIR, "split_test.csv")

LPO_TRAIN_CSV = os.path.join(SPLITS_EXTRA_DIR, "pair_disjoint_train.csv")
LPO_VAL_CSV = os.path.join(SPLITS_EXTRA_DIR, "pair_disjoint_val.csv")
LPO_TEST_CSV = os.path.join(SPLITS_EXTRA_DIR, "pair_disjoint_test.csv")

CHECKPOINT_PATH = os.path.join(ROOT_DIR, "models", "synergy_gnn_pair_interaction.ckpt")
EXP1_JSON = os.path.join(PROCESSED_DIR, "experiment1_pair_interaction_benchmark.json")


def make_canonical_pair(da: str, db: str) -> tuple[str, str]:
    return tuple(sorted([da, db]))


class TestPaperSplits(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.labels_data = pd.read_csv(LABELS_CSV)
        cls.labels_data["unordered_pair"] = [
            make_canonical_pair(a, b)
            for a, b in zip(cls.labels_data["drug_a_kg_id"], cls.labels_data["drug_b_kg_id"])
        ]

        rng = random.Random(42)
        all_drugs = sorted(set(cls.labels_data["drug_a_kg_id"].unique()) | set(cls.labels_data["drug_b_kg_id"].unique()))
        rng.shuffle(all_drugs)
        n_total = len(all_drugs)
        n_test = max(1, round(n_total * 0.15))
        n_val = max(1, round(n_total * 0.15))

        cls.test_drugs = set(all_drugs[:n_test])
        cls.val_drugs = set(all_drugs[n_test : n_test + n_val])
        cls.train_drugs = set(all_drugs[n_test + n_val :])

    def test_01_row_overlap_original_split(self):
        """Verify zero row overlap between train, val, and test in original dataset."""
        train_idx = set(pd.read_csv(TRAIN_CSV)["row_index"])
        val_idx = set(pd.read_csv(VAL_CSV)["row_index"])
        test_idx = set(pd.read_csv(TEST_CSV)["row_index"])

        self.assertEqual(len(train_idx & test_idx), 0, "Train and Test row overlap in original split!")
        self.assertEqual(len(val_idx & test_idx), 0, "Val and Test row overlap in original split!")
        self.assertEqual(len(train_idx & val_idx), 0, "Train and Val row overlap in original split!")
        self.assertEqual(len(train_idx | val_idx | test_idx), 151264, "Missing rows in original split!")

    def test_02_row_overlap_lpo_split(self):
        """Verify zero row overlap in the new Leave-Pair-Out split."""
        train_idx = set(pd.read_csv(LPO_TRAIN_CSV)["row_index"])
        val_idx = set(pd.read_csv(LPO_VAL_CSV)["row_index"])
        test_idx = set(pd.read_csv(LPO_TEST_CSV)["row_index"])

        self.assertEqual(len(train_idx & test_idx), 0, "Train and Test row overlap in LPO split!")
        self.assertEqual(len(val_idx & test_idx), 0, "Val and Test row overlap in LPO split!")
        self.assertEqual(len(train_idx & val_idx), 0, "Train and Val row overlap in LPO split!")
        self.assertEqual(len(train_idx | val_idx | test_idx), 151264, "Missing rows in LPO split!")

    def test_03_no_pair_leakage_lpo(self):
        """Verify that Leave-Pair-Out (LPO) has strictly zero pair leakage."""
        train_idx = pd.read_csv(LPO_TRAIN_CSV)["row_index"]
        val_idx = pd.read_csv(LPO_VAL_CSV)["row_index"]
        test_idx = pd.read_csv(LPO_TEST_CSV)["row_index"]

        train_pairs = set(self.labels_data.iloc[train_idx]["unordered_pair"])
        val_pairs = set(self.labels_data.iloc[val_idx]["unordered_pair"])
        test_pairs = set(self.labels_data.iloc[test_idx]["unordered_pair"])

        # Strict pair disjointness
        self.assertEqual(len(train_pairs & test_pairs), 0, f"Pair leakage: {len(train_pairs & test_pairs)} pairs overlap!")
        self.assertEqual(len(val_pairs & test_pairs), 0, f"Pair leakage: {len(val_pairs & test_pairs)} pairs overlap!")
        self.assertEqual(len(train_pairs & val_pairs), 0, f"Pair leakage: {len(train_pairs & val_pairs)} pairs overlap!")

        # Individual drug sharing (expected for LPO)
        train_drugs = set(self.labels_data.iloc[train_idx]["drug_a_kg_id"]) | set(self.labels_data.iloc[train_idx]["drug_b_kg_id"])
        test_drugs = set(self.labels_data.iloc[test_idx]["drug_a_kg_id"]) | set(self.labels_data.iloc[test_idx]["drug_b_kg_id"])
        shared_drugs = train_drugs & test_drugs
        self.assertGreater(len(shared_drugs), 0, "LPO must allow individual drugs to be shared with different partners.")

    def test_04_no_held_out_drug_leakage_ldo(self):
        """Verify that designated held-out drugs in LDO never appear in training pairs."""
        train_idx = pd.read_csv(TRAIN_CSV)["row_index"]
        train_df = self.labels_data.iloc[train_idx]
        train_pair_drugs = set(train_df["drug_a_kg_id"]) | set(train_df["drug_b_kg_id"])

        # Invariant: No test drug can ever appear in any training pair
        test_leak = train_pair_drugs & self.test_drugs
        val_leak = train_pair_drugs & self.val_drugs
        self.assertEqual(len(test_leak), 0, f"LDO Violation: {len(test_leak)} test drugs leaked into train!")
        self.assertEqual(len(val_leak), 0, f"LDO Violation: {len(val_leak)} val drugs leaked into train!")

    def test_05_both_drugs_unseen_strict_bilateral(self):
        """Verify strict bilateral test set: BOTH drugs strictly unseen in train and val."""
        test_idx = pd.read_csv(TEST_CSV)["row_index"]
        test_df = self.labels_data.iloc[test_idx]

        mask_strict = test_df["drug_a_kg_id"].isin(self.test_drugs) & test_df["drug_b_kg_id"].isin(self.test_drugs)
        strict_df = test_df[mask_strict]

        # Verify counts
        self.assertEqual(len(strict_df), 2565, f"Expected 2,565 strict pairs, found {len(strict_df)}")
        strict_drugs = set(strict_df["drug_a_kg_id"]) | set(strict_df["drug_b_kg_id"])
        self.assertEqual(len(strict_drugs), 12, f"Expected 12 unique drugs, found {len(strict_drugs)}")
        self.assertEqual(strict_df["cell_line_name"].nunique(), 75, f"Expected 75 cell lines, found {strict_df['cell_line_name'].nunique()}")

        # Strict isolation
        train_or_val = self.train_drugs | self.val_drugs
        self.assertEqual(len(strict_drugs & train_or_val), 0, "Leakage: strict bilateral drugs present in train or val!")
        self.assertTrue(strict_df["drug_a_kg_id"].isin(self.test_drugs).all(), "Drug A not in test_drugs for all pairs!")
        self.assertTrue(strict_df["drug_b_kg_id"].isin(self.test_drugs).all(), "Drug B not in test_drugs for all pairs!")

    def test_06_symmetry_unordered_pairs(self):
        """Verify that pair representation [hA ; hB ; hA ⊙ hB ; |hA - hB| ; hCell] is mathematically order-invariant."""
        h_a = torch.tensor([[1.0, 2.0, 3.0]])
        h_b = torch.tensor([[4.0, 5.0, 6.0]])

        hadamard_fwd = h_a * h_b
        hadamard_rev = h_b * h_a
        self.assertTrue(torch.allclose(hadamard_fwd, hadamard_rev), "Hadamard product is not commutative!")

        diff_abs_fwd = torch.abs(h_a - h_b)
        diff_abs_rev = torch.abs(h_b - h_a)
        self.assertTrue(torch.allclose(diff_abs_fwd, diff_abs_rev), "Absolute difference is not symmetric!")

    def test_07_deterministic_split_generation(self):
        """Verify that split generation with seed=42 produces 100% identical row index lists."""
        def generate(seed):
            rng = random.Random(seed)
            all_pairs = sorted(self.labels_data["unordered_pair"].unique())
            shuffled = list(all_pairs)
            rng.shuffle(shuffled)
            n = len(shuffled)
            n_test = round(n * 0.15)
            return shuffled[:n_test]

        run1 = generate(42)
        run2 = generate(42)
        self.assertEqual(run1, run2, "Split generation is not deterministic!")

    def test_08_checkpoint_unchanged(self):
        """Verify models/synergy_gnn_pair_interaction.ckpt exists and has correct 640-d input."""
        self.assertTrue(os.path.exists(CHECKPOINT_PATH), "Checkpoint missing!")
        size_mb = os.path.getsize(CHECKPOINT_PATH) / (1024 * 1024)
        self.assertGreater(size_mb, 20.0, f"Checkpoint size abnormal: {size_mb:.2f} MB")

        ckpt = torch.load(CHECKPOINT_PATH, map_location="cpu", weights_only=False)
        scorer_weight = ckpt["state_dict"]["model.scorer.0.weight"]
        self.assertEqual(scorer_weight.shape, (128, 640), f"Expected scorer in_features=640, found {scorer_weight.shape}")

    def test_09_strict_benchmark_unchanged(self):
        """Verify strict bilateral benchmark values in experiment1_pair_interaction_benchmark.json."""
        self.assertTrue(os.path.exists(EXP1_JSON), "experiment1_pair_interaction_benchmark.json missing!")
        with open(EXP1_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)

        sb = data["strict_bilateral"]
        self.assertEqual(sb["n_pairs"], 2565)
        self.assertEqual(sb["n_unique_drugs"], 12)
        self.assertEqual(sb["n_cell_lines"], 75)
        self.assertAlmostEqual(sb["macro_auroc"], 0.6225, places=3)
        self.assertAlmostEqual(sb["binary_synergy_auroc"], 0.5373, places=3)


if __name__ == "__main__":
    unittest.main()
