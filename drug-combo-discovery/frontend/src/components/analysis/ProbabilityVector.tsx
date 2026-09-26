import React from "react";
import type { PredictionResult } from "../../types/api";

interface ProbabilityVectorProps {
  prediction: PredictionResult;
}

export const ProbabilityVector: React.FC<ProbabilityVectorProps> = ({
  prediction,
}) => {
  const pSyn = prediction.p_synergy ?? 0;
  const pAdd = prediction.p_additive ?? 0;
  const pAnt = prediction.p_antagonism ?? 0;

  const synWidth = Math.max(0, Math.min(100, Math.round(pSyn * 100)));
  const addWidth = Math.max(0, Math.min(100, Math.round(pAdd * 100)));
  const antWidth = Math.max(0, Math.min(100, 100 - synWidth - addWidth));

  return (
    <div className="syn-card rounded-lg p-4 mb-4">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="text-xs font-semibold text-[#1C2421] uppercase tracking-wide">
            Calibrated Class Probability Distribution
          </h3>
          <p className="text-[11px] text-[#7A827C] mt-0.5">
            Probability simplex evaluated via temperature-calibrated softmax
            over GNN logits
          </p>
        </div>
        <span className="font-mono text-xs text-[#5A635E] bg-[#F3F1EC] border border-[#E5E2DC] px-2 py-0.5 rounded">
          Σ p = 1.0000
        </span>
      </div>

      {/* Stacked Probability Bar */}
      <div className="w-full h-4 rounded bg-[#EEEBE5] overflow-hidden flex border border-[#E5E2DC] mb-3">
        {synWidth > 0 && (
          <div
            style={{ width: `${synWidth}%` }}
            className="bg-[#3D7A6C] transition-all duration-500 relative group"
            title={`Synergy: ${(pSyn * 100).toFixed(1)}%`}
          />
        )}
        {addWidth > 0 && (
          <div
            style={{ width: `${addWidth}%` }}
            className="bg-[#B8893D] transition-all duration-500 relative group"
            title={`Additive: ${(pAdd * 100).toFixed(1)}%`}
          />
        )}
        {antWidth > 0 && (
          <div
            style={{ width: `${antWidth}%` }}
            className="bg-[#C45C5C] transition-all duration-500 relative group"
            title={`Antagonism: ${(pAnt * 100).toFixed(1)}%`}
          />
        )}
      </div>

      {/* Numerical Metrics */}
      <div className="grid grid-cols-3 gap-3">
        <div
          className={`p-2.5 rounded border transition-colors ${
            prediction.predicted_class === "synergy"
              ? "bg-[#E8F0ED] border-[#B5CFC6]"
              : "bg-[#F3F1EC] border-[#E5E2DC]"
          }`}
        >
          <div className="flex items-center justify-between mb-1">
            <span className="text-[11px] font-semibold text-[#2F6B5E] uppercase tracking-wide flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-[#3D7A6C]" />
              p(Synergy)
            </span>
            {prediction.predicted_class === "synergy" && (
              <span className="text-[9px] uppercase font-mono px-1 bg-[#D4E5DF] text-[#1F4A40] rounded">
                Predicted
              </span>
            )}
          </div>
          <span className="font-mono text-base font-bold text-[#1F4A40]">
            {pSyn.toFixed(4)}
          </span>
          <span className="text-[10px] font-mono text-[#3D7A6C] ml-1.5">
            ({(pSyn * 100).toFixed(1)}%)
          </span>
        </div>

        <div
          className={`p-2.5 rounded border transition-colors ${
            prediction.predicted_class === "additive"
              ? "bg-[#F7F0E4] border-[#E5D4A8]"
              : "bg-[#F3F1EC] border-[#E5E2DC]"
          }`}
        >
          <div className="flex items-center justify-between mb-1">
            <span className="text-[11px] font-semibold text-[#9A712F] uppercase tracking-wide flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-[#B8893D]" />
              p(Additive)
            </span>
            {prediction.predicted_class === "additive" && (
              <span className="text-[9px] uppercase font-mono px-1 bg-[#F5EFE4] text-[#7A5A28] rounded">
                Predicted
              </span>
            )}
          </div>
          <span className="font-mono text-base font-bold text-[#7A5A28]">
            {pAdd.toFixed(4)}
          </span>
          <span className="text-[10px] font-mono text-[#B8893D] ml-1.5">
            ({(pAdd * 100).toFixed(1)}%)
          </span>
        </div>

        <div
          className={`p-2.5 rounded border transition-colors ${
            prediction.predicted_class === "antagonism"
              ? "bg-[#F7EBEB] border-[#E8C5C5]"
              : "bg-[#F3F1EC] border-[#E5E2DC]"
          }`}
        >
          <div className="flex items-center justify-between mb-1">
            <span className="text-[11px] font-semibold text-[#A84B4B] uppercase tracking-wide flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-[#C45C5C]" />
              p(Antagonism)
            </span>
            {prediction.predicted_class === "antagonism" && (
              <span className="text-[9px] uppercase font-mono px-1 bg-[#F0D6D6] text-[#8B4040] rounded">
                Predicted
              </span>
            )}
          </div>
          <span className="font-mono text-base font-bold text-[#8B4040]">
            {pAnt.toFixed(4)}
          </span>
          <span className="text-[10px] font-mono text-[#C45C5C] ml-1.5">
            ({(pAnt * 100).toFixed(1)}%)
          </span>
        </div>
      </div>
    </div>
  );
};
