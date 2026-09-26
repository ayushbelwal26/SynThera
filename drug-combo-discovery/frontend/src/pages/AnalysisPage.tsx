import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FlaskConical, Activity, History, BarChart3,
  ShieldCheck, BookOpen, MessageSquare, GitBranch,
} from 'lucide-react';
import { useApp } from '../services/AppContext';
import { PredictionHero } from '../components/analysis/PredictionHero';
import { ProbabilityVector } from '../components/analysis/ProbabilityVector';
import { ToxicityCard } from '../components/analysis/ToxicityCard';
import { PathwayGraph } from '../components/analysis/PathwayGraph';
import { NodeDetailModal } from '../components/analysis/NodeDetailModal';
import { FaithfulnessCard } from '../components/analysis/FaithfulnessCard';
import { LiteratureSection } from '../components/analysis/LiteratureSection';
import { AnalysisChatPanel } from '../components/analysis/AnalysisChatPanel';
import { AccordionSection } from '../components/common/AccordionSection';
import { BENCHMARKS } from '../components/discover/BenchmarkPresets';
import { predictCombination } from '../services/api';
import { LoadingStages } from '../components/common/LoadingStages';

export const AnalysisPage: React.FC = () => {
  const navigate = useNavigate();
  const { currentPrediction, setCurrentPrediction, recentPredictions, addRecentPrediction } = useApp();
  const [selectedEntity, setSelectedEntity] = useState<{ type: 'node' | 'edge'; data: any } | null>(null);
  const [isLoadingBenchmark, setIsLoadingBenchmark] = useState(false);

  const handleQuickLoadBenchmark = async (index: number) => {
    const preset = BENCHMARKS[index];
    setIsLoadingBenchmark(true);
    try {
      const res = await predictCombination({ drug_a: preset.drugA.id, drug_b: preset.drugB.id, cell_line: preset.cellLine });
      setCurrentPrediction(res);
      addRecentPrediction(res);
    } catch (err) {
      console.error('Failed to load benchmark:', err);
    } finally {
      setIsLoadingBenchmark(false);
    }
  };

  if (isLoadingBenchmark) {
    return <div className="py-12"><LoadingStages title="Loading Benchmark" subtitle="Running GNN inference and attribution" /></div>;
  }

  if (!currentPrediction) {
    return (
      <div style={{ maxWidth: 560, margin: '0 auto', paddingTop: 48, paddingBottom: 48 }}>
        {/* Empty state */}
        <div style={{ textAlign: 'center', marginBottom: 36 }}>
          <div style={{
            width: 52, height: 52, borderRadius: '50%',
            backgroundColor: 'var(--surface-subtle)',
            border: '1px solid var(--border)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            margin: '0 auto 16px',
            color: 'var(--text-muted)',
          }}>
            <Activity size={22} />
          </div>
          <h3 style={{
            fontFamily: 'var(--font-serif)',
            fontSize: 22, fontWeight: 700,
            color: 'var(--text-primary)',
            margin: '0 0 8px',
          }}>
            No combination selected
          </h3>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.6, margin: '0 0 24px' }}>
            Select a drug pair from the Discover page to view its full mechanistic analysis, attribution graph, and literature evidence.
          </p>
          <button
            type="button"
            onClick={() => navigate('/discover')}
            style={{
              display: 'inline-flex', alignItems: 'center', gap: 8,
              padding: '9px 18px',
              backgroundColor: 'var(--accent)',
              color: '#FFFFFF',
              border: 'none', borderRadius: 6,
              fontSize: 13, fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            <FlaskConical size={14} />
            Go to Discover
          </button>
        </div>

        {/* Quick-load benchmarks */}
        <div style={{
          borderTop: '1px solid var(--border)', paddingTop: 24,
        }}>
          <p style={{
            fontSize: 11, fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase',
            color: 'var(--text-muted)', marginBottom: 12,
          }}>
            Load a reference case
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 8 }}>
            {BENCHMARKS.map((bm, idx) => (
              <button
                key={bm.id}
                type="button"
                onClick={() => handleQuickLoadBenchmark(idx)}
                style={{
                  padding: '10px 14px',
                  backgroundColor: 'var(--surface)',
                  border: '1px solid var(--border)',
                  borderRadius: 6,
                  textAlign: 'left',
                  cursor: 'pointer',
                  transition: 'border-color 150ms',
                }}
              >
                <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 3 }}>
                  {bm.name}
                </div>
                <div style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                  {bm.cellLine} · {bm.expectedClass}
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  }

  const hasFaithfulness = Boolean(
    currentPrediction.faithfulness ||
    typeof currentPrediction.sufficiency_retained_pct === 'number'
  );
  const hasLiterature = (currentPrediction.supporting_literature?.length ?? 0) > 0 ||
    (currentPrediction.literature?.citations?.length ?? 0) > 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {/* ── Level 0: Primary Result Hero ─────────────────────── */}
      <PredictionHero prediction={currentPrediction} />

      {/* ── Level 1: Probability Distribution ──────────────── */}
      <AccordionSection
        title="Class Probability Distribution"
        subtitle="Temperature-calibrated softmax over GNN logits · Σ p = 1.0"
        icon={<BarChart3 size={15} />}
        defaultOpen={true}
        accentColor="var(--synergy)"
      >
        <ProbabilityVector prediction={currentPrediction} />
      </AccordionSection>

      {/* ── Level 2: Pathway Attribution Graph ─────────────── */}
      <AccordionSection
        title="Biological Pathway Attribution"
        subtitle="Gradient-weighted edges from the 2-hop PrimeKG subgraph"
        icon={<GitBranch size={15} />}
        defaultOpen={true}
        accentColor="var(--accent)"
      >
        <PathwayGraph
          topEdges={currentPrediction.top_edges}
          drugAName={currentPrediction.drug_a_name}
          drugBName={currentPrediction.drug_b_name}
          explanationText={currentPrediction.explanation_text}
          onSelectEntity={setSelectedEntity}
        />
      </AccordionSection>

      {/* ── Level 3: Safety & Composite Ranking ────────────── */}
      {currentPrediction.ranking && (
        <AccordionSection
          title="Safety Profile & Multi-Objective Ranking"
          subtitle="DDI risk, phenotypic overlap, target redundancy · Composite V(pair)"
          icon={<ShieldCheck size={15} />}
          defaultOpen={false}
          accentColor="var(--additive)"
        >
          <ToxicityCard prediction={currentPrediction} />
        </AccordionSection>
      )}

      {/* ── Level 4: Faithfulness Verification ─────────────── */}
      <AccordionSection
        title="Explanation Faithfulness"
        subtitle="In-silico necessity & sufficiency ablation · Is the subgraph truly causal?"
        icon={<ShieldCheck size={15} />}
        defaultOpen={hasFaithfulness}
        accentColor={hasFaithfulness ? 'var(--synergy)' : 'var(--text-muted)'}
        badge={hasFaithfulness ? (
          <span style={{
            fontSize: 10, fontWeight: 700, fontFamily: 'var(--font-mono)',
            backgroundColor: 'var(--synergy-subtle)',
            border: '1px solid var(--synergy-border)',
            color: 'var(--synergy-text)',
            borderRadius: 4, padding: '2px 6px',
            letterSpacing: '0.04em',
          }}>
            VERIFIED
          </span>
        ) : undefined}
      >
        <FaithfulnessCard prediction={currentPrediction} />
      </AccordionSection>

      {/* ── Level 5: Literature Evidence ────────────────────── */}
      <AccordionSection
        title="Supporting Literature"
        subtitle="NCBI PubMed E-Utilities · Real abstract retrieval, independently of model reasoning"
        icon={<BookOpen size={15} />}
        defaultOpen={hasLiterature}
        accentColor="var(--lit)"
        badge={hasLiterature ? (
          <span style={{
            fontSize: 10, fontFamily: 'var(--font-mono)',
            backgroundColor: 'var(--lit-subtle)',
            border: '1px solid var(--lit-border)',
            color: 'var(--lit)',
            borderRadius: 4, padding: '2px 6px',
          }}>
            {(currentPrediction.literature?.citations?.length ?? currentPrediction.supporting_literature?.length ?? 0)} citations
          </span>
        ) : undefined}
      >
        <LiteratureSection
          citations={currentPrediction.supporting_literature}
          literature={currentPrediction.literature}
          drugAName={currentPrediction.drug_a_name}
          drugBName={currentPrediction.drug_b_name}
        />
      </AccordionSection>

      {/* ── Level 6: Grounded Research Assistant ───────────── */}
      <AccordionSection
        title="Research Assistant"
        subtitle="Grounded tool-calling · Claims restricted to tool results only"
        icon={<MessageSquare size={15} />}
        defaultOpen={false}
        accentColor="var(--accent)"
      >
        <AnalysisChatPanel prediction={currentPrediction} />
      </AccordionSection>

      {/* ── Recent Session History ───────────────────────────── */}
      {recentPredictions.length > 1 && (
        <div style={{
          backgroundColor: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: 8,
          padding: '14px 18px',
          boxShadow: 'var(--shadow-xs)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
            <History size={14} style={{ color: 'var(--text-muted)' }} />
            <span style={{
              fontSize: 11, fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase',
              color: 'var(--text-muted)',
            }}>
              Session history ({recentPredictions.length})
            </span>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {recentPredictions.map((p, idx) => (
              <button
                key={`${p.drug_a}_${p.drug_b}_${p.cell_line}_${idx}`}
                type="button"
                onClick={() => setCurrentPrediction(p)}
                style={{
                  padding: '7px 12px',
                  backgroundColor: p === currentPrediction ? 'var(--accent-subtle)' : 'var(--surface-subtle)',
                  border: `1px solid ${p === currentPrediction ? 'var(--accent-border)' : 'var(--border)'}`,
                  borderRadius: 6,
                  cursor: 'pointer',
                  textAlign: 'left',
                  transition: 'border-color 150ms',
                }}
              >
                <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)' }}>
                  {p.drug_a_name} + {p.drug_b_name}
                </div>
                <div style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', marginTop: 2 }}>
                  {p.cell_line} · {p.predicted_class}
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Entity inspector modal */}
      <NodeDetailModal entity={selectedEntity} onClose={() => setSelectedEntity(null)} />
    </div>
  );
};
