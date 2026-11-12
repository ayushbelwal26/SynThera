import React, { useEffect, useRef, useState } from "react";
import type { PredictionResult } from "../../types/api";

interface ProbabilityVectorProps {
  prediction: PredictionResult;
}

function classLabel(cls: string): string {
  if (cls === "synergy") return "Synergy";
  if (cls === "antagonism") return "Antagonism";
  return "Additive";
}

export const ProbabilityVector: React.FC<ProbabilityVectorProps> = ({
  prediction,
}) => {
  const pSyn = prediction.p_synergy ?? 0;
  const pAdd = prediction.p_additive ?? 0;
  const pAnt = prediction.p_antagonism ?? 0;
  const total = pSyn + pAdd + pAnt || 1;
  const v =
    prediction.v_score ?? prediction.ranking?.v_score ?? prediction.score ?? 0;
  const tox = prediction.ranking?.toxicity_penalty;
  const method = prediction.search_method || "beam";

  const primaryP =
    prediction.predicted_class === "antagonism"
      ? pAnt
      : prediction.predicted_class === "additive"
        ? pAdd
        : pSyn;

  // Animated fill on mount
  const [mounted, setMounted] = useState(false);
  const mountRef = useRef(false);
  useEffect(() => {
    if (!mountRef.current) {
      mountRef.current = true;
      requestAnimationFrame(() => setMounted(true));
    }
  }, []);

  const cls = prediction.predicted_class;
  const isSyn = cls === "synergy";
  const isAnt = cls === "antagonism";

  const bars = [
    {
      label: "Synergy",
      p: pSyn,
      pct: (pSyn / total) * 100,
      color: "var(--color-synergy)",
      glow: "0 0 10px var(--color-accent-glow)",
    },
    {
      label: "Additive",
      p: pAdd,
      pct: (pAdd / total) * 100,
      color: "var(--color-additive)",
      glow: "none",
    },
    {
      label: "Antagonism",
      p: pAnt,
      pct: (pAnt / total) * 100,
      color: "var(--color-antagonism)",
      glow: "none",
    },
  ];

  return (
    <div className="bench-panel border-l-4 border-l-[var(--color-accent)] space-y-5">
      {/* Headline */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div>
          <span className="bench-label block mb-1">Predicted Phenotype</span>
          <div className="flex items-baseline gap-2.5">
            <h3 className="font-serif text-[24px] font-bold text-[var(--color-text-primary)]">
              {classLabel(prediction.predicted_class)}
            </h3>
            <span className="font-serif text-[20px] font-semibold text-[var(--color-accent)]">
              p = {primaryP.toFixed(2)}
            </span>
          </div>
        </div>

        <span
          className={`font-mono text-[11px] font-bold uppercase tracking-wider px-3 py-1 rounded-full border ${
            isSyn
              ? "bg-[var(--color-accent-soft)] text-[var(--color-accent)] border-[var(--color-accent)] shadow-[0_0_12px_var(--color-accent-glow)]"
              : isAnt
                ? "bg-[var(--color-antagonism)]/15 text-[var(--color-antagonism)] border-[var(--color-antagonism)]/50"
                : "bg-[var(--color-additive)]/15 text-[var(--color-additive)] border-[var(--color-additive)]/50"
          }`}
        >
          {cls}
        </span>
      </div>

      {/* Stacked probability bar */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-[11px] font-mono text-[var(--color-text-muted)]">
          <span>PROBABILITY VECTOR</span>
          <span>100% MASS</span>
        </div>
        <div className="h-3 w-full rounded-full overflow-hidden flex bg-[var(--color-panel)] border border-[var(--color-rule)] p-0.5">
          {bars.map((bar) => (
            <div
              key={bar.label}
              title={`${bar.label}: ${bar.p.toFixed(2)}`}
              className="h-full rounded-full first:rounded-l-full last:rounded-r-full transition-all duration-700"
              style={{
                width: mounted ? `${bar.pct}%` : "0%",
                background: bar.color,
                boxShadow: bar.glow,
              }}
            />
          ))}
        </div>
      </div>

      {/* Individual probability breakdown */}
      <div className="space-y-2.5 pt-1">
        {bars.map((bar) => (
          <div
            key={bar.label}
            className="flex items-center justify-between gap-3 text-[13px]"
          >
            <div className="flex items-center gap-2">
              <span
                className="w-2.5 h-2.5 rounded-full shrink-0"
                style={{
                  background: bar.color,
                  boxShadow: bar.glow !== "none" ? bar.glow : undefined,
                }}
              />
              <span className="font-sans font-medium text-[var(--color-text-secondary)]">
                {bar.label}
              </span>
            </div>

            <div className="flex items-center gap-3">
              <div className="w-24 h-1.5 rounded-full bg-[var(--color-panel)] border border-[var(--color-rule)] overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-700"
                  style={{
                    width: mounted ? `${bar.pct}%` : "0%",
                    background: bar.color,
                  }}
                />
              </div>
              <span
                className="font-mono text-[12.5px] font-semibold w-10 text-right"
                style={{ color: bar.color }}
              >
                {bar.p.toFixed(2)}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Metric badges grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-[var(--color-rule)]">
        {[
          { label: "V(pair)", value: Number(v).toFixed(2), isAccent: true },
          {
            label: "Toxicity",
            value: tox != null ? Number(tox).toFixed(2) : "0.00",
          },
          {
            label: "Search Rank",
            value: prediction.rank != null ? `#${prediction.rank}` : "Top 1",
          },
          { label: "Traversal", value: method },
        ].map((item) => (
          <div
            key={item.label}
            className="p-2.5 rounded-md bg-[var(--color-surface)] border border-[var(--color-rule)]"
          >
            <span className="bench-label block text-[10px] mb-0.5">
              {item.label}
            </span>
            <span
              className={`metric-value text-[14px] font-mono ${
                item.isAccent
                  ? "text-[var(--color-accent)]"
                  : "text-[var(--color-text-primary)]"
              }`}
            >
              {item.value}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};
