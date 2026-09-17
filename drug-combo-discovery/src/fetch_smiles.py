"""
fetch_smiles.py — PubChem SMILES Retrieval + RDKit Morgan Fingerprint Computation
===================================================================================

PURPOSE
-------
Fetches canonical SMILES for every drug in data/processed/primekg_drugs.csv
via the PubChem PUG REST API and computes 2048-bit Morgan fingerprints (r=2)
using RDKit. Results are used to replace the learnable embedding table in the
GNN with real, deterministic drug-structure features — particularly important
for the cold-drug split where unseen drugs have uninformative random embeddings.

LOOKUP STRATEGY (per drug)
---------------------------
Pass 1 — DrugBank xref:
    GET /compound/xref/RegistryID/{DRUGBANK_ID}/property/CanonicalSMILES/JSON

Pass 2 (fallback) — name search:
    GET /compound/name/{DRUG_NAME_URL_ENCODED}/property/CanonicalSMILES/JSON
    When name search returns multiple CIDs, the first (lowest CID = most curated)
    is used.

RATE LIMITING
-------------
PubChem's free PUG REST endpoint enforces ~5 requests/second per IP.
We use 0.2 s between requests to stay under that limit. On transient
failures (HTTP 503/429/timeout) we apply exponential backoff up to
MAX_RETRIES attempts before marking the drug as failed.

OUTPUTS
-------
data/processed/drug_smiles_fingerprints.csv
    Columns: drugbank_id, name, smiles, lookup_method, cid, fingerprint
    fingerprint: 2048-character binary string ('0'/'1' per bit)

data/processed/smiles_not_found.csv
    Drugs for which both lookups failed.
"""

from __future__ import annotations

import os
import sys
import time
import urllib.parse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED  = os.path.join(ROOT, "data", "processed")

DRUGS_CSV      = os.path.join(PROCESSED, "primekg_drugs.csv")
OUT_SMILES_CSV = os.path.join(PROCESSED, "drug_smiles_fingerprints.csv")
OUT_FAILED_CSV = os.path.join(PROCESSED, "smiles_not_found.csv")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
REQUEST_DELAY    = 0.21   # seconds between requests (≤5 req/s limit)
MAX_RETRIES      = 2      # per-request retry attempts (fail fast on slow drugs)
BACKOFF_BASE     = 2.0   # exponential backoff base (seconds)
MAX_BACKOFF      = 6.0   # cap per-retry sleep
CONNECT_TIMEOUT  = 5     # seconds to establish TCP+TLS connection
READ_TIMEOUT     = 8     # seconds to wait for server to send data
PROGRESS_EVERY   = 50    # flush + print progress every N drugs (was 500)

# PubChem PUG REST base
PUBCHEM_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

# ---------------------------------------------------------------------------
# Shared requests Session with connection pooling
# (created once at import time so TCP connections are reused)
# ---------------------------------------------------------------------------
_SESSION = requests.Session()
_SESSION.headers.update({
    "User-Agent": "SynThera-Drug-Discovery/1.0 (research; contact=github)"
})
# urllib3-level retry only for connection errors, NOT for HTTP status codes
# (we handle HTTP errors ourselves for proper 404 vs 429 distinction)
_adapter = HTTPAdapter(max_retries=Retry(total=0))
_SESSION.mount("https://", _adapter)
_SESSION.mount("http://", _adapter)

# ---------------------------------------------------------------------------
# Lazy RDKit import (only used for FP computation, not for HTTP logic)
# ---------------------------------------------------------------------------
try:
    from rdkit import Chem
    from rdkit.Chem import AllChem
    from rdkit import RDLogger
    RDLogger.DisableLog("rdApp.*")      # suppress RDKit warnings
    RDKIT_OK = True
except ImportError:
    RDKIT_OK = False
    print("[WARNING] RDKit not available — SMILES will be saved but fingerprints "
          "will be empty. Install rdkit to enable fingerprint computation.")


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _get_json(url: str) -> dict | None:
    """
    Fetch a URL and return parsed JSON, or None on 404 / no-results.
    Uses requests with a hard (connect, read) timeout tuple — this
    reliably fires on Windows even during TLS handshake, unlike
    urllib.request which can hang indefinitely on SSL negotiation.
    """
    timeout = (CONNECT_TIMEOUT, READ_TIMEOUT)
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = _SESSION.get(url, timeout=timeout)
            if resp.status_code == 404:
                return None
            if resp.status_code in (429, 503, 504):
                wait = min(BACKOFF_BASE ** attempt, MAX_BACKOFF)
                time.sleep(wait)
                continue
            if resp.status_code != 200:
                return None         # unexpected status → treat as not found
            return resp.json()
        except requests.exceptions.Timeout:
            # Hard timeout exceeded — don't retry indefinitely
            wait = min(BACKOFF_BASE ** attempt, MAX_BACKOFF)
            time.sleep(wait)
            continue
        except requests.exceptions.ConnectionError:
            wait = min(BACKOFF_BASE ** attempt, MAX_BACKOFF)
            time.sleep(wait)
            continue
        except Exception:
            return None
    return None


def _extract_smiles_from_response(data: dict | None) -> tuple[str | None, int | None]:
    """
    Parse a PubChem property JSON response.
    Returns (smiles, cid) or (None, None).

    PubChem's PUG REST sometimes returns the key as 'ConnectivitySMILES'
    or 'IsomericSMILES' even when 'CanonicalSMILES' was requested — try
    all three in order of preference.
    """
    if data is None:
        return None, None
    try:
        props = data["PropertyTable"]["Properties"]
        if not props:
            return None, None
        # Use first result (lowest CID → most canonical entry)
        first = props[0]
        smiles = (
            first.get("CanonicalSMILES")
            or first.get("ConnectivitySMILES")
            or first.get("IsomericSMILES")
        )
        cid = first.get("CID")
        return smiles or None, cid
    except (KeyError, IndexError, TypeError):
        return None, None


# ---------------------------------------------------------------------------
# PubChem lookups
# ---------------------------------------------------------------------------

def lookup_by_xref(drugbank_id: str) -> tuple[str | None, int | None]:
    """Pass 1: DrugBank registry-ID cross-reference."""
    url = (
        f"{PUBCHEM_BASE}/compound/xref/RegistryID"
        f"/{urllib.parse.quote(drugbank_id, safe='')}"
        f"/property/CanonicalSMILES/JSON"
    )
    time.sleep(REQUEST_DELAY)
    data = _get_json(url)
    return _extract_smiles_from_response(data)


def lookup_by_name(name: str) -> tuple[str | None, int | None]:
    """Pass 2: name-based lookup (URL-encoded)."""
    encoded = urllib.parse.quote(name.strip(), safe="")
    url = (
        f"{PUBCHEM_BASE}/compound/name/{encoded}"
        f"/property/CanonicalSMILES/JSON"
    )
    time.sleep(REQUEST_DELAY)
    data = _get_json(url)
    return _extract_smiles_from_response(data)


# ---------------------------------------------------------------------------
# Morgan fingerprint
# ---------------------------------------------------------------------------

def smiles_to_morgan_fp(smiles: str, radius: int = 2, n_bits: int = 2048) -> str | None:
    """
    Compute a 2048-bit Morgan fingerprint from a SMILES string using RDKit.
    Returns a 2048-character binary string ('0'/'1') or None if parsing fails.
    """
    if not RDKIT_OK or not smiles:
        return None
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None
        fp  = AllChem.GetMorganFingerprintAsBitVect(mol, radius, nBits=n_bits)
        return fp.ToBitString()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Main fetch loop
# ---------------------------------------------------------------------------

COLS = ["drugbank_id", "name", "smiles", "lookup_method", "cid", "fingerprint"]


def _flush_records(
    records: list[dict],
    path: str,
    write_header: bool,
) -> None:
    """
    Append a batch of records to a CSV file.
    write_header=True only on the very first flush (when file is new).
    """
    if not records:
        return
    mode = "w" if write_header else "a"
    df = pd.DataFrame(records, columns=COLS)
    df.to_csv(path, mode=mode, header=write_header, index=False)


def fetch_all(
    drugs_df: pd.DataFrame,
    already_done_count: int,
    first_flush_found: bool,
    first_flush_fail: bool,
) -> None:
    """
    Iterate over all remaining drugs (already-done ones pre-filtered by caller),
    run two-pass PubChem lookup, compute fingerprints, and flush to CSV every
    PROGRESS_EVERY records so a crash only loses at most that many records.

    Args
    ----
    drugs_df           : DataFrame of drugs still to be fetched
    already_done_count : how many were already in the CSV (for progress display)
    first_flush_found  : whether the found-CSV already has a header row
    first_flush_fail   : whether the failed-CSV already has a header row
    """
    total_all = already_done_count + len(drugs_df)

    pending_found: list[dict] = []
    pending_fail:  list[dict] = []

    n_xref  = 0
    n_name  = 0
    n_fail  = 0
    n_no_fp = 0

    t0 = time.time()

    for i, row in enumerate(drugs_df.itertuples(index=False), start=1):
        db_id = str(row.drugbank_id)
        name  = str(row.drug_name)

        smiles, cid, method = None, None, None

        # ── Pass 1: DrugBank xref ──────────────────────────────────────
        smiles, cid = lookup_by_xref(db_id)
        if smiles:
            method = "xref"
            n_xref += 1
        else:
            # ── Pass 2: name fallback ──────────────────────────────────
            smiles, cid = lookup_by_name(name)
            if smiles:
                method = "name"
                n_name += 1
            else:
                method = "failed"
                n_fail += 1

        # ── Fingerprint ────────────────────────────────────────────────
        fp_str = None
        if smiles:
            fp_str = smiles_to_morgan_fp(smiles)
            if fp_str is None:
                n_no_fp += 1

        record = {
            "drugbank_id":   db_id,
            "name":          name,
            "smiles":        smiles or "",
            "lookup_method": method,
            "cid":           cid if cid is not None else "",
            "fingerprint":   fp_str or "",
        }

        if method == "failed":
            pending_fail.append(record)
        else:
            pending_found.append(record)

        # ── Flush to disk + progress every PROGRESS_EVERY records ──────
        global_i = already_done_count + i
        if i % PROGRESS_EVERY == 0 or i == len(drugs_df):
            # Flush found records
            _flush_records(pending_found, OUT_SMILES_CSV, write_header=first_flush_found)
            if pending_found:
                first_flush_found = False
            pending_found.clear()

            # Flush failed records
            _flush_records(pending_fail, OUT_FAILED_CSV, write_header=first_flush_fail)
            if pending_fail:
                first_flush_fail = False
            pending_fail.clear()

            elapsed = time.time() - t0
            rate    = i / elapsed if elapsed > 0 else 0
            eta_s   = (len(drugs_df) - i) / rate if rate > 0 else 0
            pct     = 100 * global_i / total_all
            print(
                f"  [{global_i:>5}/{total_all}]  "
                f"xref={n_xref:>5}  name={n_name:>4}  fail={n_fail:>4}  "
                f"no_fp={n_no_fp:>3}  |  "
                f"{pct:.1f}%  "
                f"{elapsed:.0f}s elapsed  "
                f"ETA ~{eta_s/60:.1f}m",
                flush=True,
            )
            sys.stdout.flush()


# ---------------------------------------------------------------------------
# Save outputs
# ---------------------------------------------------------------------------

def report_saved() -> tuple[list[dict], list[dict]]:
    """Read back what was incrementally flushed and report counts."""
    found_records:  list[dict] = []
    fail_records:   list[dict] = []

    if os.path.exists(OUT_SMILES_CSV):
        df = pd.read_csv(OUT_SMILES_CSV, dtype=str).fillna("")
        found_records = df.to_dict("records")
        print(f"\n  {len(found_records):,} SMILES records in {os.path.basename(OUT_SMILES_CSV)}")

    if os.path.exists(OUT_FAILED_CSV):
        df = pd.read_csv(OUT_FAILED_CSV, dtype=str).fillna("")
        fail_records = df.to_dict("records")
        print(f"  {len(fail_records):,} not-found records in {os.path.basename(OUT_FAILED_CSV)}")

    return found_records, fail_records


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def print_summary(
    found: list[dict],
    not_found: list[dict],
    total: int,
    t_start: float,
) -> None:
    n_xref  = sum(1 for r in found if r["lookup_method"] == "xref")
    n_name  = sum(1 for r in found if r["lookup_method"] == "name")
    n_fp    = sum(1 for r in found if r["fingerprint"])
    n_fail  = len(not_found)
    n_found = len(found)
    elapsed = time.time() - t_start

    sep = "=" * 66
    print(f"\n{sep}")
    print("  COVERAGE SUMMARY")
    print(sep)
    print(f"  Total drugs queried       : {total:>6,}")
    print(f"  ── SMILES via xref        : {n_xref:>6,}  ({100*n_xref/total:.1f}%)")
    print(f"  ── SMILES via name (fb)   : {n_name:>6,}  ({100*n_name/total:.1f}%)")
    print(f"  ── Total with SMILES      : {n_found:>6,}  ({100*n_found/total:.1f}%)")
    print(f"  ── With valid Morgan FP   : {n_fp:>6,}  ({100*n_fp/total:.1f}%)")
    print(f"  ── Failed both lookups    : {n_fail:>6,}  ({100*n_fail/total:.1f}%)")
    print(f"\n  Wall-clock time: {elapsed:.0f}s ({elapsed/60:.1f}m)")
    print(sep)

    if n_fp / total >= 0.75:
        print(f"\n  ✓ Coverage is strong ({100*n_fp/total:.1f}%) — ready to replace "
              f"drug embedding tables with Morgan FP features in model.py.")
    elif n_fp / total >= 0.50:
        print(f"\n  ⚠ Partial coverage ({100*n_fp/total:.1f}%). Consider keeping "
              f"the learnable embedding for uncovered drugs and using FP for covered ones.")
    else:
        print(f"\n  ✗ Low coverage ({100*n_fp/total:.1f}%). Most likely cause: "
              f"PubChem does not list these DrugBank IDs as registered cross-references. "
              f"Consider querying DrugBank directly or using the name-only lookup more "
              f"aggressively.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print("=" * 66)
    print("  PubChem SMILES Fetcher + RDKit Morgan Fingerprint Builder")
    print("=" * 66)

    if not RDKIT_OK:
        print("\n  [ERROR] RDKit is required for fingerprint computation.")
        print("  Install with: uv pip install rdkit --python .venv/Scripts/python.exe")
        sys.exit(1)

    if not os.path.exists(DRUGS_CSV):
        print(f"\n  [ERROR] Drug list not found: {DRUGS_CSV}")
        print("  Run src/build_kg.py first to generate primekg_drugs.csv.")
        sys.exit(1)

    os.makedirs(PROCESSED, exist_ok=True)
    drugs_df = pd.read_csv(DRUGS_CSV)
    total = len(drugs_df)
    print(f"\n  Loaded {total:,} drugs from {os.path.basename(DRUGS_CSV)}")
    print(f"  RDKit      : OK")
    print(f"  Rate limit : {REQUEST_DELAY}s delay + {MAX_RETRIES} retries")
    print(f"  Flush      : every {PROGRESS_EVERY} records (crash-safe incremental save)")

    # ── Resume: find already-processed drug IDs from both CSVs ─────
    already_done: set[str] = set()
    first_flush_found = True   # True means file is new → write header
    first_flush_fail  = True

    if os.path.exists(OUT_SMILES_CSV):
        df_ex = pd.read_csv(OUT_SMILES_CSV, dtype=str, usecols=["drugbank_id"]).fillna("")
        already_done.update(df_ex["drugbank_id"].tolist())
        first_flush_found = False   # file exists → append without header
        print(f"  Resume: {len(already_done):,} drugs already in "
              f"{os.path.basename(OUT_SMILES_CSV)}")

    if os.path.exists(OUT_FAILED_CSV):
        df_ex2 = pd.read_csv(OUT_FAILED_CSV, dtype=str, usecols=["drugbank_id"]).fillna("")
        new_fails = set(df_ex2["drugbank_id"].tolist()) - already_done
        already_done.update(new_fails)
        if new_fails:
            first_flush_fail = False
            print(f"  Resume: +{len(new_fails):,} failures already in "
                  f"{os.path.basename(OUT_FAILED_CSV)}")

    drugs_todo = drugs_df[
        ~drugs_df["drugbank_id"].astype(str).isin(already_done)
    ].copy().reset_index(drop=True)

    if len(drugs_todo) == 0:
        print("\n  All drugs already fetched!")
        found, failed = report_saved()
        print_summary(found, failed, total, time.time())
        return

    print(f"  Remaining  : {len(drugs_todo):,} / {total:,} drugs to fetch")
    print(f"\n  Starting fetch — flushing to disk every {PROGRESS_EVERY} drugs...\n")

    t_start = time.time()
    fetch_all(
        drugs_todo,
        already_done_count = len(already_done),
        first_flush_found  = first_flush_found,
        first_flush_fail   = first_flush_fail,
    )

    # Final summary from disk
    found, failed = report_saved()
    print_summary(found, failed, total, t_start)


if __name__ == "__main__":
    main()

