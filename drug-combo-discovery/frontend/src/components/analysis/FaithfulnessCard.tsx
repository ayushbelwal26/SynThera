import type { PredictionResult } from "../../types/api";

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
    sufficiencyRetained > 1.5
      ? sufficiencyRetained / 100
      : sufficiencyRetained;
  const nec =
    Math.abs(necessityDelta) > 1.5
      ? Math.abs(necessityDelta) / 100
      : Math.abs(necessityDelta);

  return (
    <div>
      {!isAvailable ? (
        <p className="meta-text">
          Faithfulness ablation not yet available for this record.
        </p>
      ) : errorMsg ? (
        <p className="text-[13px] text-[#A84B4B]">
          Ablation error: {errorMsg}
        </p>
      ) : (
        <div className="space-y-5">
          <div className="flex items-baseline justify-between gap-2">
            <span className="bench-label">Verdict</span>
            <span
              className={`text-[13px] font-medium ${
                isVerified ? "text-[#1A535C]" : "text-[#8B7355]"
              }`}
            >
              {isVerified ? "Supported" : "Needs review"}
            </span>
          </div>

          <div>
            <div className="flex items-baseline justify-between mb-1.5">
              <span className="bench-label">Sufficiency</span>
              <span className="metric-value text-[15px]">{suf.toFixed(2)}</span>
            </div>
            <div className="h-2.5 w-full bg-[#E8EDE0]">
              <div
                className="h-full bg-[#1A535C]"
                style={{ width: `${Math.min(100, suf * 100)}%` }}
              />
            </div>
          </div>

          <div>
            <div className="flex items-baseline justify-between mb-1.5">
              <span className="bench-label">Necessity</span>
              <span className="metric-value text-[15px]">{nec.toFixed(2)}</span>
            </div>
            <div className="h-2.5 w-full bg-[#E8EDE0]">
              <div
                className="h-full bg-[#1A535C]"
                style={{ width: `${Math.min(100, nec * 100)}%` }}
              />
            </div>
          </div>

          {f?.rationale && (
            <p className="text-[14px] text-[#4A524C] leading-relaxed border-t border-[#CFC9BC] pt-3 font-sans">
              {f.rationale}
            </p>
          )}
        </div>
      )}
    </div>
  );
};
