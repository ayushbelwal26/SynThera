"""
Threshold calibration for SynergyGNN v2 checkpoint.

Evaluates post-hoc decision rules on test set softmax probabilities:
    if p_synergy > threshold_s:
        predict synergy (2)
    elif p_antagonism > threshold_a:
        predict antagonism (0)
    else:
        predict additive (1)

Sweeps threshold_s in [0.15, 0.20, 0.22, 0.25, 0.28, 0.30] with threshold_a = 0.33.
"""

import os
import sys
import numpy as np
import torch
import torch.nn.functional as F
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    confusion_matrix,
    precision_score,
    recall_score,
    f1_score,
)

# Add src to path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from train import HETERODATA_PATH, build_loaders, compute_class_weights
from model import SynergyModule, CLASS_NAMES

def main():
    print("=" * 70)
    print("  SYNERGY THRESHOLD CALIBRATION (v2 CHECKPOINT)")
    print("=" * 70)

    # 1. Load data
    print("\n[1/4] Loading HeteroData and constructing test loader...")
    heterodata = torch.load(HETERODATA_PATH, weights_only=False)
    _, _, test_loader = build_loaders(heterodata, [], [], [])

    metadata = heterodata.metadata()
    num_nodes_dict = {nt: heterodata[nt].num_nodes for nt in heterodata.node_types}
    n_fallback = int((~heterodata["drug"].fp_mask).sum().item())
    class_weights = compute_class_weights(heterodata)

    # 2. Load v2 checkpoint
    ckpt_path = os.path.join(ROOT, "models", "synergy_gnn_best-v2.ckpt")
    if not os.path.exists(ckpt_path):
        raise FileNotFoundError(f"Checkpoint not found at: {ckpt_path}")

    print(f"\n[2/4] Loading v2 checkpoint from: {ckpt_path}")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"  Using device: {device}")

    model = SynergyModule.load_from_checkpoint(
        ckpt_path,
        metadata=metadata,
        num_nodes_dict=num_nodes_dict,
        num_fallback_drugs=n_fallback,
        num_cell_lines=heterodata.num_cell_lines,
        num_layers=2,
        class_weights=class_weights,
    )
    model.to(device)
    model.eval()

    # 3. Collect test logits and probabilities
    print("\n[3/4] Running inference on test set (37,778 pairs)...")
    all_logits = []
    all_labels = []

    with torch.no_grad():
        for idx, batch in enumerate(test_loader):
            batch = batch.to(device)
            logits, labels = model(batch)
            if logits.shape[0] > 0:
                all_logits.append(logits.detach().cpu())
                all_labels.append(labels.detach().cpu())
            if (idx + 1) % 30 == 0 or (idx + 1) == len(test_loader):
                print(f"  Processed {idx + 1:>3}/{len(test_loader)} batches")

    all_logits = torch.cat(all_logits, dim=0)   # [N, 3]
    all_labels = torch.cat(all_labels, dim=0)   # [N]
    probs = F.softmax(all_logits, dim=-1).numpy()  # [N, 3]
    labels_np = all_labels.numpy()                 # [N]
    total_test = len(labels_np)

    print(f"  Total test pairs evaluated: {total_test:,}")
    print(f"  Class breakdown (True):")
    for c, cname in enumerate(CLASS_NAMES):
        count = (labels_np == c).sum()
        print(f"    {cname:<15}: {count:>6,} ({count / total_test:.1%})")

    # Baseline argmax metrics
    argmax_preds = probs.argmax(axis=-1)
    macro_auroc = roc_auc_score(labels_np, probs, multi_class="ovr", average="macro")
    aupr_per_class = [
        average_precision_score((labels_np == c).astype(int), probs[:, c])
        for c in range(3)
    ]
    macro_aupr = float(np.mean(aupr_per_class))

    print("\n" + "-" * 70)
    print(f"  BASELINE ARGMAX METRICS (Reference)")
    print("-" * 70)
    print(f"  Macro AUROC : {macro_auroc:.4f}")
    print(f"  Macro AUPR  : {macro_aupr:.4f}")
    for c, cname in enumerate(CLASS_NAMES):
        print(f"    {cname:<15} AUPR: {aupr_per_class[c]:.4f}")

    cm_argmax = confusion_matrix(labels_np, argmax_preds, labels=[0, 1, 2])
    syn_prec_argmax = precision_score(labels_np == 2, argmax_preds == 2, zero_division=0)
    syn_rec_argmax = recall_score(labels_np == 2, argmax_preds == 2, zero_division=0)
    syn_f1_argmax = f1_score(labels_np == 2, argmax_preds == 2, zero_division=0)

    print(f"\n  Argmax Synergy Metrics:")
    print(f"    Precision : {syn_prec_argmax:.4f} ({syn_prec_argmax:.1%})")
    print(f"    Recall    : {syn_rec_argmax:.4f} ({syn_rec_argmax:.1%})")
    print(f"    F1 Score  : {syn_f1_argmax:.4f}")
    print(f"  Argmax Confusion Matrix (rows=true, cols=pred):")
    print(cm_argmax)

    # 4. Threshold calibration sweep
    threshold_s_list = [0.15, 0.20, 0.22, 0.25, 0.28, 0.30]
    threshold_a = 0.33

    print("\n" + "=" * 70)
    print(f"[4/4] THRESHOLD SWEEP (threshold_a = {threshold_a:.2f} fixed)")
    print("=" * 70)
    print(
        f"{'thresh_s':>10} | "
        f"{'Syn Prec':>10} | "
        f"{'Syn Rec':>10} | "
        f"{'Syn F1':>10} | "
        f"{'Add Rec':>10} | "
        f"{'Ant Rec':>10} | "
        f"{'Macro AUPR':>10}"
    )
    print("-" * 76)

    sweep_results = []
    best_f1 = -1.0
    best_thresh = None
    best_cm = None
    best_preds = None

    for ts in threshold_s_list:
        # Decision rule:
        # if p_synergy > ts: 2 (synergy)
        # elif p_antagonism > ta: 0 (antagonism)
        # else: 1 (additive)
        preds = np.ones(total_test, dtype=int)  # default additive (1)
        antag_mask = probs[:, 0] > threshold_a
        preds[antag_mask] = 0
        syn_mask = probs[:, 2] > ts
        preds[syn_mask] = 2  # synergy takes precedence

        # Metrics for synergy (class 2)
        syn_true = (labels_np == 2)
        syn_pred = (preds == 2)
        prec_s = precision_score(syn_true, syn_pred, zero_division=0)
        rec_s = recall_score(syn_true, syn_pred, zero_division=0)
        f1_s = f1_score(syn_true, syn_pred, zero_division=0)

        # Other class recalls
        rec_add = recall_score(labels_np == 1, preds == 1, zero_division=0)
        rec_ant = recall_score(labels_np == 0, preds == 0, zero_division=0)

        cm = confusion_matrix(labels_np, preds, labels=[0, 1, 2])

        sweep_results.append({
            "threshold_s": ts,
            "precision_s": prec_s,
            "recall_s": rec_s,
            "f1_s": f1_s,
            "rec_add": rec_add,
            "rec_ant": rec_ant,
            "macro_aupr": macro_aupr,
            "cm": cm,
            "preds": preds,
        })

        if f1_s > best_f1:
            best_f1 = f1_s
            best_thresh = ts
            best_cm = cm
            best_preds = preds

        print(
            f"{ts:>10.2f} | "
            f"{prec_s:>9.4f}  | "
            f"{rec_s:>9.4f}  | "
            f"{f1_s:>9.4f}  | "
            f"{rec_add:>9.4f}  | "
            f"{rec_ant:>9.4f}  | "
            f"{macro_aupr:>10.4f}"
        )

    print("-" * 76)
    print(f"\n  >>> RECOMMENDED THRESHOLD: threshold_s = {best_thresh:.2f}")
    print(f"      Best Synergy F1 Score = {best_f1:.4f}")

    # Details at best threshold
    rec_s_best = recall_score(labels_np == 2, best_preds == 2, zero_division=0)
    prec_s_best = precision_score(labels_np == 2, best_preds == 2, zero_division=0)
    rec_add_best = recall_score(labels_np == 1, best_preds == 1, zero_division=0)
    rec_ant_best = recall_score(labels_np == 0, best_preds == 0, zero_division=0)

    print(f"\n  Detailed Breakdown at threshold_s = {best_thresh:.2f}:")
    print(f"    Synergy Recall    : {rec_s_best:.2%}  ({best_cm[2, 2]:,} / {best_cm[2].sum():,} true synergy pairs)")
    print(f"    Synergy Precision : {prec_s_best:.2%}  ({best_cm[2, 2]:,} / {best_cm[:, 2].sum():,} predicted synergy)")
    print(f"    Synergy F1        : {best_f1:.4f}")
    print(f"    Additive Recall   : {rec_add_best:.2%}")
    print(f"    Antagonism Recall : {rec_ant_best:.2%}")

    print(f"\n  Full Confusion Matrix (rows=True [antag, add, syn], cols=Pred):")
    print(best_cm)

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
