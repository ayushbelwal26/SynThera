import React from "react";
import {
  BookOpen,
  ExternalLink,
  FileText,
  Search,
  Sparkles,
} from "lucide-react";
import type { LiteratureCitation, LiteratureResult } from "../../types/api";

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
  const activeCitations =
    literature?.citations && literature.citations.length > 0
      ? literature.citations
      : citations && citations.length > 0
        ? citations
        : [];

  const hasCitations = activeCitations.length > 0;
  const queryUsed = literature?.query_used;

  return (
    <div className="syn-card rounded-lg p-4 mb-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
        <div>
          <div className="flex items-center gap-2">
            <BookOpen className="w-4 h-4 text-[#9A712F]" />
            <h3 className="text-lg font-semibold text-[#1C2421]">
              Supporting Literature & External Evidence (NCBI PubMed RAG)
            </h3>
          </div>
          <p className="text-xs text-[#7A827C] mt-0.5">
            Retrieve-then-cite biomedical RAG via NCBI E-Utilities with real
            abstract extraction
          </p>
        </div>

        {/* Clear Trust Distinction Callout */}
        <div className="flex items-center gap-2 text-[10px] font-mono">
          <span className="bg-[#F5EFE4] text-[#7A5A28] border border-[#E5D4A8] px-2 py-0.5 rounded font-semibold">
            EXTERNAL VALIDATION (NCBI PUBMED)
          </span>
          <span className="text-[#8A918C]">&ne;</span>
          <span className="bg-[#E8F0ED] text-[#25564B] border border-[#B5CFC6] px-2 py-0.5 rounded font-semibold">
            MODEL REASONING (GRAPH GNN)
          </span>
        </div>
      </div>

      {/* Trust Notice */}
      <div className="bg-[#F7F0E4] border border-[#E5D4A8] rounded p-3 mb-4 text-xs text-[#7A5A28] leading-normal">
        <strong>Scientific Provenance: </strong>
        Attribution pathways are generated computationally by backpropagating
        gradients through the Graph Neural Network. Supporting citations below
        are independently retrieved and verified from the National Library of
        Medicine (PubMed) to confirm whether this combination or molecular axis
        has precedent in the peer-reviewed biological literature.
      </div>

      {!hasCitations ? (
        <div className="p-6 text-center bg-[#F3F1EC] border border-[#E5E2DC] rounded-md space-y-3">
          <FileText className="w-7 h-7 text-[#8A918C] mx-auto" />
          <div>
            <h4 className="text-sm font-semibold text-[#3D4742]">
              No matching PubMed hits for this mechanism query
            </h4>
            <p className="text-xs text-[#6B746F] mt-1 max-w-xl mx-auto leading-normal">
              {literature?.no_literature_reason ||
                "No published preclinical or clinical records directly coupling this specific molecular axis were retrieved from NCBI PubMed. This may indicate a novel synergistic candidate discovered computationally by the graph neural network."}
            </p>
          </div>

          {queryUsed && (
            <div className="pt-2 border-t border-[#E5E2DC] max-w-xl mx-auto">
              <span className="text-[11px] font-mono text-[#6B746F] flex items-center justify-center gap-1.5 flex-wrap">
                <Search className="w-3 h-3 text-[#8A918C]" />
                Query executed:
                <code className="bg-[#FFFEFB] border border-[#D8D5CE] text-[#1C2421] px-2 py-0.5 rounded text-[11px] max-w-full truncate font-mono">
                  {queryUsed}
                </code>
              </span>
            </div>
          )}
        </div>
      ) : (
        <div className="space-y-4">
          {queryUsed && (
            <div className="flex items-center gap-2 text-xs text-[#6B746F] font-mono bg-[#F3F1EC] border border-[#E5E2DC] px-3 py-1.5 rounded">
              <Search className="w-3.5 h-3.5 text-[#2F6B5E]" />
              <span className="font-semibold text-[#3D4742]">
                PubMed RAG Query:
              </span>
              <span className="truncate text-[#1C2421]">{queryUsed}</span>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {activeCitations.map((cite, idx) => (
              <div
                key={cite.pmid || idx}
                className="p-4 bg-[#FDFCFB] border border-[#E8E6DF] hover:border-[#D8D5CE] rounded-md transition-all flex flex-col justify-between shadow-2xs"
              >
                <div>
                  <div className="flex items-center justify-between gap-2 mb-2">
                    <span className="text-[10px] font-mono text-[#9A712F] bg-[#F5EFE4] border border-[#E5D4A8] px-1.5 py-0.5 rounded font-semibold">
                      PMID: {cite.pmid}
                    </span>
                    <span className="text-[11px] font-mono text-[#6B746F] font-medium">
                      {cite.year} {cite.journal ? `• ${cite.journal}` : ""}
                    </span>
                  </div>

                  <h4 className="text-sm font-semibold text-[#1C2421] mb-2 line-clamp-2 leading-snug">
                    {cite.title}
                  </h4>

                  {cite.first_author && (
                    <p className="text-[11px] text-[#6B746F] mb-2 font-mono">
                      Author:{" "}
                      <span className="text-[#3D4742] font-medium">
                        {cite.first_author} et al.
                      </span>
                    </p>
                  )}

                  <div className="flex flex-col gap-1.5 mb-2.5">
                    {/* Evidence Type Badge */}
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <span
                        className={`inline-flex items-center gap-1 text-[9px] font-mono font-bold uppercase tracking-wide px-2 py-0.5 rounded border ${
                          cite.evidence_type === "combination"
                            ? "bg-[#E8F0ED] text-[#1F4A40] border-[#B5CFC6]"
                            : cite.evidence_type === "single_drug"
                              ? "bg-[#EFF6FF] text-[#1E40AF] border-[#BFDBFE]"
                              : "bg-[#F7F0E4] text-[#7A5A28] border-[#E5D4A8]"
                        }`}
                      >
                        {cite.evidence_type === "combination" ? (
                          <>
                            <Sparkles className="w-2.5 h-2.5 text-[#3D7A6C]" />
                            Combination Evidence
                          </>
                        ) : cite.evidence_type === "single_drug" ? (
                          <>
                            <FileText className="w-2.5 h-2.5 text-[#2F6B5E]" />
                            Single-Drug Support
                          </>
                        ) : (
                          <>
                            <BookOpen className="w-2.5 h-2.5 text-[#B8893D]" />
                            Related Context
                          </>
                        )}
                      </span>
                    </div>

                    {/* Detailed Match Reason */}
                    {cite.match_reason && (
                      <p className="text-[11px] font-mono text-[#5A635E] leading-snug">
                        {cite.match_reason}
                      </p>
                    )}
                  </div>

                  {cite.snippet && (
                    <div className="bg-[#F3F1EC] border border-[#E5E2DC] rounded p-2.5 mb-3 text-xs text-[#3D4742] leading-normal italic">
                      &ldquo;{cite.snippet}&rdquo;
                    </div>
                  )}
                </div>

                <div className="pt-2.5 border-t border-[#F4F2EB] flex items-center justify-between text-xs mt-auto">
                  <span className="text-[10px] text-[#8A918C] font-mono">
                    MEDLINE Verified
                  </span>
                  <a
                    href={cite.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-[#2F6B5E] hover:text-[#25564B] font-semibold text-xs transition-colors"
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
