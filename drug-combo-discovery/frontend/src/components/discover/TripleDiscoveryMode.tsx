import React, { useState } from 'react';
import { SlidersHorizontal, Triangle, Info } from 'lucide-react';
import type { CellLineRelevanceStatus } from '../../types/api';
import { CellLineDropdown } from './CellLineDropdown';

interface TripleDiscoveryModeProps {
  cellLineStatus: CellLineRelevanceStatus;
  selectedCellLine: string;
  onSelectCellLine: (cl: string) => void;
  onRunTripleSearch: (
    disease: string,
    cellLine: string,
    maxCandidates: number,
    topK: number,
    timeBudgetSec: number
  ) => void;
  isLoading: boolean;
}

export const TripleDiscoveryMode: React.FC<TripleDiscoveryModeProps> = ({
  cellLineStatus,
  selectedCellLine,
  onSelectCellLine,
  onRunTripleSearch,
  isLoading,
}) => {
  const [disease, setDisease] = useState('glioblastoma');
  const [maxCandidates, setMaxCandidates] = useState(10);
  const [topK, setTopK] = useState(5);
  const [timeBudgetSec, setTimeBudgetSec] = useState(15.0);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!disease.trim() || !selectedCellLine) return;
    onRunTripleSearch(
      disease.trim(),
      selectedCellLine,
      maxCandidates,
      topK,
      timeBudgetSec
    );
  };

  const sampleDiseases = [
    'glioblastoma',
    'breast neoplasm',
    'colorectal carcinoma',
    'ovarian cancer',
    'renal cell carcinoma',
  ];

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {/* Formulation Notice Banner */}
      <div className="bg-[#F0FDFA] border border-[#99F6E4] rounded-md p-3.5 flex items-start gap-2.5 text-xs text-[#0F766E] leading-relaxed">
        <Info className="w-4 h-4 shrink-0 text-[#0D9488] mt-0.5" />
        <div>
          <span className="font-semibold block text-[#0D9488] mb-0.5">
            Composed Pair Formulation (Phase C1)
          </span>
          Three-drug combinations are evaluated strictly by composing pairwise V(pair) predictions from the calibrated GNN. Primary ranking uses the <strong>weakest-link bottleneck score</strong> (V_min) so a triad cannot outrank its weakest constituent pair.
        </div>
      </div>

      {/* Disease Input */}
      <div>
        <label className="block text-xs font-semibold text-[#334155] uppercase tracking-wider mb-1.5">
          Target Indication / Neoplasm Name
        </label>
        <div className="relative">
          <input
            type="text"
            value={disease}
            disabled={isLoading}
            onChange={(e) => setDisease(e.target.value)}
            placeholder="e.g. glioblastoma, adenocarcinoma, breast neoplasm..."
            className="w-full px-3.5 py-2.5 bg-[#FFFFFF] border border-[#CBD5E1] focus:border-[#0D9488] focus:ring-1 focus:ring-[#0D9488] rounded-md text-sm text-[#0F172A] outline-none font-medium"
            required
          />
        </div>
        <div className="flex items-center gap-1.5 mt-2 flex-wrap text-xs text-[#64748B]">
          <span className="text-[11px] font-medium text-[#475569]">Common indications:</span>
          {sampleDiseases.map((d) => (
            <button
              key={d}
              type="button"
              onClick={() => setDisease(d)}
              className="text-[11px] bg-[#F1F5F9] hover:bg-[#E2E8F0] px-2 py-0.5 rounded text-[#334155] transition-colors cursor-pointer"
            >
              {d}
            </button>
          ))}
        </div>
      </div>

      {/* Cell Line Dropdown */}
      <CellLineDropdown
        status={cellLineStatus}
        selectedCellLine={selectedCellLine}
        onSelect={onSelectCellLine}
        disabled={isLoading}
      />

      {/* Search Parameters Accordion */}
      <div className="bg-[#F8FAFC] border border-[#E2E8F0] rounded-md p-4 space-y-4">
        <div className="flex items-center justify-between border-b border-[#E2E8F0] pb-2.5">
          <div className="flex items-center gap-2">
            <SlidersHorizontal className="w-3.5 h-3.5 text-[#64748B]" />
            <span className="text-xs font-semibold text-[#334155] uppercase tracking-wider">
              Combinatorial Scaling & Budget Parameters
            </span>
          </div>
          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="text-[11px] text-[#0D9488] hover:text-[#0F766E] font-medium transition-colors cursor-pointer"
          >
            {showAdvanced ? 'Hide advanced' : 'Show advanced'}
          </button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <div className="flex justify-between items-center mb-1">
              <label className="text-xs font-medium text-[#475569]">
                Candidate Drug Pool Size: <span className="font-mono font-bold text-[#0F172A]">{maxCandidates}</span>
              </label>
              <span className="text-[10px] text-[#64748B] font-mono">(Hard-capped at 20)</span>
            </div>
            <input
              type="range"
              min="3"
              max="20"
              value={maxCandidates}
              disabled={isLoading}
              onChange={(e) => setMaxCandidates(parseInt(e.target.value))}
              className="w-full h-1.5 bg-[#CBD5E1] rounded-lg appearance-none cursor-pointer accent-[#0D9488]"
            />
            <p className="text-[10px] text-[#64748B] mt-1">
              Yields up to {Math.round((maxCandidates * (maxCandidates - 1)) / 2)} pairs and {Math.round((maxCandidates * (maxCandidates - 1) * (maxCandidates - 2)) / 6)} candidate triples.
            </p>
          </div>

          <div>
            <div className="flex justify-between items-center mb-1">
              <label className="text-xs font-medium text-[#475569]">
                Top Triples Returned (K): <span className="font-mono font-bold text-[#0F172A]">{topK}</span>
              </label>
            </div>
            <input
              type="range"
              min="1"
              max="15"
              value={topK}
              disabled={isLoading}
              onChange={(e) => setTopK(parseInt(e.target.value))}
              className="w-full h-1.5 bg-[#CBD5E1] rounded-lg appearance-none cursor-pointer accent-[#0D9488]"
            />
            <p className="text-[10px] text-[#64748B] mt-1">
              Top-K ranked by weakest-link bottleneck V(pair) score descending.
            </p>
          </div>
        </div>

        {showAdvanced && (
          <div className="pt-3 border-t border-[#E2E8F0] space-y-3">
            <div>
              <label className="block text-xs font-medium text-[#475569] mb-1">
                Evaluation Time Budget Cap (Seconds)
              </label>
              <input
                type="number"
                min="5"
                max="60"
                step="1"
                value={timeBudgetSec}
                disabled={isLoading}
                onChange={(e) => setTimeBudgetSec(parseFloat(e.target.value) || 15.0)}
                className="w-32 px-3 py-1.5 bg-[#FFFFFF] border border-[#CBD5E1] focus:border-[#0D9488] rounded text-xs font-mono text-[#0F172A]"
              />
              <p className="text-[10px] text-[#64748B] mt-1">
                Hard wall-clock timeout protecting combinatorial evaluation.
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Submit Button */}
      <div className="pt-2">
        <button
          type="submit"
          disabled={isLoading || !disease.trim() || !selectedCellLine}
          className="w-full sm:w-auto px-6 py-2.5 bg-[#0D9488] hover:bg-[#0F766E] disabled:bg-[#94A3B8] text-[#FFFFFF] rounded-md font-semibold text-sm transition-colors flex items-center justify-center gap-2 cursor-pointer disabled:cursor-not-allowed shadow-xs"
        >
          {isLoading ? (
            <span className="flex items-center gap-2">
              <svg className="animate-spin w-4 h-4 text-white" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Discovering 3-Drug Combinations...
            </span>
          ) : (
            <span className="flex items-center gap-2">
              <Triangle className="w-4 h-4" />
              Discover 3-Drug Combinations (Composed)
            </span>
          )}
        </button>
      </div>
    </form>
  );
};
