"""
literature.py -- Retrieve-Then-Cite PubMed RAG via NCBI E-utilities
==================================================================

Performs real PubMed literature retrieval for drug combination explanations:
1. Multi-tier query builder: Combines drug names, disease context, and load-bearing
   mechanism terms (genes, proteins, pathways) extracted from GNN explanation subgraphs.
2. NCBI ESearch + EFetch: Retrieves real Medline records with abstracts.
3. RAG Abstract Ranking & Extraction: Ranks returned papers by combination presence,
   mechanism overlap, and extracts authentic 1-2 sentence snippets from the real abstract.
4. Caching: Caches results by (drug_a, drug_b, disease, mechanism_terms) with TTL.
5. Strict Truthfulness: Never invents PMIDs, titles, or snippets. Returns citations=[]
   with clear reasons on zero hits or API failures.

Rate limits:
  - Without API key: ~3 requests/sec -> 0.34s delay between requests
  - With API key:    ~10 requests/sec -> 0.11s delay between requests
"""

from __future__ import annotations

import os
import re
import time
import logging
from typing import Dict, List, Optional, Tuple, Any
import xml.etree.ElementTree as ET

import requests

logger = logging.getLogger("literature")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
PUBMED_BASE = "https://pubmed.ncbi.nlm.nih.gov"

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
# In-Memory Cache with TTL
# ---------------------------------------------------------------------------

# Cache entry format: (timestamp, data_dict, is_success)
_LITERATURE_CACHE: Dict[Tuple[str, str, str, str], Tuple[float, Dict[str, Any], bool]] = {}
_SUCCESS_TTL = 86400.0   # 24 hours for successful searches
_FAILURE_TTL = 60.0      # 60 seconds for failures/empty to avoid stale errors forever


def _get_cached_literature(cache_key: Tuple[str, str, str, str]) -> Optional[Dict[str, Any]]:
    now = time.time()
    if cache_key in _LITERATURE_CACHE:
        ts, data, is_success = _LITERATURE_CACHE[cache_key]
        ttl = _SUCCESS_TTL if is_success else _FAILURE_TTL
        if now - ts < ttl:
            return dict(data)
        else:
            del _LITERATURE_CACHE[cache_key]
    return None


def _set_cached_literature(cache_key: Tuple[str, str, str, str], data: Dict[str, Any], is_success: bool) -> None:
    _LITERATURE_CACHE[cache_key] = (time.time(), dict(data), is_success)


# ---------------------------------------------------------------------------
# Internal E-utilities Callers
# ---------------------------------------------------------------------------

def _ncbi_params(extra: dict) -> dict:
    """Build base NCBI params dict, optionally with API key."""
    params = {"retmode": "json", **extra}
    if _NCBI_API_KEY:
        params["api_key"] = _NCBI_API_KEY
    return params


def _esearch(query: str, db: str = "pubmed", retmax: int = 10) -> List[str]:
    """
    Call ESearch and return a list of PMIDs (strings) for the top retmax hits.
    Returns [] on any error.
    """
    params = _ncbi_params({
        "db": db,
        "term": query,
        "retmax": retmax,
        "sort": "relevance",
    })
    try:
        time.sleep(_REQUEST_DELAY)
        r = _SESSION.get(ESEARCH_URL, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        return data.get("esearchresult", {}).get("idlist", [])
    except Exception as exc:
        logger.warning(f"ESearch failed for query '{query}': {exc}")
        return []


def _efetch_xml(pmids: List[str]) -> List[Dict[str, Any]]:
    """
    Fetch full Medline XML for a list of PMIDs and parse title, year, journal,
    authors, and abstract text.
    """
    if not pmids:
        return []

    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml",
    }
    if _NCBI_API_KEY:
        params["api_key"] = _NCBI_API_KEY

    try:
        time.sleep(_REQUEST_DELAY)
        r = _SESSION.get(EFETCH_URL, params=params, timeout=12)
        r.raise_for_status()
        root = ET.fromstring(r.content)

        articles: List[Dict[str, Any]] = []
        for article_elem in root.findall(".//PubmedArticle"):
            pmid_elem = article_elem.find(".//MedlineCitation/PMID")
            pmid = pmid_elem.text.strip() if pmid_elem is not None and pmid_elem.text else ""
            if not pmid:
                continue

            title_elem = article_elem.find(".//ArticleTitle")
            title = title_elem.text.strip().rstrip(".") if title_elem is not None and title_elem.text else "Untitled Publication"

            # Publication year
            year = "?"
            pub_date = article_elem.find(".//JournalIssue/PubDate")
            if pub_date is not None:
                year_elem = pub_date.find("Year")
                if year_elem is not None and year_elem.text:
                    year = year_elem.text.strip()
                else:
                    medline_date = pub_date.find("MedlineDate")
                    if medline_date is not None and medline_date.text:
                        year = medline_date.text.strip()[:4]

            # Journal
            journal = "PubMed Indexed Journal"
            journal_elem = article_elem.find(".//Journal/Title")
            if journal_elem is not None and journal_elem.text:
                journal = journal_elem.text.strip()
            else:
                iso_elem = article_elem.find(".//Journal/ISOAbbreviation")
                if iso_elem is not None and iso_elem.text:
                    journal = iso_elem.text.strip()

            # First author
            first_author = "Unknown Author"
            author_elems = article_elem.findall(".//AuthorList/Author")
            if author_elems:
                last_name = author_elems[0].findtext("LastName")
                initials = author_elems[0].findtext("Initials")
                if last_name:
                    first_author = f"{last_name} {initials or ''}".strip()

            # Real Abstract text
            abstract_pieces = []
            for abs_elem in article_elem.findall(".//AbstractText"):
                label = abs_elem.get("Label")
                text = abs_elem.text or ""
                if text:
                    if label:
                        abstract_pieces.append(f"{label}: {text.strip()}")
                    else:
                        abstract_pieces.append(text.strip())
            abstract = " ".join(abstract_pieces).strip()

            articles.append({
                "pmid": pmid,
                "title": title,
                "year": year,
                "journal": journal,
                "first_author": first_author,
                "abstract": abstract,
                "url": f"{PUBMED_BASE}/{pmid}/",
            })

        return articles

    except Exception as exc:
        logger.warning(f"EFetch failed for PMIDs {pmids}: {exc}")
        return []


# ---------------------------------------------------------------------------
# Snippet Extraction & RAG Ranking
# ---------------------------------------------------------------------------

def _split_into_sentences(text: str) -> List[str]:
    """Split text into sentences using simple regex."""
    if not text:
        return []
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if len(s.strip()) > 15]


def _extract_best_snippet(abstract: str, query_terms: List[str]) -> str:
    """
    Extract 1-2 sentences from the real abstract that have the highest overlap
    with the target drug and mechanism terms.
    """
    if not abstract:
        return "Abstract text not provided in the MEDLINE indexing record."

    sentences = _split_into_sentences(abstract)
    if not sentences:
        return abstract[:250] + ("..." if len(abstract) > 250 else "")

    term_patterns = [re.compile(rf"\b{re.escape(t)}\b", re.IGNORECASE) for t in query_terms if len(t) >= 3]

    def score_sentence(s: str) -> int:
        return sum(1 for p in term_patterns if p.search(s))

    scored = [(score_sentence(s), idx, s) for idx, s in enumerate(sentences)]
    scored.sort(key=lambda x: (x[0], -x[1]), reverse=True)

    best_match_score, best_idx, best_sent = scored[0]
    if best_match_score > 0:
        # Include next sentence if available for context
        if best_idx + 1 < len(sentences) and len(best_sent) < 180:
            return f"{best_sent} {sentences[best_idx + 1]}"
        return best_sent

    # Fallback to concluding or introductory sentence
    if len(sentences) > 1 and len(sentences[-1]) > 30:
        return sentences[-1]
    return sentences[0]


def _rank_and_format_citations(
    articles: List[Dict[str, Any]],
    drug_a: str,
    drug_b: str,
    disease: str,
    mechanism_terms: List[str],
    max_citations: int = 3,
) -> List[Dict[str, Any]]:
    """
    Rank candidate articles and label match reason based on evidence type:
    - Combination evidence: mentions BOTH drugs.
    - Single-drug evidence: mentions drug_a OR drug_b along with mechanism/disease.
    """
    drug_a_pat = re.compile(rf"\b{re.escape(drug_a)}\b", re.IGNORECASE)
    drug_b_pat = re.compile(rf"\b{re.escape(drug_b)}\b", re.IGNORECASE)
    dis_pat = re.compile(rf"\b{re.escape(disease)}\b", re.IGNORECASE) if disease else None
    mech_pats = [re.compile(rf"\b{re.escape(t)}\b", re.IGNORECASE) for t in mechanism_terms if len(t) >= 3]

    all_query_terms = [drug_a, drug_b] + ([disease] if disease else []) + mechanism_terms

    scored_articles = []
    for art in articles:
        text = f"{art['title']} {art.get('abstract', '')}"

        has_a = bool(drug_a_pat.search(text))
        has_b = bool(drug_b_pat.search(text))
        has_dis = bool(dis_pat.search(text)) if dis_pat else False
        matched_mechs = [t for p, t in zip(mech_pats, mechanism_terms) if p.search(text)]

        score = 0.0
        if has_a and has_b:
            score += 5.0
            evidence_type = "combination"
            matched_ctx = f" and {disease}" if has_dis else (f" and {', '.join(matched_mechs)}" if matched_mechs else "")
            match_reason = f"Combination evidence: study evaluates both {drug_a} and {drug_b}{matched_ctx}."
        elif has_a:
            score += 2.0 + len(matched_mechs) * 0.5 + (1.0 if has_dis else 0.0)
            evidence_type = "single_drug"
            ctx = f" in {disease}" if has_dis else (f" targeting {', '.join(matched_mechs)}" if matched_mechs else "")
            match_reason = f"Single-drug support: investigates {drug_a}{ctx}."
        elif has_b:
            score += 2.0 + len(matched_mechs) * 0.5 + (1.0 if has_dis else 0.0)
            evidence_type = "single_drug"
            ctx = f" in {disease}" if has_dis else (f" targeting {', '.join(matched_mechs)}" if matched_mechs else "")
            match_reason = f"Single-drug support: investigates {drug_b}{ctx}."
        else:
            score += 0.5 + len(matched_mechs) * 0.5
            evidence_type = "mechanistic_context"
            match_reason = f"Mechanistic context: reports on biological pathway ({', '.join(matched_mechs or [disease or 'oncology'])})."

        snippet = _extract_best_snippet(art.get("abstract", ""), all_query_terms)

        scored_articles.append((
            score,
            {
                "pmid": art["pmid"],
                "title": art["title"],
                "year": art["year"],
                "journal": art["journal"],
                "first_author": art["first_author"],
                "snippet": snippet,
                "url": art["url"],
                "match_reason": match_reason,
                "evidence_type": evidence_type,
            }
        ))

    # Sort combination first, then highest score
    scored_articles.sort(key=lambda x: x[0], reverse=True)

    # Return top max_citations
    return [item[1] for item in scored_articles[:max_citations]]


# ---------------------------------------------------------------------------
# Main Public RAG Function
# ---------------------------------------------------------------------------

def retrieve_literature_rag(
    drug_a_name: str,
    drug_b_name: str,
    disease_context: Optional[str] = None,
    top_edges: Optional[List[dict]] = None,
    explanation_text: Optional[str] = None,
    max_citations: int = 3,
) -> Dict[str, Any]:
    """
    Perform retrieve-then-cite PubMed RAG for a drug combination prediction:
    1. Extracts 1-3 mechanism terms from the cited graph edges/explanation.
    2. Builds multi-tiered PubMed queries prioritizing combination hits.
    3. Retrieves genuine records via NCBI ESearch + EFetch.
    4. Ranks abstracts and extracts real 1-2 sentence snippets.
    5. Returns structured literature object with citations, query, and match reasons.
    """
    drug_a = drug_a_name.strip()
    drug_b = drug_b_name.strip()
    disease = disease_context.strip() if disease_context else ""

    # 1. Extract 1-3 mechanism terms from top edges / explanation text
    mechanism_terms: List[str] = []
    if top_edges:
        for e in top_edges:
            src = e.get("source", "")
            tgt = e.get("target", "")
            for node in (src, tgt):
                node_clean = node.strip()
                if (
                    node_clean
                    and node_clean.lower() not in (drug_a.lower(), drug_b.lower(), disease.lower())
                    and len(node_clean) >= 3
                    and not node_clean.lower().startswith("db")
                    and node_clean not in mechanism_terms
                ):
                    mechanism_terms.append(node_clean)
                    if len(mechanism_terms) >= 3:
                        break
            if len(mechanism_terms) >= 3:
                break

    # If no terms found from edges, extract prominent capitalized tokens from explanation text
    if not mechanism_terms and explanation_text:
        words = re.findall(r"\b[A-Z0-9]{3,}\b", explanation_text)
        for w in words:
            if w.lower() not in (drug_a.lower(), drug_b.lower()) and w not in mechanism_terms:
                mechanism_terms.append(w)
                if len(mechanism_terms) >= 2:
                    break

    # 2. Check Cache
    cache_key = (
        drug_a.lower(),
        drug_b.lower(),
        disease.lower(),
        ",".join(sorted(t.lower() for t in mechanism_terms)),
    )
    cached = _get_cached_literature(cache_key)
    if cached is not None:
        return cached

    # 3. Formulate multi-tier queries
    # Tier 1: Combination + Disease or Mechanism
    drug_a_q = f'"{drug_a}"' if " " in drug_a else drug_a
    drug_b_q = f'"{drug_b}"' if " " in drug_b else drug_b

    context_terms = ([f'"{disease}"' if " " in disease else disease] if disease else []) + [
        f'"{m}"' if " " in m else m for m in mechanism_terms
    ]

    tier1_query = f"({drug_a_q} AND {drug_b_q})"
    if context_terms:
        tier1_query += f" AND ({' OR '.join(context_terms[:3])})"

    tier2_query = f"{drug_a_q} AND {drug_b_q}"

    # Tier 3: Drug A with mechanism + Drug B with mechanism
    tier3_a_query = f"{drug_a_q} AND ({' OR '.join(context_terms[:2])})" if context_terms else drug_a_q
    tier3_b_query = f"{drug_b_q} AND ({' OR '.join(context_terms[:2])})" if context_terms else drug_b_q

    query_used = tier1_query
    pmids = _esearch(tier1_query, retmax=10)

    if not pmids:
        # Try Tier 2 (Combination alone)
        query_used = tier2_query
        pmids = _esearch(tier2_query, retmax=8)

    if not pmids and context_terms:
        # Try Tier 3 (Single-drug mechanistic support)
        query_used = f"{tier3_a_query} [fallback single-drug]"
        pmids_a = _esearch(tier3_a_query, retmax=4)
        pmids_b = _esearch(tier3_b_query, retmax=4)
        pmids = list(dict.fromkeys(pmids_a + pmids_b))  # preserve order, deduplicate

    if not pmids:
        res = {
            "citations": [],
            "query_used": query_used,
            "retrieval_method": "ncbi_eutilities_rag",
            "error": None,
            "no_literature_reason": "No matching PubMed records found for this specific drug pair and mechanism query.",
        }
        _set_cached_literature(cache_key, res, is_success=False)
        return res

    # 4. Fetch real articles with abstracts
    articles = _efetch_xml(pmids[:8])
    if not articles:
        # Fallback to ESummary if EFetch failed
        summary = _esummary(pmids[:max_citations])
        if summary:
            articles = []
            for pmid in pmids[:max_citations]:
                if pmid in summary:
                    e = summary[pmid]
                    articles.append({
                        "pmid": pmid,
                        "title": e.get("title", "").rstrip("."),
                        "year": (e.get("pubdate", "") or e.get("epubdate", ""))[:4] or "?",
                        "journal": e.get("source", "PubMed Journal"),
                        "first_author": (e.get("authors", [{}])[0].get("name", "Unknown Author")),
                        "abstract": e.get("title", ""),
                        "url": f"{PUBMED_BASE}/{pmid}/",
                    })

    if not articles:
        res = {
            "citations": [],
            "query_used": query_used,
            "retrieval_method": "ncbi_eutilities_rag",
            "error": "Failed to parse publication metadata from NCBI E-utilities.",
            "no_literature_reason": "Publication records could not be fetched from NCBI.",
        }
        _set_cached_literature(cache_key, res, is_success=False)
        return res

    # 5. Rank and format citations
    citations = _rank_and_format_citations(
        articles=articles,
        drug_a=drug_a,
        drug_b=drug_b,
        disease=disease,
        mechanism_terms=mechanism_terms,
        max_citations=max_citations,
    )

    res = {
        "citations": citations,
        "query_used": query_used,
        "retrieval_method": "ncbi_eutilities_rag",
        "error": None,
        "no_literature_reason": None if citations else "No papers could be parsed.",
    }
    _set_cached_literature(cache_key, res, is_success=True)
    return res


# Backward compatibility wrapper for old callers
def get_supporting_literature(
    drug_name: str,
    target_or_disease: str,
    max_results: int = 2,
) -> List[Dict[str, str]]:
    """Legacy wrapper forwarding to retrieve_literature_rag."""
    rag = retrieve_literature_rag(
        drug_a_name=drug_name,
        drug_b_name="",
        disease_context=target_or_disease,
        max_citations=max_results,
    )
    return rag.get("citations", [])


def get_literature_for_explanation(
    drug_a_name: str,
    drug_b_name: str,
    explanation_text: str,
    top_edges: List[dict],
    all_edges: Optional[List[dict]] = None,
    max_results: int = 2,
    disease_context: Optional[str] = None,
) -> Dict[str, Any]:
    """Legacy-compatible wrapper returning the full RAG literature object."""
    return retrieve_literature_rag(
        drug_a_name=drug_a_name,
        drug_b_name=drug_b_name,
        disease_context=disease_context,
        top_edges=top_edges,
        explanation_text=explanation_text,
        max_citations=max_results,
    )
