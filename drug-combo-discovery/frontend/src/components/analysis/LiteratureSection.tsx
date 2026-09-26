import React from 'react';
import { ExternalLink, FileText, Search, Sparkles } from 'lucide-react';
import type { LiteratureCitation, LiteratureResult } from '../../types/api';

interface LiteratureSectionProps {
  citations?: LiteratureCitation[];
  literature?: LiteratureResult | null;
  drugAName?: string;
  drugBName?: string;
}

const evidenceTypeStyle = (type?: string) => {
  if (type === 'combination') return { bg: 'var(--synergy-subtle)', border: 'var(--synergy-border)', color: 'var(--synergy-text)', label: 'Combination Evidence' };
  if (type === 'single_drug') return { bg: 'var(--accent-subtle)', border: 'var(--accent-border)', color: 'var(--accent-text)', label: 'Single-Drug Support' };
  return { bg: 'var(--lit-subtle)', border: 'var(--lit-border)', color: 'var(--lit)', label: 'Related Context' };
};

export const LiteratureSection: React.FC<LiteratureSectionProps> = ({ citations = [], literature }) => {
  const activeCitations = (literature?.citations && literature.citations.length > 0)
    ? literature.citations
    : citations.length > 0 ? citations : [];

  const hasCitations = activeCitations.length > 0;
  const queryUsed = literature?.query_used;

  if (!hasCitations) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '24px 0', gap: 10 }}>
        <FileText size={28} style={{ color: 'var(--text-muted)' }} />
        <div style={{ textAlign: 'center' }}>
          <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)', margin: 0 }}>
            No matching PubMed records
          </p>
          <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4, lineHeight: 1.5, maxWidth: 400 }}>
            {literature?.no_literature_reason || 'This may indicate a computationally novel combination with no direct published precedent.'}
          </p>
        </div>
        {queryUsed && (
          <div style={{
            display: 'flex', alignItems: 'center', gap: 6,
            fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)',
          }}>
            <Search size={11} />
            Query: <code style={{ backgroundColor: 'var(--surface-subtle)', border: '1px solid var(--border)', padding: '1px 6px', borderRadius: 3 }}>{queryUsed}</code>
          </div>
        )}
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      {/* Provenance notice */}
      <div style={{
        fontSize: 12, color: 'var(--lit)',
        backgroundColor: 'var(--lit-subtle)',
        border: '1px solid var(--lit-border)',
        borderRadius: 6, padding: '8px 12px',
        lineHeight: 1.5,
      }}>
        <strong>Independent retrieval:</strong> These citations are fetched from NCBI PubMed independently of the GNN prediction. They are not used to train the model.
      </div>

      {/* Query */}
      {queryUsed && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8,
          fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)',
          backgroundColor: 'var(--surface-subtle)',
          border: '1px solid var(--border)',
          borderRadius: 6, padding: '6px 10px',
        }}>
          <Search size={11} style={{ color: 'var(--accent)', flexShrink: 0 }} />
          <span style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>PubMed query:</span>
          <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{queryUsed}</span>
        </div>
      )}

      {/* Citation grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 10 }}>
        {activeCitations.map((cite, idx) => {
          const evStyle = evidenceTypeStyle(cite.evidence_type);
          return (
            <div
              key={cite.pmid || idx}
              style={{
                backgroundColor: 'var(--surface)',
                border: '1px solid var(--border)',
                borderRadius: 7,
                padding: '14px 16px',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                gap: 10,
                boxShadow: 'var(--shadow-xs)',
              }}
            >
              <div>
                {/* PMID + year */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <span style={{
                    fontSize: 10, fontFamily: 'var(--font-mono)', fontWeight: 700,
                    backgroundColor: 'var(--lit-subtle)', border: '1px solid var(--lit-border)',
                    color: 'var(--lit)', borderRadius: 3, padding: '2px 6px',
                  }}>
                    PMID {cite.pmid}
                  </span>
                  <span style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                    {cite.year}{cite.journal ? ` · ${cite.journal}` : ''}
                  </span>
                </div>

                {/* Evidence type badge */}
                <span style={{
                  display: 'inline-flex', alignItems: 'center', gap: 4,
                  fontSize: 9, fontWeight: 700, fontFamily: 'var(--font-mono)',
                  letterSpacing: '0.06em', textTransform: 'uppercase',
                  backgroundColor: evStyle.bg, border: `1px solid ${evStyle.border}`,
                  color: evStyle.color,
                  borderRadius: 3, padding: '2px 6px', marginBottom: 8,
                }}>
                  {cite.evidence_type === 'combination' && <Sparkles size={9} />}
                  {cite.evidence_type === 'single_drug' && <FileText size={9} />}
                  {evStyle.label}
                </span>

                {/* Title */}
                <h4 style={{
                  fontFamily: 'var(--font-sans)', fontSize: 13, fontWeight: 600,
                  color: 'var(--text-primary)', margin: '0 0 6px',
                  lineHeight: 1.4,
                  display: '-webkit-box',
                  WebkitLineClamp: 3,
                  WebkitBoxOrient: 'vertical',
                  overflow: 'hidden',
                }}>
                  {cite.title}
                </h4>

                {/* Author */}
                {cite.first_author && (
                  <p style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', margin: '0 0 6px' }}>
                    {cite.first_author} et al.
                  </p>
                )}

                {/* Snippet */}
                {cite.snippet && (
                  <blockquote style={{
                    fontSize: 11, color: 'var(--text-secondary)',
                    backgroundColor: 'var(--surface-subtle)',
                    border: '1px solid var(--border)',
                    borderLeft: '2px solid var(--accent)',
                    borderRadius: '0 4px 4px 0',
                    padding: '6px 10px',
                    margin: '6px 0 0',
                    lineHeight: 1.5, fontStyle: 'italic',
                    display: '-webkit-box',
                    WebkitLineClamp: 3,
                    WebkitBoxOrient: 'vertical',
                    overflow: 'hidden',
                  }}>
                    "{cite.snippet}"
                  </blockquote>
                )}
              </div>

              {/* Footer */}
              <div style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                paddingTop: 8, borderTop: '1px solid var(--border)',
              }}>
                <span style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                  MEDLINE / NLM
                </span>
                <a
                  href={cite.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    display: 'inline-flex', alignItems: 'center', gap: 4,
                    fontSize: 12, fontWeight: 600, color: 'var(--accent)',
                    textDecoration: 'none',
                  }}
                >
                  Open in PubMed <ExternalLink size={12} />
                </a>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
