import React from "react";
import { BookOpen, ExternalLink, FileText } from "lucide-react";
import { useApp } from "../services/AppContext";
import { useNavigate } from "react-router-dom";
import type { LiteratureCitation } from "../types/api";

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
    <div className="space-y-4">
      {/* Header */}
      <div className="border-b border-[#E5E2DC] pb-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-[#9A712F]" />
            <h2 className="text-2xl font-semibold text-[#1C2421]">
              Scientific Evidence & Literature Catalog
            </h2>
          </div>
          <p className="text-xs text-[#7A827C] mt-0.5">
            Retrieved PubMed citations cross-referencing model-predicted drug
            synergy mechanisms with published biological experimental literature
          </p>
        </div>

        {/* Provenance Badge */}
        <div className="flex items-center gap-2 text-xs font-mono">
          <span className="bg-[#F5EFE4] text-[#7A5A28] border border-[#E5D4A8] px-2.5 py-1 rounded font-semibold">
            NCBI E-Utilities Verified
          </span>
        </div>
      </div>

      {/* Trust & Provenance Card */}
      <div className="syn-card rounded-lg p-4">
        <h3 className="text-sm font-semibold text-[#1C2421] uppercase tracking-wide mb-1.5">
          Dual Validation Methodology
        </h3>
        <p className="text-xs text-[#5A635E] leading-normal mb-3">
          Synthera establishes clinical confidence by triangulating
          computational graph attribution against peer-reviewed experimental
          publications:
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div className="p-3 bg-[#E8F0ED] border border-[#B5CFC6] rounded">
            <span className="font-semibold text-[#25564B] block mb-1">
              1. In-Silico Mechanistic Attribution
            </span>
            <p className="text-[#3D4742] leading-normal">
              Gradient backpropagation isolates specific molecular paths (e.g.
              drug-target bindings, pathway cascades) explaining why the model
              predicted synergy over additive outcomes.
            </p>
          </div>
          <div className="p-3 bg-[#F5EFE4] border border-[#E5D4A8] rounded">
            <span className="font-semibold text-[#7A5A28] block mb-1">
              2. Independent PubMed Triangulation
            </span>
            <p className="text-[#3D4742] leading-normal">
              NCBI ESearch and ESummary dynamically query the biomedical
              literature for the identified targets and indications, confirming
              whether the computational axis has experimental precedent.
            </p>
          </div>
        </div>
      </div>

      {/* Evidence Table / Cards */}
      {allCitations.length === 0 ? (
        <div className="syn-card rounded-lg p-12 text-center">
          <FileText className="w-10 h-10 text-[#8A918C] mx-auto mb-3" />
          <h3 className="text-lg font-semibold text-[#1C2421] mb-1">
            No supporting literature was retrieved for this relationship.
          </h3>
          <p className="text-xs text-[#6B746F] max-w-md mx-auto mb-5 leading-normal">
            Run a prediction in the query instrument to retrieve verified
            citations for candidate combinations from NCBI PubMed.
          </p>
          <button
            type="button"
            onClick={() => navigate("/discover")}
            className="px-4 py-2 bg-[#2F6B5E] hover:bg-[#25564B] text-[#FFFEFB] rounded text-xs font-semibold inline-flex items-center gap-2 transition-colors cursor-pointer"
          >
            Launch Query Instrument
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-semibold text-[#1C2421]">
              Retrieved Citations ({allCitations.length})
            </h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {allCitations.map((cite, idx) => (
              <div
                key={`${cite.pmid}_${idx}`}
                className="syn-card hover:border-[#B8B4AB] rounded-lg p-4 transition-all flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] font-mono text-[#9A712F] bg-[#F5EFE4] px-2 py-0.5 rounded font-bold">
                      PMID: {cite.pmid}
                    </span>
                    <span className="text-xs font-mono text-[#6B746F]">
                      {cite.year}
                    </span>
                  </div>

                  <h4 className="text-base font-semibold text-[#1C2421] mb-2 leading-snug">
                    {cite.title}
                  </h4>

                  <p className="text-xs text-[#6B746F] mb-2">
                    First Author:{" "}
                    <strong className="text-[#3D4742]">
                      {cite.first_author || "First Author et al."}
                    </strong>
                  </p>

                  <div className="inline-flex items-center gap-1.5 text-[11px] font-mono bg-[#F3F1EC] text-[#5A635E] border border-[#E5E2DC] px-2 py-1 rounded">
                    <span>Associated Combination:</span>
                    <strong className="text-[#1C2421]">
                      {cite.combination}
                    </strong>
                    <span>({cite.cellLine})</span>
                  </div>
                </div>

                <div className="mt-4 pt-3 border-t border-[#EEEBE5] flex items-center justify-between">
                  <span className="text-[11px] text-[#8A918C] font-mono">
                    National Library of Medicine
                  </span>
                  <a
                    href={cite.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-[#2F6B5E] hover:text-[#25564B] font-semibold text-xs transition-colors"
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
