import React, { useEffect, useState } from 'react';
import { Loader2, CheckCircle2, Circle } from 'lucide-react';

const STAGES = [
  'Building biological context from PrimeKG',
  'Tracing drug–target binding relationships',
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
    <div style={{
      backgroundColor: 'var(--surface)',
      border: '1px solid var(--border)',
      borderRadius: 8,
      padding: '24px',
      maxWidth: 480,
      margin: '0 auto',
      boxShadow: 'var(--shadow-sm)',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 12,
        paddingBottom: 16, borderBottom: '1px solid var(--border)',
        marginBottom: 18,
      }}>
        <Loader2
          size={18}
          style={{ color: 'var(--accent)', flexShrink: 0, animation: 'spin 1s linear infinite' }}
        />
        <div>
          <h3 style={{
            fontFamily: 'var(--font-serif)', fontSize: 16, fontWeight: 700,
            color: 'var(--text-primary)', margin: 0, letterSpacing: '-0.01em',
          }}>
            {title}
          </h3>
          <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 3 }}>{subtitle}</p>
        </div>
      </div>

      {/* Stage list */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {STAGES.map((stage, idx) => {
          const isDone = idx < currentStage;
          const isCurrent = idx === currentStage;
          const isPending = idx > currentStage;

          return (
            <div
              key={stage}
              style={{
                display: 'flex', alignItems: 'center', gap: 10,
                opacity: isPending ? 0.35 : 1,
                transition: 'opacity 300ms',
              }}
            >
              {isDone ? (
                <CheckCircle2 size={15} style={{ color: 'var(--synergy)', flexShrink: 0 }} />
              ) : isCurrent ? (
                <Loader2 size={15} style={{ color: 'var(--accent)', flexShrink: 0, animation: 'spin 1s linear infinite' }} />
              ) : (
                <Circle size={15} style={{ color: 'var(--border-strong)', flexShrink: 0 }} />
              )}
              <span style={{
                fontSize: 12,
                color: isCurrent ? 'var(--text-primary)' : isDone ? 'var(--text-secondary)' : 'var(--text-muted)',
                fontWeight: isCurrent ? 600 : 400,
                flex: 1,
              }}>
                {stage}
              </span>
              <span style={{
                fontSize: 10, fontFamily: 'var(--font-mono)',
                color: 'var(--text-muted)',
              }}>
                {String(idx + 1).padStart(2, '0')}
              </span>
            </div>
          );
        })}
      </div>

      <div style={{
        marginTop: 18, paddingTop: 14, borderTop: '1px solid var(--border)',
        display: 'flex', justifyContent: 'space-between',
        fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)',
      }}>
        <span>Heterogeneous Graph Transformer (PyG)</span>
        <span>In-silico ablation active</span>
      </div>
    </div>
  );
};
