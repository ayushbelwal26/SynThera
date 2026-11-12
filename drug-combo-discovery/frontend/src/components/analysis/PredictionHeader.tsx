import React from "react";
import type { PredictionResult } from "../../types/api";
import { Download, Sparkles, Building2 } from "lucide-react";

interface PredictionHeaderProps {
  prediction: PredictionResult;
  disease?: string;
}

export const PredictionHeader: React.FC<PredictionHeaderProps> = ({
  prediction,
  disease,
}) => {
  const handleExportJson = () => {
    const dataStr =
      "data:text/json;charset=utf-8," +
      encodeURIComponent(JSON.stringify(prediction, null, 2));
    const a = document.createElement("a");
    a.setAttribute("href", dataStr);
    a.setAttribute(
      "download",
      `synthera_${prediction.drug_a_name}_${prediction.drug_b_name}_${prediction.cell_line}.json`,
    );
    document.body.appendChild(a);
    a.click();
    a.remove();
  };

  const cls = prediction.predicted_class;
  const isSyn = cls === "synergy";
  const isAnt = cls === "antagonism";

  const pSyn = prediction.p_synergy ?? 0;
  const pAdd = prediction.p_additive ?? 0;
  const pAnt = prediction.p_antagonism ?? 0;
  const primaryP =
    cls === "antagonism" ? pAnt : cls === "additive" ? pAdd : pSyn;

  return (
    <div className="pb-6 mb-6 border-b border-[var(--color-rule)]">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
        {/* Left: Drug pairing title and identification */}
        <div className="space-y-2">
          <div className="flex items-center gap-2.5 flex-wrap">
            <span className="font-mono text-[11px] font-bold uppercase tracking-wider text-[var(--color-accent)] px-2 py-0.5 rounded bg-[var(--color-accent-soft)]">
              Pair Record
            </span>

            <span
              className={`font-mono text-[11.5px] font-bold uppercase tracking-wide px-3 py-0.5 rounded-full border ${
                isSyn
                  ? "bg-[var(--color-accent-soft)] text-[var(--color-accent)] border-[var(--color-accent)] shadow-[0_0_12px_var(--color-accent-glow)]"
                  : isAnt
                    ? "bg-[var(--color-antagonism)]/15 text-[var(--color-antagonism)] border-[var(--color-antagonism)]/50"
                    : "bg-[var(--color-additive)]/15 text-[var(--color-additive)] border-[var(--color-additive)]/50"
              }`}
            >
              {cls}
            </span>

            {disease && (
              <span className="font-mono text-[11px] text-[var(--color-text-muted)] border border-[var(--color-rule)] px-2 py-0.5 rounded bg-[var(--color-panel)]">
                {disease}
              </span>
            )}
          </div>

          <h2 className="font-serif text-[28px] sm:text-[34px] font-bold text-[var(--color-text-primary)] leading-tight tracking-tight">
            {prediction.drug_a_name}
            <span className="text-[var(--color-accent)] mx-2.5 font-light font-sans">
              +
            </span>
            {prediction.drug_b_name}
          </h2>

          <div className="flex items-center gap-2 font-mono text-[12px] text-[var(--color-text-muted)]">
            <span className="px-1.5 py-0.2 rounded bg-[var(--color-panel)] border border-[var(--color-rule)] text-[var(--color-accent)] font-semibold">
              {prediction.drug_a}
            </span>
            <span>/</span>
            <span className="px-1.5 py-0.2 rounded bg-[var(--color-panel)] border border-[var(--color-rule)] text-[var(--color-accent)] font-semibold">
              {prediction.drug_b}
            </span>
            <span>·</span>
            <span className="flex items-center gap-1 text-[var(--color-text-secondary)]">
              <Building2 size={12} />
              {prediction.cell_line}
            </span>
          </div>
        </div>

        {/* Right: Glowing Score ring & Action button */}
        <div className="flex items-center gap-5 shrink-0 flex-wrap">
          {/* Glowing synergy circle */}
          <div className="flex items-center gap-3.5 px-4 py-2.5 rounded-xl border border-[var(--color-rule-strong)] bg-[var(--color-panel)] shadow-[0_0_20px_var(--color-accent-glow)]">
            <div className="w-14 h-14 rounded-full border-2 border-[var(--color-accent)] flex flex-col items-center justify-center bg-[var(--color-surface)] shadow-[0_0_12px_var(--color-accent-glow)] animate-pulse">
              <span className="font-serif text-[18px] font-bold text-[var(--color-accent)] leading-none">
                {primaryP.toFixed(2)}
              </span>
              <span className="font-mono text-[8px] uppercase tracking-wider text-[var(--color-text-muted)] mt-0.5">
                p-score
              </span>
            </div>

            <div className="space-y-0.5">
              <div className="flex items-center gap-1 font-mono text-[11px] font-semibold text-[var(--color-accent)]">
                <Sparkles size={11} />
                <span>HGT Calibrated</span>
              </div>
              <div className="font-mono text-[12px] text-[var(--color-text-secondary)]">
                {prediction.cell_line} Cell Line
              </div>
              <div className="font-mono text-[10.5px] text-[var(--color-text-muted)]">
                PrimeKG Attributed
              </div>
            </div>
          </div>

          <button
            type="button"
            onClick={handleExportJson}
            className="bench-btn-ghost flex items-center gap-1.5 px-3 py-2 text-[12px] font-mono rounded-md border border-[var(--color-rule)] cursor-pointer"
          >
            <Download size={13} />
            <span>Export JSON</span>
          </button>
        </div>
      </div>
    </div>
  );
};
