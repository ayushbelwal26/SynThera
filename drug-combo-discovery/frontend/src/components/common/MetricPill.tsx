import React from "react";

interface MetricPillProps {
  label: string;
  value: string | number;
  subtext?: string;
  variant?: "default" | "accent" | "success" | "danger" | "warning";
}

export const MetricPill: React.FC<MetricPillProps> = ({
  label,
  value,
  subtext,
  variant = "default",
}) => {
  const valueColor = {
    default: "text-[var(--color-text-primary)]",
    accent: "text-[var(--color-accent)]",
    success: "text-[var(--color-synergy)]",
    danger: "text-[var(--color-antagonism)]",
    warning: "text-[var(--color-additive)]",
  }[variant];

  return (
    <div className="border-b border-[var(--color-rule)] px-0 py-2 flex flex-col justify-between">
      <span className="bench-label">{label}</span>
      <div className="flex items-baseline gap-1.5 mt-0.5">
        <span className={`metric-value text-[16px] font-mono ${valueColor}`}>
          {value}
        </span>
        {subtext && <span className="meta-text text-[11px]">{subtext}</span>}
      </div>
    </div>
  );
};
