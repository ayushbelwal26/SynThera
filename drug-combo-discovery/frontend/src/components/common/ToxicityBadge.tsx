import React from 'react';
import { ShieldCheck, AlertTriangle, HelpCircle } from 'lucide-react';

export interface ToxicityBadgeProps {
  hasKnownDdi: boolean | null | undefined;
  unknownRiskApplied?: boolean;
  sideEffectOverlap?: number | null;
  toxicityPenalty?: number | null;
  size?: 'sm' | 'md' | 'lg';
  showDetails?: boolean;
  className?: string;
}

/**
 * Three-state Toxicity / DDI Indicator
 *
 * Implements the backend Phase B1/B2 None-vs-0 invariant:
 * - State 1: has_known_ddi === false (Confirmed Safe / No Known DDI) -> Emerald
 * - State 2: has_known_ddi === true  (Known Adverse DDI Warning)    -> Rose
 * - State 3: has_known_ddi === null / unknown_risk_applied           -> Amber (Unknown Risk / Unindexed)
 *
 * Nulls are strictly NEVER coerced to false or collapsed into safe.
 */
export const ToxicityBadge: React.FC<ToxicityBadgeProps> = ({
  hasKnownDdi,
  unknownRiskApplied = false,
  sideEffectOverlap,
  toxicityPenalty,
  size = 'md',
  showDetails = false,
  className = '',
}) => {
  // Determine state strictly without coercing null/undefined to false
  const isKnownDdi = hasKnownDdi === true;
  const isConfirmedSafe = hasKnownDdi === false && !unknownRiskApplied;
  // If hasKnownDdi is explicitly false but unknownRiskApplied is true (e.g. SIDER unindexed),
  // we still distinguish it safely
  const isSafeDdiUnindexedSe = hasKnownDdi === false && unknownRiskApplied;

  const sizeClasses = {
    sm: 'text-[10px] px-2 py-0.5 tracking-wider gap-1',
    md: 'text-[11px] px-2.5 py-1 tracking-wide gap-1.5',
    lg: 'text-xs px-3 py-1.5 font-semibold tracking-wide gap-2',
  };

  const iconSizes = {
    sm: 'w-3 h-3',
    md: 'w-3.5 h-3.5',
    lg: 'w-4 h-4',
  };

  if (isKnownDdi) {
    return (
      <span
        title={`Known adverse drug-drug interaction flagged in PrimeKG DDI network (ddi_risk = 1.0).${
          toxicityPenalty !== undefined && toxicityPenalty !== null
            ? ` Total tox penalty: ${toxicityPenalty.toFixed(4)}.`
            : ''
        } Flags static database risk; does not model clinical dose scheduling or monitoring.`}
        className={`inline-flex items-center font-mono uppercase rounded font-semibold bg-[#FEF2F2] text-[#B91C1C] border border-[#FECACA] ${sizeClasses[size]} ${className}`}
      >
        <AlertTriangle className={`${iconSizes[size]} text-[#DC2626] shrink-0`} />
        <span>Known Adverse DDI</span>
        {showDetails && sideEffectOverlap !== undefined && sideEffectOverlap !== null && (
          <span className="text-[10px] text-[#DC2626]/80 font-normal ml-0.5">
            ({(sideEffectOverlap * 100).toFixed(0)}% SE)
          </span>
        )}
      </span>
    );
  }

  if (isConfirmedSafe) {
    return (
      <span
        title={`Both compounds indexed in PrimeKG DDI network with zero documented interactions (ddi_risk = 0.0).${
          sideEffectOverlap !== undefined && sideEffectOverlap !== null
            ? ` SIDER overlap: ${(sideEffectOverlap * 100).toFixed(1)}%`
            : ''
        }`}
        className={`inline-flex items-center font-mono uppercase rounded font-semibold bg-[#ECFDF5] text-[#047857] border border-[#A7F3D0] ${sizeClasses[size]} ${className}`}
      >
        <ShieldCheck className={`${iconSizes[size]} text-[#059669] shrink-0`} />
        <span>Confirmed Safe DDI</span>
        {showDetails && sideEffectOverlap !== undefined && sideEffectOverlap !== null && (
          <span className="text-[10px] text-[#059669]/80 font-normal ml-0.5">
            ({(sideEffectOverlap * 100).toFixed(0)}% SE)
          </span>
        )}
      </span>
    );
  }

  if (isSafeDdiUnindexedSe) {
    return (
      <span
        title="Both compounds have zero documented adverse interaction edges in PrimeKG DDI, but one or both compounds lack phenotypic side-effect records in SIDER 4.1. A conservative baseline uncertainty penalty was applied."
        className={`inline-flex items-center font-mono uppercase rounded font-semibold bg-[#FFFBEB] text-[#B45309] border border-[#FDE68A] ${sizeClasses[size]} ${className}`}
      >
        <ShieldCheck className={`${iconSizes[size]} text-[#D97706] shrink-0`} />
        <span>Safe DDI &bull; Side-Effect Data Unavailable</span>
      </span>
    );
  }

  // Explicit State 3: Unknown Risk / Unindexed Pair
  return (
    <span
      title="Neither compound has verified interaction records in PrimeKG DDI or phenotypic profiles in SIDER. A conservative baseline uncertainty penalty (0.35 DDI / 0.15 SE) was applied."
      className={`inline-flex items-center font-mono uppercase rounded font-semibold bg-[#FFFBEB] text-[#B45309] border border-[#FDE68A] ${sizeClasses[size]} ${className}`}
    >
      <HelpCircle className={`${iconSizes[size]} text-[#D97706] shrink-0`} />
      <span>Unknown Risk &bull; Data Unavailable</span>
    </span>
  );
};
