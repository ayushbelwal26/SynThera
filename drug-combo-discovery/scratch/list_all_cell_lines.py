import torch
import pandas as pd

data = torch.load("data/processed/heterodata.pt", map_location="cpu", weights_only=False)
cls = sorted(list(data.cell_line_map.keys()))
print(f"Total cell lines: {len(cls)}")
print(cls)
