import React from "react";
import { ShieldCheck, AlertTriangle, HelpCircle } from "lucide-react";

export interface ToxicityBadgeProps {
  hasKnownDdi: boolean | null | undefined;
  unknownRiskApplied?: boolean;
  sideEffectOverlap?: number | null;
  toxicityPenalty?: number | null;
  size?: "sm" | "md" | "lg";
  showDetails?: boolean;
  className?: string;
}

/**
 * Three-state Toxicity / DDI Indicator
 * - has_known_ddi === false → Confirmed safe
 * - has_known_ddi === true → Known adverse DDI
 * - null / unknown_risk_applied → Unknown risk
 */
export const ToxicityBadge: React.FC<ToxicityBadgeProps> = ({
  hasKnownDdi,
  unknownRiskApplied = false,
  sideEffectOverlap,
  toxicityPenalty,
  size = "md",
  showDetails = false,
  className = "",
}) => {
  const isKnownDdi = hasKnownDdi === true;
  const isConfirmedSafe = hasKnownDdi === false && !unknownRiskApplied;
  const isSafeDdiUnindexedSe = hasKnownDdi === false && unknownRiskApplied;

  const sizeClasses = {
    sm: "text-[12px] gap-1 px-2 py-0.5",
    md: "text-[12.5px] gap-1.5 px-2.5 py-1",
    lg: "text-[13.5px] gap-2 px-3 py-1.5",
  };

  const iconSizes = {
    sm: "w-3.5 h-3.5",
    md: "w-4 h-4",
    lg: "w-4.5 h-4.5",
  };

  if (isKnownDdi) {
    return (
      <span
        title={`Known adverse DDI in PrimeKG.${
          toxicityPenalty != null
            ? ` Tox penalty: ${toxicityPenalty.toFixed(4)}.`
            : ""
        }`}
        className={`inline-flex items-center rounded-full font-mono font-medium bg-[var(--color-antagonism)]/15 text-[var(--color-antagonism)] border border-[var(--color-antagonism)]/40 ${sizeClasses[size]} ${className}`}
      >
        <AlertTriangle className={`${iconSizes[size]} shrink-0`} />
        <span>Known Adverse DDI</span>
        {showDetails && sideEffectOverlap != null && (
          <span className="text-[11px] opacity-80 font-normal">
            ({(sideEffectOverlap * 100).toFixed(0)}% SE)
          </span>
        )}
      </span>
    );
  }

  if (isConfirmedSafe) {
    return (
      <span
        title={`Indexed in PrimeKG DDI with zero documented interactions.${
          sideEffectOverlap != null
            ? ` SIDER overlap: ${(sideEffectOverlap * 100).toFixed(1)}%`
            : ""
        }`}
        className={`inline-flex items-center rounded-full font-mono font-medium bg-[var(--color-accent-soft)] text-[var(--color-accent)] border border-[var(--color-accent)] shadow-[0_0_8px_var(--color-accent-glow)] ${sizeClasses[size]} ${className}`}
      >
        <ShieldCheck className={`${iconSizes[size]} shrink-0`} />
        <span>Confirmed Safe DDI</span>
        {showDetails && sideEffectOverlap != null && (
          <span className="text-[11px] opacity-80 font-normal">
            ({(sideEffectOverlap * 100).toFixed(0)}% SE)
          </span>
        )}
      </span>
    );
  }

  if (isSafeDdiUnindexedSe) {
    return (
      <span
        title="Zero DDI edges, but SIDER profile missing. Uncertainty penalty applied."
        className={`inline-flex items-center rounded-full font-mono font-medium bg-[var(--color-additive)]/15 text-[var(--color-additive)] border border-[var(--color-additive)]/40 ${sizeClasses[size]} ${className}`}
      >
        <ShieldCheck className={`${iconSizes[size]} shrink-0`} />
        <span>Safe DDI · SE unindexed</span>
      </span>
    );
  }

  return (
    <span
      title="Unindexed in PrimeKG DDI / SIDER. Conservative uncertainty applied."
      className={`inline-flex items-center rounded-full font-mono font-medium bg-[var(--color-panel)] text-[var(--color-text-muted)] border border-[var(--color-rule)] ${sizeClasses[size]} ${className}`}
    >
      <HelpCircle className={`${iconSizes[size]} shrink-0`} />
      <span>Unknown Risk Profile</span>
    </span>
  );
};
