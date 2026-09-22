"""
literature.py -- Retrieve-Then-Cite PubMed RAG via NCBI E-utilities
==================================================================

Performs real PubMed literature retrieval for drug combination explanations:
1. Mechanism Term Extraction: Strictly extracts gene/protein/pathway terms from the
   cited subgraph. Excludes other diseases, phenotypes, and indications (e.g. pyoureter,
   acute leukemia, breast carcinoma, cutaneous T-cell lymphoma) unless matching user disease_context.
2. Multi-tier query builder:
   - Tier 1: (drug_a AND drug_b) AND (user_disease OR gene/pathway terms) [capped at max 3 genes/pathways]
   - Tier 2: (drug_a AND drug_b) [combination alone without extra diseases]
   - Tier 3: single-drug + user_disease [explicitly single-drug evidence]
3. NCBI ESearch + EFetch: Retrieves real Medline records with XML abstracts.
4. Honest Combination & Single-Drug Detection:
   - "combination": requires BOTH drug names/synonyms in title or abstract.
   - "single_drug": exactly one of the two drugs in title or abstract.
   - "weak" / "related": disease or pathway mentioned without both drugs.
5. Abstract Ranking & Snippet Extraction: Prioritizes combination sentences from the
   real abstract with zero hallucinations.
6. In-memory caching by (drug_a, drug_b, disease, mechanism_terms) with TTL.
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

# Common oncology drug aliases/synonyms for high-recall, exact token matching
DRUG_SYNONYMS: Dict[str, List[str]] = {
    "temozolomide": ["tmz", "temodar", "temodal"],
    "carmustine": ["bcnu", "bicnu", "gliadel"],
    "lomustine": ["ccnu", "ceenu", "gleostine"],
    "cyclophosphamide": ["ctx", "cpm", "cytoxan", "endoxan", "neosar"],
    "procarbazine": ["matulane", "natulan", "pcz"],
    "vincristine": ["vcr", "oncovin", "vincasar"],
    "cisplatin": ["cddp", "platinol"],
    "carboplatin": ["cbdca", "paraplatin"],
    "oxaliplatin": ["eloxatin", "l-ohp"],
    "irinotecan": ["cpt-11", "camptosar", "cpt11"],
    "topotecan": ["hycamtin"],
    "doxorubicin": ["adriamycin", "dox"],
    "paclitaxel": ["taxol"],
    "docetaxel": ["taxotere"],
    "bevacizumab": ["avastin"],
}

_DISEASE_KEYWORDS = {
    "carcinoma", "lymphoma", "leukemia", "neoplasm", "tumor", "tumour",
    "sarcoma", "glioma", "melanoma", "blastoma", "disease", "syndrome",
    "disorder", "pyoureter", "edema", "pachymeningitis", "infection",
    "dermatophytosis", "thrombocytopenia", "reticulosis", "fungoides",
    "fibroblast", "metastasis", "cancer", "adenoma", "myeloma"
}

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
# Biological Term Extraction & Query Normalization
# ---------------------------------------------------------------------------

def normalize_disease_name(disease: Optional[str]) -> str:
    """Normalize disease string by stripping parentheticals, punctuation, and extra whitespace."""
    if not disease:
        return ""
    # Strip parentheticals like "(CNS)", "(disease)", etc.
    cleaned = re.sub(r"\s*\(.*?\)", "", disease).strip()
    return cleaned.strip("\"' ")


def _is_same_disease(candidate: str, user_disease: Optional[str]) -> bool:
    """Check whether a candidate node string refers to the user's disease."""
    if not candidate or not user_disease:
        return False
    c_norm = normalize_disease_name(candidate).lower()
    u_norm = normalize_disease_name(user_disease).lower()
    if not c_norm or not u_norm:
        return False
    if c_norm == u_norm:
        return True
    if u_norm in c_norm or c_norm in u_norm:
        return True
    return False


def _is_disease_or_phenotype(node_name: str, node_type: Optional[str] = None) -> bool:
    """
    Return True if node is classified as disease, phenotype, or indication.
    Used to prevent unrelated disease nodes from leaking into mechanism OR-terms.
    """
    if node_type:
        nt = node_type.lower()
        if "disease" in nt or "phenotype" in nt or "indication" in nt:
            return True
        if "gene" in nt or "protein" in nt or "pathway" in nt:
            return False
    # Fallback heuristic if node_type is unspecified
    tokens = set(re.findall(r"\b\w+\b", node_name.lower()))
    return bool(tokens & _DISEASE_KEYWORDS)


def extract_mechanism_terms(
    top_edges: Optional[List[dict]] = None,
    explanation_text: Optional[str] = None,
    drug_a: str = "",
    drug_b: str = "",
    disease_context: Optional[str] = None,
    max_terms: int = 3,
) -> List[str]:
    """
    Extract mechanism terms (genes, proteins, pathways) from the cited subgraph.
    Strictly EXCLUDES other diseases, phenotypes, and indications unless the node
    equals the user disease_context.
    """
    drug_a_l = drug_a.lower()
    drug_b_l = drug_b.lower()
    user_dis_norm = normalize_disease_name(disease_context).lower()

    mechanism_terms: List[str] = []

    def is_eligible_mechanism(node_name: str, node_type: Optional[str] = None) -> bool:
        if not node_name or len(node_name.strip()) < 2:
            return False
        clean = node_name.strip()
        clean_l = clean.lower()
        if clean_l in (drug_a_l, drug_b_l) or clean_l.startswith("db"):
            return False
        # If it's a disease node:
        if _is_disease_or_phenotype(clean, node_type):
            # Only allowed if it equals the user's disease (and user disease is handled as user_disease)
            return False
        # If node_type explicitly specifies gene/protein or pathway, allow
        if node_type:
            nt = node_type.lower()
            if "gene" in nt or "protein" in nt or "pathway" in nt:
                return True
            if "drug" in nt:
                return False
        # If node_type is not available, check it's not a generic word
        if clean_l in ("and", "the", "for", "with", "not", "or", "cell", "human", "drug", "target"):
            return False
        return True

    if top_edges:
        for e in top_edges:
            src = e.get("source", "")
            src_type = e.get("source_type")
            tgt = e.get("target", "")
            tgt_type = e.get("target_type")

            for node, ntype in ((src, src_type), (tgt, tgt_type)):
                node_clean = node.strip()
                if (
                    is_eligible_mechanism(node_clean, ntype)
                    and node_clean not in mechanism_terms
                ):
                    mechanism_terms.append(node_clean)
                    if len(mechanism_terms) >= max_terms:
                        return mechanism_terms

    # Fallback to explanation text if no genes/pathways found in edges
    if not mechanism_terms and explanation_text:
        candidates = re.findall(r"\b[A-Z][A-Z0-9]{2,}\b", explanation_text)
        skip_words = {"AND", "THE", "FOR", "NOT", "CNS", "GNN", "NLM", "USA", "ALL", "TOP", "DNA", "RNA"}
        for c in candidates:
            if (
                c not in skip_words
                and c.lower() not in (drug_a_l, drug_b_l, user_dis_norm)
                and c not in mechanism_terms
            ):
                mechanism_terms.append(c)
                if len(mechanism_terms) >= max_terms:
                    break

    return mechanism_terms


def build_pubmed_queries(
    drug_a: str,
    drug_b: str,
    disease_context: Optional[str] = None,
    mechanism_terms: Optional[List[str]] = None,
) -> Tuple[str, str, str, str]:
    """
    Build multi-tiered PubMed queries according to spec:
    - Tier 1: (drug_a AND drug_b) AND (user_disease OR gene/pathway terms) [capped at max 3 terms]
    - Tier 2: (drug_a AND drug_b) without extra diseases
    - Tier 3: single-drug + user_disease
    Returns (tier1_query, tier2_query, tier3_a_query, tier3_b_query).
    """
    drug_a_clean = drug_a.strip()
    drug_b_clean = drug_b.strip()
    norm_disease = normalize_disease_name(disease_context)

    drug_a_q = f'"{drug_a_clean}"' if " " in drug_a_clean else drug_a_clean
    drug_b_q = f'"{drug_b_clean}"' if " " in drug_b_clean else drug_b_clean

    mechs = (mechanism_terms or [])[:3]

    or_terms: List[str] = []
    if norm_disease:
        or_terms.append(f'"{norm_disease}"' if " " in norm_disease else norm_disease)
    for m in mechs:
        or_terms.append(f'"{m}"' if " " in m else m)

    # Tier 1: (drug_a AND drug_b) AND (user_disease OR gene/pathway terms)
    if or_terms:
        tier1_query = f"({drug_a_q} AND {drug_b_q}) AND ({' OR '.join(or_terms)})"
    else:
        tier1_query = f"{drug_a_q} AND {drug_b_q}"

    # Tier 2: (drug_a AND drug_b) without extra diseases
    tier2_query = f"{drug_a_q} AND {drug_b_q}"

    # Tier 3: single-drug + user_disease
    if norm_disease:
        dis_q = f'"{norm_disease}"' if " " in norm_disease else norm_disease
        tier3_a_query = f"{drug_a_q} AND ({dis_q})"
        tier3_b_query = f"{drug_b_q} AND ({dis_q})"
    elif mechs:
        mech_q = " OR ".join(f'"{m}"' if " " in m else m for m in mechs[:2])
        tier3_a_query = f"{drug_a_q} AND ({mech_q})"
        tier3_b_query = f"{drug_b_q} AND ({mech_q})"
    else:
        tier3_a_query = drug_a_q
        tier3_b_query = drug_b_q

    return tier1_query, tier2_query, tier3_a_query, tier3_b_query


# ---------------------------------------------------------------------------
# Drug Mentions & Evidence Verification
# ---------------------------------------------------------------------------

def _get_drug_patterns(drug_name: str) -> List[re.Pattern]:
    """Get compiled regex word-boundary patterns for drug name and synonyms."""
    d_clean = drug_name.strip()
    if not d_clean:
        return []
    names = [d_clean]
    names.extend(DRUG_SYNONYMS.get(d_clean.lower(), []))
    patterns = []
    for n in names:
        if len(n) <= 2:
            continue
        patterns.append(re.compile(rf"\b{re.escape(n)}\b", re.IGNORECASE))
    return patterns


def check_drug_mentions(text: str, drug_name: str) -> bool:
    """Return True if drug or its common synonyms appear as distinct word tokens in text."""
    if not text or not drug_name:
        return False
    patterns = _get_drug_patterns(drug_name)
    return any(p.search(text) for p in patterns)


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


def _esummary(pmids: List[str]) -> Dict[str, Any]:
    """ESummary fallback for metadata when EFetch fails."""
    if not pmids:
        return {}
    params = _ncbi_params({
        "db": "pubmed",
        "id": ",".join(pmids),
    })
    try:
        time.sleep(_REQUEST_DELAY)
        r = _SESSION.get(ESUMMARY_URL, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        return data.get("result", {})
    except Exception as exc:
        logger.warning(f"ESummary failed: {exc}")
        return {}


# ---------------------------------------------------------------------------
# Snippet Extraction & RAG Ranking
# ---------------------------------------------------------------------------

def _split_into_sentences(text: str) -> List[str]:
    """Split text into sentences using regex."""
    if not text:
        return []
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if len(s.strip()) > 15]


def _extract_best_snippet(
    abstract: str,
    all_terms: List[str],
    drug_a: str = "",
    drug_b: str = "",
) -> str:
    """
    Extract 1-2 sentences from the real abstract that have the highest overlap.
    Sentences mentioning both drugs are heavily prioritized.
    """
    if not abstract:
        return "Abstract text not provided in the MEDLINE indexing record."

    sentences = _split_into_sentences(abstract)
    if not sentences:
        return abstract[:250] + ("..." if len(abstract) > 250 else "")

    pats_a = _get_drug_patterns(drug_a) if drug_a else []
    pats_b = _get_drug_patterns(drug_b) if drug_b else []
    other_pats = [re.compile(rf"\b{re.escape(t)}\b", re.IGNORECASE) for t in all_terms if len(t) >= 3]

    def score_sentence(s: str) -> float:
        score = 0.0
        has_a = any(p.search(s) for p in pats_a)
        has_b = any(p.search(s) for p in pats_b)
        if has_a and has_b:
            score += 10.0
        elif has_a or has_b:
            score += 3.0
        for p in other_pats:
            if p.search(s):
                score += 1.0
        return score

    scored = [(score_sentence(s), idx, s) for idx, s in enumerate(sentences)]
    scored.sort(key=lambda x: (x[0], -x[1]), reverse=True)

    best_match_score, best_idx, best_sent = scored[0]
    if best_match_score > 0:
        if best_idx + 1 < len(sentences) and len(best_sent) < 180:
            return f"{best_sent} {sentences[best_idx + 1]}"
        return best_sent

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
    - combination: requires BOTH drugs in title or abstract.
    - single_drug: exactly one of the two drugs in title or abstract.
    - weak / related: disease or related context, but neither drug directly.
    """
    norm_dis = normalize_disease_name(disease)
    all_query_terms = [drug_a, drug_b] + ([norm_dis] if norm_dis else []) + mechanism_terms

    scored_articles = []
    for art in articles:
        text = f"{art['title']} {art.get('abstract', '')}"

        has_a = check_drug_mentions(text, drug_a)
        has_b = check_drug_mentions(text, drug_b)

        has_disease = False
        if norm_dis:
            has_disease = bool(re.search(rf"\b{re.escape(norm_dis)}\b", text, re.IGNORECASE))

        matched_mechs = [
            m for m in mechanism_terms
            if re.search(rf"\b{re.escape(m)}\b", text, re.IGNORECASE)
        ]

        if has_a and has_b:
            evidence_type = "combination"
            matched_ctx = f" and {norm_dis}" if has_disease else (f" and {', '.join(matched_mechs)}" if matched_mechs else "")
            match_reason = f"Combination evidence: study evaluates both {drug_a} and {drug_b}{matched_ctx}."
            score = 10.0 + (3.0 if has_disease else 0.0) + len(matched_mechs) * 0.5
        elif has_a and not has_b:
            evidence_type = "single_drug"
            matched_ctx = f" in {norm_dis}" if has_disease else (f" targeting {', '.join(matched_mechs)}" if matched_mechs else "")
            match_reason = f"Single-drug support: investigates {drug_a}{matched_ctx} (does not evaluate combination with {drug_b})."
            score = 3.0 + (2.0 if has_disease else 0.0) + len(matched_mechs) * 0.5
        elif has_b and not has_a:
            evidence_type = "single_drug"
            matched_ctx = f" in {norm_dis}" if has_disease else (f" targeting {', '.join(matched_mechs)}" if matched_mechs else "")
            match_reason = f"Single-drug support: investigates {drug_b}{matched_ctx} (does not evaluate combination with {drug_a})."
            score = 3.0 + (2.0 if has_disease else 0.0) + len(matched_mechs) * 0.5
        else:
            evidence_type = "weak"
            matched_ctx = f" for {norm_dis}" if has_disease else (f" ({', '.join(matched_mechs)})" if matched_mechs else "")
            match_reason = f"Related disease context: mentions related biological context{matched_ctx}, but neither drug directly."
            score = 0.5 + (1.0 if has_disease else 0.0) + len(matched_mechs) * 0.5

        snippet = _extract_best_snippet(art.get("abstract", ""), all_query_terms, drug_a=drug_a, drug_b=drug_b)

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

    # Sort strictly by evidence score descending (combination first, then single-drug, then weak)
    scored_articles.sort(key=lambda x: x[0], reverse=True)

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
    1. Extracts mechanism terms (genes, proteins, pathways) from the cited graph edges/explanation.
       Strictly EXCLUDES other diseases, phenotypes, and indications unless matching user disease_context.
    2. Builds multi-tiered PubMed queries prioritizing combination hits:
       - Tier 1: (drug_a AND drug_b) AND (user_disease OR gene/pathway terms) [capped at max 3 terms]
       - Tier 2: (drug_a AND drug_b) [combination alone without extra diseases]
       - Tier 3: single-drug + user_disease [explicitly single-drug evidence]
    3. Retrieves genuine records via NCBI ESearch + EFetch.
    4. Ranks abstracts and verifies both drugs appear for "combination" labeling.
    5. Returns structured literature object with citations, query_used, and match reasons.
    """
    drug_a = drug_a_name.strip()
    drug_b = drug_b_name.strip()
    norm_disease = normalize_disease_name(disease_context)

    # 1. Extract mechanism terms (genes, proteins, pathways only; NO unrelated diseases)
    mechanism_terms = extract_mechanism_terms(
        top_edges=top_edges,
        explanation_text=explanation_text,
        drug_a=drug_a,
        drug_b=drug_b,
        disease_context=norm_disease,
        max_terms=3,
    )

    # 2. Check Cache
    cache_key = (
        drug_a.lower(),
        drug_b.lower(),
        norm_disease.lower(),
        ",".join(sorted(t.lower() for t in mechanism_terms)),
    )
    cached = _get_cached_literature(cache_key)
    if cached is not None:
        return cached

    # 3. Formulate multi-tier queries
    tier1_query, tier2_query, tier3_a_query, tier3_b_query = build_pubmed_queries(
        drug_a=drug_a,
        drug_b=drug_b,
        disease_context=norm_disease,
        mechanism_terms=mechanism_terms,
    )

    query_used = tier1_query
    pmids = _esearch(tier1_query, retmax=10)

    if not pmids and tier2_query != tier1_query:
        # Try Tier 2 (Combination alone without extra terms)
        query_used = tier2_query
        pmids = _esearch(tier2_query, retmax=8)

    if not pmids and (norm_disease or mechanism_terms):
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
        disease=norm_disease,
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


# ---------------------------------------------------------------------------
# Backward Compatibility Wrappers
# ---------------------------------------------------------------------------

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


def check_triple_literature(
    drug_a: str,
    drug_b: str,
    drug_c: str,
    disease_context: Optional[str] = None,
    max_results: int = 3,
) -> Optional[Dict[str, Any]]:
    """
    Check PubMed for published literature mentioning all three drugs co-occurring,
    distinct from pairwise literature lookups.

    Adheres strictly to rate limits: uses session pooling, local caching,
    and returns a clean structured result.
    Note: Per FUTURE_SCOPE.md section 5 ('never batch-PubMed'), this should only
    be called on-demand for single inspected triples, not in batch search loops.
    """
    da = drug_a.strip()
    db = drug_b.strip()
    dc = drug_c.strip()
    if not (da and db and dc):
        return None

    qa = f'"{da}"' if " " in da else da
    qb = f'"{db}"' if " " in db else db
    qc = f'"{dc}"' if " " in dc else dc

    norm_dis = normalize_disease_name(disease_context)
    if norm_dis:
        qd = f'"{norm_dis}"' if " " in norm_dis else norm_dis
        query = f"({qa} AND {qb} AND {qc}) AND ({qd})"
    else:
        query = f"({qa} AND {qb} AND {qc})"

    cache_key = (da.lower(), db.lower(), dc.lower(), norm_dis.lower())
    cached = _get_cached_literature(cache_key)
    if cached is not None:
        return cached

    pmids = search_pubmed(query, max_results=max_results)
    if not pmids and norm_dis:
        # Fallback to pure 3-drug query without disease constraint
        query = f"({qa} AND {qb} AND {qc})"
        pmids = search_pubmed(query, max_results=max_results)

    if not pmids:
        res = {
            "query_used": query,
            "citations": [],
            "count": 0,
            "has_triple_literature": False,
        }
        _set_cached_literature(cache_key, res, is_success=False)
        return res

    citations_raw = fetch_pubmed_summaries(pmids)
    citations = []
    for c in citations_raw:
        c["match_reason"] = f"Co-occurrence of {da}, {db}, and {dc} in publication"
        c["evidence_type"] = "triple_combination"
        citations.append(c)

    res = {
        "query_used": query,
        "citations": citations,
        "count": len(citations),
        "has_triple_literature": len(citations) > 0,
    }
    _set_cached_literature(cache_key, res, is_success=True)
    return res

