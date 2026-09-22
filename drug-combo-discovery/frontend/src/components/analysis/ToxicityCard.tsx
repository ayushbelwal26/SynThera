import React, { useState } from 'react';
import {
  ShieldCheck,
  AlertTriangle,
  HelpCircle,
  ChevronDown,
  ChevronUp,
  Database,
  Sliders,
  CheckCircle2,
  XCircle,
  Lock,
  Layers,
} from 'lucide-react';
import type { PredictionResult } from '../../types/api';
import { ToxicityBadge } from '../common/ToxicityBadge';

interface ToxicityCardProps {
  prediction: PredictionResult;
}

export const ToxicityCard: React.FC<ToxicityCardProps> = ({ prediction }) => {
  const [weightsOpen, setWeightsOpen] = useState(false);

  const ranking = prediction.ranking;
  const breakdown = ranking?.breakdown;
  const weights = ranking?.weights;

  // Extract fields with strict null-preservation
  const hasKnownDdi = breakdown ? breakdown.has_known_ddi : null;
  const sideEffectOverlap = breakdown ? breakdown.side_effect_overlap : null;
  const sharedCount = breakdown?.shared_side_effects_count;
  const topSharedSideEffects = breakdown?.top_shared_side_effects;
  const unknownRiskApplied = breakdown ? breakdown.unknown_risk_applied : true;
  const sourceCoverage = breakdown?.source_coverage;
  const redundancyAvailable = breakdown?.redundancy_available ?? false;
  const redundancyPenalty = ranking?.redundancy_penalty ?? null;
  const redundancyNote =
    breakdown?.redundancy_note || 'TODO: Precompute target overlap for unindexed candidate pairs';

  // Value function components
  const vScore = prediction.v_score ?? ranking?.v_score ?? prediction.score;
  const pSyn = ranking?.p_synergy ?? prediction.p_synergy;
  const toxPenalty = ranking?.toxicity_penalty ?? null;

  return (
    <div className="bg-[#FFFFFF] border border-[#E5E5E0] rounded-lg p-5 shadow-xs mb-6 space-y-5">
      {/* Header & Multi-Objective Equation Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-[#E5E5E0] pb-4">
        <div>
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <h3 className="text-xs font-semibold text-[#0F172A] uppercase tracking-wider">
              Phase B Toxicity & Multi-Objective Ranking
            </h3>
            <ToxicityBadge
              hasKnownDdi={hasKnownDdi}
              unknownRiskApplied={unknownRiskApplied}
              sideEffectOverlap={sideEffectOverlap}
              toxicityPenalty={toxPenalty}
              size="sm"
            />
          </div>
          <p className="text-[11px] text-[#64748B]">
            Tri-objective evaluation balancing calibrated synergy against adverse DDI risks, phenotypic SIDER overlap, and target redundancy
          </p>
        </div>

        {/* Live V(pair) Score Capsule */}
        <div className="flex items-center gap-3 bg-[#F8FAFC] border border-[#E2E8F0] px-3.5 py-2 rounded-md font-mono text-xs shrink-0">
          <div>
            <span className="text-[9px] uppercase text-[#64748B] block font-sans">
              Composite V(pair)
            </span>
            <span className="font-bold text-sm text-[#0D9488]">
              {vScore.toFixed(4)}
            </span>
          </div>
          <div className="h-6 w-px bg-[#CBD5E1]" />
          <div>
            <span className="text-[9px] uppercase text-[#64748B] block font-sans">
              p(Synergy)
            </span>
            <span className="font-semibold text-xs text-[#059669]">
              {pSyn.toFixed(4)}
            </span>
          </div>
          {toxPenalty !== null && (
            <>
              <div className="h-6 w-px bg-[#CBD5E1]" />
              <div>
                <span className="text-[9px] uppercase text-[#64748B] block font-sans">
                  Tox Penalty
                </span>
                <span
                  className={`font-semibold text-xs ${
                    toxPenalty > 0.4 ? 'text-[#DC2626]' : toxPenalty > 0.1 ? 'text-[#D97706]' : 'text-[#059669]'
                  }`}
                >
                  {toxPenalty.toFixed(4)}
                </span>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Grid: 1. DDI Status | 2. SIDER Overlap | 3. Redundancy */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* 1. Drug-Drug Interaction (DDI) Status */}
        <div
          className={`p-4 rounded-lg border transition-all ${
            hasKnownDdi === true
              ? 'bg-[#FEF2F2]/60 border-[#FECACA]'
              : hasKnownDdi === false
              ? 'bg-[#ECFDF5]/60 border-[#A7F3D0]'
              : 'bg-[#FFFBEB]/60 border-[#FDE68A]'
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-[#475569] flex items-center gap-1.5">
              {hasKnownDdi === true ? (
                <AlertTriangle className="w-3.5 h-3.5 text-[#DC2626]" />
              ) : hasKnownDdi === false ? (
                <ShieldCheck className="w-3.5 h-3.5 text-[#059669]" />
              ) : (
                <HelpCircle className="w-3.5 h-3.5 text-[#D97706]" />
              )}
              DDI Interaction Edge
            </span>
            <span
              className={`text-[9px] font-mono px-1.5 py-0.5 rounded font-bold uppercase ${
                hasKnownDdi === true
                  ? 'bg-[#FEE2E2] text-[#991B1B]'
                  : hasKnownDdi === false
                  ? 'bg-[#D1FAE5] text-[#065F46]'
                  : 'bg-[#FEF3C7] text-[#92400E]'
              }`}
            >
              {hasKnownDdi === true
                ? 'Known DDI'
                : hasKnownDdi === false
                ? 'Safe'
                : 'Unknown'}
            </span>
          </div>

          <div className="font-semibold text-sm mb-1 text-[#0F172A]">
            {hasKnownDdi === true
              ? 'Adverse DDI Documented'
              : hasKnownDdi === false
              ? 'Confirmed Safe Pair'
              : 'Unknown / Unindexed Pair'}
          </div>

          <p className="text-xs text-[#475569] leading-relaxed">
            {hasKnownDdi === true
              ? 'Documented contraindication or adverse interaction edge found in PrimeKG DDI network. Maximum DDI penalty (1.0) applied.'
              : hasKnownDdi === false
              ? 'Both compounds are indexed in PrimeKG DDI topology with zero recorded adverse interactions. Zero DDI penalty (0.0) applied.'
              : 'At least one compound is unindexed in PrimeKG DDI topology. Conservative baseline uncertainty penalty (0.35) applied.'}
          </p>

          <div className="mt-3 pt-2 border-t border-black/5 flex items-center justify-between text-[11px] font-mono text-[#64748B]">
            <span>ddi_risk factor:</span>
            <strong className="text-[#0F172A]">
              {breakdown?.ddi_risk !== undefined ? breakdown.ddi_risk.toFixed(2) : hasKnownDdi === true ? '1.00' : hasKnownDdi === false ? '0.00' : '0.35'}
            </strong>
          </div>
        </div>

        {/* 2. Side-Effect Phenotypic Overlap (SIDER) */}
        <div
          className={`p-4 rounded-lg border transition-all ${
            sideEffectOverlap !== null && sideEffectOverlap !== undefined
              ? 'bg-[#F8FAFC] border-[#E2E8F0]'
              : 'bg-[#FFFBEB]/60 border-[#FDE68A]'
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-[#475569] flex items-center gap-1.5">
              <Database className="w-3.5 h-3.5 text-[#0D9488]" />
              SIDER Phenotypic Overlap
            </span>
            <span
              title={
                sideEffectOverlap !== null && sideEffectOverlap !== undefined
                  ? 'Empirical phenotypic overlap computed from SIDER 4.1 database.'
                  : 'Phenotypic side-effect records for one or both compounds are missing from the SIDER database.'
              }
              className={`text-[9px] font-mono px-1.5 py-0.5 rounded font-bold uppercase ${
                sideEffectOverlap !== null && sideEffectOverlap !== undefined
                  ? 'bg-[#E2E8F0] text-[#334155]'
                  : 'bg-[#FEF3C7] text-[#92400E]'
              }`}
            >
              {sideEffectOverlap !== null && sideEffectOverlap !== undefined
                ? 'SIDER Documented'
                : 'Data Unavailable'}
            </span>
          </div>

          {sideEffectOverlap !== null && sideEffectOverlap !== undefined ? (
            <>
              <div className="flex items-baseline gap-2 mb-1">
                <span className="font-mono text-xl font-bold text-[#0F172A]">
                  {(sideEffectOverlap * 100).toFixed(1)}%
                </span>
                <span className="text-xs text-[#64748B]">Jaccard Overlap</span>
              </div>
              <p className="text-xs text-[#475569] leading-relaxed">
                {sharedCount !== undefined && sharedCount !== null
                  ? `${sharedCount} shared adverse event term${sharedCount === 1 ? '' : 's'} recorded across both compounds in SIDER 4.1.`
                  : 'MedDRA side-effect term intersection evaluated against SIDER 4.1 catalog.'}
              </p>

              {topSharedSideEffects && topSharedSideEffects.length > 0 && (
                <div className="mt-2.5 flex flex-wrap gap-1">
                  {topSharedSideEffects.slice(0, 4).map((se, i) => (
                    <span
                      key={i}
                      className="text-[10px] bg-[#FFFFFF] border border-[#CBD5E1] text-[#334155] px-1.5 py-0.5 rounded font-mono truncate max-w-[140px]"
                      title={se}
                    >
                      {se}
                    </span>
                  ))}
                  {topSharedSideEffects.length > 4 && (
                    <span className="text-[10px] text-[#64748B] px-1 py-0.5 font-mono">
                      +{topSharedSideEffects.length - 4} more
                    </span>
                  )}
                </div>
              )}
            </>
          ) : (
            <>
              <div className="font-semibold text-sm mb-1 text-[#92400E]">
                Side-Effect Data Unavailable
              </div>
              <p className="text-xs text-[#78350F] leading-relaxed">
                Compound side-effect profile is not available in the SIDER 4.1 database. A conservative baseline uncertainty risk penalty (0.15) has been applied.
              </p>
            </>
          )}

          <div className="mt-3 pt-2 border-t border-black/5 flex items-center justify-between text-[11px] font-mono text-[#64748B]">
            <span>se_risk factor:</span>
            <strong className="text-[#0F172A]">
              {breakdown?.se_risk !== undefined ? breakdown.se_risk.toFixed(2) : sideEffectOverlap !== null && sideEffectOverlap !== undefined ? sideEffectOverlap.toFixed(2) : '0.15'}
            </strong>
          </div>
        </div>

        {/* 3. Target / Pathway Redundancy */}
        <div
          className={`p-4 rounded-lg border transition-all ${
            redundancyAvailable && redundancyPenalty !== null
              ? 'bg-[#F8FAFC] border-[#E2E8F0]'
              : 'bg-[#F8FAFC] border-[#E2E8F0]'
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-[#475569] flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-[#7C3AED]" />
              Target Redundancy
            </span>
            <span
              className={`text-[9px] font-mono px-1.5 py-0.5 rounded font-bold uppercase ${
                redundancyAvailable && redundancyPenalty !== null
                  ? 'bg-[#EDE9FE] text-[#5B21B6]'
                  : 'bg-[#F1F5F9] text-[#64748B]'
              }`}
            >
              {redundancyAvailable && redundancyPenalty !== null ? 'Phase A' : 'Pending'}
            </span>
          </div>

          {redundancyAvailable && redundancyPenalty !== null ? (
            <>
              <div className="flex items-baseline gap-2 mb-1">
                <span className="font-mono text-xl font-bold text-[#5B21B6]">
                  {(redundancyPenalty * 100).toFixed(1)}%
                </span>
                <span className="text-xs text-[#64748B]">Target Jaccard</span>
              </div>
              <p className="text-xs text-[#475569] leading-relaxed">
                Target complementarity overlap precomputed from PrimeKG PPI network in Phase A. Subtracted from V(pair) with weight w_redundancy.
              </p>
            </>
          ) : (
            <>
              <div className="font-semibold text-sm mb-1 text-[#475569]">
                Redundancy Penalty: None
              </div>
              <p className="text-xs font-mono text-[#64748B] bg-[#F1F5F9] border border-[#E2E8F0] p-2 rounded leading-relaxed">
                {redundancyNote}
              </p>
            </>
          )}

          <div className="mt-3 pt-2 border-t border-[#E2E8F0] flex items-center justify-between text-[11px] font-mono text-[#64748B]">
            <span>redundancy_penalty:</span>
            <strong className="text-[#0F172A]">
              {redundancyPenalty !== null ? redundancyPenalty.toFixed(4) : 'None'}
            </strong>
          </div>
        </div>
      </div>

      {/* Source Coverage Audit Row */}
      <div className="p-3.5 bg-[#F8FAFC] border border-[#E2E8F0] rounded-lg">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-[#0F172A] flex items-center gap-1.5">
            <Database className="w-3.5 h-3.5 text-[#64748B]" />
            Evidence Source Coverage Matrix
          </span>
          <span className="text-[10px] text-[#64748B] font-mono">
            Auditing whether safety is empirically proven vs. penalized by uncertainty
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 text-xs">
          {/* SIDER */}
          <div className="p-2.5 bg-[#FFFFFF] border border-[#E2E8F0] rounded flex items-center justify-between">
            <div>
              <span className="font-semibold text-[#0F172A] block">SIDER 4.1</span>
              <span className="text-[10px] text-[#64748B]">Phenotypic Side Effects</span>
            </div>
            {sourceCoverage?.sider ? (
              <span className="inline-flex items-center gap-1 text-[11px] font-mono font-medium text-[#059669] bg-[#ECFDF5] px-2 py-0.5 rounded border border-[#A7F3D0]">
                <CheckCircle2 className="w-3 h-3" /> Indexed
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-[11px] font-mono font-medium text-[#B45309] bg-[#FFFBEB] px-2 py-0.5 rounded border border-[#FDE68A]">
                <XCircle className="w-3 h-3" /> Missing
              </span>
            )}
          </div>

          {/* PrimeKG DDI */}
          <div className="p-2.5 bg-[#FFFFFF] border border-[#E2E8F0] rounded flex items-center justify-between">
            <div>
              <span className="font-semibold text-[#0F172A] block">PrimeKG DDI</span>
              <span className="text-[10px] text-[#64748B]">Adverse Interaction Edges</span>
            </div>
            {sourceCoverage?.primekg_ddi ? (
              <span className="inline-flex items-center gap-1 text-[11px] font-mono font-medium text-[#059669] bg-[#ECFDF5] px-2 py-0.5 rounded border border-[#A7F3D0]">
                <CheckCircle2 className="w-3 h-3" /> Indexed
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-[11px] font-mono font-medium text-[#B45309] bg-[#FFFBEB] px-2 py-0.5 rounded border border-[#FDE68A]">
                <XCircle className="w-3 h-3" /> Missing
              </span>
            )}
          </div>

          {/* DrugBank Warnings */}
          <div className="p-2.5 bg-[#FFFFFF] border border-[#E2E8F0] rounded flex items-center justify-between">
            <div>
              <span className="font-semibold text-[#0F172A] block">DrugBank Warnings</span>
              <span className="text-[10px] text-[#64748B]">Commercial Clinical Warnings</span>
            </div>
            {sourceCoverage?.drugbank_warnings ? (
              <span className="inline-flex items-center gap-1 text-[11px] font-mono font-medium text-[#059669] bg-[#ECFDF5] px-2 py-0.5 rounded border border-[#A7F3D0]">
                <CheckCircle2 className="w-3 h-3" /> Licensed
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-[11px] font-mono font-medium text-[#64748B] bg-[#F1F5F9] px-2 py-0.5 rounded border border-[#E2E8F0]">
                <Lock className="w-3 h-3" /> Academic Gated
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Auditable Weights Collapsible */}
      <div className="border border-[#E2E8F0] rounded-lg overflow-hidden">
        <button
          type="button"
          onClick={() => setWeightsOpen(!weightsOpen)}
          className="w-full flex items-center justify-between px-4 py-2.5 bg-[#F8FAFC] hover:bg-[#F1F5F9] transition-colors text-left cursor-pointer"
        >
          <div className="flex items-center gap-2">
            <Sliders className="w-3.5 h-3.5 text-[#0D9488]" />
            <span className="text-xs font-semibold text-[#0F172A]">
              Auditable Objective Weights & Uncertainty Policy (USP Inspectability)
            </span>
          </div>
          <div className="flex items-center gap-1.5 text-xs text-[#64748B]">
            <span className="text-[11px] font-mono">
              w_syn={weights?.w_synergy ?? 1.0}, w_tox={weights?.w_toxicity ?? 0.35}, w_red={weights?.w_redundancy ?? 0.1}
            </span>
            {weightsOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </div>
        </button>

        {weightsOpen && (
          <div className="p-4 bg-[#FFFFFF] border-t border-[#E2E8F0] space-y-3 text-xs">
            <div className="font-mono text-[11px] bg-[#F8FAFC] border border-[#E2E8F0] p-3 rounded leading-relaxed text-[#334155]">
              <div className="font-semibold text-[#0F172A] mb-1">
                Value Function Formulation:
              </div>
              <div>V(pair) = w_synergy &times; p_synergy - w_toxicity &times; toxicity_penalty - w_redundancy &times; redundancy_penalty</div>
              <div className="mt-1 text-[#64748B]">
                toxicity_penalty = &alpha;_ddi &times; ddi_risk + &alpha;_se &times; se_risk
              </div>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 font-mono text-[11px]">
              <div className="p-2 bg-[#F1F5F9] rounded border border-[#E2E8F0]">
                <span className="text-[#64748B] block text-[9px] uppercase">w_synergy</span>
                <span className="font-bold text-[#0F172A]">{weights?.w_synergy ?? 1.0}</span>
              </div>
              <div className="p-2 bg-[#F1F5F9] rounded border border-[#E2E8F0]">
                <span className="text-[#64748B] block text-[9px] uppercase">w_toxicity</span>
                <span className="font-bold text-[#0F172A]">{weights?.w_toxicity ?? 0.35}</span>
              </div>
              <div className="p-2 bg-[#F1F5F9] rounded border border-[#E2E8F0]">
                <span className="text-[#64748B] block text-[9px] uppercase">w_redundancy</span>
                <span className="font-bold text-[#0F172A]">{weights?.w_redundancy ?? 0.10}</span>
              </div>
              <div className="p-2 bg-[#F1F5F9] rounded border border-[#E2E8F0]">
                <span className="text-[#64748B] block text-[9px] uppercase">&alpha;_ddi</span>
                <span className="font-bold text-[#0F172A]">{weights?.alpha_ddi ?? 0.70}</span>
              </div>
              <div className="p-2 bg-[#F1F5F9] rounded border border-[#E2E8F0]">
                <span className="text-[#64748B] block text-[9px] uppercase">&alpha;_se</span>
                <span className="font-bold text-[#0F172A]">{weights?.alpha_se ?? 0.30}</span>
              </div>
            </div>

            <p className="text-[11px] text-[#64748B] leading-relaxed">
              <strong>None-vs-0 Unknown-Risk Invariant:</strong> If DDI status is unindexed (<code className="font-mono text-[#0F172A]">null</code>), <code className="font-mono text-[#0F172A]">ddi_risk</code> is penalized at <strong>0.35</strong> rather than assumed safe (0.0). If SIDER side effects are unindexed, <code className="font-mono text-[#0F172A]">se_risk</code> is penalized at <strong>0.15</strong>, yielding a composite unknown penalty of <strong>0.2800</strong>.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
