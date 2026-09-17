"""
sanity_check_batch.py - One-batch forward-pass sanity check (v2: cell-line context)
"""
import os, sys, torch
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(__file__))
from torch_geometric.loader import LinkNeighborLoader
from model import SynergyGNN, HIDDEN_DIM, NUM_HEADS, FP_DIM

ROOT      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED = os.path.join(ROOT, "data", "processed")

print("=" * 64)
print("  Sanity Check v2 - Cell-Line Context + Softened Weights")
print("=" * 64)

# 1. Load heterodata
data = torch.load(os.path.join(PROCESSED, "heterodata.pt"), weights_only=False)
print(f"\n[1] heterodata.pt loaded ({data['drug'].num_nodes} drug nodes)")
print(f"    label_train_cell shape : {tuple(data.label_train_cell.shape)}")
print(f"    num_cell_lines         : {data.num_cell_lines}")
assert data.label_train_cell.shape[0] == data.label_train_y.shape[0], \
    "FAIL: cell tensor length != y tensor length"
assert data.label_train_cell.max().item() < data.num_cell_lines, \
    "FAIL: cell ID out of range"
print("    PASS: cell tensors present and in-range")

# 2. Build model
metadata       = data.metadata()
num_nodes_dict = {nt: data[nt].num_nodes for nt in data.node_types}
num_fallback   = int((data["drug"].fallback_lookup >= 0).sum().item())
num_cell_lines = data.num_cell_lines

model = SynergyGNN(
    metadata=metadata, num_nodes_dict=num_nodes_dict,
    num_fallback_drugs=num_fallback, num_cell_lines=num_cell_lines
)
model.eval()
n_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
print(f"\n[2] Model instantiated:")
print(f"    Trainable params     : {n_params:,}")
print(f"    cell_line_emb        : {tuple(model.cell_line_emb.weight.shape)}")
print(f"    cell_line_proj       : {tuple(model.cell_line_proj.weight.shape)}")
print(f"    drug_fp_proj (Linear): in={model.drug_fp_proj.in_features} -> out={model.drug_fp_proj.out_features}")
assert model.drug_fp_proj.in_features == 768, \
    f"FAIL: drug_fp_proj in_features {model.drug_fp_proj.in_features} != 768 (ChemBERTa)"
print(f"    scorer[0] (Linear)   : in={model.scorer[0].in_features} = 3 x {HIDDEN_DIM}")
assert model.scorer[0].in_features == HIDDEN_DIM * 3, \
    f"FAIL: scorer input dim {model.scorer[0].in_features} != {HIDDEN_DIM*3}"
print("    PASS: scorer input is 3 x hidden_dim (drug_a + drug_b + cell)")

# 3. Build loader + pull one batch
NUM_NEIGHBORS = {
    ("drug","drug_drug","drug"):[4,2],
    ("drug","drug_protein","gene/protein"):[12,6],
    ("gene/protein","drug_protein","drug"):[12,6],
    ("drug","indication","disease"):[10,5],
    ("disease","indication","drug"):[10,5],
    ("drug","contraindication","disease"):[10,5],
    ("disease","contraindication","drug"):[10,5],
    ("drug","off-label use","disease"):[6,3],
    ("disease","off-label use","drug"):[6,3],
    ("gene/protein","protein_protein","gene/protein"):[10,5],
    ("disease","disease_protein","gene/protein"):[8,4],
    ("gene/protein","disease_protein","disease"):[8,4],
    ("disease","disease_disease","disease"):[5,3],
    ("gene/protein","pathway_protein","pathway"):[5,3],
    ("pathway","pathway_protein","gene/protein"):[5,3],
}
# Pack [y, cell] as [N, 2]
y_train    = data.label_train_y
cell_train = data.label_train_cell
edge_label = torch.stack([y_train, cell_train], dim=1)   # [N, 2]
edge_label_index = torch.stack([data.label_train_drug_a, data.label_train_drug_b])

loader = LinkNeighborLoader(
    data=data, num_neighbors=NUM_NEIGHBORS,
    edge_label_index=(("drug","synergy_pair","drug"), edge_label_index),
    edge_label=edge_label, batch_size=256, shuffle=False, num_workers=0,
)
batch = next(iter(loader))
pair_store = batch["drug","synergy_pair","drug"]
packed     = pair_store.edge_label           # [B, 2]
print(f"\n[3] Mini-batch sampled:")
print(f"    edge_label shape     : {tuple(packed.shape)}  (col0=class, col1=cell_id)")
assert packed.ndim == 2 and packed.shape[1] == 2, "FAIL: packed edge_label not [B, 2]"
labels   = packed[:, 0]
cell_ids = packed[:, 1]
print(f"    labels range         : [{labels.min().item()}, {labels.max().item()}]  (0-2)")
print(f"    cell_ids range       : [{cell_ids.min().item()}, {cell_ids.max().item()}] < {num_cell_lines}")
assert cell_ids.max().item() < num_cell_lines, "FAIL: cell ID out of embedding range"
print("    PASS: edge_label correctly packed and sliced")

# 4. Full forward pass
print(f"\n[4] Running full forward pass ...")
with torch.no_grad():
    logits, ret_labels = model(batch)
print(f"    logits shape  : {tuple(logits.shape)}")
print(f"    labels shape  : {tuple(ret_labels.shape)}")
assert logits.shape == (256, 3), f"FAIL: expected (256, 3), got {logits.shape}"
assert ret_labels.shape[0] == 256
print("    PASS: forward pass complete, no shape errors")

# 5. Check softened class weights
import math
y = data.label_train_y
n_total = len(y)
print(f"\n[5] Softened class weights (sqrt of inv-freq):")
for c, name in enumerate(["antagonism","additive","synergy"]):
    n_c   = (y == c).sum().item()
    raw_w = n_total / (3.0 * n_c)
    soft_w = raw_w ** 0.5
    print(f"    {name:<12}: n={n_c:>8,}  raw={raw_w:.4f}  sqrt={soft_w:.4f}")

print("\n" + "=" * 64)
print("  ALL CHECKS PASSED - cell-line context working correctly!")
print("  Run training: .venv\\Scripts\\python src\\train.py")
print("=" * 64)
