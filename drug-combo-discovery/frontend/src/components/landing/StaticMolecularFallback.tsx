import React from "react";

/**
 * Luminous particle-dotted DNA double-helix fallback displayed on
 * reduced-motion preferences, WebGL failure, or lazy chunk load.
 */
export const StaticMolecularFallback: React.FC<{ className?: string }> = ({
  className = "",
}) => {
  const strandSteps = Array.from({ length: 48 }, (_, i) => i / 47);
  const rungSteps = [0.12, 0.2, 0.28, 0.36, 0.44, 0.52, 0.6, 0.68, 0.76, 0.84, 0.92];

  return (
    <div
      aria-hidden="true"
      className={`pointer-events-none fixed inset-0 z-0 overflow-hidden bg-[#020409] ${className}`}
    >
      <div
        className="absolute inset-0"
        style={{
          background:
            "radial-gradient(60% 58% at 70% 48%, rgba(34, 211, 238, 0.08) 0%, rgba(29, 111, 255, 0.05) 38%, rgba(2, 4, 9, 0) 76%)",
        }}
      />

      <svg
        viewBox="0 0 600 720"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="absolute right-[-3%] top-1/2 h-[88vh] max-h-[780px] w-auto -translate-y-1/2 rotate-[-15deg] opacity-70"
      >
        {rungSteps.map((t) => {
          const y = 70 + t * 580;
          const theta = t * 2.5 * Math.PI * 2;
          const x1 = 300 + Math.cos(theta) * 90;
          const x2 = 300 + Math.cos(theta + 2.38) * 90;
          return Array.from({ length: 8 }, (_, k) => {
            const u = (k + 0.5) / 8;
            const px = x1 + (x2 - x1) * u;
            return (
              <circle
                key={`rung-${t}-${k}`}
                cx={px}
                cy={y}
                r={Math.abs(u - 0.5) < 0.15 ? 2.1 : 1.7}
                fill={Math.abs(u - 0.5) < 0.15 ? "#E8F8FF" : "#38BDF8"}
                fillOpacity={0.72}
              />
            );
          });
        })}

        {strandSteps.map((t, idx) => {
          const y = 70 + t * 580;
          const theta = t * 2.5 * Math.PI * 2;
          const xA = 300 + Math.cos(theta) * 90;
          const xB = 300 + Math.cos(theta + 2.38) * 90;
          const fade = Math.sin(t * Math.PI);
          return (
            <g key={`strand-${idx}`} opacity={0.35 + fade * 0.65}>
              <circle cx={xA} cy={y} r={2.6} fill="#22D3EE" />
              <circle cx={xA + 4} cy={y + 2} r={1.4} fill="#1D6FFF" opacity={0.75} />
              <circle cx={xB} cy={y} r={2.6} fill="#1D6FFF" />
              <circle cx={xB - 4} cy={y - 2} r={1.4} fill="#E8F8FF" opacity={0.75} />
            </g>
          );
        })}
      </svg>
    </div>
  );
};
