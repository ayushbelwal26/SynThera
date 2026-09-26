import React from 'react';
import { BookOpen, ExternalLink, FileText, FlaskConical, Sparkles } from 'lucide-react';
import { useApp } from '../services/AppContext';
import { useNavigate } from 'react-router-dom';
import type { LiteratureCitation } from '../types/api';

interface AugmentedCitation extends LiteratureCitation {
  combination: string;
  cellLine: string;
}

export const EvidencePage: React.FC = () => {
  const navigate = useNavigate();
  const { currentPrediction, recentPredictions } = useApp();

  const allCitations = React.useMemo(() => {
    const list: AugmentedCitation[] = [];
    if (currentPrediction?.supporting_literature) {
      currentPrediction.supporting_literature.forEach((c) => list.push({
        ...c,
        combination: `${currentPrediction.drug_a_name} + ${currentPrediction.drug_b_name}`,
        cellLine: currentPrediction.cell_line,
      }));
    }
    recentPredictions.forEach((p) => {
      if (p !== currentPrediction && p.supporting_literature) {
        p.supporting_literature.forEach((c) => list.push({
          ...c,
          combination: `${p.drug_a_name} + ${p.drug_b_name}`,
          cellLine: p.cell_line,
        }));
      }
    });
    return list;
  }, [currentPrediction, recentPredictions]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Header */}
      <div style={{
        display: 'flex', flexWrap: 'wrap', alignItems: 'flex-start',
        justifyContent: 'space-between', gap: 12,
        borderBottom: '1px solid var(--border)', paddingBottom: 16,
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <BookOpen size={18} style={{ color: 'var(--lit)' }} />
            <h2 style={{
              fontFamily: 'var(--font-serif)', fontSize: 24, fontWeight: 700,
              color: 'var(--text-primary)', margin: 0, letterSpacing: '-0.02em',
            }}>
              Scientific Evidence Catalog
            </h2>
          </div>
          <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
            Retrieved PubMed citations cross-referencing predicted combination mechanisms
          </p>
        </div>
        <span style={{
          fontSize: 11, fontFamily: 'var(--font-mono)', fontWeight: 700,
          backgroundColor: 'var(--lit-subtle)',
          border: '1px solid var(--lit-border)',
          color: 'var(--lit)',
          borderRadius: 4, padding: '5px 10px',
          height: 'fit-content',
        }}>
          NCBI E-Utilities
        </span>
      </div>

      {/* Methodology card */}
      <div style={{
        backgroundColor: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: 8,
        padding: '16px 20px',
        boxShadow: 'var(--shadow-xs)',
      }}>
        <h3 style={{ fontSize: 12, fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 12 }}>
          Dual Validation Methodology
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <div style={{
            padding: '12px 14px',
            backgroundColor: 'var(--accent-subtle)',
            border: '1px solid var(--accent-border)',
            borderRadius: 6,
          }}>
            <p style={{ fontSize: 12, fontWeight: 600, color: 'var(--accent-text)', margin: '0 0 4px' }}>
              1. In-Silico Mechanistic Attribution
            </p>
            <p style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.5, margin: 0 }}>
              Gradient backpropagation through the GNN isolates specific molecular paths explaining why synergy was predicted.
            </p>
          </div>
          <div style={{
            padding: '12px 14px',
            backgroundColor: 'var(--lit-subtle)',
            border: '1px solid var(--lit-border)',
            borderRadius: 6,
          }}>
            <p style={{ fontSize: 12, fontWeight: 600, color: 'var(--lit)', margin: '0 0 4px' }}>
              2. Independent PubMed Triangulation
            </p>
            <p style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.5, margin: 0 }}>
              NCBI ESearch and ESummary dynamically query the biomedical literature to confirm experimental precedent.
            </p>
          </div>
        </div>
      </div>

      {/* Citations */}
      {allCitations.length === 0 ? (
        <div style={{
          backgroundColor: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: 8,
          padding: '48px 24px',
          textAlign: 'center',
          boxShadow: 'var(--shadow-xs)',
        }}>
          <FileText size={32} style={{ color: 'var(--text-muted)', margin: '0 auto 12px' }} />
          <h3 style={{ fontFamily: 'var(--font-serif)', fontSize: 18, fontWeight: 700, color: 'var(--text-primary)', margin: '0 0 8px' }}>
            No citations retrieved yet
          </h3>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: '0 0 20px', lineHeight: 1.6, maxWidth: 380, marginLeft: 'auto', marginRight: 'auto' }}>
            Run a prediction in the Discover page to automatically retrieve NCBI PubMed citations for your candidate combinations.
          </p>
          <button
            type="button"
            onClick={() => navigate('/discover')}
            style={{
              display: 'inline-flex', alignItems: 'center', gap: 8,
              padding: '9px 18px',
              backgroundColor: 'var(--accent)',
              color: '#FFFFFF', border: 'none', borderRadius: 6,
              fontSize: 13, fontWeight: 600, cursor: 'pointer',
            }}
          >
            <FlaskConical size={14} />
            Go to Discover
          </button>
        </div>
      ) : (
        <div>
          <h3 style={{ fontFamily: 'var(--font-serif)', fontSize: 18, fontWeight: 700, color: 'var(--text-primary)', margin: '0 0 12px' }}>
            Retrieved Citations ({allCitations.length})
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 12 }}>
            {allCitations.map((cite, idx) => (
              <div
                key={`${cite.pmid}_${idx}`}
                style={{
                  backgroundColor: 'var(--surface)',
                  border: '1px solid var(--border)',
                  borderRadius: 7,
                  padding: '16px 18px',
                  display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: 10,
                  boxShadow: 'var(--shadow-xs)',
                }}
              >
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                    <span style={{
                      fontSize: 10, fontFamily: 'var(--font-mono)', fontWeight: 700,
                      backgroundColor: 'var(--lit-subtle)', border: '1px solid var(--lit-border)',
                      color: 'var(--lit)', borderRadius: 3, padding: '2px 6px',
                    }}>
                      PMID {cite.pmid}
                    </span>
                    <span style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                      {cite.year}
                    </span>
                  </div>

                  {cite.evidence_type === 'combination' && (
                    <span style={{
                      display: 'inline-flex', alignItems: 'center', gap: 4,
                      fontSize: 9, fontWeight: 700, fontFamily: 'var(--font-mono)',
                      letterSpacing: '0.06em', textTransform: 'uppercase',
                      backgroundColor: 'var(--synergy-subtle)', border: '1px solid var(--synergy-border)',
                      color: 'var(--synergy-text)', borderRadius: 3, padding: '2px 6px', marginBottom: 8,
                    }}>
                      <Sparkles size={9} />Combination Evidence
                    </span>
                  )}

                  <h4 style={{
                    fontSize: 13, fontWeight: 600, color: 'var(--text-primary)',
                    margin: '0 0 6px', lineHeight: 1.4,
                  }}>
                    {cite.title}
                  </h4>

                  <p style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', margin: '0 0 8px' }}>
                    {cite.first_author ? `${cite.first_author} et al.` : 'Author et al.'}
                  </p>

                  <div style={{
                    display: 'inline-flex', alignItems: 'center', gap: 5,
                    fontSize: 11, fontFamily: 'var(--font-mono)',
                    backgroundColor: 'var(--surface-subtle)', border: '1px solid var(--border)',
                    borderRadius: 4, padding: '3px 8px',
                    color: 'var(--text-muted)',
                  }}>
                    {cite.combination} · {cite.cellLine}
                  </div>
                </div>

                <div style={{
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  paddingTop: 10, borderTop: '1px solid var(--border)',
                }}>
                  <span style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                    National Library of Medicine
                  </span>
                  <a
                    href={cite.url} target="_blank" rel="noopener noreferrer"
                    style={{
                      display: 'inline-flex', alignItems: 'center', gap: 4,
                      fontSize: 12, fontWeight: 600, color: 'var(--accent)', textDecoration: 'none',
                    }}
                  >
                    PubMed <ExternalLink size={11} />
                  </a>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
