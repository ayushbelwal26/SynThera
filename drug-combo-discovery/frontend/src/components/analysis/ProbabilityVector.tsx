import React from 'react';
import type { PredictionResult } from '../../types/api';

interface ProbabilityVectorProps {
  prediction: PredictionResult;
}

interface ClassRow {
  label: string;
  prob: number;
  isActive: boolean;
  color: string;
  subtleColor: string;
  borderColor: string;
}

export const ProbabilityVector: React.FC<ProbabilityVectorProps> = ({ prediction }) => {
  const pSyn = prediction.p_synergy ?? 0;
  const pAdd = prediction.p_additive ?? 0;
  const pAnt = prediction.p_antagonism ?? 0;

  const rows: ClassRow[] = [
    {
      label: 'Synergy',
      prob: pSyn,
      isActive: prediction.predicted_class === 'synergy',
      color: 'var(--synergy)',
      subtleColor: 'var(--synergy-subtle)',
      borderColor: 'var(--synergy-border)',
    },
    {
      label: 'Additive',
      prob: pAdd,
      isActive: prediction.predicted_class === 'additive',
      color: 'var(--additive)',
      subtleColor: 'var(--additive-subtle)',
      borderColor: 'var(--additive-border)',
    },
    {
      label: 'Antagonism',
      prob: pAnt,
      isActive: prediction.predicted_class === 'antagonism',
      color: 'var(--antagonism)',
      subtleColor: 'var(--antagonism-subtle)',
      borderColor: 'var(--antagonism-border)',
    },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {/* Stacked full bar */}
      <div style={{
        width: '100%', height: 8,
        borderRadius: 4, overflow: 'hidden',
        display: 'flex',
        backgroundColor: 'var(--surface-subtle)',
        border: '1px solid var(--border)',
      }}>
        {rows.map((r) => (
          <div
            key={r.label}
            style={{
              width: `${(r.prob * 100).toFixed(2)}%`,
              height: '100%',
              backgroundColor: r.color,
              transition: 'width 600ms ease',
            }}
            title={`${r.label}: ${(r.prob * 100).toFixed(1)}%`}
          />
        ))}
      </div>

      {/* Per-class rows */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {rows.map((r) => (
          <div
            key={r.label}
            style={{
              display: 'flex', alignItems: 'center', gap: 12,
              padding: '9px 12px',
              backgroundColor: r.isActive ? r.subtleColor : 'var(--surface-subtle)',
              border: `1px solid ${r.isActive ? r.borderColor : 'var(--border)'}`,
              borderRadius: 6,
              transition: 'background-color 200ms, border-color 200ms',
            }}
          >
            {/* Color swatch */}
            <div style={{
              width: 10, height: 10, borderRadius: 2,
              backgroundColor: r.color, flexShrink: 0,
            }} />

            {/* Label */}
            <span style={{
              fontSize: 13, fontWeight: r.isActive ? 600 : 400,
              color: r.isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
              width: 80, flexShrink: 0,
            }}>
              {r.label}
            </span>

            {/* Bar */}
            <div style={{ flex: 1, position: 'relative' }}>
              <div style={{
                width: '100%', height: 5,
                backgroundColor: 'var(--border)',
                borderRadius: 3, overflow: 'hidden',
              }}>
                <div style={{
                  width: `${(r.prob * 100).toFixed(2)}%`,
                  height: '100%',
                  backgroundColor: r.color,
                  borderRadius: 3,
                  transition: 'width 600ms ease',
                }} />
              </div>
            </div>

            {/* Numeric */}
            <div style={{ display: 'flex', gap: 8, alignItems: 'baseline', flexShrink: 0 }}>
              <span style={{
                fontFamily: 'var(--font-mono)', fontSize: 14, fontWeight: 700,
                color: r.isActive ? r.color : 'var(--text-secondary)',
              }}>
                {(r.prob * 100).toFixed(1)}%
              </span>
              <span style={{
                fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-muted)',
              }}>
                {r.prob.toFixed(4)}
              </span>
              {r.isActive && (
                <span style={{
                  fontSize: 9, fontWeight: 700, fontFamily: 'var(--font-mono)',
                  letterSpacing: '0.06em', textTransform: 'uppercase',
                  backgroundColor: r.subtleColor,
                  border: `1px solid ${r.borderColor}`,
                  color: r.color,
                  borderRadius: 3, padding: '1px 5px',
                }}>
                  predicted
                </span>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Sum check */}
      <div style={{
        fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)',
        textAlign: 'right',
      }}>
        Σ p = {(pSyn + pAdd + pAnt).toFixed(4)} · Temperature-calibrated softmax
      </div>
    </div>
  );
};
