import React from "react";
import { AlertCircle, Info, CheckCircle2, ShieldAlert } from "lucide-react";

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
  const styles = {
    info: {
      container: "bg-[#EEF5F8] border-[#D0DCE6] text-[#3A4D5C]",
      icon: <Info className="w-4 h-4 text-[#3B82B8] shrink-0 mt-0.5" />,
      titleColor: "text-[#1A2B3C]",
    },
    warning: {
      container: "bg-[#FBF6E9] border-[#E5D4A8] text-[#6B4E24]",
      icon: <AlertCircle className="w-4 h-4 text-[#B8893D] shrink-0 mt-0.5" />,
      titleColor: "text-[#9A712F]",
    },
    error: {
      container: "bg-[#FBEDEF] border-[#E8BFC8] text-[#9A4050]",
      icon: <ShieldAlert className="w-4 h-4 text-[#C45C6A] shrink-0 mt-0.5" />,
      titleColor: "text-[#B84A5A]",
    },
    success: {
      container: "bg-[#E6F7F5] border-[#A5D9D4] text-[#0A5F5C]",
      icon: <CheckCircle2 className="w-4 h-4 text-[#0F9B8F] shrink-0 mt-0.5" />,
      titleColor: "text-[#0D9488]",
    },
  }[type];

  return (
    <div
      className={`border rounded-md p-3.5 flex items-start gap-3 text-xs leading-normal ${styles.container} ${className}`}
    >
      {styles.icon}
      <div className="flex-1">
        {title && (
          <p className={`font-semibold mb-0.5 ${styles.titleColor}`}>{title}</p>
        )}
        <div className="font-normal">{children}</div>
      </div>
    </div>
  );
};
