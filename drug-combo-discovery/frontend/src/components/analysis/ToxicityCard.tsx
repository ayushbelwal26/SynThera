import React, { useState } from "react";
import {
  ChevronDown,
  ChevronUp,
  ShieldAlert,
  Database,
  Layers,
} from "lucide-react";
import type { PredictionResult } from "../../types/api";
import { ToxicityBadge } from "../common/ToxicityBadge";

interface ToxicityCardProps {
  prediction: PredictionResult;
}

function ScoreGauge({ value, color }: { value: number; color: string }) {
  const pct = Math.max(0, Math.min(100, value * 100));
  return (
    <div className="w-full h-2 bg-[var(--color-surface)] border border-[var(--color-rule)] rounded-full overflow-hidden mt-2">
      <div
        className="h-full rounded-full transition-all duration-500"
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
    <div className="bench-panel p-0 overflow-hidden">
      <div className="p-4 border-b border-[var(--color-rule)] bg-[var(--color-surface)] flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div>
          <ToxicityBadge
            hasKnownDdi={hasKnownDdi}
            unknownRiskApplied={unknownRiskApplied}
            sideEffectOverlap={sideEffectOverlap}
            toxicityPenalty={toxPenalty}
            size="md"
          />
          <p className="meta-text mt-1 text-[var(--color-text-secondary)]">
            Synergy reward vs DDI risk, SIDER side effect overlap, and target
            redundancy
          </p>
        </div>
      </div>

      {/* Scoreboard */}
      <div className="grid grid-cols-3 divide-x divide-[var(--color-rule)] border-b border-[var(--color-rule)] bg-[var(--color-panel)]">
        <div className="p-4">
          <span className="bench-label block">Composite V(pair)</span>
          <span className="metric-value text-[17px] text-[var(--color-accent)] font-mono">
            {vScore.toFixed(4)}
          </span>
          <ScoreGauge
            value={Math.min(1, Math.max(0, vScore))}
            color="var(--color-accent)"
          />
        </div>
        <div className="p-4">
          <span className="bench-label block">P(Synergy)</span>
          <span className="metric-value text-[17px] text-[var(--color-synergy)] font-mono">
            {pSyn.toFixed(4)}
          </span>
          <ScoreGauge value={pSyn} color="var(--color-synergy)" />
        </div>
        <div className="p-4">
          <span className="bench-label block">Toxicity Penalty</span>
          <span
            className={`metric-value text-[17px] font-mono ${
              toxPenalty == null
                ? "text-[var(--color-text-muted)]"
                : toxPenalty > 0.4
                  ? "text-[var(--color-antagonism)]"
                  : toxPenalty > 0.1
                    ? "text-[var(--color-additive)]"
                    : "text-[var(--color-accent)]"
            }`}
          >
            {toxPenalty != null ? toxPenalty.toFixed(4) : "0.0000"}
          </span>
          <ScoreGauge
            value={toxPenalty ?? 0}
            color={
              toxPenalty != null && toxPenalty > 0.4
                ? "var(--color-antagonism)"
                : "var(--color-additive)"
            }
          />
        </div>
      </div>

      {/* DDI + SIDER details */}
      <div className="grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-[var(--color-rule)] border-b border-[var(--color-rule)]">
        <div className="p-4 space-y-2.5">
          <div className="flex items-baseline justify-between gap-2">
            <span className="bench-label">PrimeKG DDI Interaction</span>
            <span
              className={`font-mono text-[11px] font-semibold uppercase px-2 py-0.5 rounded ${
                hasKnownDdi === true
                  ? "bg-[var(--color-antagonism)]/15 text-[var(--color-antagonism)]"
                  : hasKnownDdi === false
                    ? "bg-[var(--color-accent-soft)] text-[var(--color-accent)]"
                    : "bg-[var(--color-additive)]/15 text-[var(--color-additive)]"
              }`}
            >
              {hasKnownDdi === true
                ? "Adverse Edge"
                : hasKnownDdi === false
                  ? "No Adverse Edge"
                  : "Unindexed"}
            </span>
          </div>
          <p className="text-[13px] text-[var(--color-text-secondary)] leading-relaxed">
            {prediction.drug_a_name} × {prediction.drug_b_name} in PrimeKG DDI
            network.
          </p>
          <div className="flex justify-between text-[12px] font-mono pt-1">
            <span className="text-[var(--color-text-muted)]">ddi_risk</span>
            <span className="text-[var(--color-text-primary)] font-semibold">
              {ddiRisk.toFixed(2)}
            </span>
          </div>
          <div className="flex justify-between text-[12px] font-mono">
            <span className="text-[var(--color-text-muted)]">
              PrimeKG coverage
            </span>
            <span className="text-[var(--color-accent)] font-semibold">
              {sourceCoverage?.primekg_ddi || hasKnownDdi !== null
                ? "indexed"
                : "missing"}
            </span>
          </div>
        </div>

        <div className="p-4 space-y-2.5">
          <div className="flex items-baseline justify-between gap-2">
            <span className="bench-label">SIDER Adverse Overlap</span>
            {sideEffectOverlap != null ? (
              <span className="font-mono text-[14px] font-semibold text-[var(--color-text-primary)]">
                {(sideEffectOverlap * 100).toFixed(1)}%
              </span>
            ) : (
              <span className="font-mono text-[11px] text-[var(--color-additive)]">
                Unavailable
              </span>
            )}
          </div>
          {sideEffectOverlap != null ? (
            <>
              <p className="text-[13px] text-[var(--color-text-secondary)] leading-relaxed">
                Jaccard distance on MedDRA clinical terms
                {sharedCount != null ? ` · ${sharedCount} shared events` : ""}.
              </p>
              <div className="flex justify-between text-[12px] font-mono pt-1">
                <span className="text-[var(--color-text-muted)]">se_risk</span>
                <span className="text-[var(--color-text-primary)] font-semibold">
                  {seRisk.toFixed(2)}
                </span>
              </div>
              {(topSharedSideEffects.length > 0 || sharedCount) && (
                <button
                  type="button"
                  onClick={() => setSharedOpen((o) => !o)}
                  className="text-[12px] font-mono text-[var(--color-accent)] flex items-center gap-1 cursor-pointer hover:underline"
                >
                  {sharedOpen ? (
                    <ChevronUp className="w-3.5 h-3.5" />
                  ) : (
                    <ChevronDown className="w-3.5 h-3.5" />
                  )}
                  <span>
                    View shared events (
                    {topSharedSideEffects.length || sharedCount || 0})
                  </span>
                </button>
              )}
              {sharedOpen && topSharedSideEffects.length > 0 && (
                <ul className="divide-y divide-[var(--color-rule)]/60 border-t border-[var(--color-rule)] max-h-32 overflow-y-auto mt-2 pt-1 font-mono text-[11.5px]">
                  {topSharedSideEffects.map((se, i) => (
                    <li
                      key={i}
                      className="text-[var(--color-text-secondary)] py-1.5 flex items-center gap-2"
                    >
                      <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-accent)] shrink-0" />
                      <span>{se}</span>
                    </li>
                  ))}
                </ul>
              )}
            </>
          ) : (
            <p className="text-[13px] text-[var(--color-text-secondary)] leading-relaxed">
              SIDER profile missing — baseline se_risk ≈ 0.15 applied
              conservatively.
            </p>
          )}
        </div>
      </div>

      {/* Target Redundancy penalty */}
      <div className="p-4 border-b border-[var(--color-rule)] bg-[var(--color-surface)]">
        <span className="bench-label block mb-1">
          Target Redundancy Penalty
        </span>
        {hasRedundancy ? (
          <div className="flex items-baseline gap-3">
            <span className="font-mono text-[15px] font-semibold text-[var(--color-text-primary)]">
              {(redundancyPenalty! * 100).toFixed(1)}%
            </span>
            <span className="meta-text">
              Target Jaccard similarity · penalty{" "}
              {redundancyPenalty!.toFixed(4)}
            </span>
          </div>
        ) : (
          <p className="text-[13px] text-[var(--color-text-secondary)]">
            Not indexed for this pair — omitted from V(pair), not treated as
            zero.
          </p>
        )}
      </div>

      {/* Database sources bar */}
      <div className="px-4 py-2.5 border-b border-[var(--color-rule)] flex flex-wrap gap-x-6 gap-y-1 font-mono text-[11px] text-[var(--color-text-muted)] bg-[var(--color-panel)]">
        <span className="flex items-center gap-1.5">
          <Database size={11} className="text-[var(--color-accent)]" />
          <span>SIDER:</span>
          <span className="text-[var(--color-accent)] font-semibold">
            {sourceCoverage?.sider ? "indexed" : "missing"}
          </span>
        </span>
        <span className="flex items-center gap-1.5">
          <Database size={11} className="text-[var(--color-accent)]" />
          <span>PrimeKG DDI:</span>
          <span className="text-[var(--color-accent)] font-semibold">
            {sourceCoverage?.primekg_ddi ? "indexed" : "missing"}
          </span>
        </span>
        <span className="flex items-center gap-1.5">
          <Database size={11} className="text-[var(--color-accent)]" />
          <span>DrugBank:</span>
          <span className="text-[var(--color-accent)] font-semibold">
            {sourceCoverage?.drugbank_warnings ? "licensed" : "gated"}
          </span>
        </span>
      </div>

      {/* Objective weights toggle */}
      <div className="border-b border-[var(--color-rule)]">
        <button
          type="button"
          onClick={() => setWeightsOpen((o) => !o)}
          className="w-full px-4 py-2.5 flex items-center justify-between text-left hover:bg-[var(--color-accent-soft)]/30 transition-colors cursor-pointer"
        >
          <div className="flex items-center gap-2">
            <Layers size={13} className="text-[var(--color-accent)]" />
            <span className="bench-label">Objective Multi-Factor Weights</span>
          </div>
          {weightsOpen ? (
            <ChevronUp className="w-4 h-4 text-[var(--color-text-muted)]" />
          ) : (
            <ChevronDown className="w-4 h-4 text-[var(--color-text-muted)]" />
          )}
        </button>

        <div className="px-4 pb-3 space-y-2">
          {[
            { label: "Synergy", val: wSyn, color: "var(--color-synergy)" },
            { label: "Toxicity", val: wTox, color: "var(--color-additive)" },
            {
              label: "Redundancy",
              val: wRed,
              color: "var(--color-text-muted)",
            },
          ].map((row) => (
            <div
              key={row.label}
              className="flex items-center gap-3 text-[12.5px]"
            >
              <span className="w-20 font-mono text-[var(--color-text-secondary)] shrink-0">
                {row.label}
              </span>
              <div className="flex-1 h-1.5 rounded-full bg-[var(--color-surface)] border border-[var(--color-rule)] overflow-hidden">
                <div
                  className="h-full rounded-full"
                  style={{
                    width: `${(row.val / wMax) * 100}%`,
                    backgroundColor: row.color,
                  }}
                />
              </div>
              <span className="font-mono text-[12px] w-10 text-right text-[var(--color-text-primary)]">
                {row.val.toFixed(2)}
              </span>
            </div>
          ))}
        </div>

        {weightsOpen && (
          <div className="px-4 pb-3 space-y-1.5 text-[12px] font-mono text-[var(--color-text-secondary)] border-t border-[var(--color-rule)] pt-2.5">
            <p className="text-[var(--color-accent)] font-semibold">
              V(pair) = w_syn × p_syn − w_tox × tox − w_red × redundancy
            </p>
            <p className="text-[var(--color-text-muted)]">
              tox = α_ddi × ddi_risk + α_se × se_risk (DDI default = 0.35, SIDER
              default = 0.15)
            </p>
          </div>
        )}
      </div>

      {/* Clinical interpretation caveat */}
      <div className="p-4 bg-[var(--color-surface)]">
        <button
          type="button"
          onClick={() => setCaveatOpen((o) => !o)}
          className="w-full flex items-center justify-between gap-3 text-left cursor-pointer"
        >
          <div>
            <span className="text-[13px] font-medium text-[var(--color-text-primary)] flex items-center gap-1.5">
              <ShieldAlert size={14} className="text-[var(--color-accent)]" />
              Clinical interpretation guidance
            </span>
            {!caveatOpen && (
              <p className="meta-text mt-0.5">
                Database toxicity ≠ clinical dosing recommendation
              </p>
            )}
          </div>
          <span className="font-mono text-[11px] text-[var(--color-accent)] hover:underline shrink-0">
            {caveatOpen ? "Hide" : "Details"}
          </span>
        </button>
        {caveatOpen && (
          <p className="mt-2.5 text-[12.5px] text-[var(--color-text-secondary)] leading-relaxed border-t border-[var(--color-rule)] pt-2">
            Toxicity metrics quantify static database flags from PrimeKG DDI and
            SIDER annotations. They do not model clinical dose adjustments,
            staggered dosing regimens, or patient-specific oncological
            tolerance.
          </p>
        )}
      </div>
    </div>
  );
};
