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

  return (
    <div className="max-w-xl border border-[#CFC9BC] p-5">
      <div className="border-b border-[#CFC9BC] pb-4 mb-4">
        <h3 className="font-serif text-[20px] text-[#1A1F1C] font-semibold">
          {title}
        </h3>
        <p className="font-mono text-[13px] text-[#6B746C] mt-1">{subtitle}</p>
      </div>

      <div className="space-y-2.5">
        {STAGES.map((stage, idx) => {
          const isDone = idx < currentStage;
          const isCurrent = idx === currentStage;
          const isPending = idx > currentStage;

          return (
            <div
              key={stage}
              className={`flex items-baseline gap-3 ${
                isPending ? "opacity-35" : ""
              }`}
            >
              <span className="font-mono text-[12px] text-[#6B746C] w-5">
                {String(idx + 1).padStart(2, "0")}
              </span>
              <span
                className={`text-[14px] flex-1 ${
                  isCurrent
                    ? "text-[#1A1F1C] font-medium"
                    : isDone
                      ? "text-[#4A524C]"
                      : "text-[#6B746C]"
                }`}
              >
                {stage}
                {isCurrent && (
                  <span className="font-mono text-[12px] text-[#1A535C] ml-2">
                    …
                  </span>
                )}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
