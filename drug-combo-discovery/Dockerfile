# =============================================================================
# SynThera FastAPI Backend Dockerfile
# Optimized for local execution and Hugging Face Spaces (Docker SDK)
# =============================================================================

FROM python:3.11-slim

# Prevent Python from writing .pyc files and force unbuffered output for logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies required by PyTorch, RDKit, and scientific libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libgomp1 \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

# Set up non-root user with UID 1000 for Hugging Face Spaces compatibility
RUN useradd -m -u 1000 user

# Set working directory
WORKDIR /app

# Pre-create directory structure for application, models, and data
RUN mkdir -p /app/app /app/src /app/models /app/data/processed

# Install Python dependencies first to leverage Docker layer caching
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir "torch==2.6.0+cpu" --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r /app/requirements.txt && \
    pip install --no-cache-dir pyg_lib -f https://data.pyg.org/whl/torch-2.6.0+cpu.html

# Copy runtime Python application code
COPY --chown=user:user app/main.py /app/app/main.py
COPY --chown=user:user src/predict.py \
                       src/model.py \
                       src/explain.py \
                       src/literature.py \
                       src/search.py \
                       src/cell_line_mapping.py \
                       src/why_not.py \
                       /app/src/

# Copy audited runtime models and processed data assets
COPY --chown=user:user models/synergy_gnn_final.ckpt /app/models/synergy_gnn_final.ckpt
COPY --chown=user:user data/processed/heterodata.pt /app/data/processed/heterodata.pt
COPY --chown=user:user data/processed/primekg_nodes.csv /app/data/processed/primekg_nodes.csv
COPY --chown=user:user data/processed/labeled_pairs.csv /app/data/processed/labeled_pairs.csv
COPY --chown=user:user data/processed/cell_line_metadata.csv /app/data/processed/cell_line_metadata.csv

# Ensure permissions across the application tree
RUN chown -R user:user /app

# Switch to non-root user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# Expose port (Hugging Face Spaces default is 7860)
EXPOSE 7860

# Start FastAPI application via Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
