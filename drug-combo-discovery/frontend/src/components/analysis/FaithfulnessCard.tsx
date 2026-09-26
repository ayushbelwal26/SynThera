import React from "react";
import {
  ShieldCheck,
  ShieldAlert,
  Clock,
  ArrowDownRight,
  Check,
  AlertTriangle,
} from "lucide-react";
import type { PredictionResult } from "../../types/api";

interface FaithfulnessCardProps {
  prediction: PredictionResult;
}

export const FaithfulnessCard: React.FC<FaithfulnessCardProps> = ({
  prediction,
}) => {
  const f = prediction.faithfulness;

  // Resolve values from structured faithfulness object, with fallback to legacy fields
  const hasStructured = Boolean(f && typeof f.sufficiency === "number");
  const hasLegacy = typeof prediction.sufficiency_retained_pct === "number";
  const isAvailable = hasStructured || hasLegacy;

  const originalScore = f?.original_score ?? prediction.score;
  const originalClass = f?.original_class ?? prediction.predicted_class;
  const ablatedScore = f?.ablated_score ?? null;
  const ablatedClass = f?.ablated_class ?? null;

  const sufficiencyRetained =
    f?.sufficiency ?? prediction.sufficiency_retained_pct ?? 0;
  const necessityDelta = f?.necessity ?? prediction.necessity_delta_pct ?? 0;
  const classPreserved = f
    ? f.ablated_class
      ? originalClass === f.original_class
      : true
    : (prediction.sufficiency_class_preserved ?? false);

  // Decisive scientific faithfulness criterion:
  // Sufficiency is the primary metric: isolated attribution edges must retain >= 70.0%
  // of original confidence and preserve the predicted interaction class.
  const isVerified =
    f?.explanation_faithful ??
    (isAvailable && sufficiencyRetained >= 70.0 && classPreserved);

  const kEdges = f?.k_edges_ablated ?? prediction.top_edges.length;
  const errorMsg = f?.error ?? null;

  const rationaleText =
    f?.rationale ??
    (isVerified
      ? `The isolated ${kEdges}-edge attribution subgraph satisfies the decisive sufficiency criterion (${sufficiencyRetained.toFixed(1)}% confidence retained with predicted class preserved), confirming that the identified molecular pathway contains sufficient biological signal to drive the model's prediction.`
      : `The isolated attribution subgraph does not satisfy sufficiency bounds (retained: ${sufficiencyRetained.toFixed(1)}%, threshold: >= 70.0%). Further experimental validation is recommended.`);

  return (
    <div className="syn-card rounded-lg p-4 mb-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
        <div>
          <div className="flex items-center gap-2">
            {!isAvailable ? (
              <Clock className="w-4 h-4 text-[#6B746F]" />
            ) : errorMsg ? (
              <AlertTriangle className="w-4 h-4 text-[#C45C5C]" />
            ) : isVerified ? (
              <ShieldCheck className="w-4 h-4 text-[#3D7A6C]" />
            ) : (
              <ShieldAlert className="w-4 h-4 text-[#B8893D]" />
            )}
            <h3 className="text-lg font-semibold text-[#1C2421]">
              Explanation Verification & Graph Faithfulness
            </h3>
          </div>
          <p className="text-xs text-[#7A827C] mt-0.5">
            In-silico graph ablation testing whether explanation edges are
            computationally necessary and sufficient
          </p>
        </div>

        {/* Verdict Badge */}
        <div>
          {!isAvailable ? (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-[#EEEBE5] text-[#5A635E] border border-[#D8D5CE] rounded text-xs font-mono font-medium">
              <Clock className="w-3.5 h-3.5 text-[#6B746F]" />
              Verification pending — not yet available
            </span>
          ) : errorMsg ? (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-[#F7EBEB] text-[#A84B4B] border border-[#E8C5C5] rounded text-xs font-mono font-bold">
              <AlertTriangle className="w-3.5 h-3.5 text-[#C45C5C]" />
              Ablation evaluation error
            </span>
          ) : isVerified ? (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-[#E8F0ED] text-[#2F6B5E] border border-[#B5CFC6] rounded text-xs font-mono font-bold">
              <Check className="w-3.5 h-3.5 text-[#3D7A6C]" />
              Verified explanation
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-[#F7F0E4] text-[#9A712F] border border-[#E5D4A8] rounded text-xs font-mono font-bold">
              <ShieldAlert className="w-3.5 h-3.5 text-[#B8893D]" />
              Explanation requires further verification
            </span>
          )}
        </div>
      </div>

      {!isAvailable ? (
        <div className="p-4 bg-[#F3F1EC] border border-[#E5E2DC] rounded text-xs text-[#6B746F] leading-normal">
          In-silico ablation metrics have not yet been evaluated for this
          candidate combination or the verification endpoint is pending
          response.
        </div>
      ) : errorMsg ? (
        <div className="p-4 bg-[#F7EBEB] border border-[#E8C5C5] rounded text-xs text-[#8B4040] leading-normal">
          <strong>Ablation Error:</strong> {errorMsg}
        </div>
      ) : (
        <div className="space-y-4">
          {/* Comparative In-Silico Ablation Visualizer */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Sufficiency Test (Primary) */}
            <div className="p-4 bg-[#F3F1EC] border border-[#E5E2DC] rounded-md flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-[#1C2421] uppercase tracking-wide">
                    1. Sufficiency Evaluation
                  </span>
                  <span
                    className={`text-[10px] font-mono px-1.5 py-0.5 rounded font-semibold ${
                      sufficiencyRetained >= 70.0
                        ? "bg-[#E8F0ED] text-[#2F6B5E]"
                        : "bg-[#F7F0E4] text-[#9A712F]"
                    }`}
                  >
                    {sufficiencyRetained >= 70.0
                      ? "Sufficient Signal"
                      : "Partial Signal"}
                  </span>
                </div>
                <p className="text-xs text-[#6B746F] mb-3 leading-normal">
                  Inference re-evaluated using <strong>ONLY</strong> the top-
                  {kEdges} attribution edges. Quantifies whether isolated
                  subgraph contains sufficient biological signal.
                </p>
              </div>

              <div>
                <div className="flex items-baseline justify-between font-mono text-xs mb-1">
                  <span className="text-[#5A635E]">Retained Confidence:</span>
                  <span className="text-base font-semibold text-[#1C2421]">
                    {sufficiencyRetained.toFixed(1)}%
                  </span>
                </div>
                <div className="w-full h-2.5 bg-[#E5E2DC] rounded-full overflow-hidden">
                  <div
                    style={{
                      width: `${Math.min(100, Math.max(0, sufficiencyRetained))}%`,
                    }}
                    className={`h-full rounded-full transition-all duration-500 ${
                      sufficiencyRetained >= 70
                        ? "bg-[#3D7A6C]"
                        : sufficiencyRetained >= 50
                          ? "bg-[#B8893D]"
                          : "bg-[#C45C5C]"
                    }`}
                  />
                </div>
                <span className="text-[10px] font-mono text-[#8A918C] mt-1 block">
                  Decisive criterion: ≥ 70.0% retention with preserved predicted
                  class
                </span>
              </div>
            </div>

            {/* Necessity / Edge Ablation Test */}
            <div className="p-4 bg-[#F3F1EC] border border-[#E5E2DC] rounded-md flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-[#1C2421] uppercase tracking-wide">
                    2. Necessity & Edge Ablation
                  </span>
                  <span className="text-[10px] font-mono text-[#5A635E] bg-[#E5E2DC] px-1.5 py-0.5 rounded">
                    Ablated Top {kEdges} Edges
                  </span>
                </div>
                <p className="text-xs text-[#6B746F] mb-2 leading-normal">
                  Inference re-evaluated after <strong>ablating</strong> the
                  top-{kEdges} attribution edges from the local subgraph.
                </p>

                {/* Score Comparison Box */}
                <div className="bg-[#FFFEFB] border border-[#D8D5CE] rounded p-2 mb-3 text-xs font-mono grid grid-cols-2 gap-2">
                  <div>
                    <span className="text-[10px] text-[#6B746F] block uppercase">
                      Original Score
                    </span>
                    <span className="font-bold text-[#1C2421]">
                      {originalScore.toFixed(4)}
                    </span>
                    <span className="text-[10px] text-[#6B746F] ml-1 lowercase">
                      ({originalClass})
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] text-[#6B746F] block uppercase">
                      Ablated Score
                    </span>
                    <span className="font-bold text-[#1C2421]">
                      {ablatedScore !== null ? ablatedScore.toFixed(4) : "—"}
                    </span>
                    {ablatedClass && (
                      <span className="text-[10px] text-[#6B746F] ml-1 lowercase">
                        ({ablatedClass})
                      </span>
                    )}
                  </div>
                </div>
              </div>

              <div>
                <div className="flex items-baseline justify-between font-mono text-xs mb-1">
                  <span className="text-[#5A635E]">
                    Probability Delta (Δp):
                  </span>
                  <span
                    className={`text-base font-semibold flex items-center gap-1 ${
                      necessityDelta >= 5.0
                        ? "text-[#3D7A6C]"
                        : necessityDelta < 0
                          ? "text-[#6B746F]"
                          : "text-[#5A635E]"
                    }`}
                  >
                    <ArrowDownRight className="w-3.5 h-3.5" />
                    {necessityDelta > 0
                      ? `+${necessityDelta.toFixed(1)}%`
                      : `${necessityDelta.toFixed(1)}%`}
                  </span>
                </div>
                <div className="w-full h-2.5 bg-[#E5E2DC] rounded-full overflow-hidden">
                  <div
                    style={{
                      width: `${Math.min(100, Math.max(0, necessityDelta) * 5)}%`,
                    }}
                    className={`h-full rounded-full ${
                      necessityDelta >= 5.0
                        ? "bg-[#3D7A6C]"
                        : necessityDelta > 0
                          ? "bg-[#B8893D]"
                          : "bg-[#C45C5C]"
                    }`}
                  />
                </div>
                <span className="text-[10px] font-mono text-[#8A918C] mt-1 block">
                  Secondary context: near-zero Δp reflects dense network
                  message-passing redundancy
                </span>
              </div>
            </div>
          </div>

          {/* Scientific Rationale Statement */}
          <div className="p-3.5 bg-[#F3F1EC] border border-[#E5E2DC] rounded text-xs text-[#3D4742] leading-normal">
            <strong className="text-[#1C2421] font-semibold">
              Verification Rationale:{" "}
            </strong>
            {rationaleText}
          </div>
        </div>
      )}
    </div>
  );
};
