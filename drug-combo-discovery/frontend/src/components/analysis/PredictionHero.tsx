import React from 'react';
import { Download, Share2, Clock, Database } from 'lucide-react';
import type { PredictionResult } from '../../types/api';

interface PredictionHeroProps {
  prediction: PredictionResult;
  disease?: string;
}

const classConfig = {
  synergy: {
    label: 'Synergy',
    color: 'var(--synergy)',
    subtle: 'var(--synergy-subtle)',
    border: 'var(--synergy-border)',
    text: 'var(--synergy-text)',
  },
  antagonism: {
    label: 'Antagonism',
    color: 'var(--antagonism)',
    subtle: 'var(--antagonism-subtle)',
    border: 'var(--antagonism-border)',
    text: 'var(--antagonism-text)',
  },
  additive: {
    label: 'Additive',
    color: 'var(--additive)',
    subtle: 'var(--additive-subtle)',
    border: 'var(--additive-border)',
    text: 'var(--additive-text)',
  },
} as const;

export const PredictionHero: React.FC<PredictionHeroProps> = ({ prediction, disease }) => {
  const cls = classConfig[prediction.predicted_class as keyof typeof classConfig] ?? classConfig.additive;
  const pSyn = prediction.p_synergy ?? 0;
  const vScore = prediction.v_score ?? prediction.ranking?.v_score ?? prediction.score;

  const handleExportJson = () => {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(prediction, null, 2));
    const a = document.createElement('a');
    a.setAttribute('href', dataStr);
    a.setAttribute('download', `synthera_${prediction.drug_a_name}_${prediction.drug_b_name}_${prediction.cell_line}.json`);
    document.body.appendChild(a);
    a.click();
    a.remove();
  };

  const handleCopySummary = () => {
    const s = `SynThera Prediction
Drug Pair: ${prediction.drug_a_name} + ${prediction.drug_b_name}
Cell Line: ${prediction.cell_line}${disease ? ` (${disease})` : ''}
Predicted Class: ${prediction.predicted_class.toUpperCase()}
Synergy Probability: ${(pSyn * 100).toFixed(1)}%
Composite V-Score: ${vScore.toFixed(4)}
DrugBank IDs: ${prediction.drug_a} / ${prediction.drug_b}`;
    navigator.clipboard.writeText(s);
  };

  return (
    <div
      className="hero-surface"
      style={{
        border: '1px solid var(--border)',
        borderRadius: 10,
        padding: '24px 28px',
        boxShadow: 'var(--shadow-sm)',
      }}
    >
      {/* Top row: drug pair + export controls */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap' }}>
        <div>
          {/* Drug pair headline */}
          <h2 style={{
            fontFamily: 'var(--font-serif)',
            fontSize: 26,
            fontWeight: 700,
            color: 'var(--text-primary)',
            letterSpacing: '-0.03em',
            lineHeight: 1.2,
            margin: 0,
          }}>
            {prediction.drug_a_name}{' '}
            <span style={{ fontWeight: 300, color: 'var(--text-muted)', fontFamily: 'var(--font-sans)', fontSize: 20 }}>+</span>
            {' '}{prediction.drug_b_name}
          </h2>

          {/* Context metadata */}
          <div style={{
            display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 10,
            marginTop: 6, fontSize: 12, color: 'var(--text-muted)',
            fontFamily: 'var(--font-mono)',
          }}>
            <span>
              Cell line:{' '}
              <strong style={{ color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
                {prediction.cell_line}
              </strong>
            </span>
            {disease && (
              <>
                <span style={{ color: 'var(--border-strong)' }}>·</span>
                <span>Indication: <strong style={{ color: 'var(--text-secondary)' }}>{disease}</strong></span>
              </>
            )}
            <span style={{ color: 'var(--border-strong)' }}>·</span>
            <span>{prediction.drug_a} / {prediction.drug_b}</span>
            {prediction.cached && (
              <>
                <span style={{ color: 'var(--border-strong)' }}>·</span>
                <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  <Database size={10} /> cached
                </span>
              </>
            )}
            {prediction.timestamp && (
              <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <Clock size={10} />
                {new Date(prediction.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            )}
          </div>
        </div>

        {/* Export controls */}
        <div style={{ display: 'flex', gap: 8, flexShrink: 0, marginTop: 2 }}>
          <button
            type="button"
            onClick={handleCopySummary}
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '7px 12px',
              fontSize: 12, fontWeight: 600,
              backgroundColor: 'var(--surface)',
              border: '1px solid var(--border)',
              borderRadius: 6,
              color: 'var(--text-secondary)',
              cursor: 'pointer',
              transition: 'border-color 150ms, color 150ms',
            }}
            title="Copy plaintext summary to clipboard"
          >
            <Share2 size={13} />
            Copy
          </button>
          <button
            type="button"
            onClick={handleExportJson}
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '7px 12px',
              fontSize: 12, fontWeight: 600,
              backgroundColor: 'var(--accent)',
              border: '1px solid var(--accent)',
              borderRadius: 6,
              color: '#FFFFFF',
              cursor: 'pointer',
              transition: 'background-color 150ms',
            }}
            title="Export full JSON analysis"
          >
            <Download size={13} />
            Export JSON
          </button>
        </div>
      </div>

      {/* Divider */}
      <div style={{ height: 1, backgroundColor: 'var(--border)', margin: '18px 0' }} />

      {/* Primary result row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 24, flexWrap: 'wrap' }}>
        {/* Prediction class badge */}
        <div style={{
          backgroundColor: cls.subtle,
          border: `1px solid ${cls.border}`,
          borderRadius: 8,
          padding: '12px 20px',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 2,
          minWidth: 120,
        }}>
          <span style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', color: cls.text }}>
            Predicted
          </span>
          <span style={{ fontSize: 20, fontWeight: 700, color: cls.color, letterSpacing: '-0.02em' }}>
            {cls.label}
          </span>
        </div>

        {/* Synergy probability */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <span style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
            Synergy Probability
          </span>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
            <span style={{
              fontFamily: 'var(--font-mono)',
              fontSize: 36,
              fontWeight: 700,
              color: 'var(--synergy)',
              letterSpacing: '-0.04em',
              lineHeight: 1,
            }}>
              {(pSyn * 100).toFixed(1)}%
            </span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--text-muted)' }}>
              p = {pSyn.toFixed(4)}
            </span>
          </div>
          {/* Thin probability bar */}
          <div style={{
            width: 200, height: 4, backgroundColor: 'var(--surface-subtle)',
            borderRadius: 2, overflow: 'hidden', marginTop: 4,
            border: '1px solid var(--border)',
          }}>
            <div style={{
              width: `${(pSyn * 100).toFixed(1)}%`,
              height: '100%',
              backgroundColor: cls.color,
              borderRadius: 2,
              transition: 'width 600ms ease',
            }} />
          </div>
        </div>

        {/* V-score (if available) */}
        {prediction.ranking && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2, marginLeft: 8 }}>
            <span style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
              Composite V-Score
            </span>
            <span style={{
              fontFamily: 'var(--font-mono)',
              fontSize: 22,
              fontWeight: 700,
              color: 'var(--accent)',
              letterSpacing: '-0.03em',
            }}>
              {vScore.toFixed(4)}
            </span>
            <span style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
              tox penalty: {(prediction.ranking.toxicity_penalty ?? 0).toFixed(3)}
            </span>
          </div>
        )}

        {/* Explanation snippet */}
        {prediction.explanation_text && (
          <div style={{
            flex: 1, minWidth: 200,
            borderLeft: '2px solid var(--border)',
            paddingLeft: 16,
          }}>
            <span style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>
              Model Rationale
            </span>
            <p style={{
              fontSize: 13, color: 'var(--text-secondary)',
              lineHeight: 1.55, margin: 0,
              display: '-webkit-box',
              WebkitLineClamp: 3,
              WebkitBoxOrient: 'vertical',
              overflow: 'hidden',
            }}>
              {prediction.explanation_text}
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
