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
    sm: "text-[11px] px-2 py-0.5 tracking-wide",
    md: "text-xs px-2.5 py-1 tracking-wide",
    lg: "text-sm px-3.5 py-1.5 font-semibold tracking-wide",
  };

  const variantClasses = {
    synergy: "bg-[#E8F0ED] text-[#2F6B5E] border border-[#B5CFC6]",
    antagonism: "bg-[#F7EBEB] text-[#A84B4B] border border-[#E8C5C5]",
    additive: "bg-[#F7F0E4] text-[#9A712F] border border-[#E5D4A8]",
    neutral: "bg-[#EEEBE5] text-[#5A635E] border border-[#E5E2DC]",
    accent: "bg-[#E8F0ED] text-[#25564B] border border-[#B5CFC6]",
    literature: "bg-[#F5EFE4] text-[#7A5A28] border border-[#E5D4A8]",
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-mono uppercase rounded font-medium ${sizeClasses[size]} ${variantClasses[variant]} ${className}`}
    >
      <span
        className={`w-1.5 h-1.5 rounded-full ${
          variant === "synergy"
            ? "bg-[#3D7A6C]"
            : variant === "antagonism"
              ? "bg-[#C45C5C]"
              : variant === "additive"
                ? "bg-[#B8893D]"
                : variant === "literature"
                  ? "bg-[#9A712F]"
                  : variant === "accent"
                    ? "bg-[#2F6B5E]"
                    : "bg-[#6B746F]"
        }`}
      />
      {children}
    </span>
  );
};
