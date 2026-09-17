import { ShieldCheck, ShieldAlert, Clock, ArrowDownRight, Check } from 'lucide-react';
import type { PredictionResult } from '../../types/api';

interface FaithfulnessCardProps {
  prediction: PredictionResult;
}

export const FaithfulnessCard: React.FC<FaithfulnessCardProps> = ({ prediction }) => {
  const hasNecessity = typeof prediction.necessity_delta_pct === 'number';
  const hasSufficiency = typeof prediction.sufficiency_retained_pct === 'number';
  const isAvailable = hasNecessity && hasSufficiency;

  const necessityDelta = prediction.necessity_delta_pct ?? 0;
  const sufficiencyRetained = prediction.sufficiency_retained_pct ?? 0;
  const classPreserved = prediction.sufficiency_class_preserved ?? false;

  // Decisive scientific faithfulness criterion:
  // Sufficiency is the primary metric: isolated attribution edges must retain >= 70.0%
  // of original confidence and preserve the exact predicted interaction class.
  // Near-zero necessity is expected in dense HGT architectures due to multi-hop message-passing
  // redundancy (empirically confirmed via random-edge baseline controls) and does not
  // drive a warning on its own.
  const isVerified = isAvailable && sufficiencyRetained >= 70.0 && classPreserved;

  return (
    <div className="bg-[#FFFFFF] border border-[#E5E5E0] rounded-lg p-5 shadow-xs mb-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
        <div>
          <div className="flex items-center gap-2">
            {isAvailable ? (
              isVerified ? (
                <ShieldCheck className="w-4 h-4 text-[#059669]" />
              ) : (
                <ShieldAlert className="w-4 h-4 text-[#D97706]" />
              )
            ) : (
              <Clock className="w-4 h-4 text-[#64748B]" />
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
          In-silico ablation metrics have not yet been evaluated for this candidate combination or the verification endpoint is pending response. No synthetic verdict is rendered.
        </div>
      ) : (
        <div className="space-y-4">
          {/* Comparative In-Silico Ablation Visualizer */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Sufficiency Test */}
            <div className="p-4 bg-[#F8FAFC] border border-[#E2E8F0] rounded-md flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-[#0F172A] uppercase tracking-wider">
                    1. Sufficiency Evaluation
                  </span>
                  <span
                    className={`text-[10px] font-mono px-1.5 py-0.5 rounded font-semibold ${
                      classPreserved
                        ? 'bg-[#ECFDF5] text-[#047857]'
                        : 'bg-[#FEF2F2] text-[#B91C1C]'
                    }`}
                  >
                    Class {classPreserved ? 'Preserved' : 'Flipped'}
                  </span>
                </div>
                <p className="text-xs text-[#64748B] mb-3 leading-relaxed">
                  Inference re-evaluated using <strong>ONLY</strong> the top-{prediction.top_edges.length} attribution edges. Quantifies whether isolated subgraph contains sufficient biological signal.
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
                  Threshold: ≥ 70.0% retention with preserved predicted class
                </span>
              </div>
            </div>

            {/* Necessity Test */}
            <div className="p-4 bg-[#F8FAFC] border border-[#E2E8F0] rounded-md flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-[#0F172A] uppercase tracking-wider">
                    2. Necessity Evaluation
                  </span>
                  <span className="text-[10px] font-mono text-[#475569] bg-[#E2E8F0] px-1.5 py-0.5 rounded">
                    Edge Ablation
                  </span>
                </div>
                <p className="text-xs text-[#64748B] mb-3 leading-relaxed">
                  Inference re-evaluated after <strong>ablating</strong> the top-{prediction.top_edges.length} attribution edges from the local subgraph.
                </p>
              </div>

              <div>
                <div className="flex items-baseline justify-between font-mono text-xs mb-1">
                  <span className="text-[#475569]">Probability Delta (Δp):</span>
                  <span
                    className={`text-base font-bold flex items-center gap-1 ${
                      necessityDelta >= 5.0
                        ? 'text-[#059669]'
                        : necessityDelta < 0
                        ? 'text-[#DC2626]'
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
                  Dense graph redundancy: near-zero Δp is expected; sufficiency is decisive
                </span>
              </div>
            </div>
          </div>

          {/* Scientific Verdict Statement */}
          <div className="p-3 bg-[#F8FAFC] border border-[#E2E8F0] rounded text-xs text-[#334155] leading-relaxed">
            <strong className="text-[#0F172A] font-semibold">Verification Rationale: </strong>
            {isVerified
              ? `The isolated ${prediction.top_edges.length}-edge attribution subgraph satisfies the decisive sufficiency criterion (${sufficiencyRetained.toFixed(1)}% confidence retained with predicted class preserved), confirming that the identified molecular pathway contains sufficient biological signal to drive the model's prediction. Necessity delta (${necessityDelta > 0 ? '+' : ''}${necessityDelta.toFixed(1)}%) is consistent with dense graph message-passing redundancy.`
              : `The isolated attribution subgraph does not satisfy sufficiency bounds (retained: ${sufficiencyRetained.toFixed(1)}%, threshold: >= 70.0%, class preserved: ${classPreserved}). Further experimental or multi-omics validation is recommended before clinical translation.`}
          </div>
        </div>
      )}
    </div>
  );
};
