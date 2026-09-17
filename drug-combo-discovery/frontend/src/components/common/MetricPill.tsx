import React from 'react';

interface MetricPillProps {
  label: string;
  value: string | number;
  subtext?: string;
  variant?: 'default' | 'accent' | 'success' | 'danger' | 'warning';
}

export const MetricPill: React.FC<MetricPillProps> = ({
  label,
  value,
  subtext,
  variant = 'default',
}) => {
  const valueColor = {
    default: 'text-[#0F172A]',
    accent: 'text-[#0D9488]',
    success: 'text-[#059669]',
    danger: 'text-[#DC2626]',
    warning: 'text-[#D97706]',
  }[variant];

  return (
    <div className="bg-[#FFFFFF] border border-[#E5E5E0] rounded-md px-3 py-2 flex flex-col justify-between shadow-xs">
      <span className="text-[11px] font-medium text-[#717784] uppercase tracking-wider">
        {label}
      </span>
      <div className="flex items-baseline gap-1 mt-0.5">
        <span className={`font-mono text-base font-semibold ${valueColor}`}>
          {value}
        </span>
        {subtext && (
          <span className="text-[11px] text-[#717784] font-mono">{subtext}</span>
        )}
      </div>
    </div>
  );
};
