import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeftRight, Play, ArrowRight, Clock } from 'lucide-react';
import { useApp } from '../services/AppContext';
import { predictCombination, searchCombinations } from '../services/api';
import type { Drug, PredictionResult, SearchResponse } from '../types/api';
import { DrugSelectInput } from '../components/discover/DrugSelectInput';
import { CellLineDropdown } from '../components/discover/CellLineDropdown';
import { BenchmarkPresets } from '../components/discover/BenchmarkPresets';
import type { BenchmarkPreset } from '../components/discover/BenchmarkPresets';
import { DiscoveryMode } from '../components/discover/DiscoveryMode';
import { LoadingStages } from '../components/common/LoadingStages';
import { AlertNotice } from '../components/common/AlertNotice';
import { Badge } from '../components/common/Badge';

export const DiscoverPage: React.FC = () => {
  const navigate = useNavigate();
  const {
    drugs,
    cellLineStatus,
    setCurrentPrediction,
    addRecentPrediction,
    refreshCellLines,
  } = useApp();

  const [activeTab, setActiveTab] = useState<'pair' | 'search'>('pair');

  // Pair evaluation state
  const [drugA, setDrugA] = useState<Drug | null>(null);
  const [drugB, setDrugB] = useState<Drug | null>(null);
  const [cellLine, setCellLine] = useState<string>('T98G');
  const [diseaseContext, setDiseaseContext] = useState<string>('');

  // Status & loading
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Discovery search results state
  const [searchResults, setSearchResults] = useState<SearchResponse | null>(null);
  const [inspectingPairIdx, setInspectingPairIdx] = useState<number | null>(null);

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
      setErrorMsg('Please select both Compound A and Compound B to execute analysis.');
      return;
    }
    if (drugA.id === drugB.id) {
      setErrorMsg('Please select two distinct compounds for combination analysis.');
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
      navigate('/analysis');
    } catch (err: any) {
      setErrorMsg(err.message || 'Analysis service error occurred during prediction.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRunSearch = async (
    disease: string,
    targetCellLine: string,
    maxCandidates: number,
    topK: number
  ) => {
    setIsLoading(true);
    setErrorMsg(null);
    setSearchResults(null);

    try {
      const res = await searchCombinations({
        disease,
        cell_line: targetCellLine,
        max_candidates: maxCandidates,
        top_k: topK,
      });
      setSearchResults(res);
    } catch (err: any) {
      setErrorMsg(err.message || 'Combination discovery failed. Please verify the indication name.');
    } finally {
      setIsLoading(false);
    }
  };

  // When user clicks "Inspect Analysis" on a search result:
  // Call /predict to get full faithfulness data, then navigate to /analysis.
  // Search results now skip faithfulness (run_faithfulness=False) for speed,
  // so we fetch it on-demand here.
  const handleSelectDiscoveredPair = async (pair: PredictionResult, idx: number) => {
    setInspectingPairIdx(idx);
    try {
      const full = await predictCombination({
        drug_a: pair.drug_a,
        drug_b: pair.drug_b,
        cell_line: pair.cell_line,
      });
      setCurrentPrediction(full);
      addRecentPrediction(full);
      navigate('/analysis');
    } catch {
      // Fall back to search result without faithfulness if /predict fails
      setCurrentPrediction(pair);
      addRecentPrediction(pair);
      navigate('/analysis');
    } finally {
      setInspectingPairIdx(null);
    }
  };

  return (
    <div className="space-y-8">
      {/* Hero & Instrument Purpose */}
      <div className="border-b border-[#E5E5E0] pb-5">
        <h2 className="font-serif text-3xl font-bold text-[#0F172A] tracking-tight">
          Combination Analysis & Discovery
        </h2>
        <p className="text-sm text-[#475569] mt-1 max-w-3xl leading-relaxed">
          Screen multi-drug combinations against heterogeneous knowledge graph topologies. Predict synergy or antagonism with calibrated confidence and extract load-bearing mechanistic pathways.
        </p>
      </div>

      {/* Mode Selector Tabs */}
      <div className="flex border-b border-[#E5E5E0] gap-4">
        <button
          type="button"
          onClick={() => {
            setActiveTab('pair');
            setErrorMsg(null);
          }}
          className={`pb-3 text-sm font-semibold border-b-2 transition-all cursor-pointer ${
            activeTab === 'pair'
              ? 'border-[#0D9488] text-[#0D9488]'
              : 'border-transparent text-[#64748B] hover:text-[#0F172A]'
          }`}
        >
          Compound Pair Analysis (Targeted)
        </button>
        <button
          type="button"
          onClick={() => {
            setActiveTab('search');
            setErrorMsg(null);
          }}
          className={`pb-3 text-sm font-semibold border-b-2 transition-all cursor-pointer ${
            activeTab === 'search'
              ? 'border-[#0D9488] text-[#0D9488]'
              : 'border-transparent text-[#64748B] hover:text-[#0F172A]'
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
            title={activeTab === 'pair' ? 'Evaluating Drug Combination' : 'Discovering Candidate Combinations'}
            subtitle={
              activeTab === 'pair'
                ? `Running inference for ${drugA?.name || 'Drug A'} × ${drugB?.name || 'Drug B'} @ ${cellLine}`
                : 'Traversing PrimeKG indication neighbors and ranking candidate combinations'
            }
          />
        </div>
      )}

      {/* Tab 1: Targeted Pair Evaluation */}
      {!isLoading && activeTab === 'pair' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 space-y-6">
            <form onSubmit={handleAnalyzePair} className="bg-[#FFFFFF] border border-[#E5E5E0] rounded-lg p-6 shadow-xs space-y-5">
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
                    className="p-2 border border-[#CBD5E1] rounded hover:bg-[#F1F5F9] text-[#64748B] hover:text-[#0F172A] transition-colors disabled:opacity-40"
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
                  <label className="block text-xs font-semibold text-[#334155] uppercase tracking-wider mb-1.5">
                    Indication Context (Optional)
                  </label>
                  <input
                    type="text"
                    value={diseaseContext}
                    onChange={(e) => {
                      setDiseaseContext(e.target.value);
                      refreshCellLines(e.target.value);
                    }}
                    placeholder="e.g. Glioblastoma, Ovarian Carcinoma..."
                    className="w-full px-3.5 py-2.5 bg-[#FFFFFF] border border-[#CBD5E1] focus:border-[#0D9488] focus:ring-1 focus:ring-[#0D9488] rounded-md text-sm text-[#0F172A] outline-none"
                  />
                </div>
              </div>

              <div className="pt-3 border-t border-[#F4F4F1] flex justify-end">
                <button
                  type="submit"
                  disabled={!drugA || !drugB}
                  className="px-6 py-3 bg-[#0D9488] hover:bg-[#0F766E] disabled:bg-[#94A3B8] text-[#FFFFFF] font-semibold text-sm rounded-md shadow-xs flex items-center gap-2 transition-colors cursor-pointer"
                >
                  <Play className="w-4 h-4 fill-current" />
                  Analyze Combination & Trace Pathway
                </button>
              </div>
            </form>

            {/* Benchmark Presets */}
            <BenchmarkPresets onSelect={handleSelectPreset} />
          </div>

          {/* Right Side: Instrument Overview Panel */}
          <div className="space-y-4">
            <div className="bg-[#FFFFFF] border border-[#E5E5E0] rounded-lg p-5 shadow-xs">
              <h4 className="font-serif text-sm font-bold text-[#0F172A] mb-2 uppercase tracking-wider">
                Analysis Instrument Specifications
              </h4>
              <p className="text-xs text-[#475569] leading-relaxed mb-4">
                Synthera evaluates drug synergy through a Heterogeneous Graph Transformer (HGT) trained on multimodal biological networks from PrimeKG.
              </p>

              <div className="space-y-2.5 text-xs font-mono">
                <div className="flex justify-between py-1.5 border-b border-[#F1F5F9]">
                  <span className="text-[#64748B]">Indexed Drugs:</span>
                  <span className="font-semibold text-[#0F172A]">{drugs.length.toLocaleString()}</span>
                </div>
                <div className="flex justify-between py-1.5 border-b border-[#F1F5F9]">
                  <span className="text-[#64748B]">Benchmark Cell Lines:</span>
                  <span className="font-semibold text-[#0F172A]">{cellLineStatus.cellLines.length}</span>
                </div>
                <div className="flex justify-between py-1.5 border-b border-[#F1F5F9]">
                  <span className="text-[#64748B]">Attribution Method:</span>
                  <span className="font-semibold text-[#0D9488]">Gradient Edge Saliency</span>
                </div>
                <div className="flex justify-between py-1.5 border-b border-[#F1F5F9]">
                  <span className="text-[#64748B]">Verification:</span>
                  <span className="font-semibold text-[#059669]">Dual Faithfulness Ablation</span>
                </div>
                <div className="flex justify-between py-1.5">
                  <span className="text-[#64748B]">Literature Link:</span>
                  <span className="font-semibold text-[#B45309]">NCBI PubMed E-Utilities</span>
                </div>
              </div>
            </div>

            <div className="bg-[#F8FAFC] border border-[#E2E8F0] rounded-lg p-4 text-xs text-[#64748B] leading-relaxed">
              <span className="font-semibold text-[#0F172A] block mb-1">Scientific Integrity Guarantee:</span>
              Predictions, probabilities, and attribution graphs represent live biocomputational evaluations. No simulated or mock data is generated.
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Discovery Search Mode */}
      {!isLoading && activeTab === 'search' && (
        <div className="space-y-6">
          <div className="bg-[#FFFFFF] border border-[#E5E5E0] rounded-lg p-6 shadow-xs max-w-3xl">
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
            <div className="bg-[#FFFFFF] border border-[#E5E5E0] rounded-lg p-6 shadow-xs space-y-4">
              <div className="flex items-center justify-between border-b border-[#E5E5E0] pb-3">
                <div>
                  <h3 className="font-serif text-lg font-bold text-[#0F172A]">
                    Ranked Discovery Results for '{searchResults.disease}'
                  </h3>
                  <p className="text-xs text-[#64748B] font-mono mt-0.5">
                    Context: {searchResults.cell_line} &bull; Candidate Pool: {searchResults.candidate_pool_size} compounds
                  </p>
                </div>
                <span className="text-xs font-mono text-[#0D9488] bg-[#F0FDFA] border border-[#99F6E4] px-2.5 py-1 rounded font-semibold">
                  {searchResults.results.length} Top Pairs Explained
                </span>
              </div>

              <div className="divide-y divide-[#E5E5E0]">
                {searchResults.results.map((pair, idx) => (
                  <div
                    key={`${pair.drug_a}_${pair.drug_b}_${idx}`}
                    className="py-4 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:bg-[#F8FAFC] px-3 rounded transition-colors"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs text-[#94A3B8] font-bold">
                          #{idx + 1}
                        </span>
                        <h4 className="font-semibold text-sm text-[#0F172A]">
                          {pair.drug_a_name} × {pair.drug_b_name}
                        </h4>
                        <Badge
                          variant={
                            pair.predicted_class === 'synergy'
                              ? 'synergy'
                              : pair.predicted_class === 'antagonism'
                              ? 'antagonism'
                              : 'additive'
                          }
                          size="sm"
                        >
                          {pair.predicted_class}
                        </Badge>
                      </div>
                      <p className="text-xs text-[#475569] line-clamp-2 max-w-2xl leading-relaxed">
                        {pair.explanation_text}
                      </p>
                      <div className="flex items-center gap-2 pt-1">
                        <span className="inline-flex items-center gap-1.5 text-[11px] font-mono text-[#64748B] bg-[#F1F5F9] border border-[#E2E8F0] px-2 py-0.5 rounded">
                          <Clock className="w-3 h-3 text-[#94A3B8]" />
                          Faithfulness ablation not computed during batch search &bull; Click Inspect for full verification
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-4 shrink-0 font-mono text-xs">
                      <div className="text-right">
                        <span className="text-[10px] text-[#64748B] uppercase block">
                          Calibrated Synergy
                        </span>
                        <span className="font-bold text-sm text-[#059669]">
                          {pair.score.toFixed(4)}
                        </span>
                      </div>
                      <button
                        type="button"
                        disabled={inspectingPairIdx !== null}
                        onClick={() => handleSelectDiscoveredPair(pair, idx)}
                        className="px-3.5 py-2 bg-[#F1F5F9] hover:bg-[#0D9488] hover:text-[#FFFFFF] disabled:opacity-50 text-[#0F172A] rounded font-semibold text-xs transition-colors flex items-center gap-1.5 cursor-pointer"
                      >
                        {inspectingPairIdx === idx ? (
                          <span className="flex items-center gap-1.5">
                            <svg className="animate-spin w-3.5 h-3.5" viewBox="0 0 24 24" fill="none">
                              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                            </svg>
                            Loading analysis...
                          </span>
                        ) : (
                          <span className="flex items-center gap-1.5">Inspect Analysis <ArrowRight className="w-3.5 h-3.5" /></span>
                        )}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
