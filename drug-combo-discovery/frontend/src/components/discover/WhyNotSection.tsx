import React, { useState } from "react";
import {
  ArrowRight,
  AlertTriangle,
  ExternalLink,
  HelpCircle,
} from "lucide-react";
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
        err.message || "Diagnostic query failed. Check the backend connection.",
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
    <div
      id="why-not-section"
      className="border-t border-[var(--color-rule)] pt-6 space-y-4"
    >
      <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-1">
        <div className="flex items-center gap-2">
          <HelpCircle className="w-4 h-4 text-[var(--color-accent)]" />
          <h3 className="section-title">
            Diagnostic Counterfactual (Why Not Drug X?)
          </h3>
        </div>
        <span className="id-text font-mono text-[11.5px] px-2 py-0.5 rounded bg-[var(--color-panel)] border border-[var(--color-rule)]">
          {disease} · {cellLine}
        </span>
      </div>

      <p className="page-lede max-w-2xl !mt-0">
        Inquire why a named candidate was omitted from top synergy hits,
        filtered, or how its top predicted combination compares with the current
        #1 candidate pair.
      </p>

      <div className="bench-panel space-y-3">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleAsk();
          }}
          className="space-y-3"
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
              {isLoading ? "Diagnosing…" : "Ask Diagnostic"}
            </button>
          </div>

          <div className="flex items-baseline gap-x-3 gap-y-1.5 flex-wrap pt-1">
            <span className="bench-label">Suggestions</span>
            {sampleQuestions.map((q) => (
              <button
                key={q}
                type="button"
                disabled={isLoading}
                onClick={() => {
                  setQuery(q);
                  handleAsk(q);
                }}
                className="text-[12px] font-mono text-[var(--color-accent)] underline underline-offset-2 decoration-[var(--color-rule)] hover:decoration-[var(--color-accent)] cursor-pointer disabled:opacity-50"
              >
                {q}
              </button>
            ))}
          </div>
        </form>
      </div>

      {errorMsg && (
        <div className="py-2.5 px-3 rounded-md bg-[var(--color-antagonism)]/10 border border-[var(--color-antagonism)]/30 text-[13px] text-[var(--color-antagonism)] flex items-start gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
          <span>{errorMsg}</span>
        </div>
      )}

      {result && (
        <div className="border border-[var(--color-rule)] rounded-lg p-4 bg-[var(--color-surface)] space-y-3">
          {result.error === "unsupported_question" && (
            <div className="space-y-1.5 text-[13px] text-[var(--color-text-secondary)]">
              <p className="font-semibold text-[var(--color-text-primary)]">
                Unsupported question format
              </p>
              <p>
                {result.hint ||
                  "Ask why not <drug> for the current disease and cell line."}
              </p>
              <p className="meta-text">
                Supported formats: Why not &lt;drug&gt;? · Compare &lt;A&gt; vs
                &lt;B&gt; · Why is &lt;A&gt; ranked below &lt;B&gt;?
              </p>
            </div>
          )}

          {result.status === "filtered" && (
            <div className="space-y-1.5">
              <div className="flex items-baseline justify-between gap-2 flex-wrap">
                <span className="font-serif text-[15px] font-semibold text-[var(--color-text-primary)]">
                  {result.drug_x?.name}
                  {result.drug_x?.id ? (
                    <span className="id-text ml-2 text-[var(--color-accent)]">
                      {result.drug_x.id}
                    </span>
                  ) : null}
                </span>
                <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-[var(--color-antagonism)]/10 text-[var(--color-antagonism)] border border-[var(--color-antagonism)]/30 font-medium">
                  Filtered · Non-therapeutic
                </span>
              </div>
              <p className="text-[13.5px] text-[var(--color-text-secondary)] leading-relaxed">
                {result.explanation_text}
              </p>
            </div>
          )}

          {result.status === "unknown_drug" && (
            <div className="space-y-1.5">
              <div className="flex items-baseline justify-between gap-2 flex-wrap">
                <span className="font-serif text-[15px] font-semibold text-[var(--color-text-primary)]">
                  {result.drug_x?.name || "Unknown"}
                </span>
                <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-[var(--color-additive)]/10 text-[var(--color-additive)] border border-[var(--color-additive)]/30 font-medium">
                  Not in PrimeKG subgraph
                </span>
              </div>
              <p className="text-[13.5px] text-[var(--color-text-secondary)] leading-relaxed">
                {result.explanation_text}
              </p>
            </div>
          )}

          {result.status === "scored" && (
            <div className="space-y-4">
              <div className="flex items-baseline justify-between gap-2 flex-wrap border-b border-[var(--color-rule)] pb-2.5">
                <span className="font-serif text-[16px] font-semibold text-[var(--color-text-primary)]">
                  {result.drug_x?.name}
                  {result.drug_x?.id ? (
                    <span className="id-text ml-2 text-[var(--color-accent)]">
                      {result.drug_x.id}
                    </span>
                  ) : null}
                </span>
                <span
                  className={`font-mono text-[11px] font-semibold uppercase px-2.5 py-0.5 rounded-full border ${
                    result.verdict === "competitive"
                      ? "bg-[var(--color-accent-soft)] text-[var(--color-accent)] border-[var(--color-accent)]"
                      : "bg-[var(--color-additive)]/10 text-[var(--color-additive)] border-[var(--color-additive)]/40"
                  }`}
                >
                  {result.verdict === "competitive"
                    ? "Competitive Candidate"
                    : "Lower Predicted Synergy"}
                </span>
              </div>

              <p className="text-[13.5px] text-[var(--color-text-secondary)] leading-relaxed">
                {result.explanation_text}
              </p>

              {result.best_pair && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 p-3 rounded-md bg-[var(--color-panel)] border border-[var(--color-rule)]">
                  <div className="space-y-1">
                    <span className="bench-label block">
                      Best Pairing in Candidate Pool
                    </span>
                    <div className="font-serif text-[15px] font-semibold text-[var(--color-text-primary)]">
                      {result.best_pair.drug_a_name}{" "}
                      <span className="text-[var(--color-accent)]">×</span>{" "}
                      {result.best_pair.drug_b_name}
                    </div>
                    <div className="flex items-baseline gap-2">
                      <span className="metric-value text-[15px] text-[var(--color-accent)]">
                        {result.best_pair.p_synergy.toFixed(4)}
                      </span>
                      <span className="meta-text">
                        p_syn · {result.best_pair.predicted_class}
                      </span>
                    </div>
                  </div>

                  {result.reference_top && (
                    <div className="space-y-1 sm:border-l sm:border-[var(--color-rule)] sm:pl-3">
                      <span className="bench-label block">
                        Search #1 Reference Hit
                      </span>
                      <div className="font-serif text-[15px] font-semibold text-[var(--color-text-primary)]">
                        {result.reference_top.drug_a_name}{" "}
                        <span className="text-[var(--color-accent)]">×</span>{" "}
                        {result.reference_top.drug_b_name}
                      </div>
                      <div className="flex items-baseline gap-2">
                        <span className="metric-value text-[15px]">
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
                  <div className="space-y-1.5 border-t border-[var(--color-rule)] pt-3">
                    <div className="flex items-baseline justify-between gap-2">
                      <span className="bench-label">PubMed Grounding</span>
                      <a
                        href={result.literature.citations[0].url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="id-text text-[var(--color-accent)] hover:underline inline-flex items-center gap-1"
                      >
                        PMID {result.literature.citations[0].pmid}
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                    <p className="font-serif text-[14px] font-medium text-[var(--color-text-primary)] leading-snug">
                      {result.literature.citations[0].title} (
                      {result.literature.citations[0].year}) ·{" "}
                      {result.literature.citations[0].first_author} et al.
                    </p>
                    {result.literature.citations[0].snippet && (
                      <p className="meta-text italic leading-relaxed text-[var(--color-text-secondary)]">
                        “{result.literature.citations[0].snippet}”
                      </p>
                    )}
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
                    <span>
                      Inspect {result.best_pair.drug_a_name} ×{" "}
                      {result.best_pair.drug_b_name}
                    </span>
                    <ArrowRight className="w-4 h-4" />
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
