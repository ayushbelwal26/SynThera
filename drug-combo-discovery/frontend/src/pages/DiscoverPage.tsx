import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeftRight, Play, ArrowRight, Clock } from "lucide-react";
import { useApp } from "../services/AppContext";
import { predictCombination, searchCombinations } from "../services/api";
import type { Drug, PredictionResult, SearchResponse } from "../types/api";
import { DrugSelectInput } from "../components/discover/DrugSelectInput";
import { CellLineDropdown } from "../components/discover/CellLineDropdown";
import { BenchmarkPresets } from "../components/discover/BenchmarkPresets";
import type { BenchmarkPreset } from "../components/discover/BenchmarkPresets";
import { DiscoveryMode } from "../components/discover/DiscoveryMode";
import { WhyNotSection } from "../components/discover/WhyNotSection";
import { LoadingStages } from "../components/common/LoadingStages";
import { AlertNotice } from "../components/common/AlertNotice";
import { Badge } from "../components/common/Badge";
import { ToxicityBadge } from "../components/common/ToxicityBadge";

export const DiscoverPage: React.FC = () => {
  const navigate = useNavigate();
  const { drugs, cellLineStatus, setCurrentPrediction, addRecentPrediction } =
    useApp();

  const [activeTab, setActiveTab] = useState<"pair" | "search">("pair");

  // Pair evaluation state
  const [drugA, setDrugA] = useState<Drug | null>(null);
  const [drugB, setDrugB] = useState<Drug | null>(null);
  const [cellLine, setCellLine] = useState<string>("T98G");
  const [diseaseContext, setDiseaseContext] = useState<string>("");

  // Status & loading
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Discovery search results state
  const [searchDisease, setSearchDisease] = useState<string>("glioblastoma");
  const [searchResults, setSearchResults] = useState<SearchResponse | null>(
    null,
  );
  const [inspectingPairIdx, setInspectingPairIdx] = useState<number | null>(
    null,
  );

  const handleSwapDrugs = () => {
    const temp = drugA;
    setDrugA(drugB);
    setDrugB(temp);
  };

  const handleSelectPreset = (preset: BenchmarkPreset) => {
    setDrugA(preset.drugA);
    setDrugB(preset.drugB);
    setCellLine(preset.cellLine);
    setDiseaseContext(preset.indication);
    setErrorMsg(null);
  };

  const handleAnalyzePair = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!drugA || !drugB || !cellLine) {
      setErrorMsg(
        "Please select both Compound A and Compound B to execute analysis.",
      );
      return;
    }
    if (drugA.id === drugB.id) {
      setErrorMsg(
        "Please select two distinct compounds for combination analysis.",
      );
      return;
    }

    setIsLoading(true);
    setErrorMsg(null);

    try {
      const result = await predictCombination({
        drug_a: drugA.id,
        drug_b: drugB.id,
        cell_line: cellLine,
        disease: diseaseContext.trim() || undefined,
      });

      setCurrentPrediction(result);
      addRecentPrediction(result);
      navigate("/analysis");
    } catch (err: any) {
      setErrorMsg(
        err.message || "Analysis service error occurred during prediction.",
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleRunSearch = async (
    disease: string,
    targetCellLine: string,
    maxCandidates: number,
    topK: number,
    searchMethod: "beam" | "greedy" | "mcts" = "beam",
    nSimulations: number = 50,
    mctsC: number = 1.414,
  ) => {
    setSearchDisease(disease);
    setIsLoading(true);
    setErrorMsg(null);
    setSearchResults(null);

    try {
      const res = await searchCombinations({
        disease,
        cell_line: targetCellLine,
        max_candidates: maxCandidates,
        top_k: topK,
        search_method: searchMethod,
        n_simulations: nSimulations,
        mcts_c: mctsC,
      });
      setSearchResults(res);
    } catch (err: any) {
      setErrorMsg(
        err.message ||
          "Combination discovery failed. Please verify the indication name.",
      );
    } finally {
      setIsLoading(false);
    }
  };

  // When user clicks "Inspect Analysis" on a search result:
  // Call /predict to get full faithfulness data, then navigate to /analysis.
  const handleSelectDiscoveredPair = async (
    pair: PredictionResult,
    idx: number,
  ) => {
    setInspectingPairIdx(idx);
    try {
      const full = await predictCombination({
        drug_a: pair.drug_a,
        drug_b: pair.drug_b,
        cell_line: pair.cell_line,
      });
      setCurrentPrediction(full);
      addRecentPrediction(full);
      navigate("/analysis");
    } catch {
      // Fall back to search result without faithfulness if /predict fails
      setCurrentPrediction(pair);
      addRecentPrediction(pair);
      navigate("/analysis");
    } finally {
      setInspectingPairIdx(null);
    }
  };

  const handleInspectWhyNotPair = async (
    drugAId: string,
    drugBId: string,
    cl: string,
  ) => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const full = await predictCombination({
        drug_a: drugAId,
        drug_b: drugBId,
        cell_line: cl,
      });
      setCurrentPrediction(full);
      addRecentPrediction(full);
      navigate("/analysis");
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to inspect combination.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-5">
      {/* Hero & Instrument Purpose */}
      <div className="border-b border-[#E5E2DC] pb-4">
        <h2 className="font-editorial text-2xl text-[#1C2421]">
          Combination Analysis & Discovery
        </h2>
        <p className="text-sm text-[#5A635E] mt-1 max-w-3xl leading-normal">
          Screen multi-drug combinations against heterogeneous knowledge graph
          topologies. Predict synergy or antagonism with calibrated confidence
          and extract load-bearing mechanistic pathways.
        </p>
      </div>

      {/* Mode Selector Tabs */}
      <div className="flex border-b border-[#E5E2DC] gap-4 overflow-x-auto">
        <button
          type="button"
          onClick={() => {
            setActiveTab("pair");
            setErrorMsg(null);
          }}
          className={`pb-3 text-sm font-semibold border-b-2 transition-all cursor-pointer whitespace-nowrap ${
            activeTab === "pair"
              ? "border-[#2F6B5E] text-[#2F6B5E]"
              : "border-transparent text-[#6B746F] hover:text-[#1C2421]"
          }`}
        >
          Compound Pair Analysis (Targeted)
        </button>
        <button
          type="button"
          onClick={() => {
            setActiveTab("search");
            setErrorMsg(null);
          }}
          className={`pb-3 text-sm font-semibold border-b-2 transition-all cursor-pointer whitespace-nowrap ${
            activeTab === "search"
              ? "border-[#2F6B5E] text-[#2F6B5E]"
              : "border-transparent text-[#6B746F] hover:text-[#1C2421]"
          }`}
        >
          Unbiased Indication Search (Discovery)
        </button>
      </div>

      {errorMsg && (
        <AlertNotice type="error" title="Analysis Notice">
          {errorMsg}
        </AlertNotice>
      )}

      {/* Loading Stage View */}
      {isLoading && (
        <div className="py-6">
          <LoadingStages
            title={
              activeTab === "pair"
                ? "Evaluating Drug Combination"
                : "Discovering Candidate Combinations"
            }
            subtitle={
              activeTab === "pair"
                ? `Running inference for ${drugA?.name || "Drug A"} × ${drugB?.name || "Drug B"} @ ${cellLine}`
                : "Traversing PrimeKG indication neighbors and ranking candidate combinations"
            }
          />
        </div>
      )}

      {/* Tab 1: Targeted Pair Evaluation */}
      {!isLoading && activeTab === "pair" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 space-y-4">
            <form
              onSubmit={handleAnalyzePair}
              className="syn-card rounded-lg p-6 space-y-5"
            >
              <div className="grid grid-cols-1 sm:grid-cols-[1fr_auto_1fr] items-end gap-3">
                <DrugSelectInput
                  label="Compound A"
                  selectedDrug={drugA}
                  onSelect={setDrugA}
                  drugs={drugs}
                  placeholder="Select or search Compound A..."
                />

                <div className="flex justify-center pb-1">
                  <button
                    type="button"
                    onClick={handleSwapDrugs}
                    disabled={!drugA && !drugB}
                    className="p-2 border border-[#D8D5CE] rounded hover:bg-[#EEEBE5] text-[#6B746F] hover:text-[#1C2421] transition-colors disabled:opacity-40"
                    title="Swap Compound A and Compound B"
                  >
                    <ArrowLeftRight className="w-4 h-4" />
                  </button>
                </div>

                <DrugSelectInput
                  label="Compound B"
                  selectedDrug={drugB}
                  onSelect={setDrugB}
                  drugs={drugs}
                  placeholder="Select or search Compound B..."
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
                <CellLineDropdown
                  status={cellLineStatus}
                  selectedCellLine={cellLine}
                  onSelect={setCellLine}
                />

                <div>
                  <label className="block text-xs font-semibold text-[#3D4742] uppercase tracking-wide mb-1.5">
                    Indication Context (Optional)
                  </label>
                  <input
                    type="text"
                    value={diseaseContext}
                    onChange={(e) => setDiseaseContext(e.target.value)}
                    placeholder="e.g. glioblastoma, breast cancer..."
                    className="w-full bg-[#FFFEFB] border border-[#D8D5CE] rounded px-3 py-2 text-sm text-[#1C2421] focus:outline-none focus:ring-1 focus:ring-[#2F6B5E]"
                  />
                </div>
              </div>

              <div className="pt-2 flex justify-end">
                <button
                  type="submit"
                  disabled={!drugA || !drugB || isLoading}
                  className="px-6 py-2.5 bg-[#2F6B5E] hover:bg-[#25564B] disabled:opacity-50 text-[#FFFEFB] rounded font-semibold text-sm shadow-xs flex items-center gap-2 cursor-pointer transition-colors"
                >
                  <Play className="w-4 h-4 fill-current" />
                  Run Targeted Inference
                </button>
              </div>
            </form>

            {/* Presets Panel */}
            <BenchmarkPresets onSelect={handleSelectPreset} />
          </div>

          {/* Model Specification Info Card */}
          <div className="space-y-4">
            <div className="syn-card rounded-lg p-4 space-y-3 font-mono text-xs">
              <h3 className="font-sans font-bold text-sm text-[#1C2421] pb-2 border-b border-[#E5E2DC]">
                Model Pipeline Specifications
              </h3>
              <div className="space-y-2">
                <div className="flex justify-between py-1.5 border-b border-[#EEEBE5]">
                  <span className="text-[#6B746F]">Architecture:</span>
                  <span className="font-semibold text-[#1C2421]">
                    HGT (Heterogeneous GNN)
                  </span>
                </div>
                <div className="flex justify-between py-1.5 border-b border-[#EEEBE5]">
                  <span className="text-[#6B746F]">Knowledge Base:</span>
                  <span className="font-semibold text-[#1C2421]">
                    PrimeKG (Multimodal)
                  </span>
                </div>
                <div className="flex justify-between py-1.5 border-b border-[#EEEBE5]">
                  <span className="text-[#6B746F]">Calibration:</span>
                  <span className="font-semibold text-[#1C2421]">
                    Temperature Scaling (ECE)
                  </span>
                </div>
                <div className="flex justify-between py-1.5 border-b border-[#EEEBE5]">
                  <span className="text-[#6B746F]">Explanation Engine:</span>
                  <span className="font-semibold text-[#2F6B5E]">
                    Gradient Edge Saliency
                  </span>
                </div>
                <div className="flex justify-between py-1.5 border-b border-[#EEEBE5]">
                  <span className="text-[#6B746F]">Verification:</span>
                  <span className="font-semibold text-[#3D7A6C]">
                    Dual Faithfulness Ablation
                  </span>
                </div>
                <div className="flex justify-between py-1.5">
                  <span className="text-[#6B746F]">Literature Link:</span>
                  <span className="font-semibold text-[#9A712F]">
                    NCBI PubMed E-Utilities
                  </span>
                </div>
              </div>
            </div>

            <div className="bg-[#F3F1EC] border border-[#E5E2DC] rounded-lg p-4 text-xs text-[#6B746F] leading-normal">
              <span className="font-semibold text-[#1C2421] block mb-1">
                Scientific Integrity Guarantee:
              </span>
              Predictions, probabilities, and attribution graphs represent live
              biocomputational evaluations. No simulated or mock data is
              generated.
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Discovery Search Mode */}
      {!isLoading && activeTab === "search" && (
        <div className="space-y-4">
          <div className="syn-card rounded-lg p-6">
            <DiscoveryMode
              cellLineStatus={cellLineStatus}
              selectedCellLine={cellLine}
              onSelectCellLine={setCellLine}
              onRunSearch={handleRunSearch}
              isLoading={isLoading}
            />
          </div>

          {/* Discovery Results Table */}
          {searchResults && (
            <div className="syn-card rounded-lg p-6 space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-[#E5E2DC] pb-3 gap-2">
                <div>
                  <h3 className="text-lg font-semibold text-[#1C2421]">
                    Ranked Discovery Results for '{searchResults.disease}'
                  </h3>
                  <p className="text-xs text-[#6B746F] font-mono mt-0.5">
                    Context: {searchResults.cell_line} &bull; Candidate Pool:{" "}
                    {searchResults.candidate_pool_size} compounds
                    {searchResults.max_candidates_scored
                      ? `• Scored: ${searchResults.max_candidates_scored} pairs`
                      : ""}
                  </p>
                </div>
                <div className="flex items-center gap-2 flex-wrap">
                  {searchResults.search_method && (
                    <span className="text-xs font-mono text-[#2F6B5E] bg-[#E8F0ED] border border-[#B5CFC6] px-2.5 py-1 rounded font-semibold">
                      {searchResults.search_method === "mcts"
                        ? `MCTS (${searchResults.n_simulations ?? 50} simulations, ${searchResults.n_pairs_scored ?? searchResults.max_candidates_scored ?? searchResults.results.length} pairs scored)`
                        : searchResults.search_method === "beam"
                          ? `Beam search (width=${searchResults.beam_width ?? 5}, pool=${searchResults.candidate_pool_size}, scored=${searchResults.max_candidates_scored ?? searchResults.results.length})`
                          : `Greedy search (pool=${searchResults.candidate_pool_size}, scored=${searchResults.max_candidates_scored ?? searchResults.results.length})`}
                    </span>
                  )}
                  {searchResults.truncated && (
                    <span className="text-xs font-mono text-[#9A712F] bg-[#F7F0E4] border border-[#E5D4A8] px-2.5 py-1 rounded font-semibold flex items-center gap-1">
                      <span>⚠️</span> Time budget reached (truncated)
                    </span>
                  )}
                  <span className="text-xs font-mono text-[#5A635E] bg-[#EEEBE5] border border-[#E5E2DC] px-2.5 py-1 rounded font-semibold">
                    Top {searchResults.results.length} Pairs
                  </span>
                </div>
              </div>

              <div className="divide-y divide-[#E5E2DC]">
                {searchResults.results.map((pair, idx) => (
                  <div
                    key={`${pair.drug_a}_${pair.drug_b}_${idx}`}
                    className="py-4 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:bg-[#F3F1EC] px-3 rounded transition-colors"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-mono text-xs text-[#8A918C] font-bold">
                          #{pair.rank ?? idx + 1}
                        </span>
                        <h4 className="font-semibold text-sm text-[#1C2421]">
                          {pair.drug_a_name} × {pair.drug_b_name}
                        </h4>
                        <Badge
                          variant={
                            pair.predicted_class === "synergy"
                              ? "synergy"
                              : pair.predicted_class === "antagonism"
                                ? "antagonism"
                                : "additive"
                          }
                          size="sm"
                        >
                          {pair.predicted_class}
                        </Badge>
                        <ToxicityBadge
                          hasKnownDdi={pair.ranking?.breakdown?.has_known_ddi}
                          unknownRiskApplied={
                            pair.ranking?.breakdown?.unknown_risk_applied
                          }
                          sideEffectOverlap={
                            pair.ranking?.breakdown?.side_effect_overlap
                          }
                          toxicityPenalty={pair.ranking?.toxicity_penalty}
                          size="sm"
                          showDetails={true}
                        />
                        {(pair.search_method === "mcts" ||
                          searchResults?.search_method === "mcts") &&
                          pair.mcts_visits !== undefined && (
                            <span
                              title="Number of MCTS search visits to this pair during tree exploration (algorithmic exploration count, not a biological score)"
                              className="text-[10px] font-mono text-[#6B746F] bg-[#F3F1EC] border border-[#E5E2DC] px-1.5 py-0.5 rounded"
                            >
                              visits: {pair.mcts_visits}
                            </span>
                          )}
                      </div>
                      <p className="text-xs text-[#5A635E] line-clamp-2 max-w-2xl leading-normal">
                        {pair.explanation_text}
                      </p>
                      <div className="flex items-center gap-2 pt-1">
                        <span className="inline-flex items-center gap-1.5 text-[11px] font-mono text-[#6B746F] bg-[#EEEBE5] border border-[#E5E2DC] px-2 py-0.5 rounded">
                          <Clock className="w-3 h-3 text-[#8A918C]" />
                          Faithfulness ablation not computed during batch search
                          &bull; Click Inspect for full verification
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-4 shrink-0 font-mono text-xs">
                      <div className="text-right">
                        <span className="text-[10px] text-[#6B746F] uppercase block font-sans">
                          Composite V(pair)
                        </span>
                        <span className="font-bold text-sm text-[#2F6B5E]">
                          {(
                            pair.v_score ??
                            pair.ranking?.v_score ??
                            pair.score
                          ).toFixed(4)}
                        </span>
                        <div className="text-[10px] text-[#6B746F] flex items-center justify-end gap-1.5 mt-0.5 font-mono">
                          <span>
                            p(syn):{" "}
                            <strong className="text-[#3D7A6C]">
                              {(
                                pair.p_synergy ??
                                pair.ranking?.p_synergy ??
                                pair.score
                              ).toFixed(4)}
                            </strong>
                          </span>
                          {pair.ranking?.toxicity_penalty !== undefined &&
                            pair.ranking?.toxicity_penalty !== null && (
                              <>
                                <span>&bull;</span>
                                <span
                                  title={`Toxicity penalty: ${pair.ranking.toxicity_penalty.toFixed(4)}`}
                                >
                                  tox:{" "}
                                  <strong
                                    className={
                                      pair.ranking.toxicity_penalty > 0.4
                                        ? "text-[#C45C5C]"
                                        : "text-[#B8893D]"
                                    }
                                  >
                                    {pair.ranking.toxicity_penalty.toFixed(3)}
                                  </strong>
                                </span>
                              </>
                            )}
                        </div>
                      </div>
                      <button
                        type="button"
                        disabled={inspectingPairIdx !== null}
                        onClick={() => handleSelectDiscoveredPair(pair, idx)}
                        className="px-3.5 py-2 bg-[#EEEBE5] hover:bg-[#2F6B5E] hover:text-[#FFFEFB] disabled:opacity-50 text-[#1C2421] rounded font-semibold text-xs transition-colors flex items-center gap-1.5 cursor-pointer"
                      >
                        {inspectingPairIdx === idx ? (
                          <span className="flex items-center gap-1.5">
                            <svg
                              className="animate-spin w-3.5 h-3.5"
                              viewBox="0 0 24 24"
                              fill="none"
                            >
                              <circle
                                className="opacity-25"
                                cx="12"
                                cy="12"
                                r="10"
                                stroke="currentColor"
                                strokeWidth="4"
                              />
                              <path
                                className="opacity-75"
                                fill="currentColor"
                                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                              />
                            </svg>
                            Loading analysis...
                          </span>
                        ) : (
                          <span className="flex items-center gap-1.5">
                            Inspect Analysis{" "}
                            <ArrowRight className="w-3.5 h-3.5" />
                          </span>
                        )}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Why Not Drug X Diagnostic Agent */}
          <WhyNotSection
            disease={
              searchResults?.disease ||
              searchDisease ||
              diseaseContext ||
              "glioblastoma"
            }
            cellLine={searchResults?.cell_line || cellLine}
            searchMethod={(searchResults?.search_method as any) || "beam"}
            onInspectPair={handleInspectWhyNotPair}
          />
        </div>
      )}
    </div>
  );
};
