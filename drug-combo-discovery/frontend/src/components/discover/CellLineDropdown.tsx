import { FlaskConical, ChevronDown, Info } from "lucide-react";
import type { CellLineRelevanceStatus } from "../../types/api";

interface CellLineDropdownProps {
  status: CellLineRelevanceStatus;
  selectedCellLine: string;
  onSelect: (cellLine: string) => void;
  disabled?: boolean;
}

export const CellLineDropdown: React.FC<CellLineDropdownProps> = ({
  status,
  selectedCellLine,
  onSelect,
  disabled = false,
}) => {
  return (
    <div>
      <div className="flex items-center justify-between mb-1.5">
        <label className="block text-xs font-semibold text-[#3A4D5C] uppercase tracking-wide">
          Cell Line / Biological Context
        </label>
        <span className="text-[10px] font-mono text-[#6B7C8A]">
          {status.cellLines.length} panel lines
        </span>
      </div>

      <div className="relative">
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <FlaskConical className="w-4 h-4 text-[#6B7C8A]" />
        </div>
        <select
          value={selectedCellLine}
          disabled={disabled}
          onChange={(e) => onSelect(e.target.value)}
          className="w-full pl-9 pr-10 py-2.5 bg-[#FFFFFF] border border-[#D0DCE6] focus:border-[#0D9488] focus:ring-1 focus:ring-[#0D9488] rounded-md text-sm font-mono text-[#1A2B3C] appearance-none outline-none cursor-pointer transition-all disabled:opacity-50"
        >
          {status.cellLines.map((cl) => (
            <option key={cl} value={cl}>
              {cl}
            </option>
          ))}
        </select>
        <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
          <ChevronDown className="w-4 h-4 text-[#6B7C8A]" />
        </div>
      </div>

      {status.filteringNote && (
        <div className="mt-2 flex items-start gap-2 bg-[#EEF5F8] border border-[#E2EAF0] rounded p-2 text-[11px] text-[#5A6B7A]">
          <Info className="w-3.5 h-3.5 text-[#6B7C8A] shrink-0 mt-0.5" />
          <span>{status.filteringNote}</span>
        </div>
      )}
    </div>
  );
};
