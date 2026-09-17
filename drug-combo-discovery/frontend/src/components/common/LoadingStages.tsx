import React, { useEffect, useState } from 'react';
import { Loader2, CheckCircle2, CircleDashed } from 'lucide-react';

const STAGES = [
  'Building biological context from PrimeKG',
  'Tracing drug–target relationships',
  'Analyzing pathway interactions via Heterogeneous Graph Transformer',
  'Generating calibrated synergy / additive / antagonism prediction',
  'Constructing explanation subgraph via gradient backpropagation',
  'Conducting dual faithfulness checks (necessity & sufficiency)',
  'Retrieving supporting literature from NCBI PubMed',
];

interface LoadingStagesProps {
  title?: string;
  subtitle?: string;
}

export const LoadingStages: React.FC<LoadingStagesProps> = ({
  title = 'Inference & Biological Attribution in Progress',
  subtitle = 'Evaluating compound combination through graph neural network pipeline',
}) => {
  const [currentStage, setCurrentStage] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentStage((prev) => (prev < STAGES.length - 1 ? prev + 1 : prev));
    }, 1200);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="bg-[#FFFFFF] border border-[#E5E5E0] rounded-lg p-6 max-w-xl mx-auto shadow-xs">
      <div className="flex items-center gap-3 border-b border-[#E5E5E0] pb-4 mb-5">
        <Loader2 className="w-5 h-5 text-[#0D9488] animate-spin shrink-0" />
        <div>
          <h3 className="font-serif text-lg font-semibold text-[#0F172A]">
            {title}
          </h3>
          <p className="text-xs text-[#717784] mt-0.5">{subtitle}</p>
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
                isPending ? 'opacity-40' : 'opacity-100'
              }`}
            >
              <div className="mt-0.5 shrink-0">
                {isDone ? (
                  <CheckCircle2 className="w-4 h-4 text-[#059669]" />
                ) : isCurrent ? (
                  <Loader2 className="w-4 h-4 text-[#0D9488] animate-spin" />
                ) : (
                  <CircleDashed className="w-4 h-4 text-[#94A3B8]" />
                )}
              </div>
              <div className="flex-1">
                <span
                  className={`text-xs ${
                    isCurrent
                      ? 'font-semibold text-[#0F172A]'
                      : isDone
                      ? 'text-[#334155]'
                      : 'text-[#94A3B8]'
                  }`}
                >
                  {stage}
                </span>
              </div>
              <span className="text-[10px] font-mono text-[#94A3B8]">
                0{idx + 1}
              </span>
            </div>
          );
        })}
      </div>

      <div className="mt-6 pt-4 border-t border-[#F4F4F1] flex items-center justify-between text-[11px] text-[#717784]">
        <span className="font-mono">Device: Heterogeneous Graph Transformer (PyG)</span>
        <span className="font-mono">In-silico ablation active</span>
      </div>
    </div>
  );
};
