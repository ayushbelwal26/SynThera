import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Compass, Activity, History } from "lucide-react";
import { useApp } from "../services/AppContext";
import { PredictionHeader } from "../components/analysis/PredictionHeader";
import { ProbabilityVector } from "../components/analysis/ProbabilityVector";
import { ToxicityCard } from "../components/analysis/ToxicityCard";
import { PathwayGraph } from "../components/analysis/PathwayGraph";
import { NodeDetailModal } from "../components/analysis/NodeDetailModal";
import { FaithfulnessCard } from "../components/analysis/FaithfulnessCard";
import { LiteratureSection } from "../components/analysis/LiteratureSection";
import { AnalysisChatPanel } from "../components/analysis/AnalysisChatPanel";
import { BENCHMARKS } from "../components/discover/BenchmarkPresets";
import { predictCombination } from "../services/api";
import { LoadingStages } from "../components/common/LoadingStages";

export const AnalysisPage: React.FC = () => {
  const navigate = useNavigate();
  const {
    currentPrediction,
    setCurrentPrediction,
    recentPredictions,
    addRecentPrediction,
  } = useApp();
  const [selectedEntity, setSelectedEntity] = useState<{
    type: "node" | "edge";
    data: any;
  } | null>(null);
  const [isLoadingBenchmark, setIsLoadingBenchmark] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const [chatWidth, setChatWidth] = useState(380);

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
      console.error("Failed to load benchmark:", err);
    } finally {
      setIsLoadingBenchmark(false);
    }
  };

  if (isLoadingBenchmark) {
    return (
      <div className="py-8">
        <LoadingStages
          title="Loading Benchmark Combination"
          subtitle="Querying model checkpoint and PrimeKG attribution pathway"
        />
      </div>
    );
  }

  if (!currentPrediction) {
    return (
      <div className="max-w-2xl mx-auto py-8 text-center">
        <div className="w-14 h-14 rounded-full bg-[#EEEBE5] border border-[#E5E2DC] flex items-center justify-center mx-auto mb-4 text-[#6B746F]">
          <Activity className="w-6 h-6" />
        </div>
        <h3 className="text-2xl font-semibold text-[#1C2421] mb-2">
          Select two compounds to begin analysis.
        </h3>
        <p className="text-sm text-[#6B746F] mb-4 max-w-lg mx-auto leading-normal">
          No prediction result is currently active. Configure a drug pair in
          Discover or load a benchmark below.
        </p>

        <div className="flex justify-center gap-3 mb-5">
          <button
            type="button"
            onClick={() => navigate("/discover")}
            className="px-4 py-2.5 bg-[#2F6B5E] hover:bg-[#25564B] text-[#FFFEFB] rounded-md font-semibold text-xs flex items-center gap-2 transition-colors cursor-pointer"
          >
            <Compass className="w-4 h-4" />
            Open Discover
          </button>
        </div>

        <div className="border-t border-[#E5E2DC] pt-4 text-left">
          <span className="text-xs font-semibold text-[#5A635E] uppercase tracking-wide block mb-3">
            Quick-load reference case
          </span>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
            {BENCHMARKS.map((bm, idx) => (
              <button
                key={bm.id}
                type="button"
                onClick={() => handleQuickLoadBenchmark(idx)}
                className="p-3 bg-[#FFFEFB] border border-[#D8D5CE] hover:border-[#2F6B5E] rounded-md text-left transition-all group"
              >
                <span className="font-semibold text-xs text-[#1C2421] group-hover:text-[#2F6B5E] block">
                  {bm.name}
                </span>
                <span className="font-mono text-[10px] text-[#6B746F] mt-1 block">
                  {bm.cellLine} · {bm.expectedClass}
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-0 -mx-4 sm:-mx-6 min-h-[calc(100vh-10rem)]">
      {/* Main analysis column — shrinks when chat is open */}
      <div className="flex-1 min-w-0 px-4 sm:px-6 space-y-4 pb-5 transition-[max-width] duration-200">
        <PredictionHeader prediction={currentPrediction} />

        <ProbabilityVector prediction={currentPrediction} />
        <ToxicityCard prediction={currentPrediction} />
        <PathwayGraph
          topEdges={currentPrediction.top_edges}
          drugAName={currentPrediction.drug_a_name}
          drugBName={currentPrediction.drug_b_name}
          explanationText={currentPrediction.explanation_text}
          onSelectEntity={setSelectedEntity}
        />
        <FaithfulnessCard prediction={currentPrediction} />
        <LiteratureSection
          citations={currentPrediction.supporting_literature}
          literature={currentPrediction.literature}
          drugAName={currentPrediction.drug_a_name}
          drugBName={currentPrediction.drug_b_name}
        />

        <NodeDetailModal
          entity={selectedEntity}
          onClose={() => setSelectedEntity(null)}
        />

        {recentPredictions.length > 1 && (
          <div className="syn-card rounded-lg p-4">
            <div className="flex items-center gap-2 mb-3">
              <History className="w-4 h-4 text-[#6B746F]" />
              <h4 className="text-xs font-semibold text-[#1C2421] uppercase tracking-wide">
                Recent evaluations ({recentPredictions.length})
              </h4>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
              {recentPredictions.map((p, idx) => (
                <button
                  key={`${p.drug_a}_${p.drug_b}_${p.cell_line}_${idx}`}
                  type="button"
                  onClick={() => setCurrentPrediction(p)}
                  className={`p-2.5 rounded border text-left transition-all ${
                    p === currentPrediction
                      ? "bg-[#E8F0ED] border-[#2F6B5E]"
                      : "bg-[#F3F1EC] border-[#E5E2DC] hover:border-[#D8D5CE]"
                  }`}
                >
                  <div className="font-semibold text-xs text-[#1C2421] truncate">
                    {p.drug_a_name} × {p.drug_b_name}
                  </div>
                  <div className="flex items-center justify-between text-[10px] font-mono text-[#6B746F] mt-1">
                    <span>{p.cell_line}</span>
                    <span className="uppercase font-bold text-[#2F6B5E]">
                      {p.predicted_class}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Cursor-style right assistant panel — content reflows beside it */}
      <AnalysisChatPanel
        prediction={currentPrediction}
        isOpen={chatOpen}
        onOpenChange={setChatOpen}
        width={chatWidth}
        onWidthChange={setChatWidth}
      />
    </div>
  );
};
