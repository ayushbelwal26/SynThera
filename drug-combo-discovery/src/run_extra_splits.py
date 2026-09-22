"""
End-to-end training and deterministic 5-pass evaluation for extra generalization splits:
  1. Warm/Random (pair-level random split)
  2. Leave-Cell-Line-Out (held-out cell lines)
  3. Leave-Tissue-Out (held-out tissues / cancer types)

Trains seeds 1, 2, 42 for each split using the identical baseline architecture
(384-dim simple concat head, lr=1e-3, weight_decay=1e-4, patience=5 on val_loss).
Saves checkpoints to models/extra_splits/{split_type}_seed{seed}.ckpt.
Evaluates each checkpoint deterministically across 5 passes on its test set.
Produces per-class metrics (synergy, additive, antagonism) and combined summary table.
"""

import os
import glob
import time
import shutil
import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
import pytorch_lightning as pl
from pytorch_lightning.callbacks import ModelCheckpoint, EarlyStopping
from torch_geometric.loader import LinkNeighborLoader
from sklearn.metrics import roc_auc_score, average_precision_score

from model import SynergyModule
from train import NUM_NEIGHBORS, BATCH_SIZE, MAX_EPOCHS, LR, WEIGHT_DECAY, ES_PATIENCE

PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")
SPLITS_EXTRA_DIR = os.path.join(PROCESSED_DIR, "splits_extra")
HETERODATA_PATH = os.path.join(PROCESSED_DIR, "heterodata.pt")
LABELS_PATH = os.path.join(PROCESSED_DIR, "labeled_pairs.csv")
NODES_PATH = os.path.join(PROCESSED_DIR, "primekg_nodes.csv")
EXTRA_MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "models", "extra_splits")
os.makedirs(EXTRA_MODELS_DIR, exist_ok=True)

SEEDS = [1, 2, 42]
SPLIT_TYPES = ["warm_random", "leave_cell_line", "leave_tissue"]
CLASS_MAP = {"antagonism": 0, "additive": 1, "synergy": 2}


def load_shared_resources():
    print(f"Loading HeteroData from {HETERODATA_PATH}...")
    heterodata = torch.load(HETERODATA_PATH, weights_only=False)

    print("Building drug and cell line index maps...")
    nodes = pd.read_csv(NODES_PATH)
    drug_sub = nodes[nodes["node_type"] == "drug"].reset_index(drop=True)
    drug_map = {str(row["id"]): i for i, (_, row) in enumerate(drug_sub.iterrows())}
    cell_map = heterodata.cell_line_map

    labels_df = pd.read_csv(LABELS_PATH)
    print(f"Loaded {len(labels_df):,} labeled pairs.")

    return heterodata, drug_map, cell_map, labels_df


def build_split_loaders(heterodata, drug_map, cell_map, labels_df, split_type):
    train_idx = pd.read_csv(os.path.join(SPLITS_EXTRA_DIR, f"{split_type}_train.csv"))["row_index"].tolist()
    val_idx = pd.read_csv(os.path.join(SPLITS_EXTRA_DIR, f"{split_type}_val.csv"))["row_index"].tolist()
    test_idx = pd.read_csv(os.path.join(SPLITS_EXTRA_DIR, f"{split_type}_test.csv"))["row_index"].tolist()

    def _make_loader_from_indices(idx_list, shuffle=False):
        sub = labels_df.iloc[idx_list].reset_index(drop=True)
        a_idx = torch.tensor(sub["drug_a_kg_id"].astype(str).map(drug_map).astype(int).values, dtype=torch.long)
        b_idx = torch.tensor(sub["drug_b_kg_id"].astype(str).map(drug_map).astype(int).values, dtype=torch.long)
        c_idx = torch.tensor(sub["cell_line_name"].map(cell_map).astype(int).values, dtype=torch.long)
        y_idx = torch.tensor(sub["synergy_class"].map(CLASS_MAP).astype(int).values, dtype=torch.long)

        edge_label_index = torch.stack([a_idx, b_idx], dim=0)
        edge_label = torch.stack([y_idx, c_idx], dim=1)

        loader = LinkNeighborLoader(
            data=heterodata,
            num_neighbors=NUM_NEIGHBORS,
            edge_label_index=(("drug", "synergy_pair", "drug"), edge_label_index),
            edge_label=edge_label,
            batch_size=BATCH_SIZE,
            shuffle=shuffle,
            num_workers=0,
            persistent_workers=False,
        )
        return loader, y_idx

    train_loader, train_y = _make_loader_from_indices(train_idx, shuffle=True)
    val_loader, val_y = _make_loader_from_indices(val_idx, shuffle=False)
    test_loader, test_y = _make_loader_from_indices(test_idx, shuffle=False)

    # Compute soft class weights from train split: weight_c = sqrt(N_total / (3 * N_c))
    n_total = float(len(train_y))
    class_weights = torch.tensor([
        np.sqrt(n_total / (3.0 * float((train_y == c).sum()))) for c in range(3)
    ], dtype=torch.float32)

    print(f"\n  Split '{split_type}':")
    print(f"    Train pairs: {len(train_idx):,} | class weights: {class_weights.tolist()}")
    print(f"    Val   pairs: {len(val_idx):,}")
    print(f"    Test  pairs: {len(test_idx):,}")

    return train_loader, val_loader, test_loader, class_weights, test_idx


def train_single_model(split_type, seed, heterodata, train_loader, val_loader, class_weights):
    ckpt_target = os.path.join(EXTRA_MODELS_DIR, f"{split_type}_seed{seed}.ckpt")
    if os.path.exists(ckpt_target):
        print(f"  Checkpoint already exists: {ckpt_target}. Skipping training.")
        return ckpt_target, 0.0

    print(f"\n{'=' * 75}")
    print(f"  TRAINING: split={split_type} | seed={seed}")
    print(f"{'=' * 75}")
    t0 = time.time()

    pl.seed_everything(seed, workers=True)

    metadata = heterodata.metadata()
    num_nodes_dict = {nt: heterodata[nt].num_nodes for nt in heterodata.node_types}
    n_fallback = int((~heterodata["drug"].fp_mask).sum().item())

    model = SynergyModule(
        metadata=metadata,
        num_nodes_dict=num_nodes_dict,
        num_fallback_drugs=n_fallback,
        num_cell_lines=heterodata.num_cell_lines,
        hidden_dim=128,
        num_layers=2,
        lr=LR,
        weight_decay=WEIGHT_DECAY,
        class_weights=class_weights,
        enriched_pair_head=False,
        use_target_features=False,
    )

    temp_dir = os.path.join(EXTRA_MODELS_DIR, f"temp_{split_type}_seed{seed}")
    os.makedirs(temp_dir, exist_ok=True)

    checkpoint_cb = ModelCheckpoint(
        dirpath=temp_dir,
        filename=f"{split_type}_seed{seed}",
        monitor="val_loss",
        save_top_k=1,
        mode="min",
        verbose=False,
    )
    early_stop_cb = EarlyStopping(
        monitor="val_loss",
        patience=ES_PATIENCE,
        mode="min",
        verbose=True,
    )

    trainer = pl.Trainer(
        accelerator="gpu" if torch.cuda.is_available() else "cpu",
        devices=1,
        max_epochs=MAX_EPOCHS,
        callbacks=[early_stop_cb, checkpoint_cb],
        log_every_n_steps=20,
        enable_progress_bar=True,
        deterministic=False,
        gradient_clip_val=1.0,
        inference_mode=False,
    )

    trainer.fit(model, train_loader, val_loader)
    elapsed = time.time() - t0

    best_ckpt = checkpoint_cb.best_model_path
    if not best_ckpt or not os.path.exists(best_ckpt):
        # Fallback to any ckpt in temp_dir
        ckpts = glob.glob(os.path.join(temp_dir, "*.ckpt"))
        if ckpts:
            best_ckpt = ckpts[0]

    assert best_ckpt and os.path.exists(best_ckpt), f"No checkpoint saved for {split_type}_seed{seed}!"
    shutil.copyfile(best_ckpt, ckpt_target)
    shutil.rmtree(temp_dir, ignore_errors=True)

    print(f"  Finished {split_type}_seed{seed} in {elapsed:.1f}s ({elapsed/60:.2f} min).")
    print(f"  Saved -> {ckpt_target} ({os.path.getsize(ckpt_target)/(1024*1024):.2f} MB)")

    return ckpt_target, elapsed


def evaluate_model_5pass(model, test_loader, device="cuda", n_passes=5):
    device_obj = torch.device(device if torch.cuda.is_available() else "cpu")
    model.to(device_obj)
    model.eval()

    pass_metrics = []
    labels_np = None

    for p in range(n_passes):
        torch.manual_seed(p)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(p)
        np.random.seed(p)

        logits_list, labels_list = [], []
        with torch.no_grad():
            for batch in test_loader:
                batch = batch.to(device_obj)
                logits, labels = model(batch)
                if logits.shape[0] > 0:
                    logits_list.append(logits.detach().cpu())
                    labels_list.append(labels.detach().cpu())

        logits_all = torch.cat(logits_list, dim=0)
        labels_all = torch.cat(labels_list, dim=0)
        probs_p = F.softmax(logits_all, dim=-1).numpy()
        if labels_np is None:
            labels_np = labels_all.numpy()

        # Compute metrics for this pass
        # 1. Macro AUROC & AUPR (OVR)
        macro_auroc = float(roc_auc_score(labels_np, probs_p, multi_class="ovr", average="macro"))
        
        # Per-class metrics
        class_metrics = {}
        for c, c_name in [(0, "antagonism"), (1, "additive"), (2, "synergy")]:
            y_bin = (labels_np == c).astype(int)
            scores = probs_p[:, c]
            prev = float(np.mean(y_bin))
            try:
                auc = float(roc_auc_score(y_bin, scores))
            except ValueError:
                auc = float("nan")
            try:
                aupr = float(average_precision_score(y_bin, scores))
            except ValueError:
                aupr = float("nan")
            lift = aupr / (prev + 1e-12) if not np.isnan(aupr) else float("nan")
            class_metrics[c_name] = {"auroc": auc, "aupr": aupr, "lift": lift, "prev": prev}

        pass_metrics.append({
            "macro_auroc": macro_auroc,
            "synergy_auroc": class_metrics["synergy"]["auroc"],
            "synergy_aupr": class_metrics["synergy"]["aupr"],
            "synergy_lift": class_metrics["synergy"]["lift"],
            "additive_auroc": class_metrics["additive"]["auroc"],
            "additive_aupr": class_metrics["additive"]["aupr"],
            "antagonism_auroc": class_metrics["antagonism"]["auroc"],
            "antagonism_aupr": class_metrics["antagonism"]["aupr"],
            "prevalence": {c: class_metrics[c]["prev"] for c in ["synergy", "additive", "antagonism"]},
        })

    # Summary over passes
    agg = {}
    keys = ["macro_auroc", "synergy_auroc", "synergy_aupr", "synergy_lift",
            "additive_auroc", "additive_aupr", "antagonism_auroc", "antagonism_aupr"]
    for k in keys:
        vals = [m[k] for m in pass_metrics]
        agg[f"{k}_mean"] = float(np.mean(vals))
        agg[f"{k}_sd"] = float(np.std(vals))

    agg["prevalence"] = pass_metrics[0]["prevalence"]
    return agg


def main():
    heterodata, drug_map, cell_map, labels_df = load_shared_resources()

    metadata = heterodata.metadata()
    num_nodes_dict = {nt: heterodata[nt].num_nodes for nt in heterodata.node_types}
    n_fallback = int((~heterodata["drug"].fp_mask).sum().item())
    device_obj = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    all_results = {}
    wall_clocks = {}

    for split_type in SPLIT_TYPES:
        print(f"\n{'#' * 80}")
        print(f"  PROCESSING SPLIT: {split_type.upper()}")
        print(f"{'#' * 80}")

        train_loader, val_loader, test_loader, class_weights, test_idx = build_split_loaders(
            heterodata, drug_map, cell_map, labels_df, split_type
        )

        all_results[split_type] = {}
        wall_clocks[split_type] = {}

        # Train seeds
        for s in SEEDS:
            ckpt_path, elapsed = train_single_model(
                split_type, s, heterodata, train_loader, val_loader, class_weights
            )
            wall_clocks[split_type][s] = elapsed

            # Evaluate (5-pass deterministic)
            print(f"  Evaluating {split_type} Seed {s} (5-pass deterministic)...")
            model = SynergyModule.load_from_checkpoint(
                ckpt_path,
                metadata=metadata,
                num_nodes_dict=num_nodes_dict,
                num_fallback_drugs=n_fallback,
                num_cell_lines=heterodata.num_cell_lines,
                num_layers=2,
                class_weights=class_weights,
            )
            m = evaluate_model_5pass(model, test_loader, device="cuda" if torch.cuda.is_available() else "cpu")
            all_results[split_type][s] = m

            print(f"    Macro AUROC: {m['macro_auroc_mean']:.4f} (±{m['macro_auroc_sd']:.4f}) | "
                  f"Syn AUROC: {m['synergy_auroc_mean']:.4f} (±{m['synergy_auroc_sd']:.4f}) | "
                  f"Syn AUPR: {m['synergy_aupr_mean']:.4f} (±{m['synergy_aupr_sd']:.4f}) | "
                  f"Syn Lift: {m['synergy_lift_mean']:.2f}")

    # Print Full Detailed Tables
    print("\n" + "=" * 100)
    print("  FINAL GENERALIZATION BENCHMARK SUMMARY")
    print("=" * 100)

    # 1. Detailed breakdown per split
    for split_type in SPLIT_TYPES:
        print(f"\n--- Split: {split_type} ---")
        print(f"{'Seed':<8} | {'Macro AUROC':<18} | {'Syn AUROC':<18} | {'Syn AUPR':<18} | {'Ant AUROC':<18} | {'Add AUROC':<18}")
        print("-" * 100)
        for s in SEEDS:
            m = all_results[split_type][s]
            print(f"Seed {s:<3} | {m['macro_auroc_mean']:.4f} (±{m['macro_auroc_sd']:.4f}) | "
                  f"{m['synergy_auroc_mean']:.4f} (±{m['synergy_auroc_sd']:.4f}) | "
                  f"{m['synergy_aupr_mean']:.4f} (±{m['synergy_aupr_sd']:.4f}) | "
                  f"{m['antagonism_auroc_mean']:.4f} (±{m['antagonism_auroc_sd']:.4f}) | "
                  f"{m['additive_auroc_mean']:.4f} (±{m['additive_auroc_sd']:.4f})")
        
        # Mean across seeds
        macro_vals = [all_results[split_type][s]["macro_auroc_mean"] for s in SEEDS]
        syn_vals = [all_results[split_type][s]["synergy_auroc_mean"] for s in SEEDS]
        syn_p_vals = [all_results[split_type][s]["synergy_aupr_mean"] for s in SEEDS]
        ant_vals = [all_results[split_type][s]["antagonism_auroc_mean"] for s in SEEDS]
        add_vals = [all_results[split_type][s]["additive_auroc_mean"] for s in SEEDS]
        print("-" * 100)
        print(f"{'Mean':<8} | {np.mean(macro_vals):.4f} (±{np.std(macro_vals):.4f}) | "
              f"{np.mean(syn_vals):.4f} (±{np.std(syn_vals):.4f}) | "
              f"{np.mean(syn_p_vals):.4f} (±{np.std(syn_p_vals):.4f}) | "
              f"{np.mean(ant_vals):.4f} (±{np.std(ant_vals):.4f}) | "
              f"{np.mean(add_vals):.4f} (±{np.std(add_vals):.4f})")

    # 2. Combined Generalization Summary Table (Table 3 style)
    print("\n" + "=" * 110)
    print("  COMBINED GENERALIZATION TABLE (MD-Syn Table 3 Style)")
    print("=" * 110)
    print(f"{'Generalization Axis':<24} | {'Held-Out Entity':<20} | {'Test Pairs':<11} | {'Macro AUROC':<18} | {'Synergy AUROC':<18} | {'Synergy AUPR':<18}")
    print("-" * 110)

    # Existing cold-drug numbers from prior report
    print(f"{'Cold-Drug (Mean A)':<24} | {'184 Drugs (Inductive)':<20} | {'37,778':<11} | "
          f"{'0.6472 (±0.0124)':<18} | {'0.5673 (±0.0136)':<18} | {'0.2274 (±0.0081)':<18}")

    entity_map = {
        "warm_random": "None (Random Pairs)",
        "leave_cell_line": "16 Cell Lines",
        "leave_tissue": "Breast & Ovary (19 CLs)",
    }
    pairs_map = {
        "warm_random": "37,778",
        "leave_cell_line": "35,936",
        "leave_tissue": "33,931",
    }

    for split_type in SPLIT_TYPES:
        macro_vals = [all_results[split_type][s]["macro_auroc_mean"] for s in SEEDS]
        syn_vals = [all_results[split_type][s]["synergy_auroc_mean"] for s in SEEDS]
        syn_p_vals = [all_results[split_type][s]["synergy_aupr_mean"] for s in SEEDS]
        
        name = split_type.replace("_", " ").title()
        print(f"{name:<24} | {entity_map[split_type]:<20} | {pairs_map[split_type]:<11} | "
              f"{np.mean(macro_vals):.4f} (±{np.std(macro_vals):.4f}) | "
              f"{np.mean(syn_vals):.4f} (±{np.std(syn_vals):.4f}) | "
              f"{np.mean(syn_p_vals):.4f} (±{np.std(syn_p_vals):.4f})")
    print("=" * 110)


if __name__ == "__main__":
    main()
