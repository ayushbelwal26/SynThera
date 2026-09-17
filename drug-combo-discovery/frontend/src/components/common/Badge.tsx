import React from 'react';

interface BadgeProps {
  variant: 'synergy' | 'additive' | 'antagonism' | 'neutral' | 'accent' | 'literature';
  children: React.ReactNode;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  variant,
  children,
  size = 'md',
  className = '',
}) => {
  const sizeClasses = {
    sm: 'text-[11px] px-2 py-0.5 tracking-wider',
    md: 'text-xs px-2.5 py-1 tracking-wide',
    lg: 'text-sm px-3.5 py-1.5 font-semibold tracking-wide',
  };

  const variantClasses = {
    synergy: 'bg-[#ECFDF5] text-[#047857] border border-[#A7F3D0]',
    antagonism: 'bg-[#FEF2F2] text-[#B91C1C] border border-[#FECACA]',
    additive: 'bg-[#FFFBEB] text-[#B45309] border border-[#FDE68A]',
    neutral: 'bg-[#F1F5F9] text-[#475569] border border-[#E2E8F0]',
    accent: 'bg-[#F0FDFA] text-[#0F766E] border border-[#99F6E4]',
    literature: 'bg-[#FEF3C7] text-[#92400E] border border-[#FDE68A]',
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-mono uppercase rounded font-medium ${sizeClasses[size]} ${variantClasses[variant]} ${className}`}
    >
      <span
        className={`w-1.5 h-1.5 rounded-full ${
          variant === 'synergy'
            ? 'bg-[#059669]'
            : variant === 'antagonism'
            ? 'bg-[#DC2626]'
            : variant === 'additive'
            ? 'bg-[#D97706]'
            : variant === 'literature'
            ? 'bg-[#B45309]'
            : variant === 'accent'
            ? 'bg-[#0D9488]'
            : 'bg-[#64748B]'
        }`}
      />
      {children}
    </span>
  );
};
