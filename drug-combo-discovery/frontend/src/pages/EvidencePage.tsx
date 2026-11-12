import React, { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useApp } from "../services/AppContext";
import type { LiteratureCitation } from "../types/api";
import {
  Search,
  ExternalLink,
  ArrowRight,
  FileText,
} from "lucide-react";

interface AugmentedCitation extends LiteratureCitation {
  combination: string;
  cellLine: string;
}

export const LiteraturePage: React.FC = () => {
  const { currentPrediction, recentPredictions } = useApp();
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCitation, setSelectedCitation] = useState<AugmentedCitation | null>(null);

  const allCitations = useMemo(() => {
    const list: AugmentedCitation[] = [];
    const seen = new Set<string>();

    const push = (c: LiteratureCitation, combo: string, cell: string) => {
      const key = `${c.pmid}_${combo}`;
      if (seen.has(key)) return;
      seen.add(key);
      list.push({ ...c, combination: combo, cellLine: cell });
    };

    const collect = (p: typeof currentPrediction) => {
      if (!p) return;
      const combo = `${p.drug_a_name} + ${p.drug_b_name}`;
      p.supporting_literature?.forEach((c) => push(c, combo, p.cell_line));
      p.literature?.citations?.forEach((c) => push(c, combo, p.cell_line));
    };

    collect(currentPrediction);
    recentPredictions.forEach((p) => collect(p));
    return list;
  }, [currentPrediction, recentPredictions]);

  const filteredCitations = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return allCitations;
    return allCitations.filter(
      (c) =>
        c.pmid?.toLowerCase().includes(q) ||
        c.title?.toLowerCase().includes(q) ||
        c.journal?.toLowerCase().includes(q) ||
        c.combination.toLowerCase().includes(q) ||
        c.snippet?.toLowerCase().includes(q) ||
        c.match_reason?.toLowerCase().includes(q),
    );
  }, [allCitations, searchQuery]);

  return (
    <div className="space-y-10">
      {/* ── Page Header ── */}
      <div className="border-b border-[#20343C] pb-6">
        <div className="flex items-center gap-2 mb-2">
          <span className="section-label">03 · Scientific Evidence</span>
          <span className="text-[#20343C]">•</span>
          <span className="font-mono text-[11px] text-[#94A5A6]">
            NCBI PubMed Grounded Verification
          </span>
        </div>
        <h1 className="editorial-title text-[#F1F5F2]">
          Biomedical Literature & Evidence
        </h1>
        <p className="editorial-sub max-w-2xl mt-2">
          Explore peer-reviewed publications validating discovered drug pairs, target engagement,
          and clinical synthetic lethality. All citations cite verified PubMed IDs (PMIDs).
        </p>
      </div>

      {/* ── Search & Filters Bar ── */}
      <div className="st-panel p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex-1 relative">
          <label className="text-[11px] font-mono uppercase text-[#94A5A6] block mb-1">
            Search Indexed PubMed Publications
          </label>
          <div className="relative">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by compound, target gene, PMID, journal name, or indication..."
              className="st-input pl-9"
            />
            <Search size={16} className="absolute left-3 top-3 text-[#60747A] pointer-events-none" />
          </div>
        </div>

        <div className="sm:self-end pb-1 font-mono text-[12px] text-[#60747A] shrink-0">
          <span className="text-[#00D6A0] font-semibold">{filteredCitations.length}</span>{" "}
          {filteredCitations.length === 1 ? "citation matched" : "citations matched"}
        </div>
      </div>

      {/* ── Literature Results ── */}
      {filteredCitations.length === 0 ? (
        <div className="st-panel p-12 text-center space-y-4 max-w-md mx-auto">
          <FileText size={36} className="mx-auto text-[#60747A]" />
          <h3 className="text-[18px] font-serif text-[#F1F5F2]">
            No Matched Literature Records
          </h3>
          <p className="text-[13px] text-[#94A5A6]">
            {allCitations.length === 0
              ? "Score a drug pair on the Bench to automatically retrieve and index verified PubMed publications."
              : "No citations match your active search terms. Try searching for broader terms like 'chemotherapy' or 'apoptosis'."}
          </p>
          <Link to="/bench" className="st-btn-primary inline-flex">
            <span>Return to Bench</span>
            <ArrowRight size={14} />
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Citation Cards List */}
          <div className={`${selectedCitation ? "lg:col-span-7" : "lg:col-span-12"} space-y-4`}>
            {filteredCitations.map((cite, idx) => {
              const isSelected =
                selectedCitation?.pmid === cite.pmid &&
                selectedCitation?.combination === cite.combination;

              return (
                <article
                  key={`${cite.pmid}_${idx}`}
                  onClick={() => setSelectedCitation(cite)}
                  className={`st-panel p-6 hover:border-[#00D6A0]/60 transition-all cursor-pointer space-y-3 ${
                    isSelected ? "border-[#00D6A0] bg-[#14242B]/80 shadow-[0_0_16px_rgba(0,214,160,0.1)]" : ""
                  }`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2 font-mono text-[11px] text-[#60747A]">
                        <span className="text-[#00D6A0] font-semibold">PMID: {cite.pmid}</span>
                        <span>•</span>
                        <span>{cite.journal || "PubMed Central"}</span>
                        {cite.year && (
                          <>
                            <span>•</span>
                            <span>{cite.year}</span>
                          </>
                        )}
                      </div>
                      <h4 className="font-serif text-[17px] text-[#F1F5F2] font-semibold leading-snug">
                        {cite.title}
                      </h4>
                    </div>

                    <a
                      href={cite.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      className="p-1.5 rounded hover:bg-[#20343C] text-[#00D6A0] shrink-0"
                      title="Open on NCBI PubMed"
                    >
                      <ExternalLink size={16} />
                    </a>
                  </div>

                  {cite.snippet && (
                    <p className="text-[13px] text-[#94A5A6] italic border-l-2 border-[#20343C] pl-3 leading-relaxed">
                      "{cite.snippet}"
                    </p>
                  )}

                  <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-[#20343C]/40 text-[11px] font-mono">
                    <span className="px-2.5 py-0.5 rounded bg-[#091218] border border-[#20343C] text-[#94A5A6]">
                      Combination: {cite.combination}
                    </span>

                    {cite.match_reason && (
                      <span className="text-[#35C9D5]">
                        Evidence: {cite.match_reason}
                      </span>
                    )}
                  </div>
                </article>
              );
            })}
          </div>

          {/* Contextual Evidence Inspector Drawer */}
          {selectedCitation && (
            <div className="lg:col-span-5 st-panel p-6 sticky top-24 space-y-5 border-l-2 border-l-[#00D6A0]">
              <div className="flex items-start justify-between border-b border-[#20343C] pb-3">
                <div>
                  <span className="section-label">Evidence Inspector</span>
                  <h4 className="font-serif text-[18px] text-[#F1F5F2] mt-1 font-bold">
                    PMID {selectedCitation.pmid}
                  </h4>
                </div>
                <button
                  type="button"
                  onClick={() => setSelectedCitation(null)}
                  className="text-[#60747A] hover:text-[#F1F5F2] text-xs font-mono cursor-pointer"
                >
                  Close
                </button>
              </div>

              <div className="space-y-4 text-[13px]">
                <div>
                  <label className="text-[10.5px] font-mono uppercase text-[#60747A] block mb-1">
                    Publication Title
                  </label>
                  <p className="font-serif text-[16px] text-[#F1F5F2] font-semibold leading-snug">
                    {selectedCitation.title}
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-3 text-xs font-mono">
                  <div className="p-2.5 rounded bg-[#091218] border border-[#20343C]">
                    <span className="text-[10px] text-[#60747A] uppercase block">Journal</span>
                    <span className="text-[#F1F5F2] font-medium truncate block mt-0.5">
                      {selectedCitation.journal || "NCBI PubMed"}
                    </span>
                  </div>
                  <div className="p-2.5 rounded bg-[#091218] border border-[#20343C]">
                    <span className="text-[10px] text-[#60747A] uppercase block">Year</span>
                    <span className="text-[#F1F5F2] font-medium block mt-0.5">
                      {selectedCitation.year || "Catalog Record"}
                    </span>
                  </div>
                </div>

                {selectedCitation.snippet && (
                  <div>
                    <label className="text-[10.5px] font-mono uppercase text-[#60747A] block mb-1">
                      Abstract Excerpt
                    </label>
                    <div className="p-3.5 rounded-lg bg-[#091218] border border-[#20343C] text-[12.5px] text-[#94A5A6] leading-relaxed">
                      "{selectedCitation.snippet}"
                    </div>
                  </div>
                )}

                {selectedCitation.match_reason && (
                  <div>
                    <label className="text-[10.5px] font-mono uppercase text-[#60747A] block mb-1">
                      Target Relevance
                    </label>
                    <p className="text-[12.5px] text-[#F1F5F2]">
                      {selectedCitation.match_reason}
                    </p>
                  </div>
                )}

                <div className="pt-3 border-t border-[#20343C] space-y-2">
                  <a
                    href={selectedCitation.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="st-btn-primary w-full text-[13px]"
                  >
                    <span>Read on NCBI PubMed</span>
                    <ExternalLink size={14} />
                  </a>

                  <Link
                    to="/bench"
                    className="st-btn-ghost w-full text-[13px]"
                  >
                    Return to Benchmark Analysis
                  </Link>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
