import React from 'react';
import { BookOpen, ExternalLink, FileText, Search, Sparkles } from 'lucide-react';
import type { LiteratureCitation, LiteratureResult } from '../../types/api';

interface LiteratureSectionProps {
  citations?: LiteratureCitation[];
  literature?: LiteratureResult | null;
  drugAName?: string;
  drugBName?: string;
}

export const LiteratureSection: React.FC<LiteratureSectionProps> = ({
  citations = [],
  literature,
}) => {
  const activeCitations = (literature?.citations && literature.citations.length > 0)
    ? literature.citations
    : (citations && citations.length > 0 ? citations : []);

  const hasCitations = activeCitations.length > 0;
  const queryUsed = literature?.query_used;

  return (
    <div className="bg-[#FFFFFF] border border-[#E5E5E0] rounded-lg p-5 shadow-xs mb-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
        <div>
          <div className="flex items-center gap-2">
            <BookOpen className="w-4 h-4 text-[#B45309]" />
            <h3 className="font-serif text-lg font-bold text-[#0F172A]">
              Supporting Literature & External Evidence (NCBI PubMed RAG)
            </h3>
          </div>
          <p className="text-xs text-[#717784] mt-0.5">
            Retrieve-then-cite biomedical RAG via NCBI E-Utilities with real abstract extraction
          </p>
        </div>

        {/* Clear Trust Distinction Callout */}
        <div className="flex items-center gap-2 text-[10px] font-mono">
          <span className="bg-[#FEF3C7] text-[#92400E] border border-[#FDE68A] px-2 py-0.5 rounded font-semibold">
            EXTERNAL VALIDATION (NCBI PUBMED)
          </span>
          <span className="text-[#94A3B8]">&ne;</span>
          <span className="bg-[#F0FDFA] text-[#0F766E] border border-[#99F6E4] px-2 py-0.5 rounded font-semibold">
            MODEL REASONING (GRAPH GNN)
          </span>
        </div>
      </div>

      {/* Trust Notice */}
      <div className="bg-[#FFFBEB] border border-[#FDE68A] rounded p-3 mb-4 text-xs text-[#92400E] leading-relaxed">
        <strong>Scientific Provenance: </strong>
        Attribution pathways are generated computationally by backpropagating gradients through the Graph Neural Network. Supporting citations below are independently retrieved and verified from the National Library of Medicine (PubMed) to confirm whether this combination or molecular axis has precedent in the peer-reviewed biological literature.
      </div>

      {!hasCitations ? (
        <div className="p-6 text-center bg-[#F8FAFC] border border-[#E2E8F0] rounded-md space-y-3">
          <FileText className="w-7 h-7 text-[#94A3B8] mx-auto" />
          <div>
            <h4 className="text-sm font-semibold text-[#334155]">
              No matching PubMed hits for this mechanism query
            </h4>
            <p className="text-xs text-[#64748B] mt-1 max-w-xl mx-auto leading-relaxed">
              {literature?.no_literature_reason ||
                "No published preclinical or clinical records directly coupling this specific molecular axis were retrieved from NCBI PubMed. This may indicate a novel synergistic candidate discovered computationally by the graph neural network."}
            </p>
          </div>

          {queryUsed && (
            <div className="pt-2 border-t border-[#E2E8F0] max-w-xl mx-auto">
              <span className="text-[11px] font-mono text-[#64748B] flex items-center justify-center gap-1.5 flex-wrap">
                <Search className="w-3 h-3 text-[#94A3B8]" />
                Query executed:
                <code className="bg-[#FFFFFF] border border-[#CBD5E1] text-[#0F172A] px-2 py-0.5 rounded text-[11px] max-w-full truncate font-mono">
                  {queryUsed}
                </code>
              </span>
            </div>
          )}
        </div>
      ) : (
        <div className="space-y-4">
          {queryUsed && (
            <div className="flex items-center gap-2 text-xs text-[#64748B] font-mono bg-[#F8FAFC] border border-[#E2E8F0] px-3 py-1.5 rounded">
              <Search className="w-3.5 h-3.5 text-[#0D9488]" />
              <span className="font-semibold text-[#334155]">PubMed RAG Query:</span>
              <span className="truncate text-[#0F172A]">{queryUsed}</span>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {activeCitations.map((cite, idx) => (
              <div
                key={cite.pmid || idx}
                className="p-4 bg-[#FDFCFB] border border-[#E8E6DF] hover:border-[#CBD5E1] rounded-md transition-all flex flex-col justify-between shadow-2xs"
              >
                <div>
                  <div className="flex items-center justify-between gap-2 mb-2">
                    <span className="text-[10px] font-mono text-[#B45309] bg-[#FEF3C7] border border-[#FDE68A] px-1.5 py-0.5 rounded font-semibold">
                      PMID: {cite.pmid}
                    </span>
                    <span className="text-[11px] font-mono text-[#64748B] font-medium">
                      {cite.year} {cite.journal ? `• ${cite.journal}` : ''}
                    </span>
                  </div>

                  <h4 className="font-serif text-sm font-semibold text-[#0F172A] mb-2 line-clamp-2 leading-snug">
                    {cite.title}
                  </h4>

                  {cite.first_author && (
                    <p className="text-[11px] text-[#64748B] mb-2 font-mono">
                      Author: <span className="text-[#334155] font-medium">{cite.first_author} et al.</span>
                    </p>
                  )}

                  {cite.match_reason && (
                    <div className="mb-2.5">
                      <span className={`inline-flex items-center gap-1 text-[10px] font-mono px-2 py-0.5 rounded font-semibold ${
                        cite.evidence_type === 'combination'
                          ? 'bg-[#ECFDF5] text-[#065F46] border border-[#A7F3D0]'
                          : 'bg-[#F1F5F9] text-[#334155] border border-[#CBD5E1]'
                      }`}>
                        <Sparkles className="w-2.5 h-2.5" />
                        {cite.match_reason}
                      </span>
                    </div>
                  )}

                  {cite.snippet && (
                    <div className="bg-[#F8FAFC] border border-[#E2E8F0] rounded p-2.5 mb-3 text-xs text-[#334155] leading-relaxed italic">
                      &ldquo;{cite.snippet}&rdquo;
                    </div>
                  )}
                </div>

                <div className="pt-2.5 border-t border-[#F4F2EB] flex items-center justify-between text-xs mt-auto">
                  <span className="text-[10px] text-[#94A3B8] font-mono">
                    MEDLINE Verified
                  </span>
                  <a
                    href={cite.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-[#0D9488] hover:text-[#0F766E] font-semibold text-xs transition-colors"
                  >
                    Open in PubMed <ExternalLink className="w-3.5 h-3.5" />
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
