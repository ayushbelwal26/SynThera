import React, { useState } from 'react';
import { HelpCircle, ArrowRight, AlertTriangle, CheckCircle2, XCircle, ExternalLink, Sparkles } from 'lucide-react';
import { askWhyNot } from '../../services/api';
import type { WhyNotResponse } from '../../types/api';
import { Badge } from '../common/Badge';

interface WhyNotSectionProps {
  disease: string;
  cellLine: string;
  searchMethod?: 'beam' | 'greedy' | 'mcts';
  onInspectPair: (drugAId: string, drugBId: string, cellLine: string) => void;
}

export const WhyNotSection: React.FC<WhyNotSectionProps> = ({
  disease,
  cellLine,
  searchMethod = 'beam',
  onInspectPair,
}) => {
  const [query, setQuery] = useState('Why not Temozolomide?');
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
      setErrorMsg(err.message || 'Diagnostic query failed. Please verify connection to the backend.');
      setResult(null);
    } finally {
      setIsLoading(false);
    }
  };

  const sampleQuestions = [
    'Why not Temozolomide?',
    'Why not Zinc chloride?',
    'Why not Cisplatin?',
  ];

  return (
    <div className="bg-[#FFFFFF] border border-[#E5E5E0] rounded-lg p-6 shadow-xs space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-[#E5E5E0] pb-3 gap-2">
        <div className="flex items-center gap-2">
          <HelpCircle className="w-4 h-4 text-[#0D9488]" />
          <h3 className="font-serif text-base font-bold text-[#0F172A]">
            Candidate Investigation: "Why Not Drug X?"
          </h3>
          <span className="text-[11px] font-mono text-[#0D9488] bg-[#F0FDFA] border border-[#99F6E4] px-2 py-0.5 rounded font-semibold">
            Tier 3: Grounded Agent
          </span>
        </div>
        <span className="text-xs text-[#64748B] font-mono">
          Context: {disease} &bull; {cellLine}
        </span>
      </div>

      <p className="text-xs text-[#475569] leading-relaxed">
        Ask why a named candidate drug was omitted from top hits, filtered by quality rules, or how it compares against the current #1 search hit. Evaluation uses the trained GNN pair-scorer without LLM hallucinations.
      </p>

      {/* Query Form */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleAsk();
        }}
        className="space-y-3"
      >
        <div className="flex gap-2">
          <input
            type="text"
            value={query}
            disabled={isLoading}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g. Why not Temozolomide? or Why not Zinc chloride?"
            className="flex-1 px-3.5 py-2.5 bg-[#FFFFFF] border border-[#CBD5E1] focus:border-[#0D9488] focus:ring-1 focus:ring-[#0D9488] rounded-md text-sm text-[#0F172A] outline-none font-medium"
          />
          <button
            type="submit"
            disabled={isLoading || !query.trim()}
            className="px-5 py-2.5 bg-[#0D9488] hover:bg-[#0F766E] disabled:bg-[#94A3B8] text-[#FFFFFF] font-semibold text-xs rounded-md shadow-xs transition-colors cursor-pointer shrink-0"
          >
            {isLoading ? 'Diagnosing...' : 'Ask Agent'}
          </button>
        </div>

        {/* Quick Suggestion Chips */}
        <div className="flex items-center gap-1.5 flex-wrap text-xs text-[#64748B]">
          <span className="text-[11px] font-medium text-[#475569]">Try asking:</span>
          {sampleQuestions.map((q) => (
            <button
              key={q}
              type="button"
              disabled={isLoading}
              onClick={() => {
                setQuery(q);
                handleAsk(q);
              }}
              className="text-[11px] bg-[#F1F5F9] hover:bg-[#E2E8F0] px-2 py-0.5 rounded text-[#334155] transition-colors cursor-pointer"
            >
              {q}
            </button>
          ))}
        </div>
      </form>

      {/* Error state */}
      {errorMsg && (
        <div className="p-3.5 bg-[#FEF2F2] border border-[#FECACA] rounded-md text-xs text-[#991B1B] flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-[#DC2626] shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Result Display (Single Latest Q&A) */}
      {result && (
        <div className="pt-2">
          {/* Case 1: Unsupported Question Warning */}
          {result.error === 'unsupported_question' && (
            <div className="p-4 bg-[#FFFBEB] border border-[#FDE68A] rounded-md text-xs text-[#92400E] space-y-1.5">
              <div className="flex items-center gap-2 font-semibold">
                <AlertTriangle className="w-4 h-4 text-[#D97706]" />
                <span>Unsupported Question</span>
              </div>
              <p className="leading-relaxed">
                {result.hint || 'Ask why not <drug> for the current disease and cell line.'}
              </p>
              <div className="text-[11px] text-[#B45309] opacity-90 pt-1">
                Supported formats: <code className="bg-[#FEF3C7] px-1 py-0.5 rounded">Why not &lt;drug&gt;?</code>, <code className="bg-[#FEF3C7] px-1 py-0.5 rounded">Compare &lt;drug A&gt; vs &lt;drug B&gt;</code>, or <code className="bg-[#FEF3C7] px-1 py-0.5 rounded">Why is &lt;drug A&gt; ranked below &lt;drug B&gt;?</code>
              </div>
            </div>
          )}

          {/* Case 2: Filtered Non-Therapeutic Candidate */}
          {result.status === 'filtered' && (
            <div className="p-4 bg-[#FFFBEB] border border-[#FDE68A] rounded-md space-y-2.5">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <div className="flex items-center gap-2">
                  <XCircle className="w-4 h-4 text-[#D97706]" />
                  <span className="font-semibold text-sm text-[#0F172A]">
                    {result.drug_x?.name} {result.drug_x?.id ? `(${result.drug_x.id})` : ''}
                  </span>
                </div>
                <span className="text-xs font-mono font-semibold px-2 py-0.5 bg-[#FEF3C7] border border-[#FDE68A] text-[#92400E] rounded">
                  Filtered: Non-Therapeutic
                </span>
              </div>
              <p className="text-xs text-[#78350F] leading-relaxed">
                {result.explanation_text}
              </p>
            </div>
          )}

          {/* Case 3: Unknown Drug / Not in Graph */}
          {result.status === 'unknown_drug' && (
            <div className="p-4 bg-[#F8FAFC] border border-[#E2E8F0] rounded-md space-y-2">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <span className="font-semibold text-sm text-[#0F172A]">
                  Drug: {result.drug_x?.name || 'Unknown'}
                </span>
                <span className="text-xs font-mono font-semibold px-2 py-0.5 bg-[#F1F5F9] border border-[#CBD5E1] text-[#475569] rounded">
                  Not in Knowledge Graph
                </span>
              </div>
              <p className="text-xs text-[#475569] leading-relaxed">
                {result.explanation_text}
              </p>
            </div>
          )}

          {/* Case 4: Scored Diagnostic Result */}
          {result.status === 'scored' && (
            <div className="bg-[#F8FAFC] border border-[#E2E8F0] rounded-md p-4 space-y-4">
              <div className="flex items-center justify-between flex-wrap gap-2 border-b border-[#E2E8F0] pb-2.5">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-[#0D9488]" />
                  <span className="font-semibold text-sm text-[#0F172A]">
                    Diagnostic Assessment for {result.drug_x?.name} {result.drug_x?.id ? `(${result.drug_x.id})` : ''}
                  </span>
                </div>
                <Badge
                  variant={result.verdict === 'competitive' ? 'synergy' : 'additive'}
                  size="sm"
                >
                  {result.verdict === 'competitive' ? 'Competitive Candidate' : 'Lower Predicted Synergy'}
                </Badge>
              </div>

              <p className="text-xs text-[#334155] leading-relaxed bg-[#FFFFFF] p-3 rounded border border-[#E2E8F0]">
                {result.explanation_text}
              </p>

              {/* Pair comparison metrics */}
              {result.best_pair && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 font-mono text-xs">
                  <div className="bg-[#FFFFFF] border border-[#E2E8F0] p-3 rounded space-y-1">
                    <span className="text-[10px] text-[#64748B] uppercase block">
                      Best Evaluated Pairing in Pool
                    </span>
                    <div className="font-semibold text-[#0F172A] text-sm">
                      {result.best_pair.drug_a_name} × {result.best_pair.drug_b_name}
                    </div>
                    <div className="flex items-center gap-2 pt-1">
                      <span className="text-xs font-bold text-[#0D9488]">
                        p_syn: {result.best_pair.p_synergy.toFixed(4)}
                      </span>
                      <Badge variant="synergy" size="sm">
                        {result.best_pair.predicted_class}
                      </Badge>
                    </div>
                  </div>

                  {result.reference_top && (
                    <div className="bg-[#FFFFFF] border border-[#E2E8F0] p-3 rounded space-y-1">
                      <span className="text-[10px] text-[#64748B] uppercase block">
                        Search #1 Baseline Reference
                      </span>
                      <div className="font-semibold text-[#0F172A] text-sm">
                        {result.reference_top.drug_a_name} × {result.reference_top.drug_b_name}
                      </div>
                      <div className="flex items-center gap-2 pt-1">
                        <span className="text-xs font-bold text-[#059669]">
                          p_syn: {result.reference_top.p_synergy.toFixed(4)}
                        </span>
                        <span className="text-[11px] text-[#64748B]">
                          (Δ: {(result.best_pair.p_synergy - result.reference_top.p_synergy).toFixed(4)})
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Single Literature Citation Grounding */}
              {result.literature?.citations && result.literature.citations.length > 0 && (
                <div className="bg-[#FFFFFF] border border-[#E2E8F0] p-3 rounded space-y-1.5 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-[#0F172A] flex items-center gap-1.5">
                      <CheckCircle2 className="w-3.5 h-3.5 text-[#0D9488]" />
                      PubMed Literature Grounding (1 Retrieved Study)
                    </span>
                    <a
                      href={result.literature.citations[0].url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[#0D9488] hover:underline flex items-center gap-1 font-mono text-[11px]"
                    >
                      PMID {result.literature.citations[0].pmid} <ExternalLink className="w-3 h-3" />
                    </a>
                  </div>
                  <div className="font-medium text-[#1E293B]">
                    "{result.literature.citations[0].title}" ({result.literature.citations[0].year}) &bull; {result.literature.citations[0].first_author} et al.
                  </div>
                  {result.literature.citations[0].snippet && (
                    <p className="text-[11px] text-[#64748B] italic leading-relaxed">
                      "{result.literature.citations[0].snippet}"
                    </p>
                  )}
                  <span className="inline-block text-[10px] font-mono text-[#0F766E] bg-[#F0FDFA] px-1.5 py-0.5 rounded border border-[#CCFBF1]">
                    {result.literature.citations[0].match_reason}
                  </span>
                </div>
              )}

              {/* Action: Inspect this pair */}
              {result.best_pair && (
                <div className="flex justify-end pt-1">
                  <button
                    type="button"
                    onClick={() =>
                      onInspectPair(
                        result.best_pair!.drug_a,
                        result.best_pair!.drug_b,
                        result.best_pair!.cell_line
                      )
                    }
                    className="px-4 py-2 bg-[#0D9488] hover:bg-[#0F766E] text-[#FFFFFF] rounded text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer shadow-xs"
                  >
                    <span>Inspect {result.best_pair.drug_a_name} × {result.best_pair.drug_b_name} (Faithfulness + Pathway)</span>
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
