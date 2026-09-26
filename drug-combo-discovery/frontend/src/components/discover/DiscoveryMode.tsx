import React, { useState } from "react";
import { Compass, SlidersHorizontal, GitFork, Cpu } from "lucide-react";
import type { CellLineRelevanceStatus } from "../../types/api";
import { CellLineDropdown } from "./CellLineDropdown";

interface DiscoveryModeProps {
  cellLineStatus: CellLineRelevanceStatus;
  selectedCellLine: string;
  onSelectCellLine: (cl: string) => void;
  onRunSearch: (
    disease: string,
    cellLine: string,
    maxCandidates: number,
    topK: number,
    searchMethod: "beam" | "greedy" | "mcts",
    nSimulations?: number,
    mctsC?: number,
  ) => void;
  isLoading: boolean;
}

export const DiscoveryMode: React.FC<DiscoveryModeProps> = ({
  cellLineStatus,
  selectedCellLine,
  onSelectCellLine,
  onRunSearch,
  isLoading,
}) => {
  const [disease, setDisease] = useState("glioblastoma");
  const [maxCandidates, setMaxCandidates] = useState(15);
  const [topK, setTopK] = useState(5);
  const [searchMethod, setSearchMethod] = useState<"beam" | "greedy" | "mcts">(
    "beam",
  );
  const [nSimulations, setNSimulations] = useState(50);
  const [mctsC, setMctsC] = useState(1.414);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!disease.trim() || !selectedCellLine) return;
    onRunSearch(
      disease.trim(),
      selectedCellLine,
      maxCandidates,
      topK,
      searchMethod,
      nSimulations,
      mctsC,
    );
  };

  const sampleDiseases = [
    "glioblastoma",
    "breast neoplasm",
    "colorectal carcinoma",
    "ovarian cancer",
    "renal cell carcinoma",
  ];

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div>
        <label className="block text-xs font-semibold text-[#3A4D5C] uppercase tracking-wide mb-1.5">
          Target Indication / Neoplasm Name
        </label>
        <div className="relative">
          <input
            type="text"
            value={disease}
            disabled={isLoading}
            onChange={(e) => setDisease(e.target.value)}
            placeholder="e.g. glioblastoma, adenocarcinoma, breast neoplasm..."
            className="w-full px-3.5 py-2.5 bg-[#FFFFFF] border border-[#D0DCE6] focus:border-[#0D9488] focus:ring-1 focus:ring-[#0D9488] rounded-md text-sm text-[#1A2B3C] outline-none font-medium"
            required
          />
        </div>
        <div className="flex items-center gap-1.5 mt-2 flex-wrap text-xs text-[#6B7C8A]">
          <span className="text-[11px] font-medium text-[#5A6B7A]">
            Common indications:
          </span>
          {sampleDiseases.map((d) => (
            <button
              key={d}
              type="button"
              onClick={() => setDisease(d)}
              className="text-[11px] bg-[#E8F0F5] hover:bg-[#E2EAF0] px-2 py-0.5 rounded text-[#3A4D5C] transition-colors"
            >
              {d}
            </button>
          ))}
        </div>
      </div>

      <CellLineDropdown
        status={cellLineStatus}
        selectedCellLine={selectedCellLine}
        onSelect={onSelectCellLine}
        disabled={isLoading}
      />

      <div className="bg-[#EEF5F8] border border-[#E2EAF0] rounded-md p-4 space-y-4">
        <div className="flex items-center justify-between border-b border-[#E2EAF0] pb-2.5">
          <div className="flex items-center gap-2">
            <SlidersHorizontal className="w-3.5 h-3.5 text-[#6B7C8A]" />
            <span className="text-xs font-semibold text-[#3A4D5C] uppercase tracking-wide">
              Search Strategy & Algorithm
            </span>
          </div>
          <span className="text-[11px] font-mono text-[#0D9488] font-medium">
            Tier 3: MCTS + Beam + Greedy
          </span>
        </div>

        {/* Method Toggle Buttons */}
        <div>
          <label className="block text-xs font-medium text-[#5A6B7A] mb-1.5">
            Exploration Algorithm:
          </label>
          <div className="grid grid-cols-3 gap-2">
            <button
              type="button"
              disabled={isLoading}
              onClick={() => setSearchMethod("beam")}
              className={`px-3 py-2 text-xs font-semibold rounded border transition-all cursor-pointer flex flex-col items-center gap-1 ${
                searchMethod === "beam"
                  ? "bg-[#0D9488] text-[#FFFFFF] border-[#0D9488] shadow-xs"
                  : "bg-[#FFFFFF] text-[#3A4D5C] border-[#D0DCE6] hover:bg-[#E8F0F5]"
              }`}
            >
              <div className="flex items-center gap-1.5">
                <GitFork className="w-3.5 h-3.5" />
                <span>Beam Search</span>
              </div>
              <span
                className={`text-[10px] ${searchMethod === "beam" ? "text-[#CDEEEA]" : "text-[#6B7C8A]"}`}
              >
                Width B=5 (Default)
              </span>
            </button>

            <button
              type="button"
              disabled={isLoading}
              onClick={() => setSearchMethod("mcts")}
              className={`px-3 py-2 text-xs font-semibold rounded border transition-all cursor-pointer flex flex-col items-center gap-1 ${
                searchMethod === "mcts"
                  ? "bg-[#0D9488] text-[#FFFFFF] border-[#0D9488] shadow-xs"
                  : "bg-[#FFFFFF] text-[#3A4D5C] border-[#D0DCE6] hover:bg-[#E8F0F5]"
              }`}
            >
              <div className="flex items-center gap-1.5">
                <Cpu className="w-3.5 h-3.5" />
                <span>MCTS (UCT)</span>
              </div>
              <span
                className={`text-[10px] ${searchMethod === "mcts" ? "text-[#CDEEEA]" : "text-[#6B7C8A]"}`}
              >
                Depth 2 Rollouts
              </span>
            </button>

            <button
              type="button"
              disabled={isLoading}
              onClick={() => setSearchMethod("greedy")}
              className={`px-3 py-2 text-xs font-semibold rounded border transition-all cursor-pointer flex flex-col items-center gap-1 ${
                searchMethod === "greedy"
                  ? "bg-[#0D9488] text-[#FFFFFF] border-[#0D9488] shadow-xs"
                  : "bg-[#FFFFFF] text-[#3A4D5C] border-[#D0DCE6] hover:bg-[#E8F0F5]"
              }`}
            >
              <div className="flex items-center gap-1.5">
                <Compass className="w-3.5 h-3.5" />
                <span>Greedy Search</span>
              </div>
              <span
                className={`text-[10px] ${searchMethod === "greedy" ? "text-[#CDEEEA]" : "text-[#6B7C8A]"}`}
              >
                Width B=1
              </span>
            </button>
          </div>

          <p className="text-[11px] text-[#6B7C8A] mt-2 leading-normal">
            {searchMethod === "beam" && (
              <>
                Beam search expands top anchors in parallel batches, optimizing
                latency and coverage across high-priority disease targets.
              </>
            )}
            {searchMethod === "mcts" && (
              <>
                Monte Carlo Tree Search balances exploration of under-sampled
                drugs with exploitation of high-synergy anchors via UCT (c=
                {mctsC}). Cached pairs avoid redundant GNN calls.
              </>
            )}
            {searchMethod === "greedy" && (
              <>
                Greedy search expands exclusively from the single top candidate
                anchor drug, evaluating its immediate partner space.
              </>
            )}
          </p>
        </div>

        {/* MCTS Specific Controls */}
        {searchMethod === "mcts" && (
          <div className="p-3 bg-[#E6F7F5] border border-[#A5D9D4] rounded-md space-y-3">
            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-[#0B7C78] font-medium">
                  MCTS Simulation Budget:
                </span>
                <span className="font-mono font-bold text-[#0B7C78]">
                  {nSimulations} rollouts
                </span>
              </div>
              <input
                type="range"
                min={20}
                max={100}
                step={10}
                value={nSimulations}
                disabled={isLoading}
                onChange={(e) => setNSimulations(Number(e.target.value))}
                className="w-full accent-[#0D9488]"
              />
              <div className="flex justify-between text-[10px] text-[#0B7C78] opacity-80">
                <span>Fast (20)</span>
                <span>Balanced (50)</span>
                <span>Thorough (100, hard 15s cap)</span>
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-[#0B7C78] font-medium">
                  UCT Exploration Constant (c):
                </span>
                <span className="font-mono font-bold text-[#0B7C78]">
                  {mctsC.toFixed(2)}
                </span>
              </div>
              <div className="flex gap-2">
                {[1.0, 1.414, 2.0].map((val) => (
                  <button
                    key={val}
                    type="button"
                    disabled={isLoading}
                    onClick={() => setMctsC(val)}
                    className={`px-2.5 py-1 text-xs rounded border transition-colors cursor-pointer ${
                      Math.abs(mctsC - val) < 0.01
                        ? "bg-[#0D9488] text-[#FFFFFF] border-[#0D9488]"
                        : "bg-[#FFFFFF] text-[#3A4D5C] border-[#D0DCE6] hover:bg-[#E6F7F5]"
                    }`}
                  >
                    {val === 1.414 ? "1.41 (Default)" : val.toFixed(1)}
                  </button>
                ))}
              </div>
              <span className="text-[10px] text-[#0B7C78] opacity-80 mt-1 block">
                Balances exploiting high-synergy anchors vs exploring
                under-sampled drug families.
              </span>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-1">
          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-[#6B7C8A]">Candidate Pool Size:</span>
              <span className="font-mono font-semibold text-[#1A2B3C]">
                {maxCandidates} drugs
              </span>
            </div>
            <input
              type="range"
              min={5}
              max={30}
              step={5}
              value={maxCandidates}
              disabled={isLoading}
              onChange={(e) => setMaxCandidates(Number(e.target.value))}
              className="w-full accent-[#0D9488]"
            />
            <span className="text-[10px] text-[#8A9BAA]">
              Filtered therapeutic candidates (
              {(maxCandidates * (maxCandidates - 1)) / 2} max pairs)
            </span>
          </div>

          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-[#6B7C8A]">
                Explain Top-K Combinations:
              </span>
              <span className="font-mono font-semibold text-[#1A2B3C]">
                {topK} pairs
              </span>
            </div>
            <input
              type="range"
              min={3}
              max={20}
              step={1}
              value={topK}
              disabled={isLoading}
              onChange={(e) => setTopK(Number(e.target.value))}
              className="w-full accent-[#0D9488]"
            />
            <span className="text-[10px] text-[#8A9BAA]">
              Attribution explanations on top-{topK} candidates
            </span>
          </div>
        </div>
      </div>

      <button
        type="submit"
        disabled={isLoading || !disease.trim() || !selectedCellLine}
        className="w-full py-3 bg-[#0D9488] hover:bg-[#0B7C78] disabled:bg-[#8A9BAA] text-[#FFFFFF] rounded-md font-semibold text-sm flex items-center justify-center gap-2 shadow-xs transition-colors cursor-pointer"
      >
        <Compass className="w-4 h-4" />
        {isLoading
          ? searchMethod === "mcts"
            ? "Running MCTS Tree Search & Rollouts..."
            : "Searching Candidate Space..."
          : `Run ${searchMethod === "mcts" ? "MCTS Discovery" : searchMethod === "greedy" ? "Greedy Search" : "Beam Search"}`}
      </button>
    </form>
  );
};
