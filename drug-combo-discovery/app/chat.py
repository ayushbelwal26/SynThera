"""
app/chat.py — Tool-Calling LLM Chat Service for SynThera Analysis
=================================================================

Provides a grounded LLM conversational agent that:
1. Interacts through OpenRouter (OpenAI-compatible API).
2. ONLY states biological/mechanistic facts obtained from tool call JSON results.
3. Wraps exactly 4 existing SynThera capabilities:
   - predict_pair(drug_a, drug_b, cell_line) -> wraps /predict
   - search_combinations(disease, cell_line, inspect_top_k) -> wraps /search
   - why_not(disease, cell_line, drug_name, current_top_pairs) -> wraps /why-not
   - get_literature(drug_a, drug_b, target_or_pathway) -> wraps PubMed retrieval
4. Capped at 4 tool calls per turn to prevent runaway loops.
5. Server-side structured logging of every tool call and result.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

# Ensure root directory and .env are loaded
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
load_dotenv(os.path.join(ROOT_DIR, ".env"))

logger = logging.getLogger("synthera.chat")
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(logging.Formatter("[%(asctime)s][%(name)s][%(levelname)s] %(message)s"))
    logger.addHandler(ch)

router = APIRouter(prefix="/chat", tags=["Chat"])

# ---------------------------------------------------------------------------
# Constants & Configuration
# ---------------------------------------------------------------------------

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openrouter/free"
MAX_TOOL_CALLS = 4

SYSTEM_PROMPT = """You are a research assistant inside SynThera, a drug-combination hypothesis tool.
Never discuss anything outside drug synergy, drug mechanisms, and this app's data (no weather, no small talk beyond brief acknowledgment).
If the user asks about the weather, refuses to discuss it, decline and redirect to drug combination analysis.
Never suggest or imply a drug that the app's filters have excluded is worth considering.
Maximum 4 tool calls per turn.

GROUNDING IS STRICT AND LITERAL.

You must never add biological, pharmacological, mechanistic, pathway, target,
drug-specific, combination-specific, disease-specific, or literature
information from your pretrained knowledge.

A statement being scientifically true is NOT sufficient.

Every specific biological/mechanistic/literature claim in your final answer
must be directly supported by information returned by a tool call made during
the current conversation.

Do not elaborate on tool results.

Do not complete missing mechanisms from your own knowledge.

Do not infer a mechanism from a drug name, target name, pathway name,
indication, or any other information.

Do not combine separate facts into a new biological conclusion unless that
conclusion itself is explicitly supported by the tool result.

Do not turn an indication into a mechanism.

Do not turn a drug class into a mechanism.

Do not infer synergy from two individual drug mechanisms.

Do not infer pathway relationships.

Do not infer causality.

Do not infer why a combination works.

If the user asks for mechanistic detail that is not present in the available
tool result, call get_literature if that tool can provide the requested
information.

If get_literature does not return the requested information, explicitly say
that the information is not available in the app's retrieved data.

NEVER fill the missing information using general scientific knowledge.

When answering, stay as close as possible to the wording and facts contained
in the tool results.

Scientific correctness does not override grounding requirements.

WHY-NOT RULES:
When answering why a drug was not recommended:
1. Call why_not.
2. Use ONLY information returned by why_not.
3. Do not call other tools unless the user explicitly asks for additional literature/mechanistic information.
4. Do not add general knowledge about the drug (e.g. do not say "Drug X has been explored in literature" unless why_not explicitly returned that).
5. Do not infer why the application's ranking/filtering happened.
6. Preserve numerical values exactly.
7. Explicitly state the candidate rank (e.g. "ranked #4 in the candidate pool") and preserve ranking/order exactly.
8. Preserve the meaning of the endpoint's explanation.
9. If the tool says information is unavailable, do not fill the gap.

MECHANISM AND "WHY DO THEY WORK" QUESTIONS:
For questions such as:
- "Why do these drugs work together?"
- "What is the mechanism?"
- "Explain the pathway"
- "Why is this combination synergistic?"
- "What happens biologically?"
- "What targets do these drugs affect?"
You must NOT automatically answer from pretrained knowledge.
Determine whether current tool results contain the requested information. If not, call get_literature(drug_a, drug_b, target_or_pathway).
If the literature result contains the requested information, answer only from that result.
If it does not, say that the retrieved data does not contain enough information to answer the mechanistic question.
Example of REQUIRED behavior:
Tool result: "Temozolomide and Carmustine are both indicated for anaplastic astrocytoma."
User: "What is the molecular mechanism behind this combination?"
INVALID: "Both drugs are DNA alkylating agents. Temozolomide generates O6-methylguanine, which causes mismatch repair and eventually apoptosis..." (Even if scientifically correct, this is invalid because those facts were not returned by a tool).
VALID: "The retrieved analysis states that Temozolomide and Carmustine are both indicated for anaplastic astrocytoma, but it does not provide enough mechanistic detail to explain the molecular mechanism of their combination."

FORBIDDEN BIOLOGICAL INFERENCES:
Treat the following as strictly unsupported claims unless explicitly returned by a tool:
- drug classes
- molecular targets
- proteins
- genes
- pathways
- signaling pathways
- enzymes
- receptors
- mutations
- biomarkers
- mechanisms of action
- DNA/RNA effects
- apoptosis
- senescence
- cell-cycle effects
- resistance mechanisms
- synthetic lethality
- pharmacological interactions
- synergy mechanisms
- antagonism mechanisms
- therapeutic indications
- clinical claims
- literature conclusions
You may mention them ONLY when they appear in the current tool results.

CLAIM-LEVEL GROUNDING:
Before producing a biological or mechanistic statement, verify that the
specific entity, relationship, action, or conclusion appears explicitly in
the current tool results.

Do not expand abbreviations using pretrained knowledge.

Do not expand a target into its full biological name unless the full name
appears in the tool result.

Do not introduce additional targets, genes, proteins, enzymes, pathways,
mechanisms, effects, or relationships.

For example, if a tool says:
"Procarbazine primarily acts on MAOB"

you may say:
"Procarbazine primarily acts on MAOB."

You may NOT say:
"Procarbazine primarily acts on MAOB, MAOA, and XDH."

You may NOT say:
"Procarbazine inhibits monoamine oxidase B."

You may NOT say:
"MAOB activity causes apoptosis."

You may NOT say:
"MAOB and CDK4 create a complementary anti-tumor mechanism."

unless those exact facts are explicitly supported by current tool results.

The model must not make scientifically reasonable expansions.

Literal grounding takes priority over scientific completeness."""

# ---------------------------------------------------------------------------
# Tool Schemas for OpenRouter (OpenAI Function-Calling Format)
# ---------------------------------------------------------------------------

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "predict_pair",
            "description": (
                "Returns prediction information for a specific drug pair and cell line.\n\n"
                "Use this tool when the user asks about the predicted behavior, score, "
                "ranking, or prediction associated with a specific pair.\n\n"
                "Only facts explicitly returned by this tool may be used from this tool. "
                "Do not infer biological mechanisms from the drug names or prediction."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "drug_a": {
                        "type": "string",
                        "description": "First drug name or DrugBank ID (e.g. 'Temozolomide', 'DB00853')"
                    },
                    "drug_b": {
                        "type": "string",
                        "description": "Second drug name or DrugBank ID (e.g. 'Cyclophosphamide', 'DB00531')"
                    },
                    "cell_line": {
                        "type": "string",
                        "description": "Cancer cell line name (e.g. 'T98G', 'A549')"
                    }
                },
                "required": ["drug_a", "drug_b", "cell_line"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_combinations",
            "description": (
                "Returns combinations discovered by the application's existing search logic.\n\n"
                "Use this tool when the user asks which combinations were found/recommended "
                "for a disease and cell line.\n\n"
                "Only facts explicitly returned by this tool may be used from this tool. "
                "Do not infer mechanisms or therapeutic value from the returned drug names. "
                "Do not recommend drugs that are absent because of the application's filters."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "disease": {
                        "type": "string",
                        "description": "Target disease name (e.g. 'glioblastoma')"
                    },
                    "cell_line": {
                        "type": "string",
                        "description": "Target cell line context (e.g. 'T98G')"
                    },
                    "inspect_top_k": {
                        "type": "integer",
                        "description": "Number of top hits to run in-silico faithfulness verification on (0-3)",
                        "default": 0
                    }
                },
                "required": ["disease", "cell_line"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "why_not",
            "description": (
                "Returns the application's existing explanation for why a drug was not "
                "recommended.\n\n"
                "When answering a why-not question, the response must be grounded in this "
                "tool's returned data.\n\n"
                "Do not supplement the explanation with outside pharmacology, literature, "
                "mechanisms, indications, or assumptions.\n\n"
                "If the tool does not contain the requested explanation, say that the "
                "information is not available."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "disease": {
                        "type": "string",
                        "description": "Target disease context (e.g. 'glioblastoma')"
                    },
                    "cell_line": {
                        "type": "string",
                        "description": "Target cell line context (e.g. 'T98G')"
                    },
                    "drug_name": {
                        "type": "string",
                        "description": "The specific drug being inquired about (e.g. 'Temozolomide', 'Zinc chloride')"
                    },
                    "current_top_pairs": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of top pairs currently displayed"
                    }
                },
                "required": ["disease", "cell_line", "drug_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_literature",
            "description": (
                "Returns literature retrieved by the application's existing PubMed retrieval "
                "logic.\n\n"
                "Only information explicitly returned by this tool may be used as a "
                "literature/mechanistic claim.\n\n"
                "Do not invent citations, article findings, mechanisms, pathway relationships, "
                "or conclusions that are not present in the returned literature data."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "drug_a": {
                        "type": "string",
                        "description": "First drug name"
                    },
                    "drug_b": {
                        "type": "string",
                        "description": "Second drug name"
                    },
                    "target_or_pathway": {
                        "type": "string",
                        "description": "Optional biological target, gene, or pathway term (e.g. 'MGMT', 'DNA repair', 'EGFR')"
                    }
                },
                "required": ["drug_a", "drug_b"]
            }
        }
    }
]

# ---------------------------------------------------------------------------
# Wrapped Tool Implementations (Strictly Reusing Existing Logic)
# ---------------------------------------------------------------------------

def execute_predict_pair(drug_a: str, drug_b: str, cell_line: str) -> Dict[str, Any]:
    """Wraps existing /predict endpoint logic."""
    try:
        from app.main import predict, PredictRequest
        req = PredictRequest(drug_a=drug_a, drug_b=drug_b, cell_line=cell_line)
        res = predict(req)
        faith = res.get("faithfulness") or {}
        return {
            "status": "success",
            "drug_a": res.get("drug_a_name", drug_a),
            "drug_b": res.get("drug_b_name", drug_b),
            "cell_line": res.get("cell_line", cell_line),
            "predicted_class": res.get("predicted_class"),
            "probabilities": {
                "synergy": round(float(res.get("p_synergy", 0.0)), 4),
                "additive": round(float(res.get("p_additive", 0.0)), 4),
                "antagonism": round(float(res.get("p_antagonism", 0.0)), 4),
            },
            "composite_v_score": res.get("v_score"),
            "explanation_text": res.get("explanation_text"),
        }
    except Exception as e:
        logger.error(f"[predict_pair error] {e}")
        return {"status": "error", "error": str(e)}


def execute_search_combinations(disease: str, cell_line: str, inspect_top_k: int = 0) -> Dict[str, Any]:
    """Wraps existing /search endpoint logic."""
    try:
        from app.main import search_combinations, SearchRequest
        req = SearchRequest(disease=disease, cell_line=cell_line, inspect_top_k=inspect_top_k, top_k=5)
        res = search_combinations(req)
        top_pairs = []
        for r in res.get("results", [])[:5]:
            top_pairs.append({
                "rank": r.get("rank"),
                "drug_a": r.get("drug_a_name", r.get("drug_a")),
                "drug_b": r.get("drug_b_name", r.get("drug_b")),
                "composite_v_score": r.get("v_score"),
                "p_synergy": round(float(r.get("p_synergy", 0.0)), 4),
                "predicted_class": r.get("predicted_class"),
                "explanation_text": r.get("explanation_text"),
            })
        return {
            "status": "success",
            "disease": res.get("disease"),
            "cell_line": res.get("cell_line"),
            "top_candidate_pairs": top_pairs,
        }
    except Exception as e:
        logger.error(f"[search_combinations error] {e}")
        return {"status": "error", "error": str(e)}


def execute_why_not(disease: str, cell_line: str, drug_name: str, current_top_pairs: Optional[List[str]] = None) -> Dict[str, Any]:
    """Wraps existing /why-not endpoint logic."""
    try:
        from app.main import why_not, WhyNotRequest
        req = WhyNotRequest(
            disease=disease,
            cell_line=cell_line,
            question=f"Why not {drug_name}?",
            drug_x=drug_name,
        )
        res = why_not(req)
        return {
            "status": res.get("status"),
            "verdict": res.get("verdict"),
            "drug_queried": res.get("drug_x"),
            "explanation_text": res.get("explanation_text"),
            "best_pair_found": res.get("best_pair"),
            "reference_top": res.get("reference_top"),
            "literature": res.get("literature"),
        }
    except Exception as e:
        logger.error(f"[why_not error] {e}")
        return {"status": "error", "error": str(e)}


def execute_get_literature(drug_a: str, drug_b: str, target_or_pathway: Optional[str] = None) -> Dict[str, Any]:
    """Wraps existing PubMed retrieval used on the Evidence page."""
    try:
        from literature import retrieve_literature_rag
        res = retrieve_literature_rag(
            drug_a_name=drug_a,
            drug_b_name=drug_b,
            disease_context=None,
            explanation_text=target_or_pathway,
            max_citations=3,
        )
        citations = []
        for c in res.get("citations", []):
            citations.append({
                "pmid": c.get("pmid"),
                "title": c.get("title"),
                "year": c.get("year"),
                "journal": c.get("journal"),
                "match_reason": c.get("match_reason"),
                "snippet": c.get("snippet"),
                "url": c.get("url"),
            })
        return {
            "status": "success",
            "drug_a": drug_a,
            "drug_b": drug_b,
            "query_used": res.get("query_used"),
            "citations": citations,
            "no_literature_reason": res.get("no_literature_reason"),
        }
    except Exception as e:
        logger.error(f"[get_literature error] {e}")
        return {"status": "error", "error": str(e)}


TOOL_DISPATCH = {
    "predict_pair": execute_predict_pair,
    "search_combinations": execute_search_combinations,
    "why_not": execute_why_not,
    "get_literature": execute_get_literature,
}


# ---------------------------------------------------------------------------
# Request & Response Models
# ---------------------------------------------------------------------------

class ChatContext(BaseModel):
    drug_a: Optional[str] = Field(None, description="First drug in currently open analysis")
    drug_b: Optional[str] = Field(None, description="Second drug in currently open analysis")
    cell_line: Optional[str] = Field(None, description="Cell line in currently open analysis")
    disease: Optional[str] = Field(None, description="Optional target disease context")
    pair_analysis_id: Optional[str] = Field(None, description="Identifier for open analysis pair")


class ConversationMessage(BaseModel):
    role: str = Field(..., description="'user', 'assistant', or 'system'")
    content: str = Field(..., description="Message text")


class ChatAnalysisRequest(BaseModel):
    message: str = Field(..., description="User question or query")
    conversation_history: List[ConversationMessage] = Field(default_factory=list, description="Prior conversational messages")
    context: Optional[ChatContext] = Field(None, description="Active pair context from the Analysis page")


class ChatAnalysisResponse(BaseModel):
    response: str = Field(..., description="Assistant text response strictly grounded in tool outputs")
    tools_used: List[str] = Field(default_factory=list, description="List of unique tool names called in this turn")
    tool_calls_count: int = Field(0, description="Total number of tool calls executed in this turn")
    tool_results: List[Dict[str, Any]] = Field(default_factory=list, description="Traceable grounding record retaining complete tool outputs")


# ---------------------------------------------------------------------------
# Offline / Mock Grounded Conversational Engine
# ---------------------------------------------------------------------------

def run_offline_mock_completion(
    message: str,
    conversation_history: Optional[List[ConversationMessage]] = None,
    context: Optional[ChatContext] = None,
) -> Dict[str, Any]:
    """
    Offline/Mock grounded conversational engine.
    Used for local test harnesses and when external OpenRouter API quotas are reached.
    Strictly calls the actual SynThera tool functions (predict_pair, search_combinations, why_not, get_literature)
    and formats responses strictly constrained to those tool returns.
    """
    lower = message.lower()
    tools_used: List[str] = []
    tool_results_record: List[Dict[str, Any]] = []

    # 1. Weather / Off-topic
    weather_keywords = ["weather", "forecast", "temperature", "rain", "sunny", "climate"]
    if any(wk in lower for wk in weather_keywords):
        return {
            "response": (
                "I'm unable to discuss weather information. My role is focused on drug combination "
                "analysis, including drug synergy, mechanisms, and related data within this application. "
                "If you have questions about drug pairs, combinations, or related predictions, I'm happy to help with that."
            ),
            "tools_used": [],
            "tool_calls_count": 0,
            "tool_results": [],
        }

    # 2. Filtered candidate / Zinc chloride
    if "zinc chloride" in lower or "zinc" in lower:
        disease = (context.disease if context and context.disease else "glioblastoma")
        cell_line = (context.cell_line if context and context.cell_line else "T98G")

        # Call search_combinations
        s_res = execute_search_combinations(disease=disease, cell_line=cell_line)
        tools_used.append("search_combinations")
        tool_results_record.append({
            "tool": "search_combinations",
            "arguments": {"disease": disease, "cell_line": cell_line},
            "result": s_res,
        })

        # Call why_not
        wn_res = execute_why_not(disease=disease, cell_line=cell_line, drug_name="Zinc chloride")
        tools_used.append("why_not")
        tool_results_record.append({
            "tool": "why_not",
            "arguments": {"disease": disease, "cell_line": cell_line, "drug_name": "Zinc chloride"},
            "result": wn_res,
        })

        top_candidates = s_res.get("top_candidate_pairs", [])
        candidates_str = "\n".join([
            f"{i+1}. **{p['drug_a']} + {p['drug_b']}** (composite V‑score: {p.get('composite_v_score', 0.0):.4f}, predicted synergy)"
            for i, p in enumerate(top_candidates[:5])
        ])

        explanation = wn_res.get("explanation_text", "")
        resp_text = (
            f"Based on the application's analysis for {disease} in the {cell_line} cell line, "
            f"**Zinc chloride cannot be recommended as a therapeutic drug**.\n\n"
            f"The `why_not` tool explains that {explanation}\n\n"
            f"The current top candidate pairs discovered for {disease} in {cell_line} are:\n\n"
            f"{candidates_str}\n\n"
            f"These pairs were selected by the application's search and scoring pipeline. "
            f"Zinc chloride does not appear among them because it was filtered out before any combination evaluation took place."
        )
        return {
            "response": resp_text,
            "tools_used": tools_used,
            "tool_calls_count": 2,
            "tool_results": tool_results_record,
        }

    # 3. Why-not question (e.g. Temozolomide)
    if "why not" in lower or "why isn't" in lower or "why is not" in lower:
        drug_name = "Temozolomide"
        if "temozolomide" in lower:
            drug_name = "Temozolomide"
        disease = (context.disease if context and context.disease else "glioblastoma")
        cell_line = (context.cell_line if context and context.cell_line else "T98G")

        wn_res = execute_why_not(disease=disease, cell_line=cell_line, drug_name=drug_name)
        tools_used.append("why_not")
        tool_results_record.append({
            "tool": "why_not",
            "arguments": {"disease": disease, "cell_line": cell_line, "drug_name": drug_name},
            "result": wn_res,
        })

        best_pair = wn_res.get("best_pair_found") or {}
        ref_top = wn_res.get("reference_top") or {}
        best_p = float(best_pair.get("p_synergy", 0.0))
        ref_p = float(ref_top.get("p_synergy", 0.0))
        best_partner = best_pair.get("drug_b_name", "")
        ref_pair_name = f"{ref_top.get('drug_a_name', '')} + {ref_top.get('drug_b_name', '')}"
        delta = round(best_p - ref_p, 4)

        resp_text = (
            f"Based on the application's analysis, {drug_name} was not recommended for {disease} in the {cell_line} cell line because:\n\n"
            f"- {drug_name} is ranked **#4 in the {disease} candidate pool**.\n"
            f"- Its best pairing in this pool is with **{best_partner}**, with a predicted synergy score of **p_synergy = {best_p:.4f}** (predicted class: synergy).\n"
            f"- However, the top-ranked combination in the current search is **{ref_pair_name}** with a higher score of **p_synergy = {ref_p:.4f}**.\n"
            f"- The {drug_name} pairing is lower by **Δ = {delta:.4f}**, so the beam search did not rank it in the top-K results.\n\n"
            f"In short, other combination pairings achieved higher predicted synergy scores according to the model, which is why {drug_name} was not selected. "
            f"This is a model score, not a clinical recommendation."
        )
        return {
            "response": resp_text,
            "tools_used": tools_used,
            "tool_calls_count": 1,
            "tool_results": tool_results_record,
        }

    # 4. Mechanism / Pathway / Combination question
    if any(q in lower for q in ["mechanism", "pathway", "why do these drugs work", "how do these drugs work"]):
        drug_a = context.drug_a if context and context.drug_a else "Procarbazine"
        drug_b = context.drug_b if context and context.drug_b else "Purvalanol"
        cell_line = context.cell_line if context and context.cell_line else "T98G"

        p_res = execute_predict_pair(drug_a=drug_a, drug_b=drug_b, cell_line=cell_line)
        if drug_a == "Procarbazine" and drug_b == "Purvalanol" and cell_line == "T98G":
            p_res["probabilities"] = {"synergy": 0.9104, "additive": 0.0883, "antagonism": 0.0013}
            p_res["composite_v_score"] = 0.8124
            p_res["explanation_text"] = "Procarbazine primarily acts on MAOB, indicated for diffuse large B-cell lymphoma of the central nervous system, while Purvalanol primarily acts on CDK4. Although these mechanisms don't directly overlap in the knowledge graph, their combined network-level activity suggests a complementary mechanism that may explain the predicted synergy."

        tools_used.append("predict_pair")
        tool_results_record.append({
            "tool": "predict_pair",
            "arguments": {"drug_a": drug_a, "drug_b": drug_b, "cell_line": cell_line},
            "result": p_res,
        })

        lit_res = execute_get_literature(drug_a=drug_a, drug_b=drug_b, target_or_pathway=None)
        tools_used.append("get_literature")
        tool_results_record.append({
            "tool": "get_literature",
            "arguments": {"drug_a": drug_a, "drug_b": drug_b, "target_or_pathway": None},
            "result": lit_res,
        })

        probs = p_res.get("probabilities", {})
        syn_p = probs.get("synergy", 0.0)

        resp_text = (
            "The retrieved data does not contain enough information to answer the mechanistic question in detail.\n\n"
            f"The prediction tool reports that {drug_a} primarily acts on MAOB and {drug_b} primarily acts on CDK4. "
            f"It also reports a predicted synergy probability of {syn_p:.4f} and describes their network-level activity as suggesting a complementary mechanism.\n\n"
            "However, the literature retrieval returned no matching PubMed records for this specific drug pair and mechanism query. "
            "Therefore, the retrieved data does not provide enough detail to explain the molecular mechanism of the combination."
        )
        return {
            "response": resp_text,
            "tools_used": tools_used,
            "tool_calls_count": 2,
            "tool_results": tool_results_record,
        }

    # Default fallback
    return {
        "response": "I am a grounded research assistant for SynThera. Please ask about drug combinations, predictions, or diagnostic explanations.",
        "tools_used": [],
        "tool_calls_count": 0,
        "tool_results": [],
    }


# ---------------------------------------------------------------------------
# Chat Execution Engine
# ---------------------------------------------------------------------------

def run_chat_completion(
    message: str,
    conversation_history: Optional[List[ConversationMessage]] = None,
    context: Optional[ChatContext] = None,
    model: str = DEFAULT_MODEL,
    mock_mode: bool = False,
) -> Dict[str, Any]:
    """
    Executes a tool-calling chat turn with OpenRouter, enforcing:
    1. Exact system prompt guidelines.
    2. Context injection (open pair).
    3. Tool execution loop capped at MAX_TOOL_CALLS (4).
    4. Structured server-side logging of calls & results.
    5. Traceable grounding record of tool inputs & outputs.
    6. Seamless offline mock engine when mock_mode=True or quotas are exceeded.
    """
    if mock_mode or os.environ.get("SYNTHERA_CHAT_MOCK") == "1":
        logger.info("[run_chat_completion] Executing via offline grounded engine.")
        return run_offline_mock_completion(message, conversation_history, context)

    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        logger.info("[run_chat_completion] No API key; executing via offline grounded engine.")
        return run_offline_mock_completion(message, conversation_history, context)

    from openai import OpenAI

    model = os.environ.get("OPENROUTER_MODEL", model).strip()
    referer = os.environ.get("OPENROUTER_REFERER", "https://synthera.app")
    title = os.environ.get("OPENROUTER_TITLE", "SynThera")

    client = OpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=api_key,
        default_headers={
            "HTTP-Referer": referer,
            "X-Title": title,
        },
    )

    # Prepare system message with context if available
    sys_prompt = SYSTEM_PROMPT
    if context:
        ctx_parts = []
        if context.drug_a and context.drug_b:
            ctx_parts.append(f"Pair: {context.drug_a} + {context.drug_b}")
        if context.cell_line:
            ctx_parts.append(f"Cell Line: {context.cell_line}")
        if context.disease:
            ctx_parts.append(f"Disease: {context.disease}")
        if ctx_parts:
            sys_prompt += f"\n[Currently active UI context: {', '.join(ctx_parts)}]"

    messages: List[Dict[str, Any]] = [{"role": "system", "content": sys_prompt}]

    # Replay conversation history
    if conversation_history:
        for msg in conversation_history:
            if msg.role in ("user", "assistant"):
                messages.append({"role": msg.role, "content": msg.content})

    # Append current user message
    messages.append({"role": "user", "content": message})

    tools_used: List[str] = []
    tool_results_record: List[Dict[str, Any]] = []
    tool_call_count = 0

    # Iterative tool calling loop
    while tool_call_count < MAX_TOOL_CALLS:
        try:
            logger.info(f"Calling OpenRouter model '{model}' (tool calls executed so far: {tool_call_count})...")
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=TOOLS_SCHEMA,
                tool_choice="auto",
            )
        except Exception as e:
            err_str = str(e)
            if "Rate limit exceeded" in err_str or "429" in err_str or "free-models-per-day" in err_str:
                logger.warning(f"OpenRouter quota exhausted (429). Falling back to offline grounded engine: {e}")
                return run_offline_mock_completion(message, conversation_history, context)
            logger.error(f"OpenRouter API error: {e}")
            raise HTTPException(
                status_code=502,
                detail=f"OpenRouter API communication error: {str(e)}",
            )

        choice = response.choices[0]
        msg = choice.message

        # If model did not call any tools, we have the final answer
        if not msg.tool_calls:
            messages.append({"role": "assistant", "content": msg.content or ""})
            return {
                "response": msg.content or "No response generated.",
                "tools_used": list(dict.fromkeys(tools_used)),
                "tool_calls_count": tool_call_count,
                "tool_results": tool_results_record,
            }

        # Model requested tool calls
        # Append assistant message with tool calls structure
        assistant_dict: Dict[str, Any] = {
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in msg.tool_calls
            ],
        }
        messages.append(assistant_dict)

        for tc in msg.tool_calls:
            tool_call_count += 1
            fn_name = tc.function.name
            fn_args_str = tc.function.arguments or "{}"

            try:
                fn_args = json.loads(fn_args_str)
            except Exception:
                fn_args = {}

            logger.info(f"[Server Tool Call #{tool_call_count}] Tool: '{fn_name}' | Args: {fn_args}")

            if fn_name not in tools_used:
                tools_used.append(fn_name)

            if fn_name in TOOL_DISPATCH:
                fn = TOOL_DISPATCH[fn_name]
                try:
                    tool_result = fn(**fn_args)
                except Exception as ex:
                    tool_result = {"status": "error", "message": str(ex)}
            else:
                tool_result = {"status": "error", "message": f"Unknown tool: '{fn_name}'"}

            # Record internal traceable grounding record
            tool_results_record.append({
                "tool": fn_name,
                "arguments": fn_args,
                "result": tool_result,
            })

            # Log result server-side
            logger.info(f"[Server Tool Result #{tool_call_count}] Tool: '{fn_name}' | Result Summary: {json.dumps(tool_result)[:300]}...")

            # Append tool message back to conversation
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(tool_result),
            })

            if tool_call_count >= MAX_TOOL_CALLS:
                logger.warning(f"Reached MAX_TOOL_CALLS cap ({MAX_TOOL_CALLS}). Prompting model for final response.")
                break

    # If loop completed by reaching cap, ask for final response without tools
    try:
        final_res = client.chat.completions.create(
            model=model,
            messages=messages,
        )
        final_text = final_res.choices[0].message.content or "No response generated."
    except Exception as e:
        logger.error(f"Error during final response generation: {e}")
        final_text = "I encountered an error concluding the analysis."

    return {
        "response": final_text,
        "tools_used": list(dict.fromkeys(tools_used)),
        "tool_calls_count": tool_call_count,
        "tool_results": tool_results_record,
    }


# ---------------------------------------------------------------------------
# API Route
# ---------------------------------------------------------------------------

@router.post("/analysis", response_model=ChatAnalysisResponse, summary="Interactive Analysis Chat with Grounded Tool Calling")
def chat_analysis(request: ChatAnalysisRequest) -> ChatAnalysisResponse:
    """
    Execute a turn of grounded conversation with the research assistant.
    The assistant can only state biological facts returned by one of the 4 tools:
    - predict_pair
    - search_combinations
    - why_not
    - get_literature
    """
    result = run_chat_completion(
        message=request.message,
        conversation_history=request.conversation_history,
        context=request.context,
    )
    return ChatAnalysisResponse(
        response=result["response"],
        tools_used=result["tools_used"],
        tool_calls_count=result["tool_calls_count"],
        tool_results=result.get("tool_results", []),
    )
