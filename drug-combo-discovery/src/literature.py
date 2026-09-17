"""
literature.py -- PubMed Literature Retrieval via NCBI E-utilities
=================================================================

Retrieves supporting PubMed literature for a drug-combination explanation.
Uses the NCBI ESearch + ESummary endpoints.

Rate limits:
  - Without API key: 3 requests/sec -> 0.34s delay between requests
  - With API key:    10 requests/sec -> 0.11s delay between requests

API key lookup order:
  1. NCBI_API_KEY environment variable
  2. Falls back to unauthenticated (with appropriate delay)
"""

from __future__ import annotations

import os
import time
from typing import Dict, List, Optional

import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ESEARCH_URL  = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
PUBMED_BASE  = "https://pubmed.ncbi.nlm.nih.gov"

# Look for an NCBI API key in the environment (set NCBI_API_KEY to use it)
_NCBI_API_KEY: Optional[str] = os.environ.get("NCBI_API_KEY", None)

# Delay between requests (seconds) -- 3 req/sec without key, 10/sec with key
_REQUEST_DELAY: float = 0.11 if _NCBI_API_KEY else 0.34

# Shared session for connection pooling
_SESSION = requests.Session()
_SESSION.headers.update(
    {"User-Agent": "SynThera/1.0 (drug-combo-discovery; contact=synthera-demo)"}
)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ncbi_params(extra: dict) -> dict:
    """Build base NCBI params dict, optionally with API key."""
    params = {"retmode": "json", **extra}
    if _NCBI_API_KEY:
        params["api_key"] = _NCBI_API_KEY
    return params


def _esearch(query: str, db: str = "pubmed", retmax: int = 5) -> List[str]:
    """
    Call ESearch and return a list of PMIDs (strings) for the top retmax hits.
    Returns [] on any error.
    """
    params = _ncbi_params({
        "db":     db,
        "term":   query,
        "retmax": retmax,
        "sort":   "relevance",
    })
    try:
        r = _SESSION.get(ESEARCH_URL, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        return data.get("esearchresult", {}).get("idlist", [])
    except Exception as exc:
        print(f"  [literature] ESearch failed for query '{query}': {exc}")
        return []


def _esummary(pmids: List[str], db: str = "pubmed") -> Dict[str, dict]:
    """
    Call ESummary for a list of PMIDs.
    Returns a dict keyed by PMID string -> summary dict.
    Returns {} on any error.
    """
    if not pmids:
        return {}
    params = _ncbi_params({
        "db": db,
        "id": ",".join(pmids),
    })
    try:
        time.sleep(_REQUEST_DELAY)  # rate-limit gap between ESearch and ESummary
        r = _SESSION.get(ESUMMARY_URL, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        return data.get("result", {})
    except Exception as exc:
        print(f"  [literature] ESummary failed for PMIDs {pmids}: {exc}")
        return {}


def _parse_summary(pmid: str, summary: dict) -> Optional[Dict[str, str]]:
    """
    Extract {title, year, first_author, pmid, url} from an ESummary result entry.
    Returns None if the entry is malformed.
    """
    if not summary or pmid not in summary:
        return None
    entry = summary[pmid]
    title = entry.get("title", "").strip().rstrip(".")
    if not title:
        return None
    # Publication year -- prefer "pubdate", fall back to "epubdate"
    pub_date = entry.get("pubdate", entry.get("epubdate", ""))
    year = pub_date[:4] if len(pub_date) >= 4 else "?"
    # First author
    authors = entry.get("authors", [])
    first_author = authors[0].get("name", "") if authors else ""
    return {
        "title":        title,
        "year":         year,
        "first_author": first_author,
        "pmid":         pmid,
        "url":          f"{PUBMED_BASE}/{pmid}/",
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_supporting_literature(
    drug_name: str,
    target_or_disease: str,
    max_results: int = 2,
) -> List[Dict[str, str]]:
    """
    Retrieve supporting PubMed literature for a drug + target/disease term.

    Searches PubMed for: "{drug_name} AND {target_or_disease}"
    Returns up to max_results citations as a list of dicts:
      {title, year, first_author, pmid, url}

    Returns [] gracefully on any API failure, empty results, or network error.

    Parameters
    ----------
    drug_name : str
        Generic drug name (e.g. "Temozolomide").
    target_or_disease : str
        Biological target or disease term (e.g. "glioblastoma", "CYP3A5").
    max_results : int
        Maximum number of citations to return (default 2).
    """
    if not drug_name or not target_or_disease:
        return []

    # Quote multi-word terms for PubMed precision
    drug_q   = f'"{drug_name}"' if " " in drug_name else drug_name
    target_q = f'"{target_or_disease}"' if " " in target_or_disease else target_or_disease
    query    = f"{drug_q} AND {target_q}"

    print(f"  [literature] Searching PubMed: {query}")

    # Step 1: ESearch -- get PMIDs (fetch a few extra in case some summaries are empty)
    pmids = _esearch(query, retmax=max(max_results + 2, 5))
    if not pmids:
        print(f"  [literature] No PMIDs found for query: {query}")
        return []

    # Step 2: ESummary -- get metadata (rate-limit delay applied inside)
    summary = _esummary(pmids[:max_results + 2])

    results: List[Dict[str, str]] = []
    for pmid in pmids:
        if len(results) >= max_results:
            break
        parsed = _parse_summary(pmid, summary)
        if parsed:
            results.append(parsed)

    print(f"  [literature] Retrieved {len(results)} citation(s) for '{drug_name} + {target_or_disease}'")
    return results


def get_literature_for_explanation(
    drug_a_name: str,
    drug_b_name: str,
    explanation_text: str,
    top_edges: List[dict],
    all_edges: Optional[List[dict]] = None,
    max_results: int = 2,
) -> List[Dict[str, str]]:
    """
    Convenience wrapper: extracts the key drug + biological term from the
    explanation, then calls get_supporting_literature().

    Term-extraction priority:
    0. Parse explanation_text directly to find the term that DROVE the template
       (this is the most accurate signal — it's exactly what the user sees).
       Strategy: collect all node names from the edge lists, then pick the one
       that appears in explanation_text at the highest importance.
    1. Highest-importance drug_protein edge for drug_a  -> protein target
    2. Highest-importance indication/off-label use for drug_a -> disease
    3. Highest-importance indication/off-label use for drug_b -> disease
    4. Fallback: prominent word from explanation_text itself
    """
    edges      = all_edges if all_edges is not None else top_edges
    drug_a_low = drug_a_name.lower()
    drug_b_low = drug_b_name.lower()
    expl_low   = explanation_text.lower()

    target_edges: List[tuple] = []   # (importance, term)
    indication_a: List[tuple] = []
    indication_b: List[tuple] = []
    # All non-drug node names with their importance, for text-matching pass
    all_node_terms: List[tuple] = []  # (importance, name, is_drug_a_related)

    for e in edges:
        src = e.get("source", "")
        tgt = e.get("target", "")
        rel = e.get("relation", "")
        imp = float(e.get("importance", 0.0))
        is_a_src = src.lower() == drug_a_low
        is_b_src = src.lower() == drug_b_low
        is_a_tgt = tgt.lower() == drug_a_low
        is_b_tgt = tgt.lower() == drug_b_low

        # Track all non-drug node names for explanation-text matching (priority 0)
        for node, is_drug_side in ((src, is_a_src or is_a_tgt), (tgt, is_a_src or is_a_tgt)):
            if node.lower() not in (drug_a_low, drug_b_low) and node:
                all_node_terms.append((imp, node, is_drug_side))

        if rel == "drug_protein":
            if is_a_src:
                target_edges.append((imp, tgt))
            elif is_a_tgt:
                target_edges.append((imp, src))
        elif rel in ("indication", "off-label use"):
            if is_a_src:
                indication_a.append((imp, tgt))
            elif is_a_tgt:
                indication_a.append((imp, src))
            elif is_b_src:
                indication_b.append((imp, tgt))
            elif is_b_tgt:
                indication_b.append((imp, src))

    for lst in (target_edges, indication_a, indication_b):
        lst.sort(key=lambda x: x[0], reverse=True)

    # Priority 0: find the HIGHEST-importance node whose name appears literally
    # in the explanation_text — this is the term that drove the template.
    # Sort by importance DESC, then pick first match in explanation.
    all_node_terms.sort(key=lambda x: x[0], reverse=True)
    text_matched_term: Optional[str] = None
    text_matched_is_a: bool = True
    for _imp, name, is_a_related in all_node_terms:
        if name.lower() in expl_low:
            text_matched_term = name
            text_matched_is_a = is_a_related
            break

    # Select primary_drug and term
    primary_drug = drug_a_name
    if text_matched_term:
        # Use the drug whose indication/target drove the explanation text
        primary_drug = drug_a_name if text_matched_is_a else drug_b_name
        term = text_matched_term
    elif target_edges:
        term = target_edges[0][1]
    elif indication_a:
        term = indication_a[0][1]
    elif indication_b:
        term = indication_b[0][1]
        primary_drug = drug_b_name
    else:
        words = [w.strip(".,;:") for w in explanation_text.split() if len(w.strip(".,;:")) > 5]
        term  = words[3] if len(words) > 3 else (words[0] if words else "cancer")

    return get_supporting_literature(primary_drug, term, max_results=max_results)
