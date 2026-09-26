import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Network, Table, ArrowRight } from "lucide-react";
import { useApp } from "../services/AppContext";
import { PredictionHeader } from "../components/analysis/PredictionHeader";
import { ProbabilityVector } from "../components/analysis/ProbabilityVector";
import { GraphEvidenceTable } from "../components/analysis/GraphEvidenceTable";
import { PathwayGraph } from "../components/analysis/PathwayGraph";
import { NodeDetailModal } from "../components/analysis/NodeDetailModal";
import { FaithfulnessCard } from "../components/analysis/FaithfulnessCard";
import { LiteratureSection } from "../components/analysis/LiteratureSection";
import { AnalysisChatPanel } from "../components/analysis/AnalysisChatPanel";
import { ToxicityCard } from "../components/analysis/ToxicityCard";
import { BENCHMARKS } from "../components/discover/BenchmarkPresets";
import { predictCombination } from "../services/api";
import { LoadingStages } from "../components/common/LoadingStages";

function Section({
  num,
  title,
  blurb,
  children,
  emphasis = false,
}: {
  num: string;
  title: string;
  blurb: string;
  children: React.ReactNode;
  emphasis?: boolean;
}) {
  return (
    <section
      className={`bench-section grid grid-cols-1 lg:grid-cols-12 gap-5 ${
        emphasis ? "pt-6 pb-6" : ""
      }`}
    >
      <div className="lg:col-span-3">
        <span className="meta-text">{num}</span>
        <h3 className="section-title mt-0.5">{title}</h3>
        <p className="mt-1.5 text-[12px] text-[#6B746C] leading-snug max-w-[16rem]">
          {blurb}
        </p>
      </div>
      <div className="lg:col-span-9">{children}</div>
    </section>
  );
}

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
  const [graphViewMode, setGraphViewMode] = useState<"graph" | "table">("graph");

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
          title="Loading reference pair"
          subtitle="Checkpoint inference and PrimeKG attribution"
        />
      </div>
    );
  }

  if (!currentPrediction) {
    return (
      <div className="max-w-xl py-6">
        <p className="page-kicker">Result inspector</p>
        <h2 className="page-title">No active pair record</h2>
        <p className="page-lede mb-4">
          Score a pair on the Bench, or load a reference case below.
        </p>
        <button
          type="button"
          onClick={() => navigate("/discover")}
          className="bench-btn mb-5"
        >
          Open bench
        </button>
        <div className="border-t border-[#CFC9BC] pt-3">
          <span className="bench-label block mb-2">Quick-load reference</span>
          <div className="divide-y divide-[#CFC9BC] border-y border-[#CFC9BC]">
            {BENCHMARKS.map((bm, idx) => (
              <button
                key={bm.id}
                type="button"
                onClick={() => handleQuickLoadBenchmark(idx)}
                className="w-full text-left py-2 flex justify-between gap-3 hover:bg-[#E8EDE0]/40"
              >
                <span className="font-serif text-[14px]">
                  {bm.drugA.name} + {bm.drugB.name}
                </span>
                <span className="id-text">{bm.cellLine}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-0 min-h-[calc(100vh-8rem)]">
      <div className="flex-1 min-w-0 space-y-0 pb-10">
        <PredictionHeader prediction={currentPrediction} />

        <Section
          num="3.1"
          title="Prediction"
          blurb="Calibrated class probabilities and multi-objective V(pair)."
          emphasis
        >
          <ProbabilityVector prediction={currentPrediction} />
        </Section>

        <Section
          num="3.2"
          title="Graph evidence & interaction map"
          blurb="Attributed PrimeKG subgraph driving the synergy prediction, showing drug-target binding, pathway convergence, and disease connections."
        >
          {/* View Mode Toggle Header */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4 pb-3 border-b border-[#CFC9BC]">
            <div className="flex items-center gap-1 bg-[#E8EDE0]/70 p-1 border border-[#CFC9BC]">
              <button
                type="button"
                onClick={() => setGraphViewMode("graph")}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium transition-colors ${
                  graphViewMode === "graph"
                    ? "bg-[#1A535C] text-white shadow-sm"
                    : "text-[#4A524C] hover:text-[#1A1F1C]"
                }`}
              >
                <Network className="w-3.5 h-3.5" />
                <span>Interactive Network Graph</span>
              </button>
              <button
                type="button"
                onClick={() => setGraphViewMode("table")}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium transition-colors ${
                  graphViewMode === "table"
                    ? "bg-[#1A535C] text-white shadow-sm"
                    : "text-[#4A524C] hover:text-[#1A1F1C]"
                }`}
              >
                <Table className="w-3.5 h-3.5" />
                <span>Attribution Edge Table</span>
              </button>
            </div>

            <div className="flex items-center gap-3">
              <span className="text-[12px] text-[#6B746C] font-mono">
                {(currentPrediction.top_edges || []).length} attributed edges
              </span>
              <button
                type="button"
                onClick={() => navigate("/graph")}
                className="text-[12px] text-[#1A535C] hover:underline flex items-center gap-1 font-medium"
              >
                <span>Full Graph Explorer</span>
                <ArrowRight className="w-3 h-3" />
              </button>
            </div>
          </div>

          {graphViewMode === "graph" ? (
            <div className="bench-panel-flush overflow-hidden bg-[#FFFEFB] border border-[#CFC9BC]">
              <PathwayGraph
                topEdges={currentPrediction.top_edges || []}
                drugAName={currentPrediction.drug_a_name}
                drugBName={currentPrediction.drug_b_name}
                explanationText={currentPrediction.explanation_text}
                onSelectEntity={setSelectedEntity}
              />
            </div>
          ) : (
            <GraphEvidenceTable
              edges={currentPrediction.top_edges || []}
              explanationText={currentPrediction.explanation_text}
            />
          )}
        </Section>

        <Section
          num="3.3"
          title="Faithfulness"
          blurb="Sufficiency and necessity via in-silico edge ablation."
        >
          <FaithfulnessCard prediction={currentPrediction} />
        </Section>

        {currentPrediction.ranking && (
          <Section
            num="3.3b"
            title="Toxicity & ranking"
            blurb="DDI, side-effect overlap, and composite value function terms."
          >
            <ToxicityCard prediction={currentPrediction} />
          </Section>
        )}

        <Section
          num="3.4"
          title="Literature"
          blurb="PubMed records matched to retained edges and pair context."
        >
          <LiteratureSection
            citations={currentPrediction.supporting_literature}
            literature={currentPrediction.literature}
            drugAName={currentPrediction.drug_a_name}
            drugBName={currentPrediction.drug_b_name}
          />
        </Section>

        <Section
          num="3.5"
          title="Ask this record"
          blurb="Natural-language questions grounded in this prediction."
        >
          <button
            type="button"
            onClick={() => setChatOpen(true)}
            className="w-full flex items-center justify-between border border-[#CFC9BC] bg-[#FFFEF8] px-4 py-3 group hover:border-[#1A535C]"
          >
            <span className="text-[13px] text-[#4A524C] group-hover:text-[#1A1F1C]">
              Ask about mechanism, literature, or ranking for this pair
            </span>
            <span className="bench-btn !py-1.5 !px-3 text-[12px]">Ask</span>
          </button>
        </Section>

        {recentPredictions.length > 1 && (
          <section className="bench-section">
            <span className="bench-label block mb-3">
              Recent records · {recentPredictions.length}
            </span>
            <div className="divide-y divide-[#CFC9BC] border-y border-[#CFC9BC]">
              {recentPredictions.map((p, idx) => (
                <button
                  key={`${p.drug_a}_${p.drug_b}_${p.cell_line}_${idx}`}
                  type="button"
                  onClick={() => setCurrentPrediction(p)}
                  className={`w-full text-left py-2.5 flex justify-between gap-3 ${
                    p === currentPrediction ? "bg-[#E8EDE0]/50" : ""
                  }`}
                >
                  <span className="font-serif text-[14px]">
                    {p.drug_a_name} + {p.drug_b_name}
                  </span>
                  <span className="font-mono text-[10px] text-[#6B746C]">
                    {p.predicted_class}
                  </span>
                </button>
              ))}
            </div>
          </section>
        )}

        <NodeDetailModal
          entity={selectedEntity}
          onClose={() => setSelectedEntity(null)}
        />
      </div>

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
