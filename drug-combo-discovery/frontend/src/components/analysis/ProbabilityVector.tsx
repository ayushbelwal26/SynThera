import React from 'react';
import type { PredictionResult } from '../../types/api';

interface ProbabilityVectorProps {
  prediction: PredictionResult;
}

export const ProbabilityVector: React.FC<ProbabilityVectorProps> = ({ prediction }) => {
  const pSyn = prediction.p_synergy ?? 0;
  const pAdd = prediction.p_additive ?? 0;
  const pAnt = prediction.p_antagonism ?? 0;

  const synWidth = Math.max(0, Math.min(100, Math.round(pSyn * 100)));
  const addWidth = Math.max(0, Math.min(100, Math.round(pAdd * 100)));
  const antWidth = Math.max(0, Math.min(100, 100 - synWidth - addWidth));

  return (
    <div className="bg-[#FFFFFF] border border-[#E5E5E0] rounded-lg p-5 shadow-xs mb-6">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="text-xs font-semibold text-[#0F172A] uppercase tracking-wider">
            Calibrated Class Probability Distribution
          </h3>
          <p className="text-[11px] text-[#717784] mt-0.5">
            Probability simplex evaluated via temperature-calibrated softmax over GNN logits
          </p>
        </div>
        <span className="font-mono text-xs text-[#475569] bg-[#F8FAFC] border border-[#E2E8F0] px-2 py-0.5 rounded">
          Σ p = 1.0000
        </span>
      </div>

      {/* Stacked Probability Bar */}
      <div className="w-full h-4 rounded bg-[#F1F5F9] overflow-hidden flex border border-[#E2E8F0] mb-3">
        {synWidth > 0 && (
          <div
            style={{ width: `${synWidth}%` }}
            className="bg-[#059669] transition-all duration-500 relative group"
            title={`Synergy: ${(pSyn * 100).toFixed(1)}%`}
          />
        )}
        {addWidth > 0 && (
          <div
            style={{ width: `${addWidth}%` }}
            className="bg-[#D97706] transition-all duration-500 relative group"
            title={`Additive: ${(pAdd * 100).toFixed(1)}%`}
          />
        )}
        {antWidth > 0 && (
          <div
            style={{ width: `${antWidth}%` }}
            className="bg-[#DC2626] transition-all duration-500 relative group"
            title={`Antagonism: ${(pAnt * 100).toFixed(1)}%`}
          />
        )}
      </div>

      {/* Numerical Metrics */}
      <div className="grid grid-cols-3 gap-3">
        <div
          className={`p-2.5 rounded border transition-colors ${
            prediction.predicted_class === 'synergy'
              ? 'bg-[#ECFDF5] border-[#A7F3D0]'
              : 'bg-[#F8FAFC] border-[#E2E8F0]'
          }`}
        >
          <div className="flex items-center justify-between mb-1">
            <span className="text-[11px] font-semibold text-[#047857] uppercase tracking-wider flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-[#059669]" />
              p(Synergy)
            </span>
            {prediction.predicted_class === 'synergy' && (
              <span className="text-[9px] uppercase font-mono px-1 bg-[#D1FAE5] text-[#065F46] rounded">
                Predicted
              </span>
            )}
          </div>
          <span className="font-mono text-base font-bold text-[#065F46]">
            {pSyn.toFixed(4)}
          </span>
          <span className="text-[10px] font-mono text-[#059669] ml-1.5">
            ({(pSyn * 100).toFixed(1)}%)
          </span>
        </div>

        <div
          className={`p-2.5 rounded border transition-colors ${
            prediction.predicted_class === 'additive'
              ? 'bg-[#FFFBEB] border-[#FDE68A]'
              : 'bg-[#F8FAFC] border-[#E2E8F0]'
          }`}
        >
          <div className="flex items-center justify-between mb-1">
            <span className="text-[11px] font-semibold text-[#B45309] uppercase tracking-wider flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-[#D97706]" />
              p(Additive)
            </span>
            {prediction.predicted_class === 'additive' && (
              <span className="text-[9px] uppercase font-mono px-1 bg-[#FEF3C7] text-[#92400E] rounded">
                Predicted
              </span>
            )}
          </div>
          <span className="font-mono text-base font-bold text-[#92400E]">
            {pAdd.toFixed(4)}
          </span>
          <span className="text-[10px] font-mono text-[#D97706] ml-1.5">
            ({(pAdd * 100).toFixed(1)}%)
          </span>
        </div>

        <div
          className={`p-2.5 rounded border transition-colors ${
            prediction.predicted_class === 'antagonism'
              ? 'bg-[#FEF2F2] border-[#FECACA]'
              : 'bg-[#F8FAFC] border-[#E2E8F0]'
          }`}
        >
          <div className="flex items-center justify-between mb-1">
            <span className="text-[11px] font-semibold text-[#B91C1C] uppercase tracking-wider flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-[#DC2626]" />
              p(Antagonism)
            </span>
            {prediction.predicted_class === 'antagonism' && (
              <span className="text-[9px] uppercase font-mono px-1 bg-[#FEE2E2] text-[#991B1B] rounded">
                Predicted
              </span>
            )}
          </div>
          <span className="font-mono text-base font-bold text-[#991B1B]">
            {pAnt.toFixed(4)}
          </span>
          <span className="text-[10px] font-mono text-[#DC2626] ml-1.5">
            ({(pAnt * 100).toFixed(1)}%)
          </span>
        </div>
      </div>
    </div>
  );
};
