import { Bookmark } from "lucide-react";
import type { Drug } from "../../types/api";

export interface BenchmarkPreset {
  id: string;
  name: string;
  drugA: Drug;
  drugB: Drug;
  cellLine: string;
  expectedClass: "synergy" | "antagonism" | "additive";
  indication: string;
}

export const BENCHMARKS: BenchmarkPreset[] = [
  {
    id: "benchmark-1",
    name: "Temozolomide × Cyclophosphamide",
    drugA: { id: "DB00853", name: "Temozolomide" },
    drugB: { id: "DB00531", name: "Cyclophosphamide" },
    cellLine: "T98G",
    expectedClass: "synergy",
    indication: "Glioblastoma Multiforme (CNS)",
  },
  {
    id: "benchmark-2",
    name: "Temozolomide × Docetaxel",
    drugA: { id: "DB00853", name: "Temozolomide" },
    drugB: { id: "DB01248", name: "Docetaxel" },
    cellLine: "OVCAR-5",
    expectedClass: "antagonism",
    indication: "Ovarian Carcinoma",
  },
  {
    id: "benchmark-3",
    name: "Docetaxel × Topotecan",
    drugA: { id: "DB01248", name: "Docetaxel" },
    drugB: { id: "DB01030", name: "Topotecan" },
    cellLine: "A498",
    expectedClass: "additive",
    indication: "Renal Cell Carcinoma",
  },
];

interface BenchmarkPresetsProps {
  onSelect: (preset: BenchmarkPreset) => void;
  disabled?: boolean;
}

export const BenchmarkPresets: React.FC<BenchmarkPresetsProps> = ({
  onSelect,
  disabled = false,
}) => {
  return (
    <div>
      <div className="flex items-center gap-2 mb-2">
        <Bookmark className="w-3.5 h-3.5 text-[#1A535C]" />
        <span className="bench-label">Reference pairs</span>
      </div>
      <div className="divide-y divide-[#CFC9BC] border-y border-[#CFC9BC]">
        {BENCHMARKS.map((preset) => (
          <button
            key={preset.id}
            type="button"
            disabled={disabled}
            onClick={() => onSelect(preset)}
            className="w-full text-left py-3 px-0.5 hover:bg-[#E8EDE0]/35 disabled:opacity-50 flex items-baseline justify-between gap-3"
          >
            <div className="min-w-0">
              <span className="font-serif text-[15px] text-[#1A1F1C]">
                {preset.drugA.name} + {preset.drugB.name}
              </span>
              <span className="block meta-text mt-0.5">
                <span className="id-text">{preset.cellLine}</span>
                <span className="text-[#A8A294]"> · </span>
                {preset.indication}
              </span>
            </div>
            <span
              className={`text-[12px] shrink-0 capitalize ${
                preset.expectedClass === "synergy"
                  ? "text-[#1A535C]"
                  : preset.expectedClass === "antagonism"
                    ? "text-[#A84B4B]"
                    : "text-[#8B7355]"
              }`}
            >
              {preset.expectedClass}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
};
