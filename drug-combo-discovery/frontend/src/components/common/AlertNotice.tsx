import React from 'react';
import { AlertCircle, Info, CheckCircle2, ShieldAlert } from 'lucide-react';

interface AlertNoticeProps {
  type?: 'info' | 'warning' | 'error' | 'success';
  title?: string;
  children: React.ReactNode;
  className?: string;
}

export const AlertNotice: React.FC<AlertNoticeProps> = ({
  type = 'info',
  title,
  children,
  className = '',
}) => {
  const styles = {
    info: {
      container: 'bg-[#F8FAFC] border-[#CBD5E1] text-[#334155]',
      icon: <Info className="w-4 h-4 text-[#475569] shrink-0 mt-0.5" />,
      titleColor: 'text-[#1E293B]',
    },
    warning: {
      container: 'bg-[#FFFBEB] border-[#FDE68A] text-[#92400E]',
      icon: <AlertCircle className="w-4 h-4 text-[#D97706] shrink-0 mt-0.5" />,
      titleColor: 'text-[#B45309]',
    },
    error: {
      container: 'bg-[#FEF2F2] border-[#FECACA] text-[#991B1B]',
      icon: <ShieldAlert className="w-4 h-4 text-[#DC2626] shrink-0 mt-0.5" />,
      titleColor: 'text-[#B91C1C]',
    },
    success: {
      container: 'bg-[#ECFDF5] border-[#A7F3D0] text-[#065F46]',
      icon: <CheckCircle2 className="w-4 h-4 text-[#059669] shrink-0 mt-0.5" />,
      titleColor: 'text-[#047857]',
    },
  }[type];

  return (
    <div
      className={`border rounded-md p-3.5 flex items-start gap-3 text-xs leading-relaxed ${styles.container} ${className}`}
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
