import React from "react";

interface BadgeProps {
  variant:
    | "synergy"
    | "additive"
    | "antagonism"
    | "neutral"
    | "accent"
    | "literature";
  children: React.ReactNode;
  size?: "sm" | "md" | "lg";
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  variant,
  children,
  size = "md",
  className = "",
}) => {
  const sizeClasses = {
    sm: "text-[11px]",
    md: "text-[12px]",
    lg: "text-[13px]",
  };

  const colorClasses = {
    synergy: "text-[#1A535C]",
    antagonism: "text-[#A84B4B]",
    additive: "text-[#8B7355]",
    neutral: "text-[#6B746C]",
    accent: "text-[#1A535C]",
    literature: "text-[#6B5A3A]",
  };

  const dotClasses = {
    synergy: "bg-[#1A535C]",
    antagonism: "bg-[#A84B4B]",
    additive: "bg-[#8B7355]",
    neutral: "bg-[#6B746C]",
    accent: "bg-[#1A535C]",
    literature: "bg-[#6B5A3A]",
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-sans font-medium capitalize ${sizeClasses[size]} ${colorClasses[variant]} ${className}`}
    >
      <span className={`w-1.5 h-1.5 shrink-0 ${dotClasses[variant]}`} />
      {children}
    </span>
  );
};
