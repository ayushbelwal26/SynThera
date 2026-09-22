import os
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED = os.path.join(ROOT, "data", "processed")

labels = pd.read_csv(os.path.join(PROCESSED, "labeled_pairs.csv"))
train_idx = pd.read_csv(os.path.join(PROCESSED, "split_train.csv"))["row_index"].values
val_idx = pd.read_csv(os.path.join(PROCESSED, "split_val.csv"))["row_index"].values
test_idx = pd.read_csv(os.path.join(PROCESSED, "split_test.csv"))["row_index"].values

train_df = labels.iloc[train_idx].reset_index(drop=True)
val_df = labels.iloc[val_idx].reset_index(drop=True)
test_df = labels.iloc[test_idx].reset_index(drop=True)

train_drugs = set(train_df["drug_a_kg_id"]) | set(train_df["drug_b_kg_id"])
val_drugs = set(val_df["drug_a_kg_id"]) | set(val_df["drug_b_kg_id"])
test_drugs = set(test_df["drug_a_kg_id"]) | set(test_df["drug_b_kg_id"])

val_a_in_train = val_df["drug_a_kg_id"].isin(train_drugs).values
val_b_in_train = val_df["drug_b_kg_id"].isin(train_drugs).values

mask_bilat_val = (~val_a_in_train) & (~val_b_in_train)
mask_unilat_val = (val_a_in_train & ~val_b_in_train) | (~val_a_in_train & val_b_in_train)

bilat_val_df = val_df[mask_bilat_val].reset_index(drop=True)
unilat_val_df = val_df[mask_unilat_val].reset_index(drop=True)

bilat_val_drugs = set(bilat_val_df["drug_a_kg_id"]) | set(bilat_val_df["drug_b_kg_id"])
unilat_val_drugs = set(unilat_val_df["drug_a_kg_id"]) | set(unilat_val_df["drug_b_kg_id"])

print(f"Unique drugs in bilateral val: {len(bilat_val_drugs)}")
print(f"Unique drugs in unilateral val: {len(unilat_val_drugs)}")
print(f"Total unique drugs in val: {len(val_drugs)}")
print(f"Overlap |Val drugs & Test drugs|: {len(val_drugs & test_drugs)}")
print(f"Overlap |Val drugs & Train drugs|: {len(val_drugs & train_drugs)}")
print(f"Overlap |Bilat Val drugs & Train drugs|: {len(bilat_val_drugs & train_drugs)}")
print(f"Overlap |Bilat Val drugs & Test drugs|: {len(bilat_val_drugs & test_drugs)}")
