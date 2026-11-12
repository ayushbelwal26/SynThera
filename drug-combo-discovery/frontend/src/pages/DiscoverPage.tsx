import React, { useState, useEffect, useRef } from "react";
import { Link, useSearchParams } from "react-router-dom";
import gsap from "gsap";
import { useApp } from "../services/AppContext";
import { predictCombination } from "../services/api";
import type { Drug } from "../types/api";
import { DrugSelectInput } from "../components/discover/DrugSelectInput";
import { CellLineDropdown } from "../components/discover/CellLineDropdown";
import { BENCHMARKS } from "../components/discover/BenchmarkPresets";
import type { BenchmarkPreset } from "../components/discover/BenchmarkPresets";
import { MolecularUniverse } from "../components/three/MolecularUniverse";
import {
  FlaskConical,
  TrendingUp,
  AlertTriangle,
  Minus,
  Sparkles,
  Bookmark,
  ExternalLink,
  ShieldCheck,
  Zap,
  Layers,
  ChevronRight,
} from "lucide-react";

export const BenchPage: React.FC = () => {
  const {
    drugs,
    cellLineStatus,
    setCurrentPrediction,
    addRecentPrediction,
    recentPredictions,
    currentPrediction,
  } = useApp();

  const [searchParams, setSearchParams] = useSearchParams();
  const [drugA, setDrugA] = useState<Drug | null>(null);
  const [drugB, setDrugB] = useState<Drug | null>(null);
  const [cellLine, setCellLine] = useState<string>("T98G");
  const [diseaseContext, setDiseaseContext] = useState<string>("");

  const [isLoading, setIsLoading] = useState(false);
  const [loadingStage, setLoadingStage] = useState(0);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Pre-select Drug A if navigated from Command Palette (?drug=DB...)
  useEffect(() => {
    const drugParam = searchParams.get("drug");
    if (drugParam && drugs.length > 0) {
      const matched = drugs.find(
        (d) =>
          d.id.toLowerCase() === drugParam.toLowerCase() ||
          d.name.toLowerCase() === drugParam.toLowerCase(),
      );
      if (matched) {
        setDrugA(matched);
        setSearchParams({}, { replace: true });
      }
    }
  }, [searchParams, drugs, setSearchParams]);

  // GSAP animation refs
  const headerRef = useRef<HTMLDivElement>(null);
  const resultCardRef = useRef<HTMLDivElement>(null);
  const probBarRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Entrance animations
    if (headerRef.current) {
      gsap.fromTo(
        headerRef.current,
        { opacity: 0, y: 15 },
        { opacity: 1, y: 0, duration: 0.6, ease: "power2.out" },
      );
    }
  }, []);

  const handleSelectPreset = (preset: BenchmarkPreset) => {
    setDrugA(preset.drugA);
    setDrugB(preset.drugB);
    setCellLine(preset.cellLine);
    setDiseaseContext(preset.indication);
    setErrorMsg(null);
  };

  const handleAnalyzePair = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!drugA || !drugB || !cellLine) {
      setErrorMsg("Select Drug A, Drug B, and a targeted oncology cell line.");
      return;
    }
    if (drugA.id === drugB.id) {
      setErrorMsg("Select two distinct pharmacological compounds.");
      return;
    }

    setIsLoading(true);
    setErrorMsg(null);
    setLoadingStage(1);

    // Multi-stage UI feedback sequence
    const t1 = setTimeout(() => setLoadingStage(2), 500);
    const t2 = setTimeout(() => setLoadingStage(3), 1000);

    try {
      const result = await predictCombination({
        drug_a: drugA.id,
        drug_b: drugB.id,
        cell_line: cellLine,
        disease: diseaseContext.trim() || undefined,
      });

      setCurrentPrediction(result);
      addRecentPrediction(result);

      // Trigger GSAP reveal on result card
      setTimeout(() => {
        if (resultCardRef.current) {
          gsap.fromTo(
            resultCardRef.current,
            { opacity: 0, scale: 0.98, y: 10 },
            { opacity: 1, scale: 1, y: 0, duration: 0.5, ease: "power2.out" },
          );
        }
      }, 50);
    } catch (err: any) {
      setErrorMsg(err.message || "Combination prediction failed.");
    } finally {
      clearTimeout(t1);
      clearTimeout(t2);
      setIsLoading(false);
      setLoadingStage(0);
    }
  };

  const activeResult = currentPrediction;

  const getClassBadge = (cls?: string) => {
    const c = (cls || "additive").toLowerCase();
    if (c === "synergy") {
      return (
        <span className="inline-flex items-center gap-1.5 font-mono text-[11px] font-semibold px-3 py-1 rounded-full bg-[#00D6A0]/10 text-[#00D6A0] border border-[#00D6A0]/30 shadow-[0_0_12px_rgba(0,214,160,0.15)]">
          <TrendingUp size={12} />
          Synergy
        </span>
      );
    }
    if (c === "antagonism") {
      return (
        <span className="inline-flex items-center gap-1.5 font-mono text-[11px] font-semibold px-3 py-1 rounded-full bg-[#E05260]/10 text-[#E05260] border border-[#E05260]/30">
          <AlertTriangle size={12} />
          Antagonism
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 font-mono text-[11px] font-semibold px-3 py-1 rounded-full bg-[#C7A76A]/10 text-[#C7A76A] border border-[#C7A76A]/30">
        <Minus size={12} />
        Additive
      </span>
    );
  };

  return (
    <div className="space-y-10 relative">
      {/* ── Page Hero & Identification ── */}
      <div ref={headerRef} className="relative z-10 flex flex-col md:flex-row md:items-end justify-between gap-6 border-b border-[#20343C] pb-6">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="section-label">01 · Drug Pair Analysis</span>
            <span className="text-[#20343C]">•</span>
            <span className="font-mono text-[11px] text-[#94A5A6]">
              PrimeKG Heterogeneous Graph Transformer
            </span>
          </div>
          <h1 className="editorial-title text-[#F1F5F2]">
            Combinatorial Synergy Bench
          </h1>
          <p className="editorial-sub max-w-2xl mt-2">
            Evaluate drug interaction mechanisms in silico. Predicts multi-target synergy probability,
            computes Integrated Gradient attributions over PrimeKG, and identifies synthetic lethality pathways.
          </p>
        </div>
      </div>

      {errorMsg && (
        <div className="p-4 rounded-xl bg-[#E05260]/10 border border-[#E05260]/30 text-[#E05260] text-[13px] flex items-center justify-between">
          <span>{errorMsg}</span>
          <button
            type="button"
            onClick={() => setErrorMsg(null)}
            className="text-[11px] font-mono underline"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* ── Main Asymmetric Workspace Layout ── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* LEFT REGION: Analysis Controls */}
        <div className="lg:col-span-5 space-y-6">
          <div className="st-panel p-6 space-y-5">
            <div className="flex items-center justify-between border-b border-[#20343C] pb-3">
              <div className="flex items-center gap-2">
                <FlaskConical size={16} className="text-[#00D6A0]" />
                <h3 className="font-medium text-[15px] text-[#F1F5F2]">
                  Pair Selection Workspace
                </h3>
              </div>
              <span className="text-[10.5px] font-mono text-[#60747A] uppercase">
                Dual Compound
              </span>
            </div>

            <form onSubmit={handleAnalyzePair} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-[11px] font-mono uppercase text-[#94A5A6] block">
                  Drug A · Primary Compound
                </label>
                <DrugSelectInput
                  label=""
                  selectedDrug={drugA}
                  onSelect={setDrugA}
                  drugs={drugs}
                  placeholder="e.g. Temozolomide, Osimertinib..."
                />
                {drugA && (
                  <div className="flex items-center justify-between text-[11px] font-mono text-[#60747A] px-1">
                    <span>ID: {drugA.id}</span>
                    <span className="text-[#00D6A0]">Catalog verified</span>
                  </div>
                )}
              </div>

              <div className="space-y-1.5">
                <label className="text-[11px] font-mono uppercase text-[#94A5A6] block">
                  Drug B · Combination Partner
                </label>
                <DrugSelectInput
                  label=""
                  selectedDrug={drugB}
                  onSelect={setDrugB}
                  drugs={drugs}
                  placeholder="e.g. Cyclophosphamide, Crizotinib..."
                />
                {drugB && (
                  <div className="flex items-center justify-between text-[11px] font-mono text-[#60747A] px-1">
                    <span>ID: {drugB.id}</span>
                    <span className="text-[#00D6A0]">Catalog verified</span>
                  </div>
                )}
              </div>

              <div className="pt-2 border-t border-[#20343C]/60 space-y-3">
                <div>
                  <label className="text-[11px] font-mono uppercase text-[#94A5A6] block mb-1">
                    Cancer Cell Line Context
                  </label>
                  <CellLineDropdown
                    status={cellLineStatus}
                    selectedCellLine={cellLine}
                    onSelect={setCellLine}
                  />
                </div>

                <div>
                  <label className="text-[11px] font-mono uppercase text-[#94A5A6] block mb-1">
                    Disease Indication Context (Optional)
                  </label>
                  <input
                    type="text"
                    value={diseaseContext}
                    onChange={(e) => setDiseaseContext(e.target.value)}
                    placeholder="e.g. glioblastoma, non-small cell lung carcinoma"
                    className="st-input"
                  />
                </div>
              </div>

              <div className="pt-3">
                <button
                  type="submit"
                  disabled={isLoading || !drugA || !drugB}
                  className="st-btn-primary w-full py-3"
                >
                  {isLoading ? (
                    <span className="flex items-center gap-2">
                      <span className="w-3.5 h-3.5 border-2 border-[#05090D] border-t-transparent rounded-full animate-spin" />
                      {loadingStage === 1
                        ? "Assembling PrimeKG Subgraph..."
                        : loadingStage === 2
                          ? "Running HGT GNN Inference..."
                          : "Computing Attributions..."}
                    </span>
                  ) : (
                    <span className="flex items-center gap-2">
                      <Zap size={15} />
                      <span>Execute GNN Prediction</span>
                    </span>
                  )}
                </button>
              </div>
            </form>
          </div>

          {/* Reference Benchmark Presets */}
          <div className="st-panel p-5 space-y-3">
            <div className="flex items-center justify-between border-b border-[#20343C] pb-2">
              <span className="font-medium text-[13.5px] text-[#F1F5F2] flex items-center gap-2">
                <Bookmark size={14} className="text-[#C7A76A]" />
                Curated Reference Benchmarks
              </span>
              <span className="text-[10px] font-mono text-[#60747A]">DrugComb</span>
            </div>
            <p className="text-[12px] text-[#94A5A6]">
              Pre-validated clinical combinations with observed wet-lab outcomes:
            </p>
            <div className="divide-y divide-[#20343C]/40">
              {BENCHMARKS.map((preset) => (
                <button
                  key={preset.id}
                  type="button"
                  onClick={() => handleSelectPreset(preset)}
                  className="w-full text-left py-2.5 px-1 hover:bg-[#14242B] rounded-lg transition-colors flex items-center justify-between gap-3 group cursor-pointer"
                >
                  <div>
                    <div className="text-[13.5px] text-[#F1F5F2] group-hover:text-[#00D6A0] transition-colors">
                      {preset.drugA.name} + {preset.drugB.name}
                    </div>
                    <div className="font-mono text-[11px] text-[#60747A] mt-0.5">
                      {preset.cellLine} • {preset.indication}
                    </div>
                  </div>
                  {getClassBadge(preset.expectedClass)}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* RIGHT REGION: Dominant Prediction Results Panel */}
        <div className="lg:col-span-7 space-y-6">
          {activeResult ? (
            <div
              ref={resultCardRef}
              className="st-panel st-panel-glow p-7 space-y-7 relative overflow-hidden"
            >
              {/* Subtle 3D background canvas in results */}
              <div className="absolute top-0 right-0 w-80 h-64 opacity-25 pointer-events-none -mr-16 -mt-16">
                <MolecularUniverse particleCount={45} />
              </div>

              {/* Result Header */}
              <div className="relative z-10 flex flex-col sm:flex-row sm:items-start justify-between gap-4 border-b border-[#20343C] pb-5">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="section-label">Prediction Outcome</span>
                    <span className="text-[#20343C]">•</span>
                    <span className="font-mono text-[11px] text-[#35C9D5]">
                      Model Inference v1.0
                    </span>
                  </div>
                  <h2 className="editorial-title text-[28px] text-[#F1F5F2] tracking-tight">
                    {activeResult.drug_a_name} + {activeResult.drug_b_name}
                  </h2>
                  <div className="flex flex-wrap items-center gap-3 font-mono text-[12px] text-[#94A5A6] mt-1.5">
                    <span>Cell Line: <strong className="text-[#F1F5F2]">{activeResult.cell_line}</strong></span>
                    <span>•</span>
                    <span>{activeResult.drug_a} / {activeResult.drug_b}</span>
                  </div>
                </div>

                <div className="sm:text-right shrink-0">
                  <div className="text-[10.5px] font-mono uppercase text-[#60747A] mb-1">
                    Classification
                  </div>
                  {getClassBadge(activeResult.predicted_class)}
                </div>
              </div>

              {/* Probability Vector Visualization */}
              <div className="relative z-10 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-[14px] text-[#F1F5F2]">
                    Calibrated Class Probabilities
                  </span>
                  <div className="text-right font-mono">
                    <span className="text-[11px] text-[#60747A] block">Multi-Objective Value V</span>
                    <span className="metric-number text-[16px] text-[#00D6A0]">
                      {Number(activeResult.v_score ?? activeResult.score ?? 0).toFixed(3)}
                    </span>
                  </div>
                </div>

                {/* Segmented Horizon Bar */}
                <div
                  ref={probBarRef}
                  className="h-3.5 w-full rounded-full overflow-hidden flex bg-[#091218] border border-[#20343C]"
                >
                  <div
                    style={{ width: `${(activeResult.p_synergy ?? 0) * 100}%` }}
                    className="bg-[#00D6A0] transition-all duration-500 shadow-[0_0_12px_rgba(0,214,160,0.4)]"
                    title={`Synergy: ${((activeResult.p_synergy ?? 0) * 100).toFixed(1)}%`}
                  />
                  <div
                    style={{ width: `${(activeResult.p_additive ?? 0) * 100}%` }}
                    className="bg-[#C7A76A] transition-all duration-500"
                    title={`Additive: ${((activeResult.p_additive ?? 0) * 100).toFixed(1)}%`}
                  />
                  <div
                    style={{ width: `${(activeResult.p_antagonism ?? 0) * 100}%` }}
                    className="bg-[#E05260] transition-all duration-500"
                    title={`Antagonism: ${((activeResult.p_antagonism ?? 0) * 100).toFixed(1)}%`}
                  />
                </div>

                {/* Metric Cards Grid */}
                <div className="grid grid-cols-3 gap-3 pt-2 font-mono">
                  <div className="p-3 rounded-lg bg-[#091218] border border-[#20343C] text-center">
                    <span className="text-[10px] text-[#60747A] uppercase block">P(Synergy)</span>
                    <span className="text-[18px] font-bold text-[#00D6A0]">
                      {((activeResult.p_synergy ?? 0) * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="p-3 rounded-lg bg-[#091218] border border-[#20343C] text-center">
                    <span className="text-[10px] text-[#60747A] uppercase block">P(Additive)</span>
                    <span className="text-[18px] font-bold text-[#C7A76A]">
                      {((activeResult.p_additive ?? 0) * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="p-3 rounded-lg bg-[#091218] border border-[#20343C] text-center">
                    <span className="text-[10px] text-[#60747A] uppercase block">P(Antagonism)</span>
                    <span className="text-[18px] font-bold text-[#E05260]">
                      {((activeResult.p_antagonism ?? 0) * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
              </div>

              {/* Mechanistic Attribution Rationale */}
              {activeResult.explanation_text && (
                <div className="p-4 rounded-xl bg-[#091218] border border-[#20343C] space-y-1 relative z-10">
                  <div className="flex items-center gap-2 text-[11px] font-mono text-[#00D6A0]">
                    <Sparkles size={12} />
                    <span>Biological Attribution Pathway</span>
                  </div>
                  <p className="text-[13.5px] text-[#94A5A6] leading-relaxed">
                    {activeResult.explanation_text}
                  </p>
                </div>
              )}

              {/* Verification & Literature Badges */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs font-mono relative z-10">
                <div className="p-3.5 rounded-lg bg-[#091218] border border-[#20343C] space-y-1">
                  <div className="flex items-center gap-1.5 text-[#00D6A0] font-semibold">
                    <ShieldCheck size={14} />
                    <span>In-Silico Faithfulness</span>
                  </div>
                  <p className="text-[11.5px] text-[#60747A]">
                    {activeResult.faithfulness?.explanation_faithful
                      ? "Sufficiency verified: Subgraph preserves predicted class under edge ablation."
                      : "Evaluated across 2-hop local PrimeKG topology."}
                  </p>
                </div>

                <div className="p-3.5 rounded-lg bg-[#091218] border border-[#20343C] space-y-1">
                  <div className="flex items-center gap-1.5 text-[#35C9D5] font-semibold">
                    <Bookmark size={14} />
                    <span>PubMed Literature</span>
                  </div>
                  <p className="text-[11.5px] text-[#60747A]">
                    {(activeResult.literature?.citations?.length ||
                      activeResult.supporting_literature?.length)
                      ? `${activeResult.literature?.citations?.length || activeResult.supporting_literature?.length} peer-reviewed clinical citations co-indexed.`
                      : "No co-occurring PubMed clinical citations indexed."}
                  </p>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="pt-2 flex flex-wrap items-center justify-between gap-3 border-t border-[#20343C] relative z-10">
                <Link
                  to={`/results/${activeResult.drug_a}_${activeResult.drug_b}_${activeResult.cell_line}`}
                  className="st-btn-primary"
                >
                  <span>Launch Deep Inspection Report</span>
                  <ExternalLink size={14} />
                </Link>

                <Link to="/literature" className="st-btn-ghost text-xs">
                  <span>Explore Matched Literature</span>
                  <ChevronRight size={13} />
                </Link>
              </div>
            </div>
          ) : (
            <div className="st-panel p-12 text-center space-y-3">
              <FlaskConical size={36} className="mx-auto text-[#60747A]" />
              <h3 className="text-[17px] font-medium text-[#F1F5F2]">
                No Active Pair Record
              </h3>
              <p className="text-[13px] text-[#94A5A6] max-w-sm mx-auto">
                Select two oncology compounds from the workbench or click any of the curated benchmark presets to inspect predictions.
              </p>
            </div>
          )}

          {/* Session History Register */}
          {recentPredictions.length > 0 && (
            <div className="st-panel p-5 space-y-3">
              <div className="flex items-center justify-between border-b border-[#20343C] pb-2">
                <span className="font-medium text-[13.5px] text-[#F1F5F2] flex items-center gap-2">
                  <Layers size={14} className="text-[#00D6A0]" />
                  Recent Session Evaluations
                </span>
                <span className="text-[10px] font-mono text-[#60747A]">
                  {recentPredictions.length} records
                </span>
              </div>
              <div className="divide-y divide-[#20343C]/40">
                {recentPredictions.map((p, idx) => (
                  <button
                    key={`${p.drug_a}_${p.drug_b}_${p.cell_line}_${idx}`}
                    type="button"
                    onClick={() => setCurrentPrediction(p)}
                    className="w-full text-left py-2.5 px-1 hover:bg-[#14242B] rounded-lg transition-colors flex items-center justify-between gap-3 group cursor-pointer"
                  >
                    <div>
                      <div className="text-[13.5px] text-[#F1F5F2] group-hover:text-[#00D6A0] transition-colors">
                        {p.drug_a_name} + {p.drug_b_name}
                      </div>
                      <div className="font-mono text-[11px] text-[#60747A] mt-0.5">
                        {p.cell_line} • P(syn): {((p.p_synergy ?? 0) * 100).toFixed(0)}%
                      </div>
                    </div>
                    {getClassBadge(p.predicted_class)}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
