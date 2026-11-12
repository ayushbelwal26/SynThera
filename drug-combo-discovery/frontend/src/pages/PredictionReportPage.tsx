import React, { useState, useEffect } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { useApp } from "../services/AppContext";
import { predictCombination } from "../services/api";
import type { PredictionResult } from "../types/api";
import { PathwayGraph } from "../components/analysis/PathwayGraph";
import { GraphEvidenceTable } from "../components/analysis/GraphEvidenceTable";
import { FaithfulnessCard } from "../components/analysis/FaithfulnessCard";
import { ToxicityCard } from "../components/analysis/ToxicityCard";
import { LiteratureSection } from "../components/analysis/LiteratureSection";
import { AnalysisChatPanel } from "../components/analysis/AnalysisChatPanel";
import {
  FileText,
  Printer,
  ArrowLeft,
  Sparkles,
  Network,
  Table,
} from "lucide-react";

export const PredictionReportPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { currentPrediction, setCurrentPrediction, addRecentPrediction } = useApp();

  const [isLoading, setIsLoading] = useState(false);
  const [report, setReport] = useState<PredictionResult | null>(currentPrediction);
  const [viewMode, setViewMode] = useState<"graph" | "table">("graph");
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [chatWidth, setChatWidth] = useState(380);

  useEffect(() => {
    if (
      id &&
      (!currentPrediction ||
        `${currentPrediction.drug_a}_${currentPrediction.drug_b}_${currentPrediction.cell_line}` !==
          id)
    ) {
      const parts = id.split("_");
      if (parts.length >= 3) {
        const [drugA, drugB, cellLine] = parts;
        setIsLoading(true);
        predictCombination({
          drug_a: drugA,
          drug_b: drugB,
          cell_line: cellLine,
        })
          .then((res) => {
            setReport(res);
            setCurrentPrediction(res);
            addRecentPrediction(res);
            setIsLoading(false);
          })
          .catch((err) => {
            console.error("Failed to load prediction report:", err);
            setIsLoading(false);
          });
      }
    } else if (currentPrediction) {
      setReport(currentPrediction);
    }
  }, [id, currentPrediction]);

  const handlePrint = () => {
    window.print();
  };

  if (isLoading) {
    return (
      <div className="py-16 text-center space-y-4">
        <div className="w-8 h-8 border-2 border-[#00D6A0] border-t-transparent rounded-full animate-spin mx-auto" />
        <p className="text-[14px] text-[#94A5A6] font-mono">
          Assembling deep biological report & PrimeKG attribution paths...
        </p>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="st-panel p-12 text-center space-y-4 max-w-lg mx-auto my-8">
        <FileText size={36} className="mx-auto text-[#60747A]" />
        <h3 className="text-[20px] font-serif text-[#F1F5F2]">
          Prediction Report Not Found
        </h3>
        <p className="text-[13px] text-[#94A5A6]">
          No combination record is currently loaded. Please evaluate a pair on the Bench first.
        </p>
        <Link to="/bench" className="st-btn-primary inline-flex">
          <ArrowLeft size={14} />
          <span>Return to Bench</span>
        </Link>
      </div>
    );
  }

  const pSyn = report.p_synergy ?? report.ranking?.p_synergy ?? report.score ?? 0;
  const pAdd = report.p_additive ?? 0;
  const pAnt = report.p_antagonism ?? 0;
  const vScore = report.v_score ?? report.ranking?.v_score ?? report.score ?? 0;

  return (
    <div className="space-y-10 pb-12">
      {/* ── Top Bar ── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#20343C] pb-4 print:hidden">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => navigate("/bench")}
            className="st-btn-ghost text-xs"
          >
            <ArrowLeft size={14} />
            <span>Return to Bench</span>
          </button>
          <span className="font-mono text-[11px] text-[#60747A]">
            Report ID: {report.drug_a}_{report.drug_b}_{report.cell_line}
          </span>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={handlePrint}
            className="st-btn-ghost text-xs"
          >
            <Printer size={14} />
            <span>Print Report</span>
          </button>
          <button
            type="button"
            onClick={() => setIsChatOpen(true)}
            className="st-btn-primary text-xs"
          >
            <Sparkles size={14} />
            <span>Interactive Assistant</span>
          </button>
        </div>
      </div>

      {/* ── Heading ── */}
      <div className="border-b border-[#20343C] pb-6 space-y-2 relative overflow-hidden">
        <div className="flex items-center gap-2 font-mono text-[11px] text-[#00D6A0] uppercase tracking-wider">
          <span>SynThera In-Silico Oncology Evaluation</span>
          <span>•</span>
          <span className="text-[#94A5A6]">Attribution & Evidence Profile</span>
        </div>
        <h1 className="editorial-title text-[32px] text-[#F1F5F2]">
          {report.drug_a_name} + {report.drug_b_name}
        </h1>
        <div className="flex flex-wrap items-center gap-4 text-[13px] font-mono text-[#94A5A6]">
          <span>Cancer Cell Line: <strong className="text-[#F1F5F2]">{report.cell_line}</strong></span>
          <span>•</span>
          <span>Compounds: {report.drug_a} & {report.drug_b}</span>
          <span>•</span>
          <span>Date: {new Date().toLocaleDateString()}</span>
        </div>
      </div>

      {/* ── 1. Classification & Probabilities ── */}
      <section className="st-panel p-7 space-y-5">
        <div className="flex items-center justify-between border-b border-[#20343C] pb-3">
          <h3 className="text-[18px] font-serif text-[#F1F5F2]">
            1. Calibrated Interaction Classification
          </h3>
          <span className="font-mono text-[12px] px-3 py-1 rounded-full bg-[#14242B] text-[#00D6A0] border border-[#00D6A0]/40 font-semibold uppercase">
            {report.predicted_class}
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-center font-mono">
          <div className="p-4 rounded-xl bg-[#091218] border border-[#20343C]">
            <span className="text-[10px] text-[#60747A] uppercase block">Synergy Probability</span>
            <span className="text-[22px] font-bold text-[#00D6A0] mt-1 block">
              {(pSyn * 100).toFixed(1)}%
            </span>
          </div>
          <div className="p-4 rounded-xl bg-[#091218] border border-[#20343C]">
            <span className="text-[10px] text-[#60747A] uppercase block">Additive Probability</span>
            <span className="text-[22px] font-bold text-[#C7A76A] mt-1 block">
              {(pAdd * 100).toFixed(1)}%
            </span>
          </div>
          <div className="p-4 rounded-xl bg-[#091218] border border-[#20343C]">
            <span className="text-[10px] text-[#60747A] uppercase block">Antagonism Probability</span>
            <span className="text-[22px] font-bold text-[#E05260] mt-1 block">
              {(pAnt * 100).toFixed(1)}%
            </span>
          </div>
          <div className="p-4 rounded-xl bg-[#091218] border border-[#20343C]">
            <span className="text-[10px] text-[#60747A] uppercase block">Multi-Objective V(pair)</span>
            <span className="text-[22px] font-bold text-[#35C9D5] mt-1 block">
              {Number(vScore).toFixed(3)}
            </span>
          </div>
        </div>

        {report.explanation_text && (
          <div className="p-4 rounded-xl bg-[#091218] border border-[#20343C] space-y-1">
            <span className="text-[10.5px] font-mono uppercase text-[#00D6A0] block">
              Mechanistic Attribution Summary
            </span>
            <p className="text-[13.5px] text-[#94A5A6] leading-relaxed">
              {report.explanation_text}
            </p>
          </div>
        )}
      </section>

      {/* ── 2. Biological Knowledge Graph Excerpt ── */}
      <section className="st-panel p-7 space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#20343C] pb-3">
          <div>
            <h3 className="text-[18px] font-serif text-[#F1F5F2]">
              2. PrimeKG Attributed Subgraph
            </h3>
            <p className="text-[12px] text-[#94A5A6]">
              Retained biological paths driving the GNN synergy classification.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setViewMode("graph")}
              className={`px-3 py-1.5 text-xs font-mono rounded-md border transition-all ${
                viewMode === "graph"
                  ? "bg-[#14242B] text-[#00D6A0] border-[#00D6A0]/50"
                  : "bg-transparent text-[#60747A] border-[#20343C]"
              }`}
            >
              <Network size={13} className="inline mr-1" />
              Graph View
            </button>
            <button
              type="button"
              onClick={() => setViewMode("table")}
              className={`px-3 py-1.5 text-xs font-mono rounded-md border transition-all ${
                viewMode === "table"
                  ? "bg-[#14242B] text-[#00D6A0] border-[#00D6A0]/50"
                  : "bg-transparent text-[#60747A] border-[#20343C]"
              }`}
            >
              <Table size={13} className="inline mr-1" />
              Edge Table
            </button>
          </div>
        </div>

        {viewMode === "graph" ? (
          <div className="border border-[#20343C] rounded-xl overflow-hidden bg-[#05090D]">
            <PathwayGraph
              topEdges={report.top_edges || []}
              drugAName={report.drug_a_name}
              drugBName={report.drug_b_name}
              explanationText={report.explanation_text}
            />
          </div>
        ) : (
          <GraphEvidenceTable
            edges={report.top_edges || []}
            explanationText={report.explanation_text}
          />
        )}
      </section>

      {/* ── 3. Faithfulness & Toxicity ── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <section className="st-panel p-6 space-y-4">
          <h3 className="text-[17px] font-serif text-[#F1F5F2] border-b border-[#20343C] pb-2">
            3. In-Silico Faithfulness Verification
          </h3>
          <FaithfulnessCard prediction={report} />
        </section>

        {report.ranking && (
          <section className="st-panel p-6 space-y-4">
            <h3 className="text-[17px] font-serif text-[#F1F5F2] border-b border-[#20343C] pb-2">
              4. Toxicity & Safety Profile
            </h3>
            <ToxicityCard prediction={report} />
          </section>
        )}
      </div>

      {/* ── 5. Supporting Literature ── */}
      <section className="st-panel p-6 space-y-4">
        <div className="border-b border-[#20343C] pb-2">
          <h3 className="text-[18px] font-serif text-[#F1F5F2]">
            5. Supporting Scientific Literature
          </h3>
          <p className="text-[12px] text-[#94A5A6]">
            Verified peer-reviewed PubMed citations matched to target nodes and phenotypic outcomes.
          </p>
        </div>
        <LiteratureSection
          citations={report.supporting_literature}
          literature={report.literature}
          drugAName={report.drug_a_name}
          drugBName={report.drug_b_name}
        />
      </section>

      {/* Interactive Tool-Calling Assistant Drawer */}
      <AnalysisChatPanel
        prediction={report}
        isOpen={isChatOpen}
        onOpenChange={setIsChatOpen}
        width={chatWidth}
        onWidthChange={setChatWidth}
      />
    </div>
  );
};
