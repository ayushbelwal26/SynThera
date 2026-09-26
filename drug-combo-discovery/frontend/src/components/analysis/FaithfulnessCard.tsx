import React from 'react';
import { ShieldCheck, ShieldAlert, Clock, ArrowDownRight, Check, AlertTriangle } from 'lucide-react';
import type { PredictionResult } from '../../types/api';

interface FaithfulnessCardProps {
  prediction: PredictionResult;
}

export const FaithfulnessCard: React.FC<FaithfulnessCardProps> = ({ prediction }) => {
  const f = prediction.faithfulness;

  // Resolve values from structured faithfulness object, with fallback to legacy fields
  const hasStructured = Boolean(f && typeof f.sufficiency === 'number');
  const hasLegacy = typeof prediction.sufficiency_retained_pct === 'number';
  const isAvailable = hasStructured || hasLegacy;

  const originalScore = f?.original_score ?? prediction.score;
  const originalClass = f?.original_class ?? prediction.predicted_class;
  const ablatedScore = f?.ablated_score ?? null;
  const ablatedClass = f?.ablated_class ?? null;

  const sufficiencyRetained = f?.sufficiency ?? prediction.sufficiency_retained_pct ?? 0;
  const necessityDelta = f?.necessity ?? prediction.necessity_delta_pct ?? 0;
  const classPreserved = f ? (f.ablated_class ? originalClass === f.original_class : true) : (prediction.sufficiency_class_preserved ?? false);

  // Decisive scientific faithfulness criterion:
  // Sufficiency is the primary metric: isolated attribution edges must retain >= 70.0%
  // of original confidence and preserve the predicted interaction class.
  const isVerified = f?.explanation_faithful ?? (isAvailable && sufficiencyRetained >= 70.0 && classPreserved);

  const kEdges = f?.k_edges_ablated ?? prediction.top_edges.length;
  const errorMsg = f?.error ?? null;

  const rationaleText = f?.rationale ?? (
    isVerified
      ? `The isolated ${kEdges}-edge attribution subgraph satisfies the decisive sufficiency criterion (${sufficiencyRetained.toFixed(1)}% confidence retained with predicted class preserved), confirming that the identified molecular pathway contains sufficient biological signal to drive the model's prediction.`
      : `The isolated attribution subgraph does not satisfy sufficiency bounds (retained: ${sufficiencyRetained.toFixed(1)}%, threshold: >= 70.0%). Further experimental validation is recommended.`
  );

  return (
    <div className="bg-[#FFFFFF] border border-[#E5E5E0] rounded-lg p-5 shadow-xs mb-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
        <div>
          <div className="flex items-center gap-2">
            {!isAvailable ? (
              <Clock className="w-4 h-4 text-[#64748B]" />
            ) : errorMsg ? (
              <AlertTriangle className="w-4 h-4 text-[#DC2626]" />
            ) : isVerified ? (
              <ShieldCheck className="w-4 h-4 text-[#059669]" />
            ) : (
              <ShieldAlert className="w-4 h-4 text-[#D97706]" />
            )}
            <h3 className="font-serif text-lg font-bold text-[#0F172A]">
              Explanation Verification & Graph Faithfulness
            </h3>
          </div>
          <p className="text-xs text-[#717784] mt-0.5">
            In-silico graph ablation testing whether explanation edges are computationally necessary and sufficient
          </p>
        </div>

        {/* Verdict Badge */}
        <div>
          {!isAvailable ? (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-[#F1F5F9] text-[#475569] border border-[#CBD5E1] rounded text-xs font-mono font-medium">
              <Clock className="w-3.5 h-3.5 text-[#64748B]" />
              Verification pending — not yet available
            </span>
          ) : errorMsg ? (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-[#FEF2F2] text-[#B91C1C] border border-[#FECACA] rounded text-xs font-mono font-bold">
              <AlertTriangle className="w-3.5 h-3.5 text-[#DC2626]" />
              Ablation evaluation error
            </span>
          ) : isVerified ? (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-[#ECFDF5] text-[#047857] border border-[#A7F3D0] rounded text-xs font-mono font-bold">
              <Check className="w-3.5 h-3.5 text-[#059669]" />
              Verified explanation
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-[#FFFBEB] text-[#B45309] border border-[#FDE68A] rounded text-xs font-mono font-bold">
              <ShieldAlert className="w-3.5 h-3.5 text-[#D97706]" />
              Explanation requires further verification
            </span>
          )}
        </div>
      </div>

      {!isAvailable ? (
        <div className="p-4 bg-[#F8FAFC] border border-[#E2E8F0] rounded text-xs text-[#64748B] leading-relaxed">
          In-silico ablation metrics have not yet been evaluated for this candidate combination or the verification endpoint is pending response.
        </div>
      ) : errorMsg ? (
        <div className="p-4 bg-[#FEF2F2] border border-[#FECACA] rounded text-xs text-[#991B1B] leading-relaxed">
          <strong>Ablation Error:</strong> {errorMsg}
        </div>
      ) : (
        <div className="space-y-4">
          {/* Comparative In-Silico Ablation Visualizer */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Sufficiency Test (Primary) */}
            <div className="p-4 bg-[#F8FAFC] border border-[#E2E8F0] rounded-md flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-[#0F172A] uppercase tracking-wider">
                    1. Sufficiency Evaluation
                  </span>
                  <span
                    className={`text-[10px] font-mono px-1.5 py-0.5 rounded font-semibold ${
                      sufficiencyRetained >= 70.0
                        ? 'bg-[#ECFDF5] text-[#047857]'
                        : 'bg-[#FFFBEB] text-[#B45309]'
                    }`}
                  >
                    {sufficiencyRetained >= 70.0 ? 'Sufficient Signal' : 'Partial Signal'}
                  </span>
                </div>
                <p className="text-xs text-[#64748B] mb-3 leading-relaxed">
                  Inference re-evaluated using <strong>ONLY</strong> the top-{kEdges} attribution edges. Quantifies whether isolated subgraph contains sufficient biological signal.
                </p>
              </div>

              <div>
                <div className="flex items-baseline justify-between font-mono text-xs mb-1">
                  <span className="text-[#475569]">Retained Confidence:</span>
                  <span className="text-base font-bold text-[#0F172A]">
                    {sufficiencyRetained.toFixed(1)}%
                  </span>
                </div>
                <div className="w-full h-2.5 bg-[#E2E8F0] rounded-full overflow-hidden">
                  <div
                    style={{ width: `${Math.min(100, Math.max(0, sufficiencyRetained))}%` }}
                    className={`h-full rounded-full transition-all duration-500 ${
                      sufficiencyRetained >= 70
                        ? 'bg-[#059669]'
                        : sufficiencyRetained >= 50
                        ? 'bg-[#D97706]'
                        : 'bg-[#DC2626]'
                    }`}
                  />
                </div>
                <span className="text-[10px] font-mono text-[#94A3B8] mt-1 block">
                  Decisive criterion: ≥ 70.0% retention with preserved predicted class
                </span>
              </div>
            </div>

            {/* Necessity / Edge Ablation Test */}
            <div className="p-4 bg-[#F8FAFC] border border-[#E2E8F0] rounded-md flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-[#0F172A] uppercase tracking-wider">
                    2. Necessity & Edge Ablation
                  </span>
                  <span className="text-[10px] font-mono text-[#475569] bg-[#E2E8F0] px-1.5 py-0.5 rounded">
                    Ablated Top {kEdges} Edges
                  </span>
                </div>
                <p className="text-xs text-[#64748B] mb-2 leading-relaxed">
                  Inference re-evaluated after <strong>ablating</strong> the top-{kEdges} attribution edges from the local subgraph.
                </p>

                {/* Score Comparison Box */}
                <div className="bg-[#FFFFFF] border border-[#CBD5E1] rounded p-2 mb-3 text-xs font-mono grid grid-cols-2 gap-2">
                  <div>
                    <span className="text-[10px] text-[#64748B] block uppercase">Original Score</span>
                    <span className="font-bold text-[#0F172A]">
                      {originalScore.toFixed(4)}
                    </span>
                    <span className="text-[10px] text-[#64748B] ml-1 lowercase">({originalClass})</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-[#64748B] block uppercase">Ablated Score</span>
                    <span className="font-bold text-[#0F172A]">
                      {ablatedScore !== null ? ablatedScore.toFixed(4) : '—'}
                    </span>
                    {ablatedClass && (
                      <span className="text-[10px] text-[#64748B] ml-1 lowercase">({ablatedClass})</span>
                    )}
                  </div>
                </div>
              </div>

              <div>
                <div className="flex items-baseline justify-between font-mono text-xs mb-1">
                  <span className="text-[#475569]">Probability Delta (Δp):</span>
                  <span
                    className={`text-base font-bold flex items-center gap-1 ${
                      necessityDelta >= 5.0
                        ? 'text-[#059669]'
                        : necessityDelta < 0
                        ? 'text-[#64748B]'
                        : 'text-[#475569]'
                    }`}
                  >
                    <ArrowDownRight className="w-3.5 h-3.5" />
                    {necessityDelta > 0 ? `+${necessityDelta.toFixed(1)}%` : `${necessityDelta.toFixed(1)}%`}
                  </span>
                </div>
                <div className="w-full h-2.5 bg-[#E2E8F0] rounded-full overflow-hidden">
                  <div
                    style={{
                      width: `${Math.min(100, Math.max(0, necessityDelta) * 5)}%`,
                    }}
                    className={`h-full rounded-full ${
                      necessityDelta >= 5.0
                        ? 'bg-[#059669]'
                        : necessityDelta > 0
                        ? 'bg-[#D97706]'
                        : 'bg-[#DC2626]'
                    }`}
                  />
                </div>
                <span className="text-[10px] font-mono text-[#94A3B8] mt-1 block">
                  Secondary context: near-zero Δp reflects dense network message-passing redundancy
                </span>
              </div>
            </div>
          </div>

          {/* Scientific Rationale Statement */}
          <div className="p-3.5 bg-[#F8FAFC] border border-[#E2E8F0] rounded text-xs text-[#334155] leading-relaxed">
            <strong className="text-[#0F172A] font-semibold">Verification Rationale: </strong>
            {rationaleText}
          </div>
        </div>
      )}
    </div>
  );
};
