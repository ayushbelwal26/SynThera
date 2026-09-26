import { Download, Clock, Database, Share2 } from "lucide-react";
import type { PredictionResult } from "../../types/api";
import { Badge } from "../common/Badge";
import { ToxicityBadge } from "../common/ToxicityBadge";

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
    const downloadAnchor = document.createElement("a");
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute(
      "download",
      `synthera_${prediction.drug_a_name}_${prediction.drug_b_name}_${prediction.cell_line}.json`,
    );
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  const handleCopySummary = () => {
    const summary = `Synthera Prediction Report:
Compounds: ${prediction.drug_a_name} (${prediction.drug_a}) × ${prediction.drug_b_name} (${prediction.drug_b})
Context: ${prediction.cell_line} ${disease ? `[${disease}]` : ""}
Predicted Class: ${prediction.predicted_class.toUpperCase()} (Calibrated p_synergy: ${prediction.p_synergy.toFixed(4)})
Mechanism: ${prediction.explanation_text}
Faithfulness: Necessity Delta: ${prediction.necessity_delta_pct ?? "N/A"}% | Sufficiency: ${prediction.sufficiency_retained_pct ?? "N/A"}%`;
    navigator.clipboard.writeText(summary);
    alert("Summary copied to clipboard.");
  };

  return (
    <div className="syn-card rounded-lg p-4 mb-4">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1.5 flex-wrap">
            <Badge
              variant={
                prediction.predicted_class === "synergy"
                  ? "synergy"
                  : prediction.predicted_class === "antagonism"
                    ? "antagonism"
                    : "additive"
              }
              size="lg"
            >
              {prediction.predicted_class}
            </Badge>

            {prediction.ranking && (
              <ToxicityBadge
                hasKnownDdi={prediction.ranking.breakdown.has_known_ddi}
                unknownRiskApplied={
                  prediction.ranking.breakdown.unknown_risk_applied
                }
                sideEffectOverlap={
                  prediction.ranking.breakdown.side_effect_overlap
                }
                toxicityPenalty={prediction.ranking.toxicity_penalty}
                size="md"
              />
            )}

            {prediction.cached && (
              <span className="inline-flex items-center gap-1 font-mono text-[10px] text-[#6B746F] bg-[#EEEBE5] border border-[#E5E2DC] px-2 py-0.5 rounded">
                <Database className="w-3 h-3" />
                cached result
              </span>
            )}

            {prediction.timestamp && (
              <span className="inline-flex items-center gap-1 font-mono text-[10px] text-[#6B746F]">
                <Clock className="w-3 h-3" />
                {new Date(prediction.timestamp).toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </span>
            )}
          </div>

          <h2 className="text-2xl font-semibold text-[#1C2421] tracking-tight">
            {prediction.drug_a_name}{" "}
            <span className="text-[#8A918C] font-normal font-sans text-xl">
              ×
            </span>{" "}
            {prediction.drug_b_name}
          </h2>

          <div className="flex items-center gap-3 mt-1.5 text-xs text-[#5A635E] font-mono">
            <span>
              Context:{" "}
              <strong className="text-[#1C2421] font-semibold">
                {prediction.cell_line}
              </strong>
            </span>
            {disease && (
              <>
                <span>&bull;</span>
                <span>
                  Indication:{" "}
                  <strong className="text-[#1C2421]">{disease}</strong>
                </span>
              </>
            )}
            <span>&bull;</span>
            <span className="text-[#6B746F]">
              IDs: {prediction.drug_a} / {prediction.drug_b}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            type="button"
            onClick={handleCopySummary}
            className="px-3 py-2 bg-[#F3F1EC] hover:bg-[#EEEBE5] border border-[#D8D5CE] text-[#3D4742] rounded text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer"
            title="Copy plaintext summary"
          >
            <Share2 className="w-3.5 h-3.5 text-[#6B746F]" />
            Copy Report
          </button>
          <button
            type="button"
            onClick={handleExportJson}
            className="px-3 py-2 bg-[#2F6B5E] hover:bg-[#25564B] text-[#FFFEFB] rounded text-xs font-semibold flex items-center gap-1.5 shadow-xs transition-colors cursor-pointer"
            title="Export complete JSON analysis object"
          >
            <Download className="w-3.5 h-3.5" />
            Export JSON
          </button>
        </div>
      </div>
    </div>
  );
};
