import React, { useState } from 'react';
import { Compass, SlidersHorizontal } from 'lucide-react';
import type { CellLineRelevanceStatus } from '../../types/api';
import { CellLineDropdown } from './CellLineDropdown';

interface DiscoveryModeProps {
  cellLineStatus: CellLineRelevanceStatus;
  selectedCellLine: string;
  onSelectCellLine: (cl: string) => void;
  onRunSearch: (disease: string, cellLine: string, maxCandidates: number, topK: number) => void;
  isLoading: boolean;
}

export const DiscoveryMode: React.FC<DiscoveryModeProps> = ({
  cellLineStatus,
  selectedCellLine,
  onSelectCellLine,
  onRunSearch,
  isLoading,
}) => {
  const [disease, setDisease] = useState('glioblastoma');
  const [maxCandidates, setMaxCandidates] = useState(15);
  const [topK, setTopK] = useState(5);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!disease.trim() || !selectedCellLine) return;
    onRunSearch(disease.trim(), selectedCellLine, maxCandidates, topK);
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
              className="text-[11px] bg-[#F1F5F9] hover:bg-[#E2E8F0] px-2 py-0.5 rounded text-[#334155] transition-colors"
            >
              {d}
            </button>
          ))}
        </div>
      </div>

      <CellLineDropdown
        status={cellLineStatus}
        selectedCellLine={selectedCellLine}
        onSelect={onSelectCellLine}
        disabled={isLoading}
      />

      <div className="bg-[#F8FAFC] border border-[#E2E8F0] rounded-md p-4">
        <div className="flex items-center gap-2 mb-3">
          <SlidersHorizontal className="w-3.5 h-3.5 text-[#64748B]" />
          <span className="text-xs font-semibold text-[#334155] uppercase tracking-wider">
            Discovery Scope & Ranking
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-[#64748B]">Candidate Pool Size:</span>
              <span className="font-mono font-semibold text-[#0F172A]">
                {maxCandidates} drugs
              </span>
            </div>
            <input
              type="range"
              min={5}
              max={30}
              step={5}
              value={maxCandidates}
              disabled={isLoading}
              onChange={(e) => setMaxCandidates(Number(e.target.value))}
              className="w-full accent-[#0D9488]"
            />
            <span className="text-[10px] text-[#94A3B8]">
              Traces indication & target overlap in PrimeKG (up to {maxCandidates * (maxCandidates - 1) / 2} pairs)
            </span>
          </div>

          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-[#64748B]">Explain Top-K Combinations:</span>
              <span className="font-mono font-semibold text-[#0F172A]">
                {topK} pairs
              </span>
            </div>
            <input
              type="range"
              min={3}
              max={10}
              step={1}
              value={topK}
              disabled={isLoading}
              onChange={(e) => setTopK(Number(e.target.value))}
              className="w-full accent-[#0D9488]"
            />
            <span className="text-[10px] text-[#94A3B8]">
              Full gradient backprop + PubMed retrieval on top-{topK} candidates
            </span>
          </div>
        </div>
      </div>

      <button
        type="submit"
        disabled={isLoading || !disease.trim() || !selectedCellLine}
        className="w-full py-3 bg-[#0D9488] hover:bg-[#0F766E] disabled:bg-[#94A3B8] text-[#FFFFFF] rounded-md font-semibold text-sm flex items-center justify-center gap-2 shadow-xs transition-colors cursor-pointer"
      >
        <Compass className="w-4 h-4" />
        {isLoading ? 'Searching Candidate Space...' : 'Run Discovery & Score Candidate Combinations'}
      </button>
    </form>
  );
};
