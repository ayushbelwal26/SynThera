import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useApp } from "../services/AppContext";
import { searchCombinations, predictCombination } from "../services/api";
import type { SearchResponse, PredictionResult } from "../types/api";
import { CellLineDropdown } from "../components/discover/CellLineDropdown";
import { WhyNotSection } from "../components/discover/WhyNotSection";
import {
  Search,
  TrendingUp,
  AlertTriangle,
  Minus,
  ExternalLink,
  X,
  ChevronRight,
  Compass,
} from "lucide-react";

export const IndicationPage: React.FC = () => {
  const navigate = useNavigate();
  const { cellLineStatus, setCurrentPrediction, addRecentPrediction } = useApp();

  const [disease, setDisease] = useState("non-small cell lung carcinoma");
  const [cellLine, setCellLine] = useState("A549");
  const [searchMethod, setSearchMethod] = useState<"beam" | "greedy" | "mcts">("beam");
  const [candidatePoolSize, setCandidatePoolSize] = useState(15);
  const [topK, setTopK] = useState(5);

  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [searchResults, setSearchResults] = useState<SearchResponse | null>(null);
  const [selectedCandidate, setSelectedCandidate] = useState<PredictionResult | null>(null);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!disease.trim()) {
      setErrorMsg("Please enter an oncology indication or cancer phenotype.");
      return;
    }

    setIsLoading(true);
    setErrorMsg(null);
    setSearchResults(null);
    setSelectedCandidate(null);

    try {
      const res = await searchCombinations({
        disease: disease.trim(),
        cell_line: cellLine,
        max_candidates: candidatePoolSize,
        top_k: topK,
        search_method: searchMethod,
      });
      setSearchResults(res);
      if (res.results.length > 0) {
        setSelectedCandidate(res.results[0]);
      }
    } catch (err: any) {
      setErrorMsg(err.message || "Indication candidate search failed.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleInspectInFull = async (pair: PredictionResult) => {
    try {
      const full = await predictCombination({
        drug_a: pair.drug_a,
        drug_b: pair.drug_b,
        cell_line: pair.cell_line,
        disease: searchResults?.disease || disease,
      });
      setCurrentPrediction(full);
      addRecentPrediction(full);
      navigate(`/results/${pair.drug_a}_${pair.drug_b}_${pair.cell_line}`);
    } catch {
      setCurrentPrediction(pair);
      addRecentPrediction(pair);
      navigate(`/results/${pair.drug_a}_${pair.drug_b}_${pair.cell_line}`);
    }
  };

  const getClassBadge = (cls?: string) => {
    const c = (cls || "additive").toLowerCase();
    if (c === "synergy") {
      return (
        <span className="inline-flex items-center gap-1 font-mono text-[10.5px] font-semibold px-2.5 py-0.5 rounded-full bg-[#00D6A0]/10 text-[#00D6A0] border border-[#00D6A0]/30 shadow-[0_0_8px_rgba(0,214,160,0.15)]">
          <TrendingUp size={11} />
          Synergy
        </span>
      );
    }
    if (c === "antagonism") {
      return (
        <span className="inline-flex items-center gap-1 font-mono text-[10.5px] font-semibold px-2.5 py-0.5 rounded-full bg-[#E05260]/10 text-[#E05260] border border-[#E05260]/30">
          <AlertTriangle size={11} />
          Antagonism
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 font-mono text-[10.5px] font-semibold px-2.5 py-0.5 rounded-full bg-[#C7A76A]/10 text-[#C7A76A] border border-[#C7A76A]/30">
        <Minus size={11} />
        Additive
      </span>
    );
  };

  return (
    <div className="space-y-10">
      {/* ── Page Header ── */}
      <div className="border-b border-[#20343C] pb-6">
        <div className="flex items-center gap-2 mb-2">
          <span className="section-label">02 · Indication Discovery</span>
          <span className="text-[#20343C]">•</span>
          <span className="font-mono text-[11px] text-[#94A5A6]">
            Disease-Driven Combinatorial Search
          </span>
        </div>
        <h1 className="editorial-title text-[#F1F5F2]">
          Disease-Specific Combinatorial Discovery
        </h1>
        <p className="editorial-sub max-w-2xl mt-2">
          Traverse disease neighborhoods in PrimeKG to identify multi-target candidate pairings.
          Evaluate candidate pools with Beam Search or Monte Carlo Tree Search (MCTS) to rank synergistic opportunities.
        </p>
      </div>

      {errorMsg && (
        <div className="p-4 rounded-xl bg-[#E05260]/10 border border-[#E05260]/30 text-[#E05260] text-[13px]">
          {errorMsg}
        </div>
      )}

      {/* ── Search & Filter Panel ── */}
      <div className="st-panel p-6 space-y-4">
        <form onSubmit={handleSearch} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-12 gap-5">
            <div className="md:col-span-7 space-y-1.5">
              <label className="text-[11px] font-mono uppercase text-[#94A5A6] block">
                Target Oncology Indication / Phenotype
              </label>
              <div className="relative">
                <input
                  type="text"
                  value={disease}
                  onChange={(e) => setDisease(e.target.value)}
                  placeholder="e.g. non-small cell lung carcinoma, glioblastoma..."
                  className="st-input pl-9 text-[14px]"
                />
                <Search size={16} className="absolute left-3 top-3 text-[#60747A] pointer-events-none" />
              </div>
            </div>

            <div className="md:col-span-5 space-y-1.5">
              <label className="text-[11px] font-mono uppercase text-[#94A5A6] block">
                Cancer Cell Line Context
              </label>
              <CellLineDropdown
                status={cellLineStatus}
                selectedCellLine={cellLine}
                onSelect={setCellLine}
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-3 border-t border-[#20343C]/60 text-xs">
            <div>
              <label className="text-[10.5px] font-mono uppercase text-[#94A5A6] block mb-1">
                Traversal Search Algorithm
              </label>
              <select
                value={searchMethod}
                onChange={(e) => setSearchMethod(e.target.value as any)}
                className="st-input py-2 text-xs bg-[#091218]"
              >
                <option value="beam">Beam Search (Width 5)</option>
                <option value="greedy">Greedy Search</option>
                <option value="mcts">MCTS with UCT Exploration</option>
              </select>
            </div>

            <div>
              <label className="text-[10.5px] font-mono uppercase text-[#94A5A6] block mb-1">
                Candidate Pool Dimension
              </label>
              <select
                value={candidatePoolSize}
                onChange={(e) => setCandidatePoolSize(Number(e.target.value))}
                className="st-input py-2 text-xs bg-[#091218]"
              >
                <option value={10}>10 Candidates</option>
                <option value={15}>15 Candidates (Balanced)</option>
                <option value={25}>25 Candidates (Exhaustive)</option>
                <option value={40}>40 Candidates</option>
              </select>
            </div>

            <div>
              <label className="text-[10.5px] font-mono uppercase text-[#94A5A6] block mb-1">
                Top-K Ranked Combinations
              </label>
              <select
                value={topK}
                onChange={(e) => setTopK(Number(e.target.value))}
                className="st-input py-2 text-xs bg-[#091218]"
              >
                <option value={5}>Top 5 Pairings</option>
                <option value={10}>Top 10 Pairings</option>
                <option value={15}>Top 15 Pairings</option>
              </select>
            </div>
          </div>

          <div className="flex justify-end pt-2">
            <button
              type="submit"
              disabled={isLoading || !disease.trim()}
              className="st-btn-primary"
            >
              {isLoading ? (
                <span className="flex items-center gap-2">
                  <span className="w-3.5 h-3.5 border-2 border-[#05090D] border-t-transparent rounded-full animate-spin" />
                  <span>Traversing PrimeKG & Scoring Candidates...</span>
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  <Compass size={15} />
                  <span>Discover & Rank Combinations</span>
                </span>
              )}
            </button>
          </div>
        </form>
      </div>

      {/* ── Ranked Candidate Workspace ── */}
      {searchResults && (
        <div className="space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#20343C] pb-3">
            <div>
              <h3 className="text-[18px] font-serif text-[#F1F5F2]">
                Ranked Combinations for {searchResults.disease}
              </h3>
              <p className="font-mono text-[11px] text-[#60747A] mt-0.5">
                {searchResults.results.length} ranked pairs • Method: {searchResults.search_method || searchMethod} • Pool: {searchResults.candidate_pool_size} compounds
              </p>
            </div>
            <span className="font-mono text-[11.5px] px-3 py-1 rounded-full bg-[#101C23] border border-[#20343C] text-[#00D6A0]">
              Cell Line: {searchResults.cell_line}
            </span>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            {/* Scientific Data Table */}
            <div className={`space-y-3 ${selectedCandidate ? "lg:col-span-7" : "lg:col-span-12"}`}>
              <div className="st-panel overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-[13px]">
                    <thead className="bg-[#091218] border-b border-[#20343C] font-mono text-[10.5px] text-[#60747A] uppercase tracking-wider">
                      <tr>
                        <th className="py-3 px-3">Rank</th>
                        <th className="py-3 px-3">Drug A</th>
                        <th className="py-3 px-3">Drug B</th>
                        <th className="py-3 px-3">Class</th>
                        <th className="py-3 px-3 text-right">P(Syn)</th>
                        <th className="py-3 px-3 text-right">V(pair)</th>
                        <th className="py-3 px-3 text-center">Inspect</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#20343C]/40 font-sans">
                      {searchResults.results.map((pair, idx) => {
                        const rank = pair.rank ?? idx + 1;
                        const isSelected =
                          selectedCandidate?.drug_a === pair.drug_a &&
                          selectedCandidate?.drug_b === pair.drug_b;
                        const pSyn = pair.p_synergy ?? pair.ranking?.p_synergy ?? pair.score ?? 0;
                        const vScore = pair.v_score ?? pair.ranking?.v_score ?? pair.score ?? 0;

                        return (
                          <tr
                            key={`${pair.drug_a}_${pair.drug_b}_${idx}`}
                            onClick={() => setSelectedCandidate(pair)}
                            className={`hover:bg-[#14242B] transition-colors cursor-pointer ${
                              isSelected ? "bg-[#14242B] border-l-2 border-l-[#00D6A0]" : ""
                            }`}
                          >
                            <td className="py-3 px-3 font-mono font-bold text-[#60747A]">
                              #{String(rank).padStart(2, "0")}
                            </td>
                            <td className="py-3 px-3 font-medium text-[#F1F5F2]">
                              {pair.drug_a_name}
                            </td>
                            <td className="py-3 px-3 font-medium text-[#F1F5F2]">
                              {pair.drug_b_name}
                            </td>
                            <td className="py-3 px-3">
                              {getClassBadge(pair.predicted_class)}
                            </td>
                            <td className="py-3 px-3 text-right font-mono font-semibold text-[#00D6A0]">
                              {Number(pSyn).toFixed(2)}
                            </td>
                            <td className="py-3 px-3 text-right font-mono text-[#F1F5F2]">
                              {Number(vScore).toFixed(2)}
                            </td>
                            <td className="py-3 px-3 text-center">
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleInspectInFull(pair);
                                }}
                                className="p-1 rounded hover:bg-[#20343C] text-[#00D6A0] inline-flex items-center cursor-pointer"
                                title="Open full report"
                              >
                                <ChevronRight size={15} />
                              </button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            {/* Candidate Inspection Drawer */}
            {selectedCandidate && (
              <div className="lg:col-span-5 st-panel p-6 space-y-5 border-l-2 border-l-[#00D6A0] sticky top-24">
                <div className="flex items-start justify-between border-b border-[#20343C] pb-3">
                  <div>
                    <span className="section-label">Candidate Inspection</span>
                    <h4 className="font-serif text-[19px] text-[#F1F5F2] mt-0.5 font-bold">
                      {selectedCandidate.drug_a_name} + {selectedCandidate.drug_b_name}
                    </h4>
                    <span className="font-mono text-[11px] text-[#60747A]">
                      Rank #{selectedCandidate.rank ?? 1} in discovery beam
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => setSelectedCandidate(null)}
                    className="text-[#60747A] hover:text-[#F1F5F2] p-1 cursor-pointer"
                  >
                    <X size={16} />
                  </button>
                </div>

                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-3 text-xs font-mono">
                    <div className="p-3 rounded-lg bg-[#091218] border border-[#20343C]">
                      <span className="text-[10px] uppercase text-[#60747A] block">Class</span>
                      <div className="mt-1">{getClassBadge(selectedCandidate.predicted_class)}</div>
                    </div>
                    <div className="p-3 rounded-lg bg-[#091218] border border-[#20343C]">
                      <span className="text-[10px] uppercase text-[#60747A] block">Multi-Objective V</span>
                      <span className="text-[18px] font-bold text-[#00D6A0] mt-0.5 block">
                        {Number(selectedCandidate.v_score ?? selectedCandidate.score ?? 0).toFixed(3)}
                      </span>
                    </div>
                  </div>

                  {selectedCandidate.explanation_text && (
                    <div className="p-3.5 rounded-lg bg-[#091218] border border-[#20343C] text-[13px] text-[#94A5A6] leading-relaxed">
                      <span className="text-[10px] font-mono uppercase text-[#00D6A0] block mb-1">
                        Mechanistic Hypothesis
                      </span>
                      {selectedCandidate.explanation_text}
                    </div>
                  )}

                  <div className="pt-2">
                    <button
                      type="button"
                      onClick={() => handleInspectInFull(selectedCandidate)}
                      className="st-btn-primary w-full text-[13px]"
                    >
                      <span>Open Full Prediction Report</span>
                      <ExternalLink size={14} />
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Diagnostic "Why Not?" Reasoner */}
          <div className="pt-8 border-t border-[#20343C]">
            <WhyNotSection
              disease={searchResults.disease}
              cellLine={searchResults.cell_line}
              searchMethod={searchMethod}
              onInspectPair={async (drugAId, drugBId, cl) => {
                const full = await predictCombination({
                  drug_a: drugAId,
                  drug_b: drugBId,
                  cell_line: cl,
                  disease: disease,
                });
                setCurrentPrediction(full);
                addRecentPrediction(full);
                navigate(`/results/${drugAId}_${drugBId}_${cl}`);
              }}
            />
          </div>
        </div>
      )}

      {/* Default State: Why-Not Ready */}
      {!isLoading && !searchResults && (
        <div className="pt-4 border-t border-[#20343C]">
          <WhyNotSection
            disease={disease}
            cellLine={cellLine}
            searchMethod={searchMethod}
            onInspectPair={async (drugAId, drugBId, cl) => {
              const full = await predictCombination({
                drug_a: drugAId,
                drug_b: drugBId,
                cell_line: cl,
                disease: disease,
              });
              setCurrentPrediction(full);
              addRecentPrediction(full);
              navigate(`/results/${drugAId}_${drugBId}_${cl}`);
            }}
          />
        </div>
      )}
    </div>
  );
};
