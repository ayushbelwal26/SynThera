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
  const styles: Record<string, React.CSSProperties> = {
    error: {
      borderLeft: "3px solid var(--color-antagonism)",
      background: "rgba(168, 75, 75, 0.08)",
      borderTop: "1px solid rgba(168, 75, 75, 0.2)",
      borderRight: "1px solid rgba(168, 75, 75, 0.2)",
      borderBottom: "1px solid rgba(168, 75, 75, 0.2)",
    },
    warning: {
      borderLeft: "3px solid var(--color-additive)",
      background: "rgba(139, 115, 85, 0.08)",
      borderTop: "1px solid rgba(139, 115, 85, 0.2)",
      borderRight: "1px solid rgba(139, 115, 85, 0.2)",
      borderBottom: "1px solid rgba(139, 115, 85, 0.2)",
    },
    success: {
      borderLeft: "3px solid var(--color-synergy)",
      background: "var(--color-accent-soft)",
      borderTop: "1px solid var(--color-rule)",
      borderRight: "1px solid var(--color-rule)",
      borderBottom: "1px solid var(--color-rule)",
    },
    info: {
      borderLeft: "3px solid var(--color-rule-strong)",
      background: "var(--color-panel)",
      borderTop: "1px solid var(--color-rule)",
      borderRight: "1px solid var(--color-rule)",
      borderBottom: "1px solid var(--color-rule)",
    },
  };

  const titleColor: Record<string, string> = {
    error: "var(--color-antagonism)",
    warning: "var(--color-additive)",
    success: "var(--color-synergy)",
    info: "var(--color-text-primary)",
  };

  const iconMap: Record<string, React.ReactNode> = {
    error: (
      <svg width="15" height="15" viewBox="0 0 15 15" fill="none" style={{ flexShrink: 0, marginTop: "1px" }}>
        <circle cx="7.5" cy="7.5" r="6.5" stroke="var(--color-antagonism)" strokeWidth="1.5"/>
        <path d="M7.5 4.5V8" stroke="var(--color-antagonism)" strokeWidth="1.5" strokeLinecap="round"/>
        <circle cx="7.5" cy="10.5" r="0.75" fill="var(--color-antagonism)"/>
      </svg>
    ),
    warning: (
      <svg width="15" height="15" viewBox="0 0 15 15" fill="none" style={{ flexShrink: 0, marginTop: "1px" }}>
        <path d="M7.5 2L13.5 12H1.5L7.5 2Z" stroke="var(--color-additive)" strokeWidth="1.5" strokeLinejoin="round"/>
        <path d="M7.5 6V9" stroke="var(--color-additive)" strokeWidth="1.5" strokeLinecap="round"/>
        <circle cx="7.5" cy="10.5" r="0.75" fill="var(--color-additive)"/>
      </svg>
    ),
    success: (
      <svg width="15" height="15" viewBox="0 0 15 15" fill="none" style={{ flexShrink: 0, marginTop: "1px" }}>
        <circle cx="7.5" cy="7.5" r="6.5" stroke="var(--color-synergy)" strokeWidth="1.5"/>
        <path d="M4.5 7.5L6.5 9.5L10.5 5.5" stroke="var(--color-synergy)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
    ),
    info: (
      <svg width="15" height="15" viewBox="0 0 15 15" fill="none" style={{ flexShrink: 0, marginTop: "1px" }}>
        <circle cx="7.5" cy="7.5" r="6.5" stroke="var(--color-accent)" strokeWidth="1.5"/>
        <path d="M7.5 7V10.5" stroke="var(--color-accent)" strokeWidth="1.5" strokeLinecap="round"/>
        <circle cx="7.5" cy="4.5" r="0.75" fill="var(--color-accent)"/>
      </svg>
    ),
  };

  return (
    <div
      className={className}
      style={{
        ...styles[type],
        borderRadius: "6px",
        padding: "12px 16px",
        fontSize: "14px",
        lineHeight: 1.6,
      }}
    >
      <div style={{ display: "flex", gap: "10px", alignItems: "flex-start" }}>
        {iconMap[type]}
        <div style={{ flex: 1 }}>
          {title && (
            <p
              style={{
                fontFamily: "monospace",
                fontSize: "11px",
                fontWeight: 600,
                letterSpacing: "0.08em",
                textTransform: "uppercase",
                color: titleColor[type],
                marginBottom: "4px",
              }}
            >
              {title}
            </p>
          )}
          <div style={{ color: "var(--color-text-secondary)" }}>{children}</div>
        </div>
      </div>
    </div>
  );
};
