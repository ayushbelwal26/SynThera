import type { PredictionResult } from "../../types/api";
import { AlertTriangle, ShieldCheck } from "lucide-react";

interface FaithfulnessCardProps {
  prediction: PredictionResult;
}

export const FaithfulnessCard: React.FC<FaithfulnessCardProps> = ({
  prediction,
}) => {
  const f = prediction.faithfulness;
  const hasStructured = Boolean(f && typeof f.sufficiency === "number");
  const hasLegacy = typeof prediction.sufficiency_retained_pct === "number";
  const isAvailable = hasStructured || hasLegacy;

  const sufficiencyRetained =
    f?.sufficiency ?? prediction.sufficiency_retained_pct ?? 0;
  const necessityDelta = f?.necessity ?? prediction.necessity_delta_pct ?? 0;
  const classPreserved = f
    ? f.ablated_class
      ? f.original_class === prediction.predicted_class
      : true
    : (prediction.sufficiency_class_preserved ?? false);

  const isVerified =
    f?.explanation_faithful ??
    (isAvailable && sufficiencyRetained >= 70.0 && classPreserved);

  const errorMsg = f?.error ?? null;

  // Normalize to 0–1 display if values look like percentages
  const suf =
    sufficiencyRetained > 1.5 ? sufficiencyRetained / 100 : sufficiencyRetained;
  const nec =
    Math.abs(necessityDelta) > 1.5
      ? Math.abs(necessityDelta) / 100
      : Math.abs(necessityDelta);

  return (
    <div className="bench-panel space-y-4">
      {!isAvailable ? (
        <p className="meta-text text-[var(--color-text-muted)]">
          Faithfulness ablation not yet computed for this record.
        </p>
      ) : errorMsg ? (
        <div className="p-3 rounded bg-[var(--color-antagonism)]/10 text-[var(--color-antagonism)] text-[13px] flex items-center gap-2">
          <AlertTriangle size={15} />
          <span>Ablation error: {errorMsg}</span>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-[var(--color-rule)]">
            <span className="bench-label">Ablation Verification</span>
            <div className="flex items-center gap-1.5 font-mono text-[12px] font-bold">
              {isVerified ? (
                <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-[var(--color-accent-soft)] text-[var(--color-accent)] border border-[var(--color-accent)] shadow-[0_0_8px_var(--color-accent-glow)]">
                  <ShieldCheck size={13} />
                  <span>Faithful & Grounded</span>
                </span>
              ) : (
                <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-[var(--color-additive)]/15 text-[var(--color-additive)] border border-[var(--color-additive)]/40">
                  <AlertTriangle size={13} />
                  <span>Under-determined</span>
                </span>
              )}
            </div>
          </div>

          <div className="space-y-3">
            <div>
              <div className="flex items-baseline justify-between mb-1 text-[12px] font-mono">
                <span className="text-[var(--color-text-secondary)]">
                  Sufficiency (Retained on Subgraph)
                </span>
                <span className="metric-value text-[14px] text-[var(--color-accent)]">
                  {(suf * 100).toFixed(1)}%
                </span>
              </div>
              <div className="h-2 w-full rounded-full bg-[var(--color-surface)] border border-[var(--color-rule)] overflow-hidden">
                <div
                  className="h-full rounded-full bg-[var(--color-accent)] shadow-[0_0_6px_var(--color-accent)] transition-all duration-500"
                  style={{ width: `${Math.min(100, suf * 100)}%` }}
                />
              </div>
            </div>

            <div>
              <div className="flex items-baseline justify-between mb-1 text-[12px] font-mono">
                <span className="text-[var(--color-text-secondary)]">
                  Necessity (Drop on Ablation)
                </span>
                <span className="metric-value text-[14px] text-[var(--color-synergy)]">
                  {(nec * 100).toFixed(1)}%
                </span>
              </div>
              <div className="h-2 w-full rounded-full bg-[var(--color-surface)] border border-[var(--color-rule)] overflow-hidden">
                <div
                  className="h-full rounded-full bg-[var(--color-synergy)] transition-all duration-500"
                  style={{ width: `${Math.min(100, nec * 100)}%` }}
                />
              </div>
            </div>
          </div>

          {f?.rationale && (
            <p className="text-[13px] text-[var(--color-text-secondary)] leading-relaxed border-t border-[var(--color-rule)] pt-3 font-sans">
              {f.rationale}
            </p>
          )}
        </div>
      )}
    </div>
  );
};
