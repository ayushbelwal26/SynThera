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
    default: "text-[#1A2B3C]",
    accent: "text-[#0D9488]",
    success: "text-[#0F9B8F]",
    danger: "text-[#C45C6A]",
    warning: "text-[#B8893D]",
  }[variant];

  return (
    <div className="bg-[#FFFFFF] border border-[#E2EAF0] rounded-md px-3 py-2 flex flex-col justify-between shadow-xs">
      <span className="text-[11px] font-medium text-[#7A8B9A] uppercase tracking-wide">
        {label}
      </span>
      <div className="flex items-baseline gap-1 mt-0.5">
        <span className={`font-mono text-base font-semibold ${valueColor}`}>
          {value}
        </span>
        {subtext && (
          <span className="text-[11px] text-[#7A8B9A] font-mono">
            {subtext}
          </span>
        )}
      </div>
    </div>
  );
};
