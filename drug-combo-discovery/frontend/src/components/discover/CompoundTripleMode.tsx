import React, { useMemo } from 'react';
import { Play, Info, AlertTriangle, Sparkles } from 'lucide-react';
import type { Drug, CellLineRelevanceStatus } from '../../types/api';
import { DrugSelectInput } from './DrugSelectInput';
import { CellLineDropdown } from './CellLineDropdown';

interface CompoundTripleModeProps {
  drugs: Drug[];
  cellLineStatus: CellLineRelevanceStatus;
  drugA: Drug | null;
  drugB: Drug | null;
  drugC: Drug | null;
  cellLine: string;
  onSelectDrugA: (drug: Drug | null) => void;
  onSelectDrugB: (drug: Drug | null) => void;
  onSelectDrugC: (drug: Drug | null) => void;
  onSelectCellLine: (cl: string) => void;
  onAnalyzeTriple: () => void;
  isLoading: boolean;
}

export const CompoundTripleMode: React.FC<CompoundTripleModeProps> = ({
  drugs,
  cellLineStatus,
  drugA,
  drugB,
  drugC,
  cellLine,
  onSelectDrugA,
  onSelectDrugB,
  onSelectDrugC,
  onSelectCellLine,
  onAnalyzeTriple,
  isLoading,
}) => {
  // Client-side duplicate detection
  const duplicateWarning = useMemo(() => {
    if (drugA && drugB && drugA.id === drugB.id) {
      return `Duplicate compound selected: Compound A and Compound B are both "${drugA.name}". All three compounds must be distinct.`;
    }
    if (drugA && drugC && drugA.id === drugC.id) {
      return `Duplicate compound selected: Compound A and Compound C are both "${drugA.name}". All three compounds must be distinct.`;
    }
    if (drugB && drugC && drugB.id === drugC.id) {
      return `Duplicate compound selected: Compound B and Compound C are both "${drugB.name}". All three compounds must be distinct.`;
    }
    return null;
  }, [drugA, drugB, drugC]);

  const isFormComplete = Boolean(drugA && drugB && drugC && cellLine);
  const canSubmit = isFormComplete && !duplicateWarning && !isLoading;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    onAnalyzeTriple();
  };

  const handleLoadWorkedExample = () => {
    // Find Procarbazine (DB01168), Carmustine (DB00262), Vincristine (DB00541) in drug catalog
    const procarbazine = drugs.find((d) => d.id === 'DB01168') || { id: 'DB01168', name: 'Procarbazine' };
    const carmustine = drugs.find((d) => d.id === 'DB00262') || { id: 'DB00262', name: 'Carmustine' };
    const vincristine = drugs.find((d) => d.id === 'DB00541') || { id: 'DB00541', name: 'Vincristine' };

    onSelectDrugA(procarbazine);
    onSelectDrugB(carmustine);
    onSelectDrugC(vincristine);
    onSelectCellLine('T98G');
  };

  return (
    <form onSubmit={handleSubmit} className="bg-[#FFFFFF] border border-[#E5E5E0] rounded-lg p-6 shadow-xs space-y-6">
      {/* Formulation Notice Banner */}
      <div className="bg-[#F0FDFA] border border-[#99F6E4] rounded-md p-3.5 flex items-start gap-2.5 text-xs text-[#0F766E] leading-relaxed">
        <Info className="w-4 h-4 shrink-0 text-[#0D9488] mt-0.5" />
        <div>
          <span className="font-semibold block text-[#0D9488] mb-0.5">
            Targeted Three-Drug Composed Analysis (Phase C1)
          </span>
          Direct evaluation of three user-specified compounds. Constituent pairs (A×B, A×C, B×C) are evaluated via calibrated GNN inference and scored via multi-objective V(pair) composite ranking.
          <span className="block mt-1 italic font-semibold text-[11px] text-[#0F766E]">
            "We compose pair scores; we do not have DrugComb 3-way synergy labels."
          </span>
        </div>
      </div>

      {/* Preset Worked Example Quick Action */}
      <div className="flex items-center justify-between bg-[#F8FAFC] border border-[#E2E8F0] rounded-md px-4 py-2.5">
        <div className="flex items-center gap-2 text-xs text-[#334155]">
          <Sparkles className="w-4 h-4 text-[#0D9488] shrink-0" />
          <span>
            <strong>Reference Triad:</strong> Procarbazine + Carmustine + Vincristine @ T98G (PCV Analog)
          </span>
        </div>
        <button
          type="button"
          onClick={handleLoadWorkedExample}
          className="text-xs bg-[#0D9488]/10 hover:bg-[#0D9488]/20 text-[#0D9488] font-semibold px-3 py-1.5 rounded transition-colors cursor-pointer"
        >
          Load Worked Example
        </button>
      </div>

      {/* 3 Compound Pickers */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <DrugSelectInput
          label="Compound A"
          selectedDrug={drugA}
          onSelect={onSelectDrugA}
          drugs={drugs}
          placeholder="Select Compound A..."
          disabled={isLoading}
        />

        <DrugSelectInput
          label="Compound B"
          selectedDrug={drugB}
          onSelect={onSelectDrugB}
          drugs={drugs}
          placeholder="Select Compound B..."
          disabled={isLoading}
        />

        <DrugSelectInput
          label="Compound C"
          selectedDrug={drugC}
          onSelect={onSelectDrugC}
          drugs={drugs}
          placeholder="Select Compound C..."
          disabled={isLoading}
        />
      </div>

      {/* Client-side Duplicate Warning */}
      {duplicateWarning && (
        <div className="bg-[#FEF2F2] border border-[#FECACA] rounded-md p-3.5 flex items-center gap-2.5 text-xs text-[#B91C1C]">
          <AlertTriangle className="w-4 h-4 shrink-0 text-[#EF4444]" />
          <span>{duplicateWarning}</span>
        </div>
      )}

      {/* Cell Line Selector */}
      <div className="max-w-md">
        <CellLineDropdown
          status={cellLineStatus}
          selectedCellLine={cellLine}
          onSelect={onSelectCellLine}
          disabled={isLoading}
        />
      </div>

      {/* Submit Button */}
      <div className="pt-4 border-t border-[#F4F4F1] flex justify-end">
        <button
          type="submit"
          disabled={!canSubmit}
          className="px-6 py-3 bg-[#0D9488] hover:bg-[#0F766E] disabled:bg-[#94A3B8] text-[#FFFFFF] font-semibold text-sm rounded-md shadow-xs flex items-center gap-2 transition-colors cursor-pointer"
        >
          <Play className="w-4 h-4 fill-current" />
          Analyze Triple Combination
        </button>
      </div>
    </form>
  );
};
