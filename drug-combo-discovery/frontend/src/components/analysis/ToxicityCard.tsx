import React, { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import type { PredictionResult } from "../../types/api";
import { ToxicityBadge } from "../common/ToxicityBadge";

interface ToxicityCardProps {
  prediction: PredictionResult;
}

function ScoreGauge({ value, color }: { value: number; color: string }) {
  const pct = Math.max(0, Math.min(100, value * 100));
  return (
    <div className="w-full h-1.5 bg-[#E5E2DC] overflow-hidden mt-1.5">
      <div
        className="h-full"
        style={{ width: `${pct}%`, backgroundColor: color }}
      />
    </div>
  );
}

export const ToxicityCard: React.FC<ToxicityCardProps> = ({ prediction }) => {
  const [sharedOpen, setSharedOpen] = useState(false);
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

  const vScore =
    prediction.v_score ?? ranking?.v_score ?? prediction.score ?? 0;
  const pSyn = ranking?.p_synergy ?? prediction.p_synergy ?? 0;
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

  const wSyn = weights?.w_synergy ?? 1.0;
  const wTox = weights?.w_toxicity ?? 0.35;
  const wRed = weights?.w_redundancy ?? 0.1;
  const wMax = Math.max(wSyn, wTox, wRed, 0.01);

  return (
    <div className="bench-panel-flush">
      <div className="px-4 py-3 border-b border-[#CFC9BC] flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div>
          <ToxicityBadge
            hasKnownDdi={hasKnownDdi}
            unknownRiskApplied={unknownRiskApplied}
            sideEffectOverlap={sideEffectOverlap}
            toxicityPenalty={toxPenalty}
            size="md"
          />
          <p className="meta-text mt-1">
            Synergy reward vs DDI risk, SIDER overlap, and target redundancy
          </p>
        </div>
      </div>

      {/* Scoreboard */}
      <div className="grid grid-cols-3 divide-x divide-[#CFC9BC] border-b border-[#CFC9BC]">
        <div className="px-4 py-3">
          <span className="bench-label block">Composite V(pair)</span>
          <span className="metric-value text-[#1A535C]">
            {vScore.toFixed(4)}
          </span>
          <ScoreGauge
            value={Math.min(1, Math.max(0, vScore))}
            color="#1A535C"
          />
        </div>
        <div className="px-4 py-3">
          <span className="bench-label block">P(synergy)</span>
          <span className="metric-value">{pSyn.toFixed(4)}</span>
          <ScoreGauge value={pSyn} color="#3D7A6C" />
        </div>
        <div className="px-4 py-3">
          <span className="bench-label block">Toxicity penalty</span>
          <span
            className={`metric-value ${
              toxPenalty == null
                ? "text-[#8A918C]"
                : toxPenalty > 0.4
                  ? "text-[#A84B4B]"
                  : toxPenalty > 0.1
                    ? "text-[#8B7355]"
                    : "text-[#1A535C]"
            }`}
          >
            {toxPenalty != null ? toxPenalty.toFixed(4) : "—"}
          </span>
          <ScoreGauge
            value={toxPenalty ?? 0}
            color={
              toxPenalty != null && toxPenalty > 0.4 ? "#A84B4B" : "#8B7355"
            }
          />
        </div>
      </div>

      {/* DDI + SIDER */}
      <div className="grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-[#CFC9BC] border-b border-[#CFC9BC]">
        <div className="px-4 py-3 space-y-2">
          <div className="flex items-baseline justify-between gap-2">
            <span className="bench-label">DDI interaction</span>
            <span
              className={`text-[12px] font-medium ${
                hasKnownDdi === true
                  ? "text-[#A84B4B]"
                  : hasKnownDdi === false
                    ? "text-[#1A535C]"
                    : "text-[#8B7355]"
              }`}
            >
              {hasKnownDdi === true
                ? "Adverse edge present"
                : hasKnownDdi === false
                  ? "No adverse edge"
                  : "Unindexed"}
            </span>
          </div>
          <p className="text-[13px] text-[#4A524C] leading-relaxed">
            {prediction.drug_a_name} × {prediction.drug_b_name} in PrimeKG DDI.
          </p>
          <div className="flex justify-between text-[12px]">
            <span className="meta-text">ddi_risk</span>
            <span className="id-text text-[#1A1F1C]">{ddiRisk.toFixed(2)}</span>
          </div>
          <div className="flex justify-between text-[12px]">
            <span className="meta-text">PrimeKG coverage</span>
            <span className="id-text text-[#1A1F1C]">
              {sourceCoverage?.primekg_ddi || hasKnownDdi !== null
                ? "indexed"
                : "missing"}
            </span>
          </div>
        </div>

        <div className="px-4 py-3 space-y-2">
          <div className="flex items-baseline justify-between gap-2">
            <span className="bench-label">SIDER overlap</span>
            {sideEffectOverlap != null ? (
              <span className="metric-value text-[14px]">
                {(sideEffectOverlap * 100).toFixed(1)}%
              </span>
            ) : (
              <span className="text-[12px] text-[#8B7355]">Unavailable</span>
            )}
          </div>
          {sideEffectOverlap != null ? (
            <>
              <p className="text-[13px] text-[#4A524C] leading-relaxed">
                Jaccard on MedDRA terms
                {sharedCount != null ? ` · ${sharedCount} shared` : ""}.
              </p>
              <div className="flex justify-between text-[12px]">
                <span className="meta-text">se_risk</span>
                <span className="id-text text-[#1A1F1C]">{seRisk.toFixed(2)}</span>
              </div>
              {(topSharedSideEffects.length > 0 || sharedCount) && (
                <button
                  type="button"
                  onClick={() => setSharedOpen((o) => !o)}
                  className="text-[12px] text-[#1A535C] flex items-center gap-1"
                >
                  {sharedOpen ? (
                    <ChevronUp className="w-3.5 h-3.5" />
                  ) : (
                    <ChevronDown className="w-3.5 h-3.5" />
                  )}
                  Shared events ({topSharedSideEffects.length || sharedCount || 0})
                </button>
              )}
              {sharedOpen && topSharedSideEffects.length > 0 && (
                <ul className="divide-y divide-[#CFC9BC] border-t border-[#CFC9BC] max-h-32 overflow-y-auto">
                  {topSharedSideEffects.map((se, i) => (
                    <li key={i} className="text-[13px] text-[#4A524C] py-1.5">
                      {se}
                    </li>
                  ))}
                </ul>
              )}
            </>
          ) : (
            <p className="text-[13px] text-[#4A524C] leading-relaxed">
              SIDER profile missing — baseline se_risk ≈ 0.15 applied.
            </p>
          )}
        </div>
      </div>

      {/* Redundancy */}
      <div className="px-4 py-3 border-b border-[#CFC9BC]">
        <span className="bench-label block mb-1">Target redundancy</span>
        {hasRedundancy ? (
          <div className="flex items-baseline gap-3">
            <span className="metric-value text-[14px]">
              {(redundancyPenalty! * 100).toFixed(1)}%
            </span>
            <span className="meta-text">
              Target Jaccard · penalty {redundancyPenalty!.toFixed(4)}
            </span>
          </div>
        ) : (
          <p className="text-[13px] text-[#4A524C]">
            Not indexed for this pair — omitted from V(pair), not treated as
            zero.
          </p>
        )}
      </div>

      {/* Sources */}
      <div className="px-4 py-2.5 border-b border-[#CFC9BC] flex flex-wrap gap-x-5 gap-y-1 text-[12px] text-[#6B746C]">
        <span>
          SIDER{" "}
          <span className="id-text">
            {sourceCoverage?.sider ? "indexed" : "missing"}
          </span>
        </span>
        <span>
          PrimeKG{" "}
          <span className="id-text">
            {sourceCoverage?.primekg_ddi ? "indexed" : "missing"}
          </span>
        </span>
        <span>
          DrugBank{" "}
          <span className="id-text">
            {sourceCoverage?.drugbank_warnings ? "licensed" : "gated"}
          </span>
        </span>
      </div>

      {/* Weights */}
      <div className="border-b border-[#CFC9BC]">
        <button
          type="button"
          onClick={() => setWeightsOpen((o) => !o)}
          className="w-full px-4 py-2.5 flex items-center justify-between text-left hover:bg-[#F5F5ED]/60"
        >
          <span className="bench-label">Objective weights</span>
          {weightsOpen ? (
            <ChevronUp className="w-4 h-4 text-[#6B746C]" />
          ) : (
            <ChevronDown className="w-4 h-4 text-[#6B746C]" />
          )}
        </button>
        <div className="px-4 pb-3 space-y-2">
          {(
            [
              { label: "Synergy", val: wSyn, color: "#1A535C" },
              { label: "Toxicity", val: wTox, color: "#8B7355" },
              { label: "Redundancy", val: wRed, color: "#6B746C" },
            ] as const
          ).map((row) => (
            <div key={row.label} className="flex items-center gap-3 text-[13px]">
              <span className="w-[5.5rem] text-[#4A524C] shrink-0">
                {row.label}
              </span>
              <div className="flex-1 h-1.5 bg-[#E5E2DC] overflow-hidden">
                <div
                  className="h-full"
                  style={{
                    width: `${(row.val / wMax) * 100}%`,
                    backgroundColor: row.color,
                  }}
                />
              </div>
              <span className="id-text w-10 text-right text-[#1A1F1C]">
                {row.val.toFixed(2)}
              </span>
            </div>
          ))}
        </div>
        {weightsOpen && (
          <div className="px-4 pb-3 space-y-2 text-[13px] text-[#4A524C]">
            <p className="id-text leading-relaxed text-[#1A1F1C]">
              V(pair) = w_syn × p_syn − w_tox × tox − w_red × redundancy
              <br />
              tox = α_ddi × ddi_risk + α_se × se_risk
            </p>
            <p className="meta-text leading-relaxed">
              Unindexed DDI uses ddi_risk = 0.35. Missing SIDER uses se_risk =
              0.15.
            </p>
          </div>
        )}
      </div>

      {/* Caveat */}
      <div className="px-4 py-3">
        <button
          type="button"
          onClick={() => setCaveatOpen((o) => !o)}
          className="w-full flex items-center justify-between gap-3 text-left"
        >
          <div>
            <span className="text-[13px] font-medium text-[#1A1F1C]">
              Clinical interpretation
            </span>
            {!caveatOpen && (
              <p className="meta-text mt-0.5">
                Database toxicity ≠ clinical dosing recommendation
              </p>
            )}
          </div>
          <span className="text-[12px] text-[#1A535C] shrink-0">
            {caveatOpen ? "Hide" : "Details"}
          </span>
        </button>
        {caveatOpen && (
          <p className="mt-2 text-[13px] text-[#4A524C] leading-relaxed">
            Toxicity flags static database risk (PrimeKG DDI, SIDER). They do
            not model clinical dose scheduling or monitoring. Example: PCV
            regimens may be standard of care despite high computed penalties.
          </p>
        )}
      </div>
    </div>
  );
};
