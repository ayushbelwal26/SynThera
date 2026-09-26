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
    default: "text-[#1A1F1C]",
    accent: "text-[#1A535C]",
    success: "text-[#1A535C]",
    danger: "text-[#A84B4B]",
    warning: "text-[#8B7355]",
  }[variant];

  return (
    <div className="border-b border-[#CFC9BC] px-0 py-2 flex flex-col justify-between">
      <span className="bench-label">{label}</span>
      <div className="flex items-baseline gap-1 mt-0.5">
        <span className={`metric-value text-[15px] ${valueColor}`}>{value}</span>
        {subtext && <span className="meta-text">{subtext}</span>}
      </div>
    </div>
  );
};
