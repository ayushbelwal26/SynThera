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
 * Nulls are never coerced to false.
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
    sm: "text-[12px] gap-1",
    md: "text-[13px] gap-1.5",
    lg: "text-sm gap-2",
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
        className={`inline-flex items-center font-sans font-medium text-[#A84B4B] ${sizeClasses[size]} ${className}`}
      >
        <AlertTriangle className={`${iconSizes[size]} shrink-0`} />
        <span>Known adverse DDI</span>
        {showDetails && sideEffectOverlap != null && (
          <span className="text-[12px] opacity-80 font-normal">
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
        className={`inline-flex items-center font-sans font-medium text-[#1A535C] ${sizeClasses[size]} ${className}`}
      >
        <ShieldCheck className={`${iconSizes[size]} shrink-0`} />
        <span>Confirmed safe DDI</span>
        {showDetails && sideEffectOverlap != null && (
          <span className="text-[12px] opacity-80 font-normal">
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
        className={`inline-flex items-center font-sans font-medium text-[#8B7355] ${sizeClasses[size]} ${className}`}
      >
        <ShieldCheck className={`${iconSizes[size]} shrink-0`} />
        <span>Safe DDI · SE data unavailable</span>
      </span>
    );
  }

  return (
    <span
      title="Unindexed in PrimeKG DDI / SIDER. Conservative uncertainty applied."
      className={`inline-flex items-center font-sans font-medium text-[#8B7355] ${sizeClasses[size]} ${className}`}
    >
      <HelpCircle className={`${iconSizes[size]} shrink-0`} />
      <span>Unknown risk · data unavailable</span>
    </span>
  );
};
