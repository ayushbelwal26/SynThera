import type { CellLineRelevanceStatus } from "../../types/api";

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
      <div className="flex items-center justify-between mb-1">
        <label className="bench-label">{label}</label>
        <span className="font-mono text-[10px] text-[#6B746C]">
          {status.cellLines.length} lines
        </span>
      </div>
      <select
        value={selectedCellLine}
        disabled={disabled}
        onChange={(e) => onSelect(e.target.value)}
        className="bench-input appearance-none cursor-pointer"
      >
        {status.cellLines.length === 0 && (
          <option value="">No cell lines loaded</option>
        )}
        {status.cellLines.map((cl) => (
          <option key={cl} value={cl}>
            {cl}
          </option>
        ))}
      </select>
      {status.filteringNote && (
        <p className="mt-1.5 font-mono text-[10px] text-[#6B746C] leading-relaxed">
          {status.filteringNote}
        </p>
      )}
    </div>
  );
};
