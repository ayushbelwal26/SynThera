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
    sm: "text-[11px] px-2 py-0.5",
    md: "text-[12px] px-2.5 py-0.5",
    lg: "text-[13px] px-3 py-1",
  };

  const styleMap = {
    synergy: {
      color: "var(--color-synergy)",
      background: "var(--color-accent-soft)",
      border: "1px solid var(--color-synergy)",
      glow: "0 0 8px var(--color-accent-glow)",
    },
    accent: {
      color: "var(--color-accent)",
      background: "var(--color-accent-soft)",
      border: "1px solid var(--color-accent)",
      glow: "0 0 8px var(--color-accent-glow)",
    },
    additive: {
      color: "var(--color-additive)",
      background: "rgba(227, 186, 120, 0.12)",
      border: "1px solid rgba(227, 186, 120, 0.4)",
      glow: "none",
    },
    antagonism: {
      color: "var(--color-antagonism)",
      background: "rgba(255, 92, 103, 0.12)",
      border: "1px solid rgba(255, 92, 103, 0.4)",
      glow: "none",
    },
    neutral: {
      color: "var(--color-text-muted)",
      background: "var(--color-panel)",
      border: "1px solid var(--color-rule)",
      glow: "none",
    },
    literature: {
      color: "var(--color-accent)",
      background: "var(--color-panel)",
      border: "1px solid var(--color-rule)",
      glow: "none",
    },
  }[variant];

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-mono font-medium rounded-full uppercase tracking-wider ${sizeClasses[size]} ${className}`}
      style={{
        color: styleMap.color,
        background: styleMap.background,
        border: styleMap.border,
        boxShadow: styleMap.glow,
      }}
    >
      <span
        className="w-1.5 h-1.5 rounded-full shrink-0"
        style={{ background: styleMap.color }}
      />
      {children}
    </span>
  );
};
