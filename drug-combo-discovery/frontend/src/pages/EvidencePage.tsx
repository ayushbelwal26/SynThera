import React from 'react';
import { BookOpen, ExternalLink, FileText } from 'lucide-react';
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

  // Aggregate all literature from current and recent evaluations
  const allCitations = React.useMemo(() => {
    const list: AugmentedCitation[] = [];
    if (currentPrediction && currentPrediction.supporting_literature) {
      currentPrediction.supporting_literature.forEach((c) => {
        list.push({
          ...c,
          combination: `${currentPrediction.drug_a_name} × ${currentPrediction.drug_b_name}`,
          cellLine: currentPrediction.cell_line,
        });
      });
    }
    recentPredictions.forEach((p) => {
      if (p !== currentPrediction && p.supporting_literature) {
        p.supporting_literature.forEach((c) => {
          list.push({
            ...c,
            combination: `${p.drug_a_name} × ${p.drug_b_name}`,
            cellLine: p.cell_line,
          });
        });
      }
    });
    return list;
  }, [currentPrediction, recentPredictions]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="border-b border-[#E5E5E0] pb-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-[#B45309]" />
            <h2 className="font-serif text-2xl font-bold text-[#0F172A]">
              Scientific Evidence & Literature Catalog
            </h2>
          </div>
          <p className="text-xs text-[#717784] mt-0.5">
            Retrieved PubMed citations cross-referencing model-predicted drug synergy mechanisms with published biological experimental literature
          </p>
        </div>

        {/* Provenance Badge */}
        <div className="flex items-center gap-2 text-xs font-mono">
          <span className="bg-[#FEF3C7] text-[#92400E] border border-[#FDE68A] px-2.5 py-1 rounded font-semibold">
            NCBI E-Utilities Verified
          </span>
        </div>
      </div>

      {/* Trust & Provenance Card */}
      <div className="bg-[#FFFFFF] border border-[#E5E5E0] rounded-lg p-5 shadow-xs">
        <h3 className="font-serif text-sm font-bold text-[#0F172A] uppercase tracking-wider mb-1.5">
          Dual Validation Methodology
        </h3>
        <p className="text-xs text-[#475569] leading-relaxed mb-3">
          Synthera establishes clinical confidence by triangulating computational graph attribution against peer-reviewed experimental publications:
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div className="p-3 bg-[#F0FDFA] border border-[#99F6E4] rounded">
            <span className="font-semibold text-[#0F766E] block mb-1">
              1. In-Silico Mechanistic Attribution
            </span>
            <p className="text-[#334155] leading-relaxed">
              Gradient backpropagation isolates specific molecular paths (e.g. drug-target bindings, pathway cascades) explaining why the model predicted synergy over additive outcomes.
            </p>
          </div>
          <div className="p-3 bg-[#FEF3C7] border border-[#FDE68A] rounded">
            <span className="font-semibold text-[#92400E] block mb-1">
              2. Independent PubMed Triangulation
            </span>
            <p className="text-[#334155] leading-relaxed">
              NCBI ESearch and ESummary dynamically query the biomedical literature for the identified targets and indications, confirming whether the computational axis has experimental precedent.
            </p>
          </div>
        </div>
      </div>

      {/* Evidence Table / Cards */}
      {allCitations.length === 0 ? (
        <div className="bg-[#FFFFFF] border border-[#E5E5E0] rounded-lg p-12 text-center shadow-xs">
          <FileText className="w-10 h-10 text-[#94A3B8] mx-auto mb-3" />
          <h3 className="font-serif text-lg font-bold text-[#0F172A] mb-1">
            No supporting literature was retrieved for this relationship.
          </h3>
          <p className="text-xs text-[#64748B] max-w-md mx-auto mb-5 leading-relaxed">
            Run a prediction in the query instrument to retrieve verified citations for candidate combinations from NCBI PubMed.
          </p>
          <button
            type="button"
            onClick={() => navigate('/discover')}
            className="px-4 py-2 bg-[#0D9488] hover:bg-[#0F766E] text-[#FFFFFF] rounded text-xs font-semibold inline-flex items-center gap-2 transition-colors cursor-pointer"
          >
            Launch Query Instrument
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-serif text-base font-bold text-[#0F172A]">
              Retrieved Citations ({allCitations.length})
            </h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {allCitations.map((cite, idx) => (
              <div
                key={`${cite.pmid}_${idx}`}
                className="bg-[#FFFFFF] border border-[#E5E5E0] hover:border-[#CBD5E1] rounded-lg p-5 shadow-xs transition-all flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] font-mono text-[#B45309] bg-[#FEF3C7] px-2 py-0.5 rounded font-bold">
                      PMID: {cite.pmid}
                    </span>
                    <span className="text-xs font-mono text-[#64748B]">
                      {cite.year}
                    </span>
                  </div>

                  <h4 className="font-serif text-base font-semibold text-[#0F172A] mb-2 leading-snug">
                    {cite.title}
                  </h4>

                  <p className="text-xs text-[#64748B] mb-2">
                    First Author: <strong className="text-[#334155]">{cite.first_author || 'First Author et al.'}</strong>
                  </p>

                  <div className="inline-flex items-center gap-1.5 text-[11px] font-mono bg-[#F8FAFC] text-[#475569] border border-[#E2E8F0] px-2 py-1 rounded">
                    <span>Associated Combination:</span>
                    <strong className="text-[#0F172A]">{cite.combination}</strong>
                    <span>({cite.cellLine})</span>
                  </div>
                </div>

                <div className="mt-4 pt-3 border-t border-[#F1F5F9] flex items-center justify-between">
                  <span className="text-[11px] text-[#94A3B8] font-mono">
                    National Library of Medicine
                  </span>
                  <a
                    href={cite.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-[#0D9488] hover:text-[#0F766E] font-semibold text-xs transition-colors"
                  >
                    Read on PubMed <ExternalLink className="w-3.5 h-3.5" />
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
