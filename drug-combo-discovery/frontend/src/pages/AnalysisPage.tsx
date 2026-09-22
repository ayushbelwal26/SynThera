import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Compass, Activity, History } from 'lucide-react';
import { useApp } from '../services/AppContext';
import { PredictionHeader } from '../components/analysis/PredictionHeader';
import { ProbabilityVector } from '../components/analysis/ProbabilityVector';
import { ToxicityCard } from '../components/analysis/ToxicityCard';
import { PathwayGraph } from '../components/analysis/PathwayGraph';
import { NodeDetailModal } from '../components/analysis/NodeDetailModal';
import { FaithfulnessCard } from '../components/analysis/FaithfulnessCard';
import { LiteratureSection } from '../components/analysis/LiteratureSection';
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
      const res = await predictCombination({
        drug_a: preset.drugA.id,
        drug_b: preset.drugB.id,
        cell_line: preset.cellLine,
      });
      setCurrentPrediction(res);
      addRecentPrediction(res);
    } catch (err) {
      console.error('Failed to load benchmark:', err);
    } finally {
      setIsLoadingBenchmark(false);
    }
  };

  if (isLoadingBenchmark) {
    return (
      <div className="py-12">
        <LoadingStages
          title="Loading Benchmark Combination"
          subtitle="Querying model checkpoint and PrimeKG attribution pathway"
        />
      </div>
    );
  }

  // Section 10 Empty State: "Select two compounds to begin analysis."
  if (!currentPrediction) {
    return (
      <div className="max-w-2xl mx-auto py-12 text-center">
        <div className="w-14 h-14 rounded-full bg-[#F1F5F9] border border-[#E2E8F0] flex items-center justify-center mx-auto mb-4 text-[#64748B]">
          <Activity className="w-6 h-6" />
        </div>
        <h3 className="font-serif text-2xl font-bold text-[#0F172A] mb-2">
          Select two compounds to begin analysis.
        </h3>
        <p className="text-sm text-[#64748B] mb-6 max-w-lg mx-auto leading-relaxed">
          No prediction result is currently active in the workspace. Configure a drug pair in the discovery instrument or load a benchmark reference case below.
        </p>

        <div className="flex justify-center gap-3 mb-8">
          <button
            type="button"
            onClick={() => navigate('/discover')}
            className="px-5 py-2.5 bg-[#0D9488] hover:bg-[#0F766E] text-[#FFFFFF] rounded-md font-semibold text-xs flex items-center gap-2 transition-colors cursor-pointer shadow-xs"
          >
            <Compass className="w-4 h-4" />
            Open Query Instrument
          </button>
        </div>

        <div className="border-t border-[#E5E5E0] pt-6 text-left">
          <span className="text-xs font-semibold text-[#475569] uppercase tracking-wider block mb-3">
            Quick-Load Reference Case:
          </span>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
            {BENCHMARKS.map((bm, idx) => (
              <button
                key={bm.id}
                type="button"
                onClick={() => handleQuickLoadBenchmark(idx)}
                className="p-3 bg-[#FFFFFF] border border-[#CBD5E1] hover:border-[#0D9488] rounded-md text-left transition-all group"
              >
                <span className="font-semibold text-xs text-[#0F172A] group-hover:text-[#0D9488] block">
                  {bm.name}
                </span>
                <span className="font-mono text-[10px] text-[#64748B] mt-1 block">
                  {bm.cellLine} &bull; {bm.expectedClass}
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 1. Header with Metadata, Class Badge, Export */}
      <PredictionHeader prediction={currentPrediction} />

      {/* 2. Calibrated Probability Vector Bar */}
      <ProbabilityVector prediction={currentPrediction} />

      {/* 3. Multi-Objective Value Function & Toxicity Breakdown (Phase B1/B2) */}
      <ToxicityCard prediction={currentPrediction} />

      {/* 4. Interactive Biological Pathway Attribution Map */}
      <PathwayGraph
        topEdges={currentPrediction.top_edges}
        drugAName={currentPrediction.drug_a_name}
        drugBName={currentPrediction.drug_b_name}
        explanationText={currentPrediction.explanation_text}
        onSelectEntity={setSelectedEntity}
      />

      {/* 4. Explanation Verification & Graph Faithfulness (Necessity & Sufficiency) */}
      <FaithfulnessCard prediction={currentPrediction} />

      {/* 5. Supporting Literature & External Validation */}
      <LiteratureSection
        citations={currentPrediction.supporting_literature}
        literature={currentPrediction.literature}
        drugAName={currentPrediction.drug_a_name}
        drugBName={currentPrediction.drug_b_name}
      />

      {/* Detail Inspector Modal when entity is clicked */}
      <NodeDetailModal
        entity={selectedEntity}
        onClose={() => setSelectedEntity(null)}
      />

      {/* Recent History Drawer */}
      {recentPredictions.length > 1 && (
        <div className="bg-[#FFFFFF] border border-[#E5E5E0] rounded-lg p-5 shadow-xs">
          <div className="flex items-center gap-2 mb-3">
            <History className="w-4 h-4 text-[#64748B]" />
            <h4 className="text-xs font-semibold text-[#0F172A] uppercase tracking-wider">
              Recent Session Evaluations ({recentPredictions.length})
            </h4>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-2.5">
            {recentPredictions.map((p, idx) => (
              <button
                key={`${p.drug_a}_${p.drug_b}_${p.cell_line}_${idx}`}
                type="button"
                onClick={() => setCurrentPrediction(p)}
                className={`p-2.5 rounded border text-left transition-all ${
                  p === currentPrediction
                    ? 'bg-[#F0FDFA] border-[#0D9488]'
                    : 'bg-[#F8FAFC] border-[#E2E8F0] hover:border-[#CBD5E1]'
                }`}
              >
                <div className="font-semibold text-xs text-[#0F172A] truncate">
                  {p.drug_a_name} × {p.drug_b_name}
                </div>
                <div className="flex items-center justify-between text-[10px] font-mono text-[#64748B] mt-1">
                  <span>{p.cell_line}</span>
                  <span className="uppercase font-bold text-[#0D9488]">
                    {p.predicted_class}
                  </span>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
