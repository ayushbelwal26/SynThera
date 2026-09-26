import React, { useEffect, useState } from "react";
import { Loader2, CheckCircle2, CircleDashed } from "lucide-react";

const STAGES = [
  "Building biological context from PrimeKG",
  "Tracing drug–target relationships",
  "Analyzing pathway interactions via Heterogeneous Graph Transformer",
  "Generating calibrated synergy / additive / antagonism prediction",
  "Constructing explanation subgraph via gradient backpropagation",
  "Conducting dual faithfulness checks (necessity & sufficiency)",
  "Retrieving supporting literature from NCBI PubMed",
];

interface LoadingStagesProps {
  title?: string;
  subtitle?: string;
}

export const LoadingStages: React.FC<LoadingStagesProps> = ({
  title = "Inference & Biological Attribution in Progress",
  subtitle = "Evaluating compound combination through graph neural network pipeline",
}) => {
  const [currentStage, setCurrentStage] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentStage((prev) => (prev < STAGES.length - 1 ? prev + 1 : prev));
    }, 1200);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="syn-card rounded-lg p-6 max-w-xl mx-auto">
      <div className="flex items-center gap-3 border-b border-[#E5E2DC] pb-4 mb-5">
        <Loader2 className="w-5 h-5 text-[#2F6B5E] animate-spin shrink-0" />
        <div>
          <h3 className="text-lg font-semibold text-[#1C2421]">{title}</h3>
          <p className="text-xs text-[#7A827C] mt-0.5">{subtitle}</p>
        </div>
      </div>

      <div className="space-y-3">
        {STAGES.map((stage, idx) => {
          const isDone = idx < currentStage;
          const isCurrent = idx === currentStage;
          const isPending = idx > currentStage;

          return (
            <div
              key={stage}
              className={`flex items-start gap-3 transition-opacity duration-300 ${
                isPending ? "opacity-40" : "opacity-100"
              }`}
            >
              <div className="mt-0.5 shrink-0">
                {isDone ? (
                  <CheckCircle2 className="w-4 h-4 text-[#3D7A6C]" />
                ) : isCurrent ? (
                  <Loader2 className="w-4 h-4 text-[#2F6B5E] animate-spin" />
                ) : (
                  <CircleDashed className="w-4 h-4 text-[#8A918C]" />
                )}
              </div>
              <div className="flex-1">
                <span
                  className={`text-xs ${
                    isCurrent
                      ? "font-semibold text-[#1C2421]"
                      : isDone
                        ? "text-[#3D4742]"
                        : "text-[#8A918C]"
                  }`}
                >
                  {stage}
                </span>
              </div>
              <span className="text-[10px] font-mono text-[#8A918C]">
                0{idx + 1}
              </span>
            </div>
          );
        })}
      </div>

      <div className="mt-4 pt-4 border-t border-[#F4F4F1] flex items-center justify-between text-[11px] text-[#7A827C]">
        <span className="font-mono">
          Device: Heterogeneous Graph Transformer (PyG)
        </span>
        <span className="font-mono">In-silico ablation active</span>
      </div>
    </div>
  );
};
