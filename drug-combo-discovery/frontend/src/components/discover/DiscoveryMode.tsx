import React, { useState } from "react";
import type { CellLineRelevanceStatus } from "../../types/api";
import { CellLineDropdown } from "./CellLineDropdown";
import { Search, Sparkles } from "lucide-react";

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
    <form onSubmit={handleSubmit} className="space-y-5">
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-end">
        <div className="lg:col-span-5">
          <label className="bench-label block mb-1.5">
            Target Indication / Neoplasm
          </label>
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
          <label className="bench-label block mb-1.5">
            Search Traversal Method
          </label>
          <div className="flex border border-[var(--color-rule)] rounded-md overflow-hidden bg-[var(--color-surface)]">
            {methods.map((m) => (
              <button
                key={m}
                type="button"
                disabled={isLoading}
                onClick={() => setSearchMethod(m)}
                className={`flex-1 py-1.5 text-[12.5px] font-mono font-medium capitalize transition-all cursor-pointer ${
                  searchMethod === m
                    ? "bg-[var(--color-accent)] text-[#041A1E] font-bold shadow-[0_0_12px_var(--color-accent-glow)]"
                    : "bg-transparent text-[var(--color-text-secondary)] hover:bg-[var(--color-accent-soft)]/50"
                } ${m !== "beam" ? "border-l border-[var(--color-rule)]" : ""}`}
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
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-5 border-t border-[var(--color-rule)] pt-4">
        <div>
          <div className="flex justify-between mb-1.5">
            <span className="bench-label">Candidate Pool</span>
            <span className="font-mono text-[12px] font-semibold text-[var(--color-accent)]">
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
            className="w-full accent-[var(--color-accent)] cursor-pointer"
          />
        </div>
        <div>
          <div className="flex justify-between mb-1.5">
            <span className="bench-label">Top Synergies (K)</span>
            <span className="font-mono text-[12px] font-semibold text-[var(--color-accent)]">
              {topK}
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
            className="w-full accent-[var(--color-accent)] cursor-pointer"
          />
        </div>
        {searchMethod === "mcts" && (
          <>
            <div>
              <div className="flex justify-between mb-1.5">
                <span className="bench-label">MCTS Rollouts</span>
                <span className="font-mono text-[12px] font-semibold text-[var(--color-accent)]">
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
                className="w-full accent-[var(--color-accent)] cursor-pointer"
              />
            </div>
            <div>
              <div className="flex justify-between mb-1.5">
                <span className="bench-label">Exploration (c)</span>
                <span className="font-mono text-[12px] font-semibold text-[var(--color-accent)]">
                  {mctsC.toFixed(2)}
                </span>
              </div>
              <div className="flex gap-1.5">
                {[1.0, 1.414, 2.0].map((val) => (
                  <button
                    key={val}
                    type="button"
                    disabled={isLoading}
                    onClick={() => setMctsC(val)}
                    className={`flex-1 py-1 font-mono text-[11.5px] rounded border border-[var(--color-rule)] transition-colors cursor-pointer ${
                      Math.abs(mctsC - val) < 0.01
                        ? "bg-[var(--color-accent)] text-[#041A1E] font-bold border-[var(--color-accent)]"
                        : "text-[var(--color-text-secondary)] hover:bg-[var(--color-accent-soft)]"
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

      <div className="pt-2">
        <button
          type="submit"
          disabled={isLoading || !disease.trim()}
          className="bench-btn"
        >
          {isLoading ? (
            <>
              <Sparkles className="w-4 h-4 animate-spin" />
              <span>Traversing PrimeKG...</span>
            </>
          ) : (
            <>
              <Search className="w-4 h-4" />
              <span>Discover Indication Combinations</span>
            </>
          )}
        </button>
      </div>
    </form>
  );
};
