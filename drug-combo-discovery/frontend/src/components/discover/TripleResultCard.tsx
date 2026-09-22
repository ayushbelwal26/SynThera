import React, { useState } from 'react';
import {
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  ExternalLink,
  BookOpen,
  Layers,
} from 'lucide-react';
import type { TripleResult, RankingBlock } from '../../types/api';
import { ToxicityBadge } from '../common/ToxicityBadge';

interface TripleResultCardProps {
  triple: TripleResult;
  rank: number;
  diseaseContext?: string;
}

export const TripleResultCard: React.FC<TripleResultCardProps> = ({
  triple,
  rank,
  diseaseContext = '',
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [litNotice, setLitNotice] = useState<string | null>(null);

  // Constituent pair definitions
  const pairItems: {
    key: 'pair_ab' | 'pair_ac' | 'pair_bc';
    label: string;
    drug1: string;
    drug2: string;
    ranking: RankingBlock;
  }[] = [
    {
      key: 'pair_ab',
      label: 'Pair A × B',
      drug1: triple.drug_a_name,
      drug2: triple.drug_b_name,
      ranking: triple.pair_ab,
    },
    {
      key: 'pair_ac',
      label: 'Pair A × C',
      drug1: triple.drug_a_name,
      drug2: triple.drug_c_name,
      ranking: triple.pair_ac,
    },
    {
      key: 'pair_bc',
      label: 'Pair B × C',
      drug1: triple.drug_b_name,
      drug2: triple.drug_c_name,
      ranking: triple.pair_bc,
    },
  ];

  const bottleneckKey = triple.bottleneck_pair?.pair_key;
  const bottleneckD1 = triple.bottleneck_pair?.drug_1 || triple.drug_a_name;
  const bottleneckD2 = triple.bottleneck_pair?.drug_2 || triple.drug_b_name;

  const handleOpenPubMed = () => {
    const terms = [
      `"${triple.drug_a_name}"`,
      `"${triple.drug_b_name}"`,
      `"${triple.drug_c_name}"`,
    ];
    if (diseaseContext.trim()) {
      terms.push(`"${diseaseContext.trim()}"`);
    }
    const query = terms.join(' AND ');
    const url = `https://pubmed.ncbi.nlm.nih.gov/?term=${encodeURIComponent(query)}`;
    window.open(url, '_blank', 'noopener,noreferrer');
    setLitNotice('Targeted PubMed search query opened in a new tab.');
  };

  return (
    <div className="bg-[#FFFFFF] border border-[#E5E5E0] hover:border-[#CBD5E1] rounded-lg p-5 shadow-xs transition-all space-y-4">
      {/* Top Row: Rank, Drug Triad, Toxicity Badge, and Primary Score */}
      <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
        <div className="space-y-2 flex-1">
          {/* Header Line with Rank & 3 Drug Badges */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-mono text-xs text-[#94A3B8] font-bold">
              #{triple.rank ?? rank}
            </span>

            {/* Triad of drugs */}
            <div className="inline-flex items-center gap-1.5 flex-wrap">
              <span className="px-2 py-0.5 bg-[#F1F5F9] border border-[#CBD5E1] text-[#0F172A] rounded text-xs font-semibold">
                {triple.drug_a_name}
              </span>
              <span className="text-[#94A3B8] text-xs font-bold">+</span>
              <span className="px-2 py-0.5 bg-[#F1F5F9] border border-[#CBD5E1] text-[#0F172A] rounded text-xs font-semibold">
                {triple.drug_b_name}
              </span>
              <span className="text-[#94A3B8] text-xs font-bold">+</span>
              <span className="px-2 py-0.5 bg-[#F1F5F9] border border-[#CBD5E1] text-[#0F172A] rounded text-xs font-semibold">
                {triple.drug_c_name}
              </span>
            </div>

            {/* Overall Triple Toxicity Badge */}
            <ToxicityBadge
              hasKnownDdi={triple.has_known_ddi}
              toxicityPenalty={triple.triple_toxicity_penalty}
              size="sm"
              showDetails={true}
            />
          </div>

          {/* Mandatory Universal Disclaimer */}
          <p className="text-[11px] font-mono text-[#64748B] italic flex items-center gap-1.5">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-[#0D9488]" />
            {triple.composition_caption ||
              'We compose pair scores; we do not have DrugComb 3-way synergy labels.'}
          </p>
        </div>

        {/* Primary and Secondary Score Badges */}
        <div className="flex items-center gap-4 shrink-0 font-mono text-xs">
          <div className="text-right">
            <span className="text-[10px] text-[#64748B] uppercase block font-sans tracking-wider font-semibold">
              Weakest-Pair Score
            </span>
            <span className="font-bold text-base text-[#0D9488]">
              {triple.aggregate_min.toFixed(4)}
            </span>
            <div className="text-[11px] text-[#64748B] flex items-center justify-end gap-2 mt-0.5 font-mono">
              <span title="Mean pairwise V-score across all 3 constituent pairs">
                mean V: <strong className="text-[#334155]">{triple.aggregate_mean.toFixed(4)}</strong>
              </span>
              <span>&bull;</span>
              <span title={`Max constituent pair toxicity penalty: ${triple.triple_toxicity_penalty.toFixed(4)}`}>
                tox: <strong className={triple.triple_toxicity_penalty > 0.4 ? 'text-[#DC2626]' : 'text-[#D97706]'}>{triple.triple_toxicity_penalty.toFixed(3)}</strong>
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Prominent Bottleneck Pair Callout (High Visual Weight) */}
      <div
        className={`p-3 rounded-md border text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
          triple.has_known_ddi
            ? 'bg-[#FEF2F2] border-[#FECACA] text-[#991B1B]'
            : 'bg-[#FFFBEB] border-[#FDE68A] text-[#92400E]'
        }`}
      >
        <div className="flex items-start sm:items-center gap-2">
          <AlertTriangle
            className={`w-4 h-4 shrink-0 ${
              triple.has_known_ddi ? 'text-[#DC2626]' : 'text-[#D97706]'
            }`}
          />
          <div>
            <span className="font-semibold uppercase tracking-wider text-[11px]">
              Weak-Link Bottleneck Pair:
            </span>{' '}
            <strong className="font-semibold font-mono text-xs">
              {bottleneckD1} × {bottleneckD2}
            </strong>{' '}
            <span className="opacity-90">
              defines the composite limiting score for this triad.
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3 shrink-0 font-mono text-[11px]">
          <span className="bg-[#FFFFFF]/80 px-2 py-0.5 rounded border border-current/20">
            pair V: <strong>{triple.bottleneck_pair?.v_score?.toFixed(4) ?? triple.aggregate_min.toFixed(4)}</strong>
          </span>
          <span className="bg-[#FFFFFF]/80 px-2 py-0.5 rounded border border-current/20">
            p(syn): <strong>{triple.bottleneck_pair?.p_synergy?.toFixed(4) ?? '—'}</strong>
          </span>
          {triple.bottleneck_pair?.toxicity_penalty !== undefined && (
            <span className="bg-[#FFFFFF]/80 px-2 py-0.5 rounded border border-current/20">
              tox: <strong>{triple.bottleneck_pair.toxicity_penalty.toFixed(3)}</strong>
            </span>
          )}
        </div>
      </div>

      {/* Literature Check Row */}
      <div className="flex items-center justify-between gap-3 pt-1 text-xs border-t border-[#F1F5F9]">
        <div className="flex items-center gap-2 text-[#64748B]">
          <BookOpen className="w-3.5 h-3.5 text-[#94A3B8]" />
          <span>
            {triple.literature_all_three
              ? `PubMed citations found: ${triple.literature_all_three.count}`
              : 'Literature check available on request'}
          </span>
          {litNotice && (
            <span className="text-[10px] text-[#0D9488] font-mono ml-2">
              ({litNotice})
            </span>
          )}
        </div>

        <button
          type="button"
          onClick={handleOpenPubMed}
          className="text-[11px] font-semibold text-[#0D9488] hover:text-[#0F766E] inline-flex items-center gap-1 cursor-pointer hover:underline"
        >
          Check 3-Drug Literature in PubMed
          <ExternalLink className="w-3 h-3" />
        </button>
      </div>

      {/* Expand/Collapse Toggle for Constituent Pairwise Breakdown */}
      <div className="pt-1">
        <button
          type="button"
          onClick={() => setIsExpanded(!isExpanded)}
          className="w-full py-2 px-3 bg-[#F8FAFC] hover:bg-[#F1F5F9] border border-[#E2E8F0] rounded text-xs font-semibold text-[#334155] flex items-center justify-between transition-colors cursor-pointer"
        >
          <span className="flex items-center gap-2">
            <Layers className="w-3.5 h-3.5 text-[#64748B]" />
            <span>
              {isExpanded
                ? 'Hide Pairwise Breakdown (A×B, A×C, B×C)'
                : 'Show Pairwise Breakdown (A×B, A×C, B×C)'}
            </span>
          </span>
          {isExpanded ? (
            <ChevronUp className="w-4 h-4 text-[#64748B]" />
          ) : (
            <ChevronDown className="w-4 h-4 text-[#64748B]" />
          )}
        </button>
      </div>

      {/* Expanded Constituent Pairwise Breakdown */}
      {isExpanded && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2">
          {pairItems.map((item) => {
            const isBottleneck =
              item.key === bottleneckKey ||
              (item.drug1 === bottleneckD1 && item.drug2 === bottleneckD2) ||
              (item.drug1 === bottleneckD2 && item.drug2 === bottleneckD1);

            const v = item.ranking.v_score ?? item.ranking.score;
            const psyn = item.ranking.p_synergy;
            const tox = item.ranking.toxicity_penalty;
            const bd = item.ranking.breakdown;

            return (
              <div
                key={item.key}
                className={`p-3.5 rounded-md border space-y-2.5 transition-all ${
                  isBottleneck
                    ? 'bg-[#FEF2F2]/60 border-[#FECACA] shadow-2xs'
                    : 'bg-[#F8FAFC] border-[#E2E8F0]'
                }`}
              >
                <div className="flex items-center justify-between gap-1.5 flex-wrap">
                  <span className="text-[10px] uppercase font-bold tracking-wider text-[#64748B]">
                    {item.label}
                  </span>
                  {isBottleneck && (
                    <span className="text-[10px] font-mono font-bold uppercase bg-[#DC2626] text-[#FFFFFF] px-1.5 py-0.2 rounded">
                      Bottleneck
                    </span>
                  )}
                </div>

                <div className="font-semibold text-xs text-[#0F172A] line-clamp-1">
                  {item.drug1} × {item.drug2}
                </div>

                <div className="pt-0.5">
                  <ToxicityBadge
                    hasKnownDdi={bd?.has_known_ddi}
                    unknownRiskApplied={bd?.unknown_risk_applied}
                    sideEffectOverlap={bd?.side_effect_overlap}
                    toxicityPenalty={tox}
                    size="sm"
                    showDetails={true}
                  />
                </div>

                <div className="bg-[#FFFFFF] border border-[#E2E8F0] p-2 rounded text-[11px] font-mono space-y-1">
                  <div className="flex justify-between">
                    <span className="text-[#64748B]">V(pair):</span>
                    <strong className="text-[#0D9488]">{v.toFixed(4)}</strong>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#64748B]">p(synergy):</span>
                    <strong className="text-[#059669]">{psyn.toFixed(4)}</strong>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#64748B]">toxicity penalty:</span>
                    <strong className={tox > 0.4 ? 'text-[#DC2626]' : 'text-[#D97706]'}>
                      {tox.toFixed(4)}
                    </strong>
                  </div>
                  {bd?.side_effect_overlap !== null && bd?.side_effect_overlap !== undefined && (
                    <div className="flex justify-between">
                      <span className="text-[#64748B]">SIDER overlap:</span>
                      <span>{(bd.side_effect_overlap * 100).toFixed(1)}%</span>
                    </div>
                  )}
                </div>

                {bd?.top_shared_side_effects && bd.top_shared_side_effects.length > 0 && (
                  <div className="text-[10px] text-[#64748B]">
                    <span className="font-medium text-[#475569]">Shared SEs ({bd.shared_side_effects_count}):</span>{' '}
                    <span className="line-clamp-2 italic">
                      {bd.top_shared_side_effects.slice(0, 4).join(', ')}
                    </span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
