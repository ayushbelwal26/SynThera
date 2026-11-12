import React, { useEffect, useState } from "react";

const STAGES = [
  "Building biological context from PrimeKG",
  "Tracing drug–target relationships",
  "Analyzing pathway interactions via HGT",
  "Generating calibrated class probabilities",
  "Constructing explanation subgraph",
  "Running faithfulness ablation",
  "Retrieving PubMed literature",
];

interface LoadingStagesProps {
  title?: string;
  subtitle?: string;
}

export const LoadingStages: React.FC<LoadingStagesProps> = ({
  title = "Inference in progress",
  subtitle = "Heterogeneous Graph Transformer over PrimeKG",
}) => {
  const [currentStage, setCurrentStage] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentStage((prev) => (prev < STAGES.length - 1 ? prev + 1 : prev));
    }, 1200);
    return () => clearInterval(interval);
  }, []);

  const progressPct = Math.round((currentStage / (STAGES.length - 1)) * 100);

  return (
    <>
      <style>{`
        @keyframes loading-pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.4; transform: scale(0.7); }
        }
        @keyframes dna-spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
        @keyframes dna-counter-spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(-360deg); }
        }
        .dna-ring-outer {
          animation: dna-spin 3s linear infinite;
        }
        .dna-ring-inner {
          animation: dna-counter-spin 2s linear infinite;
        }
        .dot-pulse-1 { animation: loading-pulse 1.4s ease-in-out 0s infinite; }
        .dot-pulse-2 { animation: loading-pulse 1.4s ease-in-out 0.2s infinite; }
        .dot-pulse-3 { animation: loading-pulse 1.4s ease-in-out 0.4s infinite; }
        .progress-bar-fill {
          transition: width 0.9s cubic-bezier(0.4, 0, 0.2, 1);
        }
      `}</style>

      <div
        style={{
          maxWidth: "520px",
          border: "1px solid var(--color-rule-strong)",
          borderRadius: "12px",
          padding: "24px",
          background: "var(--color-panel)",
        }}
      >
        {/* Header with DNA spinner */}
        <div
          style={{
            borderBottom: "1px solid var(--color-rule)",
            paddingBottom: "20px",
            marginBottom: "20px",
            display: "flex",
            alignItems: "flex-start",
            gap: "16px",
          }}
        >
          {/* DNA Helix / Molecule spinner */}
          <div style={{ position: "relative", width: "48px", height: "48px", flexShrink: 0 }}>
            {/* Outer ring */}
            <div
              className="dna-ring-outer"
              style={{
                position: "absolute",
                inset: 0,
                borderRadius: "50%",
                border: "2px solid var(--color-accent)",
                borderTopColor: "transparent",
                borderRightColor: "transparent",
                boxShadow: "0 0 12px var(--color-accent-glow)",
              }}
            />
            {/* Inner ring */}
            <div
              className="dna-ring-inner"
              style={{
                position: "absolute",
                inset: "8px",
                borderRadius: "50%",
                border: "2px solid var(--color-accent)",
                borderBottomColor: "transparent",
                borderLeftColor: "transparent",
                opacity: 0.6,
              }}
            />
            {/* Center dot */}
            <div
              style={{
                position: "absolute",
                inset: "18px",
                borderRadius: "50%",
                background: "var(--color-accent)",
                boxShadow: "0 0 8px var(--color-accent-glow)",
              }}
            />
          </div>

          <div>
            <h3
              style={{
                fontFamily: "Georgia, serif",
                fontSize: "18px",
                fontWeight: 600,
                color: "var(--color-text-primary)",
                lineHeight: 1.3,
                margin: 0,
              }}
            >
              {title}
            </h3>
            <p
              style={{
                fontFamily: "monospace",
                fontSize: "12px",
                color: "var(--color-text-muted)",
                marginTop: "4px",
              }}
            >
              {subtitle}
            </p>
          </div>
        </div>

        {/* Progress bar */}
        <div
          style={{
            height: "4px",
            background: "var(--color-rule)",
            borderRadius: "2px",
            marginBottom: "20px",
            overflow: "hidden",
          }}
        >
          <div
            className="progress-bar-fill"
            style={{
              height: "100%",
              width: `${progressPct}%`,
              background: "var(--color-accent)",
              borderRadius: "2px",
              boxShadow: "0 0 10px var(--color-accent-glow)",
            }}
          />
        </div>

        {/* Stage list */}
        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          {STAGES.map((stage, idx) => {
            const isDone = idx < currentStage;
            const isCurrent = idx === currentStage;
            const isPending = idx > currentStage;

            return (
              <div
                key={stage}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "12px",
                  opacity: isPending ? 0.3 : 1,
                  transition: "opacity 0.4s ease",
                }}
              >
                {/* Stage indicator */}
                <div
                  style={{
                    width: "20px",
                    height: "20px",
                    borderRadius: "50%",
                    flexShrink: 0,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    background: isDone
                      ? "var(--color-accent)"
                      : isCurrent
                        ? "var(--color-accent-soft)"
                        : "transparent",
                    border: isCurrent
                      ? "2px solid var(--color-accent)"
                      : isDone
                        ? "none"
                        : "2px solid var(--color-rule-strong)",
                    boxShadow: isCurrent ? "0 0 10px var(--color-accent-glow)" : undefined,
                    transition: "all 0.4s ease",
                  }}
                >
                  {isDone && (
                    <svg width="10" height="8" viewBox="0 0 10 8" fill="none">
                      <path d="M1 4L3.5 6.5L9 1" stroke="var(--color-bg)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                  )}
                  {isCurrent && (
                    <div
                      style={{
                        width: "6px",
                        height: "6px",
                        borderRadius: "50%",
                        background: "var(--color-accent)",
                        animation: "loading-pulse 1.2s ease-in-out infinite",
                      }}
                    />
                  )}
                </div>

                {/* Stage text */}
                <span
                  style={{
                    fontSize: "13px",
                    flex: 1,
                    color: isCurrent
                      ? "var(--color-text-primary)"
                      : isDone
                        ? "var(--color-text-secondary)"
                        : "var(--color-text-muted)",
                    fontWeight: isCurrent ? 500 : 400,
                    transition: "color 0.4s ease",
                  }}
                >
                  {stage}
                </span>

                {/* Animated dots for current stage */}
                {isCurrent && (
                  <div style={{ display: "flex", gap: "3px", alignItems: "center" }}>
                    <div
                      className="dot-pulse-1"
                      style={{
                        width: "5px",
                        height: "5px",
                        borderRadius: "50%",
                        background: "var(--color-accent)",
                      }}
                    />
                    <div
                      className="dot-pulse-2"
                      style={{
                        width: "5px",
                        height: "5px",
                        borderRadius: "50%",
                        background: "var(--color-accent)",
                      }}
                    />
                    <div
                      className="dot-pulse-3"
                      style={{
                        width: "5px",
                        height: "5px",
                        borderRadius: "50%",
                        background: "var(--color-accent)",
                      }}
                    />
                  </div>
                )}

                {/* Step number for pending */}
                {isPending && (
                  <span
                    style={{
                      fontFamily: "monospace",
                      fontSize: "11px",
                      color: "var(--color-text-muted)",
                    }}
                  >
                    {String(idx + 1).padStart(2, "0")}
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </>
  );
};
