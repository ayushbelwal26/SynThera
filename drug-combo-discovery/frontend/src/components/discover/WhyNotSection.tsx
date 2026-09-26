import React, { useState } from "react";
import { ArrowRight, AlertTriangle, ExternalLink } from "lucide-react";
import { askWhyNot } from "../../services/api";
import type { WhyNotResponse } from "../../types/api";

interface WhyNotSectionProps {
  disease: string;
  cellLine: string;
  searchMethod?: "beam" | "greedy" | "mcts";
  onInspectPair: (drugAId: string, drugBId: string, cellLine: string) => void;
}

export const WhyNotSection: React.FC<WhyNotSectionProps> = ({
  disease,
  cellLine,
  searchMethod = "beam",
  onInspectPair,
}) => {
  const [query, setQuery] = useState("Why not Temozolomide?");
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<WhyNotResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleAsk = async (questionToAsk?: string) => {
    const q = (questionToAsk || query).trim();
    if (!q || !disease || !cellLine) return;

    setIsLoading(true);
    setErrorMsg(null);
    try {
      const res = await askWhyNot({
        disease,
        cell_line: cellLine,
        question: q,
        search_method: searchMethod,
      });
      setResult(res);
    } catch (err: any) {
      setErrorMsg(
        err.message ||
          "Diagnostic query failed. Check the backend connection.",
      );
      setResult(null);
    } finally {
      setIsLoading(false);
    }
  };

  const sampleQuestions = [
    "Why not Temozolomide?",
    "Why not Zinc chloride?",
    "Why not Cisplatin?",
  ];

  return (
    <div id="why-not-section" className="border-t border-[#CFC9BC] pt-6 space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-1">
        <div>
          <p className="page-kicker">Diagnostic</p>
          <h3 className="section-title">Why not drug X?</h3>
        </div>
        <span className="id-text">
          {disease} · {cellLine}
        </span>
      </div>

      <p className="page-lede max-w-2xl !mt-0">
        Ask why a named candidate was omitted from top hits, filtered, or how it
        compares to the current #1 search hit. Uses the trained GNN pair-scorer.
      </p>

      <div className="bench-panel space-y-3">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleAsk();
          }}
          className="space-y-2"
        >
          <div className="flex gap-2 items-end">
            <input
              type="text"
              value={query}
              disabled={isLoading}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. Why not Temozolomide?"
              className="bench-input flex-1"
            />
            <button
              type="submit"
              disabled={isLoading || !query.trim()}
              className="bench-btn shrink-0"
            >
              {isLoading ? "Diagnosing…" : "Ask"}
            </button>
          </div>

          <div className="flex items-baseline gap-x-3 gap-y-1 flex-wrap">
            <span className="bench-label">Try</span>
            {sampleQuestions.map((q) => (
              <button
                key={q}
                type="button"
                disabled={isLoading}
                onClick={() => {
                  setQuery(q);
                  handleAsk(q);
                }}
                className="text-[12px] text-[#1A535C] underline underline-offset-2 decoration-[#CFC9BC] hover:decoration-[#1A535C] cursor-pointer disabled:opacity-50"
              >
                {q}
              </button>
            ))}
          </div>
        </form>
      </div>

      {errorMsg && (
        <div className="py-2 border-y border-[#E8C5C5] text-[13px] text-[#A84B4B] flex items-start gap-2">
          <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
          <span>{errorMsg}</span>
        </div>
      )}

      {result && (
        <div className="border-t border-[#CFC9BC] pt-3 space-y-3">
          {result.error === "unsupported_question" && (
            <div className="space-y-1.5 text-[13px] text-[#4A524C]">
              <p className="font-medium text-[#1A1F1C]">Unsupported question</p>
              <p>
                {result.hint ||
                  "Ask why not &lt;drug&gt; for the current disease and cell line."}
              </p>
              <p className="meta-text">
                Formats: Why not &lt;drug&gt;? · Compare &lt;A&gt; vs &lt;B&gt; ·
                Why is &lt;A&gt; ranked below &lt;B&gt;?
              </p>
            </div>
          )}

          {result.status === "filtered" && (
            <div className="space-y-1.5">
              <div className="flex items-baseline justify-between gap-2 flex-wrap">
                <span className="font-serif text-[15px] text-[#1A1F1C]">
                  {result.drug_x?.name}
                  {result.drug_x?.id ? (
                    <span className="id-text ml-2">{result.drug_x.id}</span>
                  ) : null}
                </span>
                <span className="meta-text">Filtered · non-therapeutic</span>
              </div>
              <p className="text-[13px] text-[#4A524C] leading-relaxed">
                {result.explanation_text}
              </p>
            </div>
          )}

          {result.status === "unknown_drug" && (
            <div className="space-y-1.5">
              <div className="flex items-baseline justify-between gap-2 flex-wrap">
                <span className="font-serif text-[15px] text-[#1A1F1C]">
                  {result.drug_x?.name || "Unknown"}
                </span>
                <span className="meta-text">Not in knowledge graph</span>
              </div>
              <p className="text-[13px] text-[#4A524C] leading-relaxed">
                {result.explanation_text}
              </p>
            </div>
          )}

          {result.status === "scored" && (
            <div className="space-y-4">
              <div className="flex items-baseline justify-between gap-2 flex-wrap border-b border-[#CFC9BC] pb-2">
                <span className="font-serif text-[15px] text-[#1A1F1C]">
                  {result.drug_x?.name}
                  {result.drug_x?.id ? (
                    <span className="id-text ml-2">{result.drug_x.id}</span>
                  ) : null}
                </span>
                <span
                  className={`text-[12px] font-medium capitalize ${
                    result.verdict === "competitive"
                      ? "text-[#1A535C]"
                      : "text-[#8B7355]"
                  }`}
                >
                  {result.verdict === "competitive"
                    ? "Competitive candidate"
                    : "Lower predicted synergy"}
                </span>
              </div>

              <p className="text-[13px] text-[#4A524C] leading-relaxed">
                {result.explanation_text}
              </p>

              {result.best_pair && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-0 divide-y sm:divide-y-0 sm:divide-x divide-[#CFC9BC] border-y border-[#CFC9BC]">
                  <div className="py-2.5 sm:pr-4 space-y-1">
                    <span className="bench-label block">
                      Best pairing in pool
                    </span>
                    <div className="font-serif text-[14px] text-[#1A1F1C]">
                      {result.best_pair.drug_a_name} ×{" "}
                      {result.best_pair.drug_b_name}
                    </div>
                    <div className="flex items-baseline gap-2">
                      <span className="metric-value text-[14px]">
                        {result.best_pair.p_synergy.toFixed(4)}
                      </span>
                      <span className="meta-text">
                        p_syn · {result.best_pair.predicted_class}
                      </span>
                    </div>
                  </div>

                  {result.reference_top && (
                    <div className="py-2.5 sm:pl-4 space-y-1">
                      <span className="bench-label block">
                        Search #1 reference
                      </span>
                      <div className="font-serif text-[14px] text-[#1A1F1C]">
                        {result.reference_top.drug_a_name} ×{" "}
                        {result.reference_top.drug_b_name}
                      </div>
                      <div className="flex items-baseline gap-2">
                        <span className="metric-value text-[14px]">
                          {result.reference_top.p_synergy.toFixed(4)}
                        </span>
                        <span className="meta-text">
                          p_syn · Δ{" "}
                          {(
                            result.best_pair.p_synergy -
                            result.reference_top.p_synergy
                          ).toFixed(4)}
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {result.literature?.citations &&
                result.literature.citations.length > 0 && (
                  <div className="space-y-1.5 border-t border-[#CFC9BC] pt-3">
                    <div className="flex items-baseline justify-between gap-2">
                      <span className="bench-label">PubMed grounding</span>
                      <a
                        href={result.literature.citations[0].url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="id-text text-[#1A535C] hover:underline inline-flex items-center gap-1"
                      >
                        PMID {result.literature.citations[0].pmid}
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                    <p className="font-serif text-[14px] text-[#1A1F1C] leading-snug">
                      {result.literature.citations[0].title} (
                      {result.literature.citations[0].year}) ·{" "}
                      {result.literature.citations[0].first_author} et al.
                    </p>
                    {result.literature.citations[0].snippet && (
                      <p className="meta-text italic leading-relaxed">
                        “{result.literature.citations[0].snippet}”
                      </p>
                    )}
                    <span className="meta-text">
                      {result.literature.citations[0].match_reason}
                    </span>
                  </div>
                )}

              {result.best_pair && (
                <div className="flex justify-end pt-1">
                  <button
                    type="button"
                    onClick={() =>
                      onInspectPair(
                        result.best_pair!.drug_a,
                        result.best_pair!.drug_b,
                        result.best_pair!.cell_line,
                      )
                    }
                    className="bench-btn"
                  >
                    Inspect {result.best_pair.drug_a_name} ×{" "}
                    {result.best_pair.drug_b_name}
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
