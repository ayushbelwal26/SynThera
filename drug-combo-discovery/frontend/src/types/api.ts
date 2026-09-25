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
  pmid: string;
  title: string;
  year: string;
  journal?: string;
  first_author?: string;
  snippet?: string;
  url: string;
  match_reason?: string;
  evidence_type?: 'combination' | 'single_drug' | 'mechanistic_context' | string;
  relation_context?: string;
  summary?: string;
}

export interface LiteratureResult {
  citations: LiteratureCitation[];
  query_used: string;
  retrieval_method: string;
  error?: string | null;
  no_literature_reason?: string | null;
}

export interface FaithfulnessResult {
  original_score: number;
  original_class: string;
  ablated_score: number | null;
  ablated_class: string | null;
  sufficiency: number | null;
  necessity: number | null;
  explanation_faithful: boolean;
  rationale: string;
  k_edges_ablated: number;
  error?: string | null;
}

export interface SourceCoverage {
  sider: boolean;
  primekg_ddi: boolean;
  drugbank_warnings: boolean;
}

export interface RankingWeights {
  w_synergy: number;
  w_toxicity: number;
  w_redundancy: number;
  alpha_ddi?: number;
  alpha_se?: number;
}

export interface ToxicityBreakdown {
  has_known_ddi: boolean | null;
  side_effect_overlap: number | null;
  shared_side_effects_count?: number | null;
  top_shared_side_effects?: string[] | null;
  ddi_risk: number;
  se_risk: number;
  unknown_risk_applied: boolean;
  source_coverage: SourceCoverage;
  redundancy_available: boolean;
  redundancy_note?: string | null;
}

export interface RankingBlock {
  v_score: number;
  score: number;             // same as v_score, kept for back-compat
  p_synergy: number;
  toxicity_penalty: number;
  redundancy_penalty: number | null;
  weights: RankingWeights;
  breakdown: ToxicityBreakdown;
}

export interface PredictionResult {
  drug_a: string;
  drug_a_name: string;
  drug_b: string;
  drug_b_name: string;
  cell_line: string;
  predicted_class: 'synergy' | 'additive' | 'antagonism' | string;
  score: number;             // calibrated p_synergy or composite v_score depending on search/predict
  p_antagonism: number;
  p_additive: number;
  p_synergy: number;
  top_edges: ExplanationEdge[];
  explanation_text: string;
  supporting_literature: LiteratureCitation[];
  literature?: LiteratureResult | null;
  
  // Real faithfulness metrics (measured via in-silico ablation on the GNN)
  faithfulness?: FaithfulnessResult | null;
  necessity_delta_pct?: number;        // probability drop when top edges are removed
  sufficiency_retained_pct?: number;   // probability retained when ONLY top edges are kept
  sufficiency_class_preserved?: boolean;
  sufficiency_prob?: number;
  
  // Phase B Multi-Objective Value Function & Toxicity Ranking
  ranking?: RankingBlock | null;
  v_score?: number;

  rank?: number;
  search_method?: string;
  mcts_visits?: number;
  evidence_tier?: string;
  direct_disease_target?: boolean;

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
  search_method?: 'beam' | 'greedy' | 'mcts';
  beam_width?: number;
  n_simulations?: number;
  mcts_c?: number;
  time_budget_sec?: number;
  inspect_top_k?: number;
}

export interface SearchResponse {
  disease: string;
  cell_line: string;
  search_method?: string;
  beam_width?: number;
  candidate_pool_size: number;
  max_candidates_scored?: number;
  n_simulations?: number;
  n_pairs_scored?: number;
  truncated?: boolean;
  weights?: RankingWeights;
  results: PredictionResult[];
}


export interface WhyNotRequest {
  disease: string;
  cell_line: string;
  question: string;
  drug_x?: string;
  search_method?: 'beam' | 'greedy' | 'mcts';
}

export interface WhyNotScoredPair {
  drug_a: string;
  drug_a_name: string;
  drug_b: string;
  drug_b_name: string;
  score: number;
  p_synergy: number;
  predicted_class: string;
  cell_line: string;
}

export interface WhyNotResponse {
  intent?: string;
  drug_x?: {
    id: string | null;
    name: string;
  };
  status?: 'scored' | 'filtered' | 'unknown_drug' | 'unsupported_question';
  best_pair?: WhyNotScoredPair | null;
  reference_top?: WhyNotScoredPair | null;
  verdict?: 'competitive' | 'weaker' | 'filtered' | 'not_in_graph';
  explanation_text?: string;
  literature?: {
    citations: LiteratureCitation[];
    query_used?: string;
    retrieval_method?: string;
  } | null;
  faithfulness?: null;
  error?: string;
  hint?: string;
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

export interface ChatAnalysisRequest {
  message: string;
  conversation_history?: Array<{ role: 'user' | 'assistant' | 'system'; content: string }>;
  context?: {
    drug_a?: string;
    drug_b?: string;
    cell_line?: string;
    disease?: string;
    pair_analysis_id?: string;
  };
}

export interface ChatAnalysisResponse {
  response: string;
  tools_used: string[];
  tool_calls_count: number;
  tool_results?: Array<Record<string, unknown>>;
}

