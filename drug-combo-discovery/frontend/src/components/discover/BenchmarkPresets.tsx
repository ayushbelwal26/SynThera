import { Bookmark, Sparkles } from "lucide-react";
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
    <div className="bench-panel p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Bookmark className="w-4 h-4 text-[var(--color-accent)]" />
          <span className="bench-label">Benchmark Reference Pairs</span>
        </div>
        <span className="font-mono text-[11px] text-[var(--color-text-muted)] flex items-center gap-1">
          <Sparkles size={11} className="text-[var(--color-accent)]" />
          Pre-validated
        </span>
      </div>

      <div className="divide-y divide-[var(--color-rule)]/60">
        {BENCHMARKS.map((preset) => {
          const isSyn = preset.expectedClass === "synergy";
          const isAnt = preset.expectedClass === "antagonism";

          return (
            <button
              key={preset.id}
              type="button"
              disabled={disabled}
              onClick={() => onSelect(preset)}
              className="w-full text-left py-3 px-2 rounded hover:bg-[var(--color-accent-soft)]/40 disabled:opacity-50 flex items-center justify-between gap-3 transition-colors cursor-pointer group"
            >
              <div className="min-w-0">
                <span className="font-serif text-[14.5px] font-semibold text-[var(--color-text-primary)] group-hover:text-[var(--color-accent)] transition-colors">
                  {preset.drugA.name}{" "}
                  <span className="text-[var(--color-accent)] font-sans">
                    +
                  </span>{" "}
                  {preset.drugB.name}
                </span>
                <div className="flex items-center gap-2 mt-0.5 text-[11.5px]">
                  <span className="font-mono px-1.5 py-0.2 rounded bg-[var(--color-panel)] border border-[var(--color-rule)] text-[var(--color-text-secondary)] font-medium">
                    {preset.cellLine}
                  </span>
                  <span className="text-[var(--color-text-muted)]">
                    {preset.indication}
                  </span>
                </div>
              </div>

              <span
                className={`font-mono text-[11px] font-semibold uppercase px-2.5 py-1 rounded-full border shrink-0 transition-all ${
                  isSyn
                    ? "bg-[var(--color-accent-soft)] text-[var(--color-accent)] border-[var(--color-accent)] group-hover:shadow-[0_0_10px_var(--color-accent-glow)]"
                    : isAnt
                      ? "bg-[var(--color-antagonism)]/10 text-[var(--color-antagonism)] border-[var(--color-antagonism)]/40"
                      : "bg-[var(--color-additive)]/10 text-[var(--color-additive)] border-[var(--color-additive)]/40"
                }`}
              >
                {preset.expectedClass}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
};
