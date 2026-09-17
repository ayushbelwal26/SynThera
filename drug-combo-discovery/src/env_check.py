import sys
import importlib

# Ensure UTF-8 output encoding on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

PACKAGES = [
    ("torch", "torch"),
    ("torch-geometric", "torch_geometric"),
    ("rdkit", "rdkit"),
    ("pandas", "pandas"),
    ("numpy", "numpy"),
    ("scikit-learn", "sklearn"),
    ("pytorch-lightning", "pytorch_lightning"),
    ("fastapi", "fastapi"),
    ("uvicorn", "uvicorn"),
    ("streamlit", "streamlit"),
    ("networkx", "networkx"),
    ("pyvis", "pyvis"),
    ("matplotlib", "matplotlib"),
    ("tqdm", "tqdm"),
    ("requests", "requests"),
]

def main():
    print("=" * 55)
    print("       ENVIRONMENT & HARDWARE VERIFICATION")
    print("=" * 55)
    print(f"Python Version: {sys.version.split()[0]}")
    
    print("\n[Package Installation Status]")
    for pkg_label, module_name in PACKAGES:
        try:
            mod = importlib.import_module(module_name)
            ver = getattr(mod, "__version__", "unknown")
            print(f"  [INSTALLED] {pkg_label} ({module_name}): {ver}")
        except Exception:
            print(f"  [MISSING]   {pkg_label} ({module_name}): Not yet installed")

    print("\n[PyTorch CUDA & GPU Hardware Verification]")
    try:
        import torch
        print(f"  PyTorch Version      : {torch.__version__}")
        cuda_avail = torch.cuda.is_available()
        print(f"  CUDA Available       : {cuda_avail}")
        if cuda_avail:
            device_idx = 0
            props = torch.cuda.get_device_properties(device_idx)
            gpu_name = torch.cuda.get_device_name(0)
            print(f"  Detected GPU (get_device_name(0)): {gpu_name}")
            print(f"  Device Count         : {torch.cuda.device_count()}")
            print(f"  CUDA Version (Torch) : {torch.version.cuda}")
            print(f"  cuDNN Available      : {torch.backends.cudnn.is_available()}")
            print(f"  cuDNN Version        : {torch.backends.cudnn.version()}")
            print(f"  Compute Capability   : {props.major}.{props.minor}")
            print(f"  Total GPU Memory     : {props.total_memory / (1024**2):.1f} MB ({props.total_memory / (1024**3):.2f} GB)")

            # Run actual tensor computation on GPU
            print("\n  [Testing GPU Tensor Computation...]")
            x = torch.randn(1000, 1000, device="cuda")
            y = torch.randn(1000, 1000, device="cuda")
            z = torch.matmul(x, y)
            torch.cuda.synchronize()
            print(f"  [SUCCESS] Matrix multiplication executed on {z.device}!")
            print(f"  Allocated Memory     : {torch.cuda.memory_allocated(device_idx) / (1024**2):.2f} MB")
            print(f"  Reserved Memory      : {torch.cuda.memory_reserved(device_idx) / (1024**2):.2f} MB")
            print("\n>>> PyTorch with CUDA is completely installed and operational! <<<")
        else:
            print("  CUDA is NOT available to PyTorch.")
    except Exception as e:
        print(f"  Error checking PyTorch / CUDA: {e}")
    print("=" * 55)

if __name__ == "__main__":
    main()
