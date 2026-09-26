import React, { useState } from "react";
import {
  ShieldCheck,
  AlertTriangle,
  HelpCircle,
  ChevronDown,
  ChevronUp,
  Database,
  CheckCircle2,
  Lock,
  Layers,
  Network,
  Pill,
} from "lucide-react";
import type { PredictionResult } from "../../types/api";
import { ToxicityBadge } from "../common/ToxicityBadge";

interface ToxicityCardProps {
  prediction: PredictionResult;
}

/** Horizontal gauge — value in [0,1], no invented good/bad labels */
function ScoreGauge({ value, color }: { value: number; color: string }) {
  const pct = Math.max(0, Math.min(100, value * 100));
  return (
    <div className="w-full h-1.5 rounded-full bg-[#E5E2DC] overflow-hidden mt-2">
      <div
        className="h-full rounded-full transition-all duration-500"
        style={{ width: `${pct}%`, backgroundColor: color }}
      />
    </div>
  );
}

export const ToxicityCard: React.FC<ToxicityCardProps> = ({ prediction }) => {
  const [sharedOpen, setSharedOpen] = useState(false);
  const [ddiDetailsOpen, setDdiDetailsOpen] = useState(false);
  const [sourcesOpen, setSourcesOpen] = useState(false);
  const [weightsOpen, setWeightsOpen] = useState(false);
  const [caveatOpen, setCaveatOpen] = useState(false);

  const ranking = prediction.ranking;
  const breakdown = ranking?.breakdown;
  const weights = ranking?.weights;

  const hasKnownDdi = breakdown ? breakdown.has_known_ddi : null;
  const sideEffectOverlap = breakdown ? breakdown.side_effect_overlap : null;
  const sharedCount = breakdown?.shared_side_effects_count ?? null;
  const topSharedSideEffects = breakdown?.top_shared_side_effects ?? [];
  const unknownRiskApplied = breakdown ? breakdown.unknown_risk_applied : true;
  const sourceCoverage = breakdown?.source_coverage;
  const redundancyAvailable = breakdown?.redundancy_available ?? false;
  const redundancyPenalty = ranking?.redundancy_penalty ?? null;
  const hasRedundancy = redundancyAvailable && redundancyPenalty !== null;

  const vScore = prediction.v_score ?? ranking?.v_score ?? prediction.score;
  const pSyn = ranking?.p_synergy ?? prediction.p_synergy;
  const toxPenalty = ranking?.toxicity_penalty ?? null;

  const ddiRisk =
    breakdown?.ddi_risk !== undefined
      ? breakdown.ddi_risk
      : hasKnownDdi === true
        ? 1
        : hasKnownDdi === false
          ? 0
          : 0.35;

  const seRisk =
    breakdown?.se_risk !== undefined
      ? breakdown.se_risk
      : sideEffectOverlap != null
        ? sideEffectOverlap
        : 0.15;

  const ddiLabel =
    hasKnownDdi === true
      ? "KNOWN DDI"
      : hasKnownDdi === false
        ? "SAFE"
        : "UNKNOWN";
  const ddiColor =
    hasKnownDdi === true
      ? "text-[#C45C5C] bg-[#F7EBEB] border-[#E8C5C5]"
      : hasKnownDdi === false
        ? "text-[#2F6B5E] bg-[#E8F0ED] border-[#B5CFC6]"
        : "text-[#9A712F] bg-[#F7F0E4] border-[#E5D4A8]";

  const wSyn = weights?.w_synergy ?? 1.0;
  const wTox = weights?.w_toxicity ?? 0.35;
  const wRed = weights?.w_redundancy ?? 0.1;
  const wMax = Math.max(wSyn, wTox, wRed, 0.01);

  return (
    <div className="syn-card rounded-xl overflow-hidden">
      {/* Header */}
      <div className="px-4 pt-4 pb-3 border-b border-[#E5E2DC] flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="text-xs font-semibold text-[#1C2421] uppercase tracking-wide">
              Toxicity & Multi-Objective Ranking
            </h3>
            <ToxicityBadge
              hasKnownDdi={hasKnownDdi}
              unknownRiskApplied={unknownRiskApplied}
              sideEffectOverlap={sideEffectOverlap}
              toxicityPenalty={toxPenalty}
              size="sm"
            />
          </div>
          <p className="text-[11px] text-[#6B746F] mt-0.5">
            Tri-objective evaluation: synergy vs DDI risk, SIDER overlap, and
            target redundancy
          </p>
        </div>
        <span
          className={`self-start text-[10px] font-mono font-bold uppercase tracking-wide px-2 py-1 rounded border ${ddiColor}`}
        >
          {hasKnownDdi === false ? "✓ " : ""}
          {ddiLabel} DDI
        </span>
      </div>

      {/* 1. Pair evaluation scorecard */}
      <div className="px-4 py-4 bg-[#F3F1EC] border-b border-[#E5E2DC]">
        <div className="text-center mb-4 max-w-xl mx-auto">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-[#6B746F]">
            Pair evaluation
          </p>
          <p className="text-[11px] text-[#6B746F] mt-1 leading-normal">
            Summary of the multi-objective value for this pair. Bars show
            relative magnitude of each metric (0–1 scale) — not clinical grades.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-3 sm:gap-5 max-w-2xl mx-auto">
          <div className="text-center px-1">
            <div className="font-mono text-xl sm:text-2xl font-semibold text-[#2F6B5E] tabular-nums">
              {vScore.toFixed(4)}
            </div>
            <div className="text-[11px] font-semibold text-[#1C2421] mt-1">
              Composite score
            </div>
            <div className="text-[10px] text-[#8A918C] font-mono">V(pair)</div>
            <ScoreGauge
              value={Math.min(1, Math.max(0, vScore))}
              color="#2F6B5E"
            />
            <p className="text-[10px] text-[#6B746F] mt-2 leading-snug">
              Synergy reward minus toxicity (and redundancy) penalties
            </p>
          </div>
          <div className="text-center px-1">
            <div className="font-mono text-xl sm:text-2xl font-semibold text-[#3D7A6C] tabular-nums">
              {pSyn.toFixed(4)}
            </div>
            <div className="text-[11px] font-semibold text-[#1C2421] mt-1">
              Synergy probability
            </div>
            <div className="text-[10px] text-[#8A918C] font-mono">
              p(synergy)
            </div>
            <ScoreGauge value={pSyn} color="#3D7A6C" />
            <p className="text-[10px] text-[#6B746F] mt-2 leading-snug">
              Calibrated model probability this pair is synergistic
            </p>
          </div>
          <div className="text-center px-1">
            <div
              className={`font-mono text-xl sm:text-2xl font-semibold tabular-nums ${
                toxPenalty == null
                  ? "text-[#8A918C]"
                  : toxPenalty > 0.4
                    ? "text-[#C45C5C]"
                    : toxPenalty > 0.1
                      ? "text-[#B8893D]"
                      : "text-[#3D7A6C]"
              }`}
            >
              {toxPenalty != null ? toxPenalty.toFixed(4) : "—"}
            </div>
            <div className="text-[11px] font-semibold text-[#1C2421] mt-1">
              Toxicity penalty
            </div>
            <div className="text-[10px] text-[#8A918C] font-mono">penalty</div>
            <ScoreGauge
              value={toxPenalty ?? 0}
              color={
                toxPenalty != null && toxPenalty > 0.4 ? "#C45C5C" : "#B8893D"
              }
            />
            <p className="text-[10px] text-[#6B746F] mt-2 leading-snug">
              Combined DDI + SIDER risk term used in V(pair)
            </p>
          </div>
        </div>
      </div>

      {/* 2. DDI + SIDER row */}
      <div className="grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-[#E5E2DC] border-b border-[#E5E2DC]">
        {/* DDI interaction diagram */}
        <div className="p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] font-semibold uppercase tracking-wide text-[#5A635E] flex items-center gap-1.5">
              {hasKnownDdi === true ? (
                <AlertTriangle className="w-3.5 h-3.5 text-[#C45C5C]" />
              ) : hasKnownDdi === false ? (
                <ShieldCheck className="w-3.5 h-3.5 text-[#3D7A6C]" />
              ) : (
                <HelpCircle className="w-3.5 h-3.5 text-[#B8893D]" />
              )}
              DDI interaction
            </span>
            <span
              className={`text-[9px] font-mono font-bold uppercase px-2 py-0.5 rounded border ${ddiColor}`}
            >
              {ddiLabel}
            </span>
          </div>
          <p className="text-[11px] text-[#6B746F] mb-4 leading-normal">
            Checks whether PrimeKG records an adverse drug–drug interaction edge
            between these two compounds.
          </p>

          {/* Relationship diagram */}
          <div className="flex items-center justify-between gap-2 mb-3 px-1">
            <div className="flex-1 text-center px-2 py-2.5 rounded-lg bg-[#E8F0ED] border border-[#B5CFC6]">
              <div className="text-[9px] uppercase text-[#6B746F] font-semibold">
                Drug A
              </div>
              <div
                className="text-xs font-semibold text-[#1C2421] truncate"
                title={prediction.drug_a_name}
              >
                {prediction.drug_a_name}
              </div>
            </div>
            <div className="flex flex-col items-center shrink-0 px-1">
              <div className="w-10 sm:w-14 h-px bg-[#D8D5CE]" />
              <div
                className={`my-1 w-7 h-7 rounded-full flex items-center justify-center text-sm border ${
                  hasKnownDdi === false
                    ? "bg-[#E8F0ED] border-[#B5CFC6] text-[#3D7A6C]"
                    : hasKnownDdi === true
                      ? "bg-[#F7EBEB] border-[#E8C5C5] text-[#C45C5C]"
                      : "bg-[#F7F0E4] border-[#E5D4A8] text-[#B8893D]"
                }`}
              >
                {hasKnownDdi === false ? "✓" : hasKnownDdi === true ? "!" : "?"}
              </div>
              <div className="w-10 sm:w-14 h-px bg-[#D8D5CE]" />
            </div>
            <div className="flex-1 text-center px-2 py-2.5 rounded-lg bg-[#E8F0ED] border border-[#B5CFC6]">
              <div className="text-[9px] uppercase text-[#6B746F] font-semibold">
                Drug B
              </div>
              <div
                className="text-xs font-semibold text-[#1C2421] truncate"
                title={prediction.drug_b_name}
              >
                {prediction.drug_b_name}
              </div>
            </div>
          </div>

          <div className="text-center mb-3 px-2">
            <div className="text-xs font-semibold text-[#1C2421]">
              {hasKnownDdi === true
                ? "Adverse DDI documented"
                : hasKnownDdi === false
                  ? "0 recorded interactions"
                  : "DDI status unindexed"}
            </div>
            <p className="text-[11px] text-[#6B746F] mt-1 leading-normal">
              {hasKnownDdi === true
                ? "An adverse interaction edge exists in the knowledge graph for this pair."
                : hasKnownDdi === false
                  ? "Both drugs are indexed; no adverse DDI edge was found between them."
                  : "At least one compound is missing from the DDI index — uncertainty is applied."}
            </p>
            <div className="text-[11px] font-mono text-[#5A635E] mt-1.5">
              DDI penalty (ddi_risk) = {ddiRisk.toFixed(2)}
            </div>
          </div>

          <div className="flex items-center justify-between text-[11px] bg-[#F3F1EC] border border-[#E5E2DC] rounded-lg px-3 py-2">
            <span className="flex items-center gap-1.5 text-[#5A635E]">
              <Network className="w-3.5 h-3.5 text-[#2F6B5E]" />
              PrimeKG DDI
            </span>
            {sourceCoverage?.primekg_ddi || hasKnownDdi !== null ? (
              <span className="font-mono font-semibold text-[#3D7A6C] flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" /> Indexed
              </span>
            ) : (
              <span className="font-mono text-[#9A712F]">Missing</span>
            )}
          </div>

          <button
            type="button"
            onClick={() => setDdiDetailsOpen((o) => !o)}
            className="mt-3 text-[11px] font-medium text-[#2F6B5E] flex items-center gap-1 cursor-pointer"
          >
            {ddiDetailsOpen ? (
              <ChevronUp className="w-3.5 h-3.5" />
            ) : (
              <ChevronDown className="w-3.5 h-3.5" />
            )}
            DDI evidence
          </button>
          {ddiDetailsOpen && (
            <p className="mt-2 text-xs text-[#5A635E] leading-normal bg-[#F3F1EC] border border-[#E5E2DC] rounded-lg p-3">
              {hasKnownDdi === true
                ? "Documented contraindication or adverse interaction edge found in PrimeKG DDI network. Maximum DDI risk applied."
                : hasKnownDdi === false
                  ? "Both compounds are indexed in PrimeKG DDI topology with zero recorded adverse interactions. Zero DDI penalty (0.0) applied."
                  : "At least one compound is unindexed in PrimeKG DDI topology. Conservative baseline uncertainty penalty applied."}
              <span className="block mt-1 font-mono text-[10px] text-[#6B746F]">
                ddi_risk = {ddiRisk.toFixed(2)}
              </span>
            </p>
          )}
        </div>

        {/* SIDER overlap visual */}
        <div className="p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] font-semibold uppercase tracking-wide text-[#5A635E] flex items-center gap-1.5">
              <Pill className="w-3.5 h-3.5 text-[#2F6B5E]" />
              SIDER phenotypic overlap
            </span>
          </div>
          <p className="text-[11px] text-[#6B746F] mb-4 leading-normal">
            How much the two drugs’ known side-effect profiles overlap in SIDER
            (Jaccard on MedDRA terms). Higher overlap increases the toxicity
            penalty.
          </p>

          {sideEffectOverlap != null ? (
            <>
              {/* Simple overlap visualization */}
              <div className="flex items-center justify-center gap-0 mb-2 relative h-16">
                <div className="w-24 h-14 rounded-xl bg-[#D4E5DF]/80 border-2 border-[#2F6B5E] flex items-center justify-center z-0 -mr-4">
                  <span className="text-[10px] font-semibold text-[#25564B] px-1 text-center leading-snug">
                    {prediction.drug_a_name.split(" ")[0]}
                  </span>
                </div>
                <div
                  className="absolute left-1/2 -translate-x-1/2 w-10 h-14 rounded-lg bg-[#2F6B5E]/25 border border-[#2F6B5E] z-10 flex items-center justify-center"
                  title={`${sharedCount ?? "—"} shared`}
                >
                  <span className="text-[10px] font-bold text-[#25564B]">
                    {sharedCount != null ? sharedCount : "∩"}
                  </span>
                </div>
                <div className="w-24 h-14 rounded-xl bg-[#F5EFE4]/90 border-2 border-[#B8893D] flex items-center justify-center z-0 -ml-4">
                  <span className="text-[10px] font-semibold text-[#7A5A28] px-1 text-center leading-snug">
                    {prediction.drug_b_name.split(" ")[0]}
                  </span>
                </div>
              </div>
              <p className="text-[10px] text-[#8A918C] text-center mb-3">
                Overlap region = shared adverse-event terms
              </p>

              <div className="text-center mb-3">
                <div className="font-mono text-xl font-semibold text-[#1C2421] tabular-nums">
                  {(sideEffectOverlap * 100).toFixed(1)}%
                </div>
                <div className="text-[11px] text-[#6B746F]">
                  Jaccard overlap
                </div>
                <div className="text-[11px] text-[#5A635E] mt-1">
                  {sharedCount != null
                    ? `${sharedCount} shared adverse event term${sharedCount === 1 ? "" : "s"} in SIDER 4.1`
                    : "Shared terms from SIDER 4.1"}
                </div>
              </div>

              <button
                type="button"
                onClick={() => setSharedOpen((o) => !o)}
                className="w-full text-[11px] font-medium text-[#2F6B5E] flex items-center justify-center gap-1 cursor-pointer py-1.5 border border-[#B5CFC6] rounded-lg bg-[#E8F0ED] hover:bg-[#D4E5DF]"
              >
                {sharedOpen ? (
                  <ChevronUp className="w-3.5 h-3.5" />
                ) : (
                  <ChevronDown className="w-3.5 h-3.5" />
                )}
                Shared adverse events (
                {topSharedSideEffects.length || sharedCount || 0})
              </button>
              {sharedOpen && topSharedSideEffects.length > 0 && (
                <div className="mt-2 pt-2 border-t border-[#E5E2DC]">
                  <div className="text-[10px] font-semibold uppercase tracking-wide text-[#6B746F] mb-2">
                    Shared side effects · {topSharedSideEffects.length}
                  </div>
                  <ul className="space-y-1 max-h-36 overflow-y-auto">
                    {topSharedSideEffects.map((se, i) => (
                      <li
                        key={i}
                        className="text-xs text-[#3D4742] flex items-center gap-2 px-2 py-1 rounded bg-[#F3F1EC]"
                      >
                        <span className="w-1.5 h-1.5 rounded-full bg-[#2F6B5E] shrink-0" />
                        {se}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              <div className="mt-2 text-[10px] font-mono text-[#8A918C] text-right">
                se_risk = {seRisk.toFixed(2)}
              </div>
            </>
          ) : (
            <div className="text-center py-4">
              <HelpCircle className="w-6 h-6 text-[#B8893D] mx-auto mb-2" />
              <div className="text-sm font-semibold text-[#7A5A28]">
                Side-effect data unavailable
              </div>
              <p className="text-xs text-[#6B4E24] mt-1 leading-normal">
                Profile missing in SIDER 4.1 — baseline uncertainty (se_risk ≈
                0.15) applied.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* 3. Target redundancy status */}
      <div className="px-4 py-4 border-b border-[#E5E2DC]">
        <div className="flex items-start gap-3">
          <Layers className="w-4 h-4 text-[#6B746F] mt-0.5 shrink-0" />
          <div className="flex-1 min-w-0">
            <div className="text-[10px] font-semibold uppercase tracking-wide text-[#5A635E] mb-1">
              Target redundancy
            </div>
            <p className="text-[11px] text-[#6B746F] mb-2 leading-normal">
              Measures whether both drugs hit overlapping protein targets
              (complementarity vs redundant mechanism). Separate from DDI and
              SIDER.
            </p>
            {hasRedundancy ? (
              <div className="flex flex-wrap items-baseline gap-3">
                <span className="font-mono text-lg font-semibold text-[#1C2421]">
                  {(redundancyPenalty! * 100).toFixed(1)}%
                </span>
                <span className="text-xs text-[#6B746F]">
                  Target Jaccard · indexed
                </span>
                <span className="text-[11px] font-mono text-[#6B746F]">
                  penalty {redundancyPenalty!.toFixed(4)}
                </span>
              </div>
            ) : (
              <div>
                <div className="inline-flex items-center gap-2 text-xs font-semibold text-[#6B746F] bg-[#EEEBE5] border border-[#E5E2DC] px-2.5 py-1 rounded-md">
                  <span className="w-2 h-2 rounded-full border-2 border-[#8A918C]" />
                  Not indexed
                </div>
                <p className="text-[11px] text-[#6B746F] mt-1.5 leading-normal">
                  No target-overlap evidence is available for this pair. That is
                  not the same as a redundancy score of zero — the term is
                  simply omitted from V(pair).
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 4. Evidence sources — expandable */}
      <div className="border-b border-[#E5E2DC]">
        <button
          type="button"
          onClick={() => setSourcesOpen((o) => !o)}
          className="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-[#F3F1EC] cursor-pointer"
        >
          <span className="text-[10px] font-semibold uppercase tracking-wide text-[#5A635E] flex items-center gap-1.5">
            <Database className="w-3.5 h-3.5" />
            Evidence sources
          </span>
          {sourcesOpen ? (
            <ChevronUp className="w-4 h-4 text-[#6B746F]" />
          ) : (
            <ChevronDown className="w-4 h-4 text-[#6B746F]" />
          )}
        </button>
        {!sourcesOpen && (
          <div className="px-4 pb-3 flex flex-wrap gap-2">
            <span className="text-[10px] font-mono px-2 py-0.5 rounded border border-[#E5E2DC] bg-[#F3F1EC]">
              SIDER {sourceCoverage?.sider ? "✓" : "○"}
            </span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded border border-[#E5E2DC] bg-[#F3F1EC]">
              PrimeKG {sourceCoverage?.primekg_ddi ? "✓" : "○"}
            </span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded border border-[#E5E2DC] bg-[#F3F1EC]">
              DrugBank {sourceCoverage?.drugbank_warnings ? "✓" : "🔒"}
            </span>
          </div>
        )}
        {sourcesOpen && (
          <div className="px-4 pb-4 grid grid-cols-1 sm:grid-cols-3 gap-2.5">
            <div className="p-3 rounded-xl border border-[#E5E2DC] bg-[#F3F1EC]">
              <div className="flex items-center gap-2 mb-1">
                <Pill className="w-4 h-4 text-[#2F6B5E]" />
                <span className="text-xs font-semibold text-[#1C2421]">
                  SIDER 4.1
                </span>
              </div>
              <p className="text-[10px] text-[#6B746F] mb-2">Side effects</p>
              {sourceCoverage?.sider ? (
                <span className="text-[10px] font-mono font-bold text-[#3D7A6C]">
                  ✓ INDEXED
                </span>
              ) : (
                <span className="text-[10px] font-mono font-bold text-[#9A712F]">
                  MISSING
                </span>
              )}
            </div>
            <div className="p-3 rounded-xl border border-[#E5E2DC] bg-[#F3F1EC]">
              <div className="flex items-center gap-2 mb-1">
                <Network className="w-4 h-4 text-[#2F6B5E]" />
                <span className="text-xs font-semibold text-[#1C2421]">
                  PrimeKG DDI
                </span>
              </div>
              <p className="text-[10px] text-[#6B746F] mb-2">DDI edges</p>
              {sourceCoverage?.primekg_ddi ? (
                <span className="text-[10px] font-mono font-bold text-[#3D7A6C]">
                  ✓ INDEXED
                </span>
              ) : (
                <span className="text-[10px] font-mono font-bold text-[#9A712F]">
                  MISSING
                </span>
              )}
            </div>
            <div className="p-3 rounded-xl border border-[#E5E2DC] bg-[#F3F1EC]">
              <div className="flex items-center gap-2 mb-1">
                <Lock className="w-4 h-4 text-[#6B746F]" />
                <span className="text-xs font-semibold text-[#1C2421]">
                  DrugBank
                </span>
              </div>
              <p className="text-[10px] text-[#6B746F] mb-2">Warnings</p>
              {sourceCoverage?.drugbank_warnings ? (
                <span className="text-[10px] font-mono font-bold text-[#3D7A6C]">
                  ✓ LICENSED
                </span>
              ) : (
                <span className="text-[10px] font-mono font-bold text-[#6B746F]">
                  ACADEMIC GATED
                </span>
              )}
            </div>
          </div>
        )}
      </div>

      {/* 5. Objective weights — bars + expand */}
      <div className="border-b border-[#E5E2DC]">
        <button
          type="button"
          onClick={() => setWeightsOpen((o) => !o)}
          className="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-[#F3F1EC] cursor-pointer"
        >
          <span className="text-[10px] font-semibold uppercase tracking-wide text-[#5A635E]">
            Objective weights & uncertainty
          </span>
          {weightsOpen ? (
            <ChevronUp className="w-4 h-4 text-[#6B746F]" />
          ) : (
            <ChevronDown className="w-4 h-4 text-[#6B746F]" />
          )}
        </button>
        <div className="px-4 pb-3 space-y-2">
          <p className="text-[11px] text-[#6B746F] leading-normal mb-1">
            Relative contribution of each term in V(pair). Expand for the exact
            formula and α coefficients.
          </p>
          {(
            [
              { label: "Synergy", key: "w_syn", val: wSyn, color: "#3D7A6C" },
              { label: "Toxicity", key: "w_tox", val: wTox, color: "#B8893D" },
              {
                label: "Redundancy",
                key: "w_red",
                val: wRed,
                color: "#6B746F",
              },
            ] as const
          ).map((row) => (
            <div key={row.key} className="flex items-center gap-3 text-xs">
              <span className="w-20 text-[#5A635E] font-medium shrink-0">
                {row.label}
              </span>
              <div className="flex-1 h-2 rounded-full bg-[#E5E2DC] overflow-hidden">
                <div
                  className="h-full rounded-full"
                  style={{
                    width: `${(row.val / wMax) * 100}%`,
                    backgroundColor: row.color,
                  }}
                />
              </div>
              <span className="font-mono w-10 text-right text-[#1C2421] font-semibold">
                {row.val.toFixed(2)}
              </span>
            </div>
          ))}
        </div>
        {weightsOpen && (
          <div className="px-4 pb-4 space-y-2 text-xs">
            <div className="font-mono text-[11px] bg-[#F3F1EC] border border-[#E5E2DC] p-3 rounded-lg text-[#3D4742] leading-normal">
              <div className="font-semibold text-[#1C2421] mb-1">
                Value function
              </div>
              <div>
                V(pair) = w_syn × p_syn − w_tox × tox − w_red × redundancy
              </div>
              <div className="mt-1 text-[#6B746F]">
                tox = α_ddi × ddi_risk + α_se × se_risk
              </div>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 font-mono text-[11px]">
              {[
                ["w_syn", wSyn],
                ["w_tox", wTox],
                ["w_red", wRed],
                ["α_ddi", weights?.alpha_ddi ?? 0.7],
                ["α_se", weights?.alpha_se ?? 0.3],
              ].map(([k, v]) => (
                <div
                  key={String(k)}
                  className="p-2 bg-[#EEEBE5] rounded border border-[#E5E2DC]"
                >
                  <span className="text-[#6B746F] block text-[9px] uppercase">
                    {k}
                  </span>
                  <span className="font-bold text-[#1C2421]">
                    {Number(v).toFixed(2)}
                  </span>
                </div>
              ))}
            </div>
            <p className="text-[11px] text-[#6B746F] leading-normal">
              <strong>Unknown-risk invariant:</strong> Unindexed DDI uses
              ddi_risk = 0.35 (not assumed safe). Missing SIDER uses se_risk =
              0.15.
            </p>
          </div>
        )}
      </div>

      {/* 6. Clinical caveat — collapsed */}
      <div className="px-4 py-3">
        <button
          type="button"
          onClick={() => setCaveatOpen((o) => !o)}
          className="w-full flex items-center justify-between gap-3 text-left cursor-pointer group"
        >
          <div className="flex items-start gap-2 min-w-0">
            <AlertTriangle className="w-4 h-4 text-[#B8893D] shrink-0 mt-0.5" />
            <div>
              <div className="text-xs font-semibold text-[#1C2421]">
                Clinical interpretation
              </div>
              {!caveatOpen && (
                <p className="text-[11px] text-[#6B746F] mt-0.5">
                  Database toxicity ≠ clinical dosing recommendation
                </p>
              )}
            </div>
          </div>
          <span className="text-[11px] font-medium text-[#2F6B5E] shrink-0 flex items-center gap-0.5">
            {caveatOpen ? "Hide" : "View details"}
            {caveatOpen ? (
              <ChevronUp className="w-3.5 h-3.5" />
            ) : (
              <ChevronDown className="w-3.5 h-3.5" />
            )}
          </span>
        </button>
        {caveatOpen && (
          <div className="mt-3 ml-6 text-xs text-[#5A635E] leading-normal space-y-2 bg-[#F7F0E4] border border-[#E5D4A8] rounded-lg p-3">
            <p>
              <strong className="text-[#1C2421]">Clinical caveat:</strong>{" "}
              Toxicity flags static database risk (PrimeKG DDI, SIDER). They do
              not model clinical dose scheduling or monitoring.
            </p>
            <p>
              Example: PCV regimens may be standard of care despite high
              computed penalties.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
