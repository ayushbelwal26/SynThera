import React from "react";

interface AlertNoticeProps {
  type?: "info" | "warning" | "error" | "success";
  title?: string;
  children: React.ReactNode;
  className?: string;
}

export const AlertNotice: React.FC<AlertNoticeProps> = ({
  type = "info",
  title,
  children,
  className = "",
}) => {
  const border =
    type === "error"
      ? "border-[#A84B4B]"
      : type === "warning"
        ? "border-[#8B7355]"
        : type === "success"
          ? "border-[#1A535C]"
          : "border-[#CFC9BC]";

  return (
    <div className={`border ${border} px-4 py-3 text-[14px] leading-relaxed ${className}`}>
      {title && (
        <p className="bench-label mb-1 text-[#1A1F1C]">{title}</p>
      )}
      <div className="text-[#4A524C]">{children}</div>
    </div>
  );
};
