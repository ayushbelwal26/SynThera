import React, { useState } from "react";
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
  initialDisease?: string;
}

export const DiscoveryMode: React.FC<DiscoveryModeProps> = ({
  cellLineStatus,
  selectedCellLine,
  onSelectCellLine,
  onRunSearch,
  isLoading,
  initialDisease = "non-small cell lung carcinoma",
}) => {
  const [disease, setDisease] = useState(initialDisease);
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

  const methods: Array<"beam" | "greedy" | "mcts"> = ["beam", "greedy", "mcts"];

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-end">
        <div className="lg:col-span-5">
          <label className="bench-label block mb-1">Indication</label>
          <input
            type="text"
            value={disease}
            disabled={isLoading}
            onChange={(e) => setDisease(e.target.value)}
            placeholder="e.g. non-small cell lung carcinoma"
            className="bench-input"
            required
          />
        </div>

        <div className="lg:col-span-4">
          <label className="bench-label block mb-1">Traversal</label>
          <div className="flex border border-[#CFC9BC]">
            {methods.map((m) => (
              <button
                key={m}
                type="button"
                disabled={isLoading}
                onClick={() => setSearchMethod(m)}
                className={`flex-1 py-1.5 text-[12px] capitalize transition-colors ${
                  searchMethod === m
                    ? "bg-[#1A1F1C] text-[#F5F5ED]"
                    : "bg-transparent text-[#4A524C] hover:bg-[#E8EDE0]"
                } ${m !== "beam" ? "border-l border-[#CFC9BC]" : ""}`}
              >
                {m}
              </button>
            ))}
          </div>
        </div>

        <div className="lg:col-span-3">
          <CellLineDropdown
            status={cellLineStatus}
            selectedCellLine={selectedCellLine}
            onSelect={onSelectCellLine}
            disabled={isLoading}
          />
        </div>
      </div>

      {/* Advanced params — compact row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 border-t border-[#CFC9BC] pt-4">
        <div>
          <div className="flex justify-between mb-1">
            <span className="bench-label">Pool</span>
            <span className="font-mono text-[12px] text-[#1A1F1C]">
              {maxCandidates}
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
            className="w-full accent-[#1A535C]"
          />
        </div>
        <div>
          <div className="flex justify-between mb-1">
            <span className="bench-label">Top-K</span>
            <span className="font-mono text-[12px] text-[#1A1F1C]">{topK}</span>
          </div>
          <input
            type="range"
            min={3}
            max={20}
            step={1}
            value={topK}
            disabled={isLoading}
            onChange={(e) => setTopK(Number(e.target.value))}
            className="w-full accent-[#1A535C]"
          />
        </div>
        {searchMethod === "mcts" && (
          <>
            <div>
              <div className="flex justify-between mb-1">
                <span className="bench-label">Simulations</span>
                <span className="font-mono text-[12px] text-[#1A1F1C]">
                  {nSimulations}
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
                className="w-full accent-[#1A535C]"
              />
            </div>
            <div>
              <div className="flex justify-between mb-1">
                <span className="bench-label">UCT c</span>
                <span className="font-mono text-[12px] text-[#1A1F1C]">
                  {mctsC.toFixed(2)}
                </span>
              </div>
              <div className="flex gap-1">
                {[1.0, 1.414, 2.0].map((val) => (
                  <button
                    key={val}
                    type="button"
                    disabled={isLoading}
                    onClick={() => setMctsC(val)}
                    className={`flex-1 py-1 font-mono text-[12px] border border-[#CFC9BC] ${
                      Math.abs(mctsC - val) < 0.01
                        ? "bg-[#1A1F1C] text-[#F5F5ED] border-[#1A1F1C]"
                        : "text-[#4A524C]"
                    }`}
                  >
                    {val === 1.414 ? "√2" : val.toFixed(1)}
                  </button>
                ))}
              </div>
            </div>
          </>
        )}
      </div>

      <button type="submit" disabled={isLoading || !disease.trim()} className="bench-btn">
        {isLoading ? "Searching…" : "Run indication search"}
      </button>
    </form>
  );
};
