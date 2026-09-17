/**
 * Synthera API & Scientific Domain Types
 * Matches the FastAPI backend contract and scientific domain model.
 */

export interface HealthResponse {
  status: string;
  model_loaded: boolean;
  device: string;
  total_drugs: number;
  total_cell_lines: number;
  cache_entries: number;
}

export interface Drug {
  id: string;   // DrugBank ID e.g. "DB00853"
  name: string; // Generic name e.g. "Temozolomide"
}

export interface ExplanationEdge {
  source: string;
  source_type?: 'drug' | 'protein' | 'disease' | 'pathway' | string;
  relation: string;
  target: string;
  target_type?: 'drug' | 'protein' | 'disease' | 'pathway' | string;
  importance: number;
  [key: string]: unknown;
}

export interface LiteratureCitation {
  title: string;
  year: string;
  first_author: string;
  pmid: string;
  url: string;
  relation_context?: string;
  summary?: string;
}

export interface PredictionResult {
  drug_a: string;
  drug_a_name: string;
  drug_b: string;
  drug_b_name: string;
  cell_line: string;
  predicted_class: 'synergy' | 'additive' | 'antagonism' | string;
  score: number;             // calibrated p_synergy
  p_antagonism: number;
  p_additive: number;
  p_synergy: number;
  top_edges: ExplanationEdge[];
  explanation_text: string;
  supporting_literature: LiteratureCitation[];
  
  // Real faithfulness metrics (measured via in-silico ablation on the GNN)
  necessity_delta_pct?: number;        // probability drop when top edges are removed
  sufficiency_retained_pct?: number;   // probability retained when ONLY top edges are kept
  sufficiency_class_preserved?: boolean;
  sufficiency_prob?: number;
  
  cached?: boolean;
  timestamp?: string;
}

export interface PredictRequest {
  drug_a: string;
  drug_b: string;
  cell_line: string;
  disease?: string;
}

export interface SearchRequest {
  disease: string;
  cell_line: string;
  max_candidates?: number;
  top_k?: number;
}

export interface SearchResponse {
  disease: string;
  cell_line: string;
  candidate_pool_size: number;
  results: PredictionResult[];
}

export interface CellLineRelevanceStatus {
  cellLines: string[];
  isFiltered: boolean;
  filteringNote?: string;
}

export interface FaithfulnessStatus {
  status: 'verified' | 'requires_verification' | 'pending' | 'unavailable';
  necessityDelta?: number;
  sufficiencyRetained?: number;
  classPreserved?: boolean;
  verdictMessage: string;
}

export type EntityType = 'drug' | 'protein' | 'gene' | 'pathway' | 'disease';

export interface KGNode {
  id: string;
  name: string;
  type: EntityType;
  description?: string;
  degree?: number;
}

export interface KGEdge {
  id: string;
  source: string;
  target: string;
  relation: string;
  importance?: number;
  [key: string]: unknown;
}

export interface KGGraph {
  nodes: KGNode[];
  edges: KGEdge[];
}
