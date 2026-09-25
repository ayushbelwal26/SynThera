"""
tests/test_random_split.py — Verification Suite for Random/Warm Split Benchmark
================================================================================

Validates that:
  1. No duplicate rows in any partition
  2. Every original observation in exactly one partition (disjoint union = 151,264)
  3. Partition counts match 70/15/15: train=105,884, val=22,690, test=22,690
  4. Seed 42 is deterministic (builder logic yields identical partitions)
  5. Different seed produces different partition
  6. Existing benchmark files unchanged (hash check)
  7. Champion checkpoint unchanged (hash check)
  8. Drug overlap train/test > 0 (confirms warm benchmark)
  9. Pair overlap train/test > 0 (confirms warm benchmark, >90% test pairs in train)
  10. (A, B) == (B, A) unordered pair canonicalization
  11. Metrics use same definitions as eval_paper_splits.py
  12. No test labels used for training (strict index disjointness)
  13. Random checkpoint path is distinct from champion checkpoint path
"""

import hashlib
import json
import os
import sys
import unittest
import numpy as np
import pandas as pd

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

PROCESSED_DIR = os.path.join(ROOT_DIR, "data", "processed")
SPLITS_RANDOM_DIR = os.path.join(PROCESSED_DIR, "splits_random")
MODELS_DIR = os.path.join(ROOT_DIR, "models")

LABELS_CSV = os.path.join(PROCESSED_DIR, "labeled_pairs.csv")
RANDOM_TRAIN_CSV = os.path.join(SPLITS_RANDOM_DIR, "random_train.csv")
RANDOM_VAL_CSV = os.path.join(SPLITS_RANDOM_DIR, "random_val.csv")
RANDOM_TEST_CSV = os.path.join(SPLITS_RANDOM_DIR, "random_test.csv")
BENCH_JSON = os.path.join(PROCESSED_DIR, "random_benchmark.json")

CHAMPION_CKPT = os.path.join(MODELS_DIR, "synergy_gnn_pair_interaction.ckpt")
RANDOM_CKPT = os.path.join(MODELS_DIR, "synergy_gnn_random_split_seed42.ckpt")

PROTECTED_HASHES = {
    "synergy_gnn_pair_interaction.ckpt": "271a592e065879f2",
    "pair_disjoint_benchmark.json": "f6766d9694da89f2",
    "leave_drug_out_benchmark.json": "eaf3fecd65f8458a",
    "strict_bilateral_benchmark.json": "e252b2a42e459f0f",
    "split_train.csv": "6511b36236c4d767",
    "split_val.csv": "2cf620f5db8e8cd1",
    "split_test.csv": "75f64e9761b1ad9d",
}


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def canonical_pair(a: str, b: str) -> tuple[str, str]:
    return tuple(sorted([a, b]))


class TestRandomSplit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.train_df = pd.read_csv(RANDOM_TRAIN_CSV)
        cls.val_df = pd.read_csv(RANDOM_VAL_CSV)
        cls.test_df = pd.read_csv(RANDOM_TEST_CSV)
        cls.labels_df = pd.read_csv(LABELS_CSV)

    def test_01_no_duplicate_rows(self):
        """1. No duplicate row_index within train, val, or test."""
        self.assertEqual(len(self.train_df["row_index"]), len(self.train_df["row_index"].unique()))
        self.assertEqual(len(self.val_df["row_index"]), len(self.val_df["row_index"].unique()))
        self.assertEqual(len(self.test_df["row_index"]), len(self.test_df["row_index"].unique()))

    def test_02_every_observation_in_exactly_one_partition(self):
        """2. Disjoint union equals all 151,264 rows."""
        s_train = set(self.train_df["row_index"])
        s_val = set(self.val_df["row_index"])
        s_test = set(self.test_df["row_index"])

        self.assertEqual(len(s_train & s_val), 0, "Train and Val overlap!")
        self.assertEqual(len(s_train & s_test), 0, "Train and Test overlap!")
        self.assertEqual(len(s_val & s_test), 0, "Val and Test overlap!")

        union_all = s_train | s_val | s_test
        self.assertEqual(len(union_all), 151264)
        self.assertEqual(union_all, set(range(151264)))

    def test_03_partition_counts_70_15_15(self):
        """3. Partition row counts match 70/15/15 specification."""
        self.assertEqual(len(self.train_df), 105884)
        self.assertEqual(len(self.val_df), 22690)
        self.assertEqual(len(self.test_df), 22690)
        self.assertEqual(len(self.train_df) + len(self.val_df) + len(self.test_df), 151264)

    def test_04_seed_42_deterministic(self):
        """4. Seed 42 permutation is 100% deterministic."""
        n_total = 151264
        n_test = round(n_total * 0.15)
        n_val = round(n_total * 0.15)

        rng1 = np.random.default_rng(42)
        perm1 = rng1.permutation(n_total)

        rng2 = np.random.default_rng(42)
        perm2 = rng2.permutation(n_total)

        np.testing.assert_array_equal(perm1, perm2)

        expected_train = sorted(perm1[n_test + n_val:].tolist())
        np.testing.assert_array_equal(self.train_df["row_index"].values, expected_train)

    def test_05_different_seed_different_partition(self):
        """5. Different seeds produce distinct partitions."""
        n_total = 151264
        n_test = round(n_total * 0.15)
        n_val = round(n_total * 0.15)

        rng_other = np.random.default_rng(99)
        perm_other = rng_other.permutation(n_total)
        other_train = sorted(perm_other[n_test + n_val:].tolist())
        self.assertFalse(np.array_equal(self.train_df["row_index"].values, other_train))

    def test_06_existing_benchmarks_unchanged(self):
        """6. Existing benchmark files are intact with exact matching SHA-256 hashes."""
        for fname, expected_hash in PROTECTED_HASHES.items():
            if fname.endswith(".ckpt"):
                continue  # checked in test_07
            fpath = os.path.join(PROCESSED_DIR, fname)
            self.assertTrue(os.path.exists(fpath), f"Protected file missing: {fname}")
            actual_hash = _sha256_file(fpath)
            self.assertEqual(
                actual_hash, expected_hash,
                f"PROTECTED FILE MODIFIED! {fname}: expected {expected_hash}, got {actual_hash}"
            )

    def test_07_champion_checkpoint_unchanged(self):
        """7. Champion checkpoint exists and its SHA-256 hash matches the frozen snapshot."""
        self.assertTrue(os.path.exists(CHAMPION_CKPT), "Champion checkpoint missing!")
        size_mb = os.path.getsize(CHAMPION_CKPT) / (1024 * 1024)
        self.assertGreater(size_mb, 20.0, f"Abnormal champion ckpt size: {size_mb:.2f} MB")

        actual_hash = _sha256_file(CHAMPION_CKPT)
        expected_hash = PROTECTED_HASHES["synergy_gnn_pair_interaction.ckpt"]
        self.assertEqual(
            actual_hash, expected_hash,
            f"CHAMPION CHECKPOINT MODIFIED! Expected {expected_hash}, got {actual_hash}"
        )

    def test_08_drug_overlap_train_test_warm(self):
        """8. Drug overlap between train and test is > 0 (confirms warm split)."""
        train_sub = self.labels_df.iloc[self.train_df["row_index"]]
        test_sub = self.labels_df.iloc[self.test_df["row_index"]]

        train_drugs = set(train_sub["drug_a_kg_id"]) | set(train_sub["drug_b_kg_id"])
        test_drugs = set(test_sub["drug_a_kg_id"]) | set(test_sub["drug_b_kg_id"])
        overlap = train_drugs & test_drugs
        self.assertGreater(len(overlap), 0, "No drug overlap in random split (expected warm benchmark)!")
        self.assertEqual(len(overlap), 182, f"Expected 182 overlapping drugs, found {len(overlap)}")
        # In random split, 100% of test observations have at least one partner drug in train:
        has_train_drug = (test_sub["drug_a_kg_id"].isin(train_drugs) | test_sub["drug_b_kg_id"].isin(train_drugs)).all()
        self.assertTrue(has_train_drug, "All test observations must have at least one drug seen in train!")

    def test_09_pair_overlap_train_test_warm(self):
        """9. Unordered pair overlap between train and test > 0 (>95% test obs have pair in train)."""
        train_sub = self.labels_df.iloc[self.train_df["row_index"]]
        test_sub = self.labels_df.iloc[self.test_df["row_index"]]

        train_pairs = set(canonical_pair(a, b) for a, b in zip(train_sub["drug_a_kg_id"], train_sub["drug_b_kg_id"]))
        test_pairs = [canonical_pair(a, b) for a, b in zip(test_sub["drug_a_kg_id"], test_sub["drug_b_kg_id"])]

        overlap_count = sum(1 for p in test_pairs if p in train_pairs)
        overlap_pct = (overlap_count / len(test_pairs)) * 100.0
        self.assertGreater(overlap_pct, 95.0, f"Expected >95% test pairs in train, got {overlap_pct:.2f}%")

    def test_10_unordered_pair_symmetry(self):
        """10. Unordered pair representation canonical_pair(a, b) is order-independent."""
        p1 = canonical_pair("DB00001", "DB00002")
        p2 = canonical_pair("DB00002", "DB00001")
        self.assertEqual(p1, p2)
        self.assertEqual(p1, ("DB00001", "DB00002"))

    def test_11_metrics_definitions_consistent(self):
        """11. evaluate_metrics returns standard paper metrics dict with all required keys."""
        from eval_paper_splits import evaluate_metrics
        mock_df = pd.DataFrame({
            "cell_line_name": ["C1", "C1", "C2", "C2"],
            "drug_a_kg_id": ["D1", "D2", "D1", "D2"],
            "drug_b_kg_id": ["D3", "D4", "D3", "D4"],
            "synergy_class": ["synergy", "additive", "antagonism", "synergy"]
        })
        mock_probs = np.array([
            [0.1, 0.2, 0.7],
            [0.2, 0.6, 0.2],
            [0.7, 0.2, 0.1],
            [0.2, 0.3, 0.5],
        ])
        res = evaluate_metrics(mock_df, mock_probs, k_list=[3])
        expected_keys = [
            "macro_auroc", "macro_aupr",
            "binary_synergy_auroc", "binary_synergy_aupr",
            "precision@3", "ndcg@3"
        ]
        for k in expected_keys:
            self.assertIn(k, res, f"Missing metric key: {k}")

    def test_12_no_test_labels_in_training(self):
        """12. Strict disjointness guarantees zero test labels are seen during training."""
        train_indices = set(self.train_df["row_index"])
        test_indices = set(self.test_df["row_index"])
        self.assertEqual(len(train_indices & test_indices), 0)

    def test_13_random_checkpoint_path_distinct(self):
        """13. Random checkpoint path is distinct from champion checkpoint."""
        self.assertNotEqual(
            os.path.abspath(RANDOM_CKPT),
            os.path.abspath(CHAMPION_CKPT),
            "Random checkpoint path must not be the champion checkpoint!"
        )
        self.assertIn("random", os.path.basename(RANDOM_CKPT))


if __name__ == "__main__":
    unittest.main()
