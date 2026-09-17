import { BookOpen, ExternalLink, FileText } from 'lucide-react';
import type { LiteratureCitation } from '../../types/api';

interface LiteratureSectionProps {
  citations: LiteratureCitation[];
  drugAName?: string;
  drugBName?: string;
}

export const LiteratureSection: React.FC<LiteratureSectionProps> = ({
  citations,
}) => {
  const hasCitations = citations && citations.length > 0;

  return (
    <div className="bg-[#FFFFFF] border border-[#E5E5E0] rounded-lg p-5 shadow-xs mb-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
        <div>
          <div className="flex items-center gap-2">
            <BookOpen className="w-4 h-4 text-[#B45309]" />
            <h3 className="font-serif text-lg font-bold text-[#0F172A]">
              Supporting Literature & External Evidence
            </h3>
          </div>
          <p className="text-xs text-[#717784] mt-0.5">
            Peer-reviewed PubMed citations retrieved via NCBI E-Utilities to validate proposed mechanisms
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
        Attribution pathways are generated computationally by backpropagating gradients through the Graph Neural Network. Supporting citations below are independently retrieved from the National Library of Medicine (PubMed) to confirm whether this molecular axis has precedent in the biological literature.
      </div>

      {!hasCitations ? (
        <div className="p-8 text-center bg-[#F8FAFC] border border-[#E2E8F0] rounded-md">
          <FileText className="w-8 h-8 text-[#94A3B8] mx-auto mb-2" />
          <p className="text-xs font-semibold text-[#475569]">
            No supporting literature was retrieved for this relationship.
          </p>
          <p className="text-[11px] text-[#94A3B8] mt-1 max-w-md mx-auto">
            This may indicate a novel, uncharacterized synergistic mechanism discovered by the graph neural network, or that published preclinical data for this pair in this cell line context is currently sparse.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {citations.map((cite, idx) => (
            <div
              key={cite.pmid || idx}
              className="p-4 bg-[#FDFCFB] border border-[#E8E6DF] hover:border-[#D1CEBF] rounded-md transition-all flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] font-mono text-[#B45309] bg-[#FEF3C7] px-1.5 py-0.5 rounded font-semibold">
                    PMID: {cite.pmid}
                  </span>
                  <span className="text-[11px] font-mono text-[#64748B]">
                    {cite.year}
                  </span>
                </div>

                <h4 className="font-serif text-sm font-semibold text-[#0F172A] mb-2 line-clamp-3 leading-snug">
                  {cite.title}
                </h4>

                <p className="text-xs text-[#64748B] mb-3">
                  Author: <span className="text-[#334155] font-medium">{cite.first_author || 'First Author et al.'}</span>
                </p>
              </div>

              <div className="pt-3 border-t border-[#F4F2EB] flex items-center justify-between text-xs">
                <span className="text-[11px] text-[#94A3B8] font-mono">
                  Indexed via NCBI PubMed
                </span>
                <a
                  href={cite.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-[#0D9488] hover:text-[#0F766E] font-semibold text-xs transition-colors"
                >
                  View Publication <ExternalLink className="w-3.5 h-3.5" />
                </a>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
