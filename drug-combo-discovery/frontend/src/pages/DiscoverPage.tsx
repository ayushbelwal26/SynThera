import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeftRight, Play, ArrowRight, Clock, ChevronDown, ChevronUp } from 'lucide-react';
import { useApp } from '../services/AppContext';
import { predictCombination, searchCombinations } from '../services/api';
import type { Drug, PredictionResult, SearchResponse } from '../types/api';
import { DrugSelectInput } from '../components/discover/DrugSelectInput';
import { CellLineDropdown } from '../components/discover/CellLineDropdown';
import { BenchmarkPresets } from '../components/discover/BenchmarkPresets';
import type { BenchmarkPreset } from '../components/discover/BenchmarkPresets';
import { DiscoveryMode } from '../components/discover/DiscoveryMode';
import { WhyNotSection } from '../components/discover/WhyNotSection';
import { LoadingStages } from '../components/common/LoadingStages';
import { AlertNotice } from '../components/common/AlertNotice';

/* ── Predicted class pill ── */
const ClassPill: React.FC<{ cls: string; size?: 'sm' | 'md' }> = ({ cls, size = 'md' }) => {
  const map: Record<string, { bg: string; border: string; color: string }> = {
    synergy:    { bg: 'var(--synergy-subtle)',    border: 'var(--synergy-border)',    color: 'var(--synergy)'    },
    antagonism: { bg: 'var(--antagonism-subtle)', border: 'var(--antagonism-border)', color: 'var(--antagonism)' },
    additive:   { bg: 'var(--additive-subtle)',   border: 'var(--additive-border)',   color: 'var(--additive)'   },
  };
  const style = map[cls] ?? map.additive;
  return (
    <span style={{
      fontSize: size === 'sm' ? 10 : 11,
      fontWeight: 700, fontFamily: 'var(--font-mono)',
      letterSpacing: '0.06em', textTransform: 'uppercase',
      backgroundColor: style.bg,
      border: `1px solid ${style.border}`,
      color: style.color,
      borderRadius: 4, padding: size === 'sm' ? '2px 6px' : '3px 8px',
    }}>
      {cls}
    </span>
  );
};

/* ── Search result card ── */
const SearchResultCard: React.FC<{
  pair: PredictionResult;
  idx: number;
  isInspecting: boolean;
  searchMethod?: string;
  onInspect: () => void;
}> = ({ pair, idx, isInspecting, searchMethod, onInspect }) => {
  const [expanded, setExpanded] = useState(false);
  const vScore = pair.v_score ?? pair.ranking?.v_score ?? pair.score;
  const pSyn = pair.p_synergy ?? pair.ranking?.p_synergy ?? pair.score;

  return (
    <div style={{
      backgroundColor: 'var(--surface)',
      border: '1px solid var(--border)',
      borderRadius: 8,
      overflow: 'hidden',
      boxShadow: 'var(--shadow-xs)',
      transition: 'border-color 150ms',
    }}>
      {/* Main row */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '12px 16px', gap: 12, flexWrap: 'wrap',
      }}>
        {/* Rank + names + class */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0 }}>
          <span style={{
            fontSize: 11, fontFamily: 'var(--font-mono)', fontWeight: 700,
            color: 'var(--text-muted)', flexShrink: 0,
            width: 24, textAlign: 'center',
          }}>
            #{pair.rank ?? idx + 1}
          </span>
          <div style={{ minWidth: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
              <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>
                {pair.drug_a_name} + {pair.drug_b_name}
              </span>
              <ClassPill cls={pair.predicted_class} size="sm" />
              {(pair.search_method === 'mcts' || searchMethod === 'mcts') && pair.mcts_visits !== undefined && (
                <span style={{
                  fontSize: 10, fontFamily: 'var(--font-mono)',
                  color: 'var(--text-muted)',
                  backgroundColor: 'var(--surface-subtle)',
                  border: '1px solid var(--border)',
                  borderRadius: 3, padding: '1px 5px',
                }}>
                  {pair.mcts_visits} visits
                </span>
              )}
            </div>
            {/* Short explanation */}
            <p style={{
              fontSize: 12, color: 'var(--text-muted)',
              marginTop: 3, lineHeight: 1.5,
              overflow: 'hidden',
              display: '-webkit-box',
              WebkitLineClamp: expanded ? undefined : 2,
              WebkitBoxOrient: 'vertical',
            }}>
              {pair.explanation_text}
            </p>
          </div>
        </div>

        {/* Scores + actions */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexShrink: 0 }}>
          {/* V-score */}
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: 10, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', marginBottom: 1 }}>
              V(pair)
            </div>
            <div style={{ fontSize: 16, fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--accent)' }}>
              {vScore.toFixed(4)}
            </div>
            <div style={{ fontSize: 10, fontFamily: 'var(--font-mono)', color: 'var(--synergy)' }}>
              p(syn)={pSyn.toFixed(3)}
            </div>
          </div>

          {/* Expand toggle */}
          <button
            type="button"
            onClick={() => setExpanded(!expanded)}
            style={{
              padding: '6px', borderRadius: 5,
              backgroundColor: 'var(--surface-subtle)',
              border: '1px solid var(--border)',
              cursor: 'pointer', color: 'var(--text-muted)',
              display: 'flex', alignItems: 'center',
            }}
            title={expanded ? 'Collapse details' : 'Expand details'}
          >
            {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>

          {/* Inspect button */}
          <button
            type="button"
            disabled={isInspecting}
            onClick={onInspect}
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '7px 14px',
              backgroundColor: isInspecting ? 'var(--surface-subtle)' : 'var(--accent)',
              color: isInspecting ? 'var(--text-muted)' : '#FFFFFF',
              border: `1px solid ${isInspecting ? 'var(--border)' : 'var(--accent)'}`,
              borderRadius: 6,
              fontSize: 12, fontWeight: 600,
              cursor: isInspecting ? 'not-allowed' : 'pointer',
              transition: 'background-color 150ms',
              flexShrink: 0,
            }}
          >
            {isInspecting ? (
              <><svg className="animate-spin" viewBox="0 0 24 24" fill="none" style={{ width: 13, height: 13 }}><circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" className="opacity-25" /><path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" className="opacity-75" /></svg>Loading…</>
            ) : (
              <>Inspect <ArrowRight size={13} /></>
            )}
          </button>
        </div>
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div style={{
          borderTop: '1px solid var(--border)',
          padding: '12px 16px',
          backgroundColor: 'var(--surface-subtle)',
          display: 'flex', flexWrap: 'wrap', gap: 16,
        }}>
          {/* Toxicity detail */}
          {pair.ranking?.breakdown && (
            <div style={{ minWidth: 200 }}>
              <p style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.05em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 6 }}>
                Safety
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4, fontSize: 12, fontFamily: 'var(--font-mono)' }}>
                <span>DDI known: <strong style={{ color: pair.ranking.breakdown.has_known_ddi ? 'var(--antagonism)' : 'var(--synergy)' }}>
                  {pair.ranking.breakdown.has_known_ddi === null ? 'Unknown' : pair.ranking.breakdown.has_known_ddi ? 'Yes' : 'No'}
                </strong></span>
                {pair.ranking.breakdown.side_effect_overlap !== null && (
                  <span>SE overlap: <strong>{((pair.ranking.breakdown.side_effect_overlap ?? 0) * 100).toFixed(0)}%</strong></span>
                )}
                <span>Tox penalty: <strong>{pair.ranking.toxicity_penalty.toFixed(3)}</strong></span>
              </div>
            </div>
          )}

          {/* Faithfulness notice */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
            <Clock size={11} />
            Faithfulness ablation not computed during batch search. Click Inspect for full verification.
          </div>
        </div>
      )}
    </div>
  );
};

/* ── Main DiscoverPage ── */
export const DiscoverPage: React.FC = () => {
  const navigate = useNavigate();
  const { drugs, cellLineStatus, setCurrentPrediction, addRecentPrediction } = useApp();

  const [activeTab, setActiveTab] = useState<'pair' | 'search'>('pair');
  const [drugA, setDrugA] = useState<Drug | null>(null);
  const [drugB, setDrugB] = useState<Drug | null>(null);
  const [cellLine, setCellLine] = useState<string>('T98G');
  const [diseaseContext, setDiseaseContext] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [searchDisease, setSearchDisease] = useState<string>('glioblastoma');
  const [searchResults, setSearchResults] = useState<SearchResponse | null>(null);
  const [inspectingPairIdx, setInspectingPairIdx] = useState<number | null>(null);

  const handleSwapDrugs = () => { const t = drugA; setDrugA(drugB); setDrugB(t); };

  const handleSelectPreset = (preset: BenchmarkPreset) => {
    setDrugA(preset.drugA);
    setDrugB(preset.drugB);
    setCellLine(preset.cellLine);
    setDiseaseContext(preset.indication);
    setErrorMsg(null);
  };

  const handleAnalyzePair = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!drugA || !drugB || !cellLine) { setErrorMsg('Please select both Compound A and Compound B.'); return; }
    if (drugA.id === drugB.id) { setErrorMsg('Please select two distinct compounds.'); return; }
    setIsLoading(true); setErrorMsg(null);
    try {
      const result = await predictCombination({ drug_a: drugA.id, drug_b: drugB.id, cell_line: cellLine, disease: diseaseContext.trim() || undefined });
      setCurrentPrediction(result); addRecentPrediction(result); navigate('/analysis');
    } catch (err: any) { setErrorMsg(err.message || 'Analysis service error.'); }
    finally { setIsLoading(false); }
  };

  const handleRunSearch = async (disease: string, targetCellLine: string, maxCandidates: number, topK: number, searchMethod: 'beam' | 'greedy' | 'mcts' = 'beam', nSimulations = 50, mctsC = 1.414) => {
    setSearchDisease(disease); setIsLoading(true); setErrorMsg(null); setSearchResults(null);
    try {
      const res = await searchCombinations({ disease, cell_line: targetCellLine, max_candidates: maxCandidates, top_k: topK, search_method: searchMethod, n_simulations: nSimulations, mcts_c: mctsC });
      setSearchResults(res);
    } catch (err: any) { setErrorMsg(err.message || 'Discovery failed. Verify the indication name.'); }
    finally { setIsLoading(false); }
  };

  const handleSelectDiscoveredPair = async (pair: PredictionResult, idx: number) => {
    setInspectingPairIdx(idx);
    try {
      const full = await predictCombination({ drug_a: pair.drug_a, drug_b: pair.drug_b, cell_line: pair.cell_line });
      setCurrentPrediction(full); addRecentPrediction(full); navigate('/analysis');
    } catch {
      setCurrentPrediction(pair); addRecentPrediction(pair); navigate('/analysis');
    } finally { setInspectingPairIdx(null); }
  };

  const handleInspectWhyNotPair = async (drugAId: string, drugBId: string, cl: string) => {
    setIsLoading(true); setErrorMsg(null);
    try {
      const full = await predictCombination({ drug_a: drugAId, drug_b: drugBId, cell_line: cl });
      setCurrentPrediction(full); addRecentPrediction(full); navigate('/analysis');
    } catch (err: any) { setErrorMsg(err.message || 'Failed to inspect combination.'); }
    finally { setIsLoading(false); }
  };

  /* ── Tab button ── */
  const TabBtn: React.FC<{ id: 'pair' | 'search'; label: string }> = ({ id, label }) => (
    <button
      type="button"
      onClick={() => { setActiveTab(id); setErrorMsg(null); }}
      style={{
        padding: '10px 16px',
        fontSize: 13, fontWeight: 600,
        color: activeTab === id ? 'var(--accent)' : 'var(--text-secondary)',
        backgroundColor: 'transparent',
        border: 'none',
        borderBottom: `2px solid ${activeTab === id ? 'var(--accent)' : 'transparent'}`,
        cursor: 'pointer',
        transition: 'color 150ms, border-color 150ms',
        letterSpacing: '-0.01em',
      }}
    >
      {label}
    </button>
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Page header */}
      <div style={{ borderBottom: '1px solid var(--border)', paddingBottom: 16 }}>
        <h2 style={{
          fontFamily: 'var(--font-serif)', fontSize: 24, fontWeight: 700,
          color: 'var(--text-primary)', margin: 0, letterSpacing: '-0.02em',
        }}>
          Drug Combination Discovery
        </h2>
        <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 4, lineHeight: 1.6 }}>
          Screen combinations against PrimeKG · Heterogeneous Graph Transformer prediction · Mechanistic attribution
        </p>
      </div>

      {/* Tab bar */}
      <div style={{ display: 'flex', borderBottom: '1px solid var(--border)', gap: 0, overflow: 'visible' }}>
        <TabBtn id="pair" label="Targeted Pair Analysis" />
        <TabBtn id="search" label="Unbiased Discovery Search" />
      </div>

      {/* Error */}
      {errorMsg && <AlertNotice type="error" title="Notice">{errorMsg}</AlertNotice>}

      {/* Loading */}
      {isLoading && (
        <div style={{ paddingTop: 8, paddingBottom: 8 }}>
          <LoadingStages
            title={activeTab === 'pair' ? 'Evaluating Drug Combination' : 'Discovering Candidate Combinations'}
            subtitle={activeTab === 'pair'
              ? `Running GNN inference for ${drugA?.name ?? 'Drug A'} + ${drugB?.name ?? 'Drug B'} @ ${cellLine}`
              : 'Traversing PrimeKG indication neighbors and ranking candidates'}
          />
        </div>
      )}

      {/* Tab 1: Targeted Pair */}
      {!isLoading && activeTab === 'pair' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: 20 }} className="sm:block">
          <div>
            {/* Pair form */}
            <form
              onSubmit={handleAnalyzePair}
              style={{
                backgroundColor: 'var(--surface)',
                border: '1px solid var(--border)',
                borderRadius: 8,
                padding: '20px 22px',
                boxShadow: 'var(--shadow-xs)',
                marginBottom: 16,
              }}
            >
              <p style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 14 }}>
                Select compounds
              </p>

              {/* Drug selectors */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', alignItems: 'end', gap: 10, marginBottom: 16 }}>
                <DrugSelectInput label="Compound A" selectedDrug={drugA} onSelect={setDrugA} drugs={drugs} />
                <div style={{ display: 'flex', justifyContent: 'center', paddingBottom: 2 }}>
                  <button
                    type="button"
                    onClick={handleSwapDrugs}
                    disabled={!drugA && !drugB}
                    style={{
                      padding: '8px', borderRadius: 6,
                      backgroundColor: 'var(--surface-subtle)',
                      border: '1px solid var(--border)',
                      cursor: 'pointer', color: 'var(--text-muted)',
                      display: 'flex', alignItems: 'center',
                      opacity: !drugA && !drugB ? 0.4 : 1,
                    }}
                    title="Swap drugs"
                  >
                    <ArrowLeftRight size={15} />
                  </button>
                </div>
                <DrugSelectInput label="Compound B" selectedDrug={drugB} onSelect={setDrugB} drugs={drugs} />
              </div>

              {/* Cell line + disease */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 18 }}>
                <CellLineDropdown status={cellLineStatus} selectedCellLine={cellLine} onSelect={setCellLine} />
                <div>
                  <label style={{ display: 'block', fontSize: 11, fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--text-secondary)', marginBottom: 6 }}>
                    Disease Context
                    <span style={{ fontWeight: 400, textTransform: 'none', letterSpacing: 0, color: 'var(--text-muted)', marginLeft: 6 }}>
                      optional
                    </span>
                  </label>
                  <input
                    type="text"
                    value={diseaseContext}
                    onChange={(e) => setDiseaseContext(e.target.value)}
                    placeholder="e.g. glioblastoma"
                    style={{
                      width: '100%', padding: '8px 12px',
                      fontSize: 13, fontFamily: 'var(--font-sans)',
                      backgroundColor: 'var(--surface)',
                      border: '1px solid var(--border)',
                      borderRadius: 6, color: 'var(--text-primary)',
                      outline: 'none',
                    }}
                    onFocus={(e) => { e.currentTarget.style.borderColor = 'var(--accent)'; }}
                    onBlur={(e) => { e.currentTarget.style.borderColor = 'var(--border)'; }}
                  />
                </div>
              </div>

              {/* Submit */}
              <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                <button
                  type="submit"
                  disabled={!drugA || !drugB || isLoading}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 8,
                    padding: '9px 20px',
                    backgroundColor: 'var(--accent)',
                    border: 'none', borderRadius: 6,
                    color: '#FFFFFF', fontSize: 13, fontWeight: 600,
                    cursor: 'pointer',
                    opacity: !drugA || !drugB ? 0.5 : 1,
                    transition: 'opacity 150ms',
                  }}
                >
                  <Play size={14} fill="currentColor" />
                  Analyze Combination
                </button>
              </div>
            </form>

            {/* Benchmark presets */}
            <BenchmarkPresets onSelect={handleSelectPreset} />
          </div>

          {/* Sidebar: model specs */}
          <div style={{
            backgroundColor: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: 8,
            padding: '18px',
            boxShadow: 'var(--shadow-xs)',
            height: 'fit-content',
          }}>
            <p style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 14 }}>
              Model Pipeline
            </p>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              {[
                ['Architecture', 'HGT (Heterogeneous GNN)'],
                ['Knowledge Base', 'PrimeKG Multimodal'],
                ['Calibration', 'Temperature Scaling'],
                ['Explanation', 'Gradient Edge Saliency'],
                ['Verification', 'Dual Faithfulness Ablation'],
                ['Literature', 'NCBI PubMed E-Utilities'],
              ].map(([k, v]) => (
                <tr key={k} style={{ borderBottom: '1px solid var(--border)' }}>
                  <td style={{ padding: '7px 0', fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', paddingRight: 12 }}>{k}</td>
                  <td style={{ padding: '7px 0', fontSize: 11, fontWeight: 600, color: 'var(--text-primary)', textAlign: 'right' }}>{v}</td>
                </tr>
              ))}
            </table>
            <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 14, lineHeight: 1.5 }}>
              All predictions represent live GNN inference. No simulated data.
            </p>
          </div>
        </div>
      )}

      {/* Tab 2: Discovery Search */}
      {!isLoading && activeTab === 'search' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Search form */}
          <div style={{
            backgroundColor: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: 8,
            padding: '20px 22px',
            boxShadow: 'var(--shadow-xs)',
            maxWidth: 640,
          }}>
            <DiscoveryMode
              cellLineStatus={cellLineStatus}
              selectedCellLine={cellLine}
              onSelectCellLine={setCellLine}
              onRunSearch={handleRunSearch}
              isLoading={isLoading}
            />
          </div>

          {/* Results */}
          {searchResults && (
            <div>
              {/* Results header */}
              <div style={{
                display: 'flex', flexWrap: 'wrap', alignItems: 'center',
                justifyContent: 'space-between', gap: 10, marginBottom: 12,
              }}>
                <div>
                  <h3 style={{ fontFamily: 'var(--font-serif)', fontSize: 18, fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
                    Results for "{searchResults.disease}"
                  </h3>
                  <p style={{ fontSize: 12, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', marginTop: 3 }}>
                    {searchResults.cell_line} · {searchResults.candidate_pool_size} candidates
                    {searchResults.max_candidates_scored ? ` · ${searchResults.max_candidates_scored} pairs scored` : ''}
                  </p>
                </div>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  {searchResults.search_method && (
                    <span style={{
                      fontSize: 11, fontFamily: 'var(--font-mono)', fontWeight: 600,
                      backgroundColor: 'var(--accent-subtle)',
                      border: '1px solid var(--accent-border)',
                      color: 'var(--accent-text)',
                      borderRadius: 4, padding: '4px 8px',
                    }}>
                      {searchResults.search_method === 'mcts'
                        ? `MCTS · ${searchResults.n_simulations ?? 50} sims`
                        : searchResults.search_method === 'beam'
                        ? `Beam width=${searchResults.beam_width ?? 5}`
                        : 'Greedy'
                      }
                    </span>
                  )}
                  {searchResults.truncated && (
                    <span style={{
                      fontSize: 11, fontFamily: 'var(--font-mono)',
                      backgroundColor: 'var(--warning-subtle)',
                      border: '1px solid var(--warning-border)',
                      color: 'var(--warning)',
                      borderRadius: 4, padding: '4px 8px',
                    }}>
                      ⚠ Time budget reached
                    </span>
                  )}
                  <span style={{
                    fontSize: 11, fontFamily: 'var(--font-mono)',
                    backgroundColor: 'var(--surface-subtle)',
                    border: '1px solid var(--border)',
                    color: 'var(--text-muted)',
                    borderRadius: 4, padding: '4px 8px',
                  }}>
                    Top {searchResults.results.length}
                  </span>
                </div>
              </div>

              {/* Result cards */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {searchResults.results.map((pair, idx) => (
                  <SearchResultCard
                    key={`${pair.drug_a}_${pair.drug_b}_${idx}`}
                    pair={pair}
                    idx={idx}
                    isInspecting={inspectingPairIdx === idx}
                    searchMethod={searchResults.search_method}
                    onInspect={() => handleSelectDiscoveredPair(pair, idx)}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Why Not diagnostic */}
          <WhyNotSection
            disease={searchResults?.disease || searchDisease || diseaseContext || 'glioblastoma'}
            cellLine={searchResults?.cell_line || cellLine}
            searchMethod={(searchResults?.search_method as any) || 'beam'}
            onInspectPair={handleInspectWhyNotPair}
          />
        </div>
      )}
    </div>
  );
};
