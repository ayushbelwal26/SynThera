/**
 * SynThera API Client
 *
 * Talks to the FastAPI backend configured via VITE_API_BASE_URL.
 *
 * Endpoints:
 * - GET  /health              : Backend health, device, model loading status.
 * - GET  /drugs               : PrimeKG compound catalog.
 * - GET  /cell-lines          : Benchmark cancer cell line panel.
 * - GET  /cell-lines?disease= : Disease-relevance filtering via cell_line_mapping.py.
 * - POST /predict             : HGT inference + attribution + literature + faithfulness.
 * - POST /search              : Indication search — candidate retrieval, scoring, ranking.
 * - POST /why-not             : Why-not diagnostic for a missing / outranked drug.
 * - POST /chat/analysis       : Grounded tool-calling research assistant.
 */

import type {
  HealthResponse,
  Drug,
  PredictRequest,
  PredictionResult,
  SearchRequest,
  SearchResponse,
  WhyNotRequest,
  WhyNotResponse,
  CellLineRelevanceStatus,
  FaithfulnessStatus,
  ChatAnalysisRequest,
  ChatAnalysisResponse,
} from "../types/api";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

class ApiError extends Error {
  statusCode?: number;
  constructor(message: string, statusCode?: number) {
    super(message);
    this.name = "ApiError";
    this.statusCode = statusCode;
  }
}

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const timeoutMs = options?.method === "POST" ? 60000 : 15000;
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      ...options,
      signal: options?.signal || controller.signal,
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        ...options?.headers,
      },
    });
    clearTimeout(id);

    if (!response.ok) {
      let detail = `HTTP ${response.status}: ${response.statusText}`;
      try {
        const errorBody = await response.json();
        if (errorBody.detail) {
          detail =
            typeof errorBody.detail === "string"
              ? errorBody.detail
              : JSON.stringify(errorBody.detail);
        }
      } catch {
        // keep default detail
      }
      throw new ApiError(detail, response.status);
    }

    return (await response.json()) as T;
  } catch (err: unknown) {
    clearTimeout(id);
    if (err instanceof ApiError) throw err;
    if ((err as Error).name === "AbortError") {
      throw new ApiError(
        `Request timeout after ${timeoutMs / 1000}s. The service may be under high load.`,
        408,
      );
    }
    throw new ApiError(
      `Synthera could not reach the analysis service at ${API_BASE}. Please verify that the backend is operational.`,
      0,
    );
  }
}

export async function checkHealth(signal?: AbortSignal): Promise<HealthResponse> {
  return fetchJson<HealthResponse>(`${API_BASE}/health`, { signal });
}

export async function fetchDrugs(signal?: AbortSignal): Promise<Drug[]> {
  return fetchJson<Drug[]>(`${API_BASE}/drugs`, { signal });
}

export async function predictCombination(
  request: PredictRequest,
  signal?: AbortSignal,
): Promise<PredictionResult> {
  const payload: Record<string, unknown> = {
    drug_a: request.drug_a.trim(),
    drug_b: request.drug_b.trim(),
    cell_line: request.cell_line.trim(),
  };
  if (request.disease?.trim()) {
    payload.disease = request.disease.trim();
  }

  const result = await fetchJson<PredictionResult>(`${API_BASE}/predict`, {
    method: "POST",
    body: JSON.stringify(payload),
    signal,
  });
  return { ...result, timestamp: new Date().toISOString() };
}

export async function searchCombinations(
  request: SearchRequest,
  signal?: AbortSignal,
): Promise<SearchResponse> {
  const payload = {
    disease: request.disease.trim(),
    cell_line: request.cell_line.trim(),
    max_candidates: request.max_candidates ?? 15,
    top_k: request.top_k ?? 5,
    search_method: request.search_method ?? "beam",
    beam_width: request.beam_width ?? 5,
    n_simulations: request.n_simulations ?? 50,
    mcts_c: request.mcts_c ?? 1.414,
    time_budget_sec: request.time_budget_sec ?? 15.0,
    inspect_top_k: request.inspect_top_k ?? 0,
  };

  return fetchJson<SearchResponse>(`${API_BASE}/search`, {
    method: "POST",
    body: JSON.stringify(payload),
    signal,
  });
}

export async function askWhyNot(
  request: WhyNotRequest,
  signal?: AbortSignal,
): Promise<WhyNotResponse> {
  return fetchJson<WhyNotResponse>(`${API_BASE}/why-not`, {
    method: "POST",
    body: JSON.stringify(request),
    signal,
  });
}

export async function fetchCellLines(
  disease?: string,
  signal?: AbortSignal,
): Promise<CellLineRelevanceStatus> {
  const url =
    disease && disease.trim()
      ? `${API_BASE}/cell-lines?disease=${encodeURIComponent(disease.trim())}`
      : `${API_BASE}/cell-lines`;

  try {
    const lines = await fetchJson<string[]>(url, { signal });
    if (lines.length > 0 && lines.length < 80) {
      return { cellLines: lines, isFiltered: true };
    }
    if (lines.length === 0 && disease?.trim()) {
      const allLines = await fetchJson<string[]>(`${API_BASE}/cell-lines`, {
        signal,
      });
      return {
        cellLines: allLines,
        isFiltered: false,
        filteringNote: `No cell lines specifically mapped to "${disease}" — displaying all ${allLines.length} panel lines.`,
      };
    }
    return { cellLines: lines, isFiltered: false };
  } catch {
    const lines = await fetchJson<string[]>(`${API_BASE}/cell-lines`, {
      signal,
    });
    return {
      cellLines: lines,
      isFiltered: false,
      filteringNote: disease
        ? `Relevance filtering unavailable — displaying all ${lines.length} panel cell lines.`
        : undefined,
    };
  }
}

export function getFaithfulnessStatus(
  prediction: PredictionResult,
): FaithfulnessStatus {
  if (
    typeof prediction.necessity_delta_pct === "number" &&
    typeof prediction.sufficiency_retained_pct === "number"
  ) {
    const nec = prediction.necessity_delta_pct;
    const suf = prediction.sufficiency_retained_pct;
    const preserved = Boolean(prediction.sufficiency_class_preserved);
    const isVerified = preserved && suf >= 70.0;

    return {
      status: isVerified ? "verified" : "requires_verification",
      necessityDelta: nec,
      sufficiencyRetained: suf,
      classPreserved: preserved,
      verdictMessage: isVerified
        ? "Verified explanation: Subgraph is sufficient (retention >= 70%) to preserve predicted interaction class."
        : "Explanation requires further verification: Subgraph does not satisfy the sufficiency criterion (retention < 70% or class flipped).",
    };
  }

  return {
    status: "pending",
    verdictMessage:
      "Faithfulness ablation not yet evaluated — inspect combination for full in-silico verification.",
  };
}

export async function sendAnalysisChatMessage(
  request: ChatAnalysisRequest,
): Promise<ChatAnalysisResponse> {
  return fetchJson<ChatAnalysisResponse>(`${API_BASE}/chat/analysis`, {
    method: "POST",
    body: JSON.stringify(request),
  });
}
