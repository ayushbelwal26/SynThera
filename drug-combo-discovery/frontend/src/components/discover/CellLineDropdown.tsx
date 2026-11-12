import type { CellLineRelevanceStatus } from "../../types/api";
import { ChevronDown } from "lucide-react";

interface CellLineDropdownProps {
  status: CellLineRelevanceStatus;
  selectedCellLine: string;
  onSelect: (cellLine: string) => void;
  disabled?: boolean;
  label?: string;
}

export const CellLineDropdown: React.FC<CellLineDropdownProps> = ({
  status,
  selectedCellLine,
  onSelect,
  disabled = false,
  label = "Cell line",
}) => {
  return (
    <div>
      <div className="flex items-center justify-between mb-1.5">
        <label className="bench-label">{label}</label>
        <span className="font-mono text-[10.5px] px-1.5 py-0.2 rounded bg-[var(--color-accent-soft)] text-[var(--color-accent)] font-semibold">
          {status.cellLines.length} LINES
        </span>
      </div>
      <div className="relative">
        <select
          value={selectedCellLine}
          disabled={disabled}
          onChange={(e) => onSelect(e.target.value)}
          className="bench-input appearance-none cursor-pointer pr-7 font-mono font-medium text-[14px]"
        >
          {status.cellLines.length === 0 && (
            <option value="">No cell lines loaded</option>
          )}
          {status.cellLines.map((cl) => (
            <option
              key={cl}
              value={cl}
              className="bg-[var(--color-panel)] text-[var(--color-text-primary)]"
            >
              {cl}
            </option>
          ))}
        </select>
        <ChevronDown className="w-4 h-4 text-[var(--color-text-muted)] absolute right-1 top-1/2 -translate-y-1/2 pointer-events-none" />
      </div>
      {status.filteringNote && (
        <p className="mt-1.5 font-mono text-[10.5px] text-[var(--color-text-muted)] leading-relaxed">
          {status.filteringNote}
        </p>
      )}
    </div>
  );
};
