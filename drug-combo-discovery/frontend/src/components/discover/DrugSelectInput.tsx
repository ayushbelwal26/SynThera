import React, { useState, useRef, useEffect, useMemo } from "react";
import { X, Search, ChevronDown, Check } from "lucide-react";
import type { Drug } from "../../types/api";

interface DrugSelectInputProps {
  label: string;
  selectedDrug: Drug | null;
  onSelect: (drug: Drug | null) => void;
  drugs: Drug[];
  placeholder?: string;
  disabled?: boolean;
}

const COMMON_BENCHMARK_DRUG_IDS = new Set([
  "DB00853", // Temozolomide
  "DB00531", // Cyclophosphamide
  "DB09330", // Osimertinib
  "DB08865", // Crizotinib
  "DB00997", // Doxorubicin
  "DB00515", // Cisplatin
  "DB01204", // Paclitaxel
  "DB00530", // Erlotinib
  "DB01259", // Lapatinib
  "DB00188", // Bortezomib
  "DB01030", // Topotecan
  "DB03496", // Alvocidib
  "DB01168", // Procarbazine
  "DB00441", // Gemcitabine
  "DB00544", // Fluorouracil
  "DB09074", // Olaparib
]);

// Resilient fallback preset if backend is still establishing initial connection
const FALLBACK_BENCHMARK_DRUGS: Drug[] = [
  { id: "DB00853", name: "Temozolomide" },
  { id: "DB00531", name: "Cyclophosphamide" },
  { id: "DB09330", name: "Osimertinib" },
  { id: "DB08865", name: "Crizotinib" },
  { id: "DB00997", name: "Doxorubicin" },
  { id: "DB00515", name: "Cisplatin" },
  { id: "DB01204", name: "Paclitaxel" },
  { id: "DB00530", name: "Erlotinib" },
  { id: "DB01259", name: "Lapatinib" },
  { id: "DB00188", name: "Bortezomib" },
  { id: "DB01030", name: "Topotecan" },
  { id: "DB03496", name: "Alvocidib" },
  { id: "DB01168", name: "Procarbazine" },
  { id: "DB00441", name: "Gemcitabine" },
  { id: "DB00544", name: "Fluorouracil" },
  { id: "DB09074", name: "Olaparib" },
];

export const DrugSelectInput: React.FC<DrugSelectInputProps> = ({
  label,
  selectedDrug,
  onSelect,
  drugs,
  placeholder = "Search name or DrugBank ID…",
  disabled = false,
}) => {
  const [mode, setMode] = useState<"search" | "dropdown">("search");
  const [query, setQuery] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const [visibleCount, setVisibleCount] = useState(100);
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Close floating dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Use provided drugs or fallback if catalog is loading
  const effectiveDrugs = useMemo(() => {
    if (drugs && drugs.length > 0) return drugs;
    return FALLBACK_BENCHMARK_DRUGS;
  }, [drugs]);

  // Sort ALL drugs alphabetically A-Z
  const sortedDrugs = useMemo(() => {
    return [...effectiveDrugs].sort((a, b) => a.name.localeCompare(b.name));
  }, [effectiveDrugs]);

  // Extract curated benchmark drugs for quick one-click selection
  const benchmarkDrugs = useMemo(() => {
    return sortedDrugs.filter((d) =>
      COMMON_BENCHMARK_DRUG_IDS.has(d.id.toUpperCase()),
    );
  }, [sortedDrugs]);

  // Search filter across ALL drugs in dataset
  const filteredAll = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return sortedDrugs;
    return sortedDrugs.filter(
      (d) =>
        d.name.toLowerCase().includes(q) || d.id.toLowerCase().includes(q),
    );
  }, [query, sortedDrugs]);

  // Reset pagination window when query changes
  useEffect(() => {
    setVisibleCount(100);
  }, [query]);

  // Slice for responsive DOM rendering
  const displayedDrugs = useMemo(() => {
    return filteredAll.slice(0, visibleCount);
  }, [filteredAll, visibleCount]);

  const handleSelect = (drug: Drug) => {
    onSelect(drug);
    setQuery("");
    setIsOpen(false);
  };

  const handleClear = (e?: React.MouseEvent) => {
    e?.stopPropagation();
    onSelect(null);
    setQuery("");
    if (mode === "search") {
      inputRef.current?.focus();
    }
  };

  // Infinite scroll loader for the floating search dropdown
  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const { scrollTop, scrollHeight, clientHeight } = e.currentTarget;
    if (scrollHeight - scrollTop <= clientHeight + 150) {
      if (visibleCount < filteredAll.length) {
        setVisibleCount((prev) => Math.min(prev + 100, filteredAll.length));
      }
    }
  };

  return (
    <div className="relative" ref={containerRef}>
      {/* Header with Mode Toggle: Search vs Dropdown */}
      <div className="flex items-center justify-between mb-1.5">
        <label className="bench-label">{label}</label>
        <div className="flex items-center gap-1.5">
          {selectedDrug && (
            <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-[#00D6A0]/15 text-[#00D6A0] font-semibold border border-[#00D6A0]/30 flex items-center gap-1">
              <Check size={10} />
              SELECTED
            </span>
          )}
          <div className="flex items-center rounded-md bg-[#091218] p-0.5 border border-[#20343C]">
            <button
              type="button"
              onClick={() => setMode("search")}
              title="Search by typing or autocomplete"
              className={`flex items-center gap-1 px-2 py-0.5 rounded text-[10.5px] font-mono transition-colors cursor-pointer ${
                mode === "search"
                  ? "bg-[#00D6A0] text-[#05090D] font-bold shadow-sm"
                  : "text-[#94A5A6] hover:text-[#F1F5F2]"
              }`}
            >
              <Search size={11} />
              Search
            </button>
            <button
              type="button"
              onClick={() => setMode("dropdown")}
              title="Select from full dataset dropdown"
              className={`flex items-center gap-1 px-2 py-0.5 rounded text-[10.5px] font-mono transition-colors cursor-pointer ${
                mode === "dropdown"
                  ? "bg-[#00D6A0] text-[#05090D] font-bold shadow-sm"
                  : "text-[#94A5A6] hover:text-[#F1F5F2]"
              }`}
            >
              <ChevronDown size={12} />
              Dropdown
            </button>
          </div>
        </div>
      </div>

      {mode === "dropdown" ? (
        /* Explicit Native Select Dropdown Mode (All 7,946 Dataset Drugs) */
        <div className="relative">
          <select
            disabled={disabled}
            value={selectedDrug?.id || ""}
            onChange={(e) => {
              const val = e.target.value;
              if (!val) {
                onSelect(null);
                return;
              }
              const matched = sortedDrugs.find((d) => d.id === val);
              if (matched) handleSelect(matched);
            }}
            className="bench-input appearance-none cursor-pointer pr-8 font-mono text-[13px] bg-[#091218] border border-[#20343C] text-[#F1F5F2] focus:border-[#00D6A0] hover:border-[#00D6A0]/40 transition-colors"
          >
            <option value="" disabled className="text-[#60747A]">
              -- Select drug ({sortedDrugs.length} compounds in dataset) --
            </option>

            {benchmarkDrugs.length > 0 && (
              <optgroup
                label="⭐ Curated Benchmark Compounds (Quick Presets)"
                className="bg-[#0B141A] text-[#00D6A0] font-bold"
              >
                {benchmarkDrugs.map((d) => (
                  <option
                    key={`preset-${d.id}`}
                    value={d.id}
                    className="bg-[#091218] text-[#F1F5F2] font-normal"
                  >
                    {d.name} ({d.id})
                  </option>
                ))}
              </optgroup>
            )}

            <optgroup
              label={`📋 All Dataset Compounds (${sortedDrugs.length} Compounds A–Z)`}
              className="bg-[#0B141A] text-[#35C9D5] font-bold"
            >
              {sortedDrugs.map((d) => (
                <option
                  key={`all-${d.id}`}
                  value={d.id}
                  className="bg-[#091218] text-[#F1F5F2] font-normal"
                >
                  {d.name} ({d.id})
                </option>
              ))}
            </optgroup>
          </select>
          <div className="absolute right-2.5 top-1/2 -translate-y-1/2 flex items-center gap-1.5 pointer-events-none">
            {selectedDrug && (
              <button
                type="button"
                onClick={handleClear}
                className="pointer-events-auto p-0.5 text-[#94A5A6] hover:text-[#E05260] transition-colors cursor-pointer"
                title="Clear selection"
              >
                <X size={13} />
              </button>
            )}
            <ChevronDown className="w-4 h-4 text-[#60747A]" />
          </div>
        </div>
      ) : selectedDrug ? (
        /* Selected Drug Chip (Search Mode) */
        <div className="flex items-center justify-between border border-[#00D6A0]/50 py-2.5 px-3 bg-[#00D6A0]/10 rounded-lg transition-colors">
          <div className="min-w-0 flex items-baseline gap-2">
            <span className="text-[14px] font-medium text-[#F1F5F2] truncate">
              {selectedDrug.name}
            </span>
            <span className="shrink-0 text-[#00D6A0] font-mono text-[11px] font-semibold">
              {selectedDrug.id}
            </span>
          </div>
          {!disabled && (
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleClear}
                className="text-[11px] font-mono text-[#94A5A6] hover:text-[#00D6A0] px-1.5 py-0.5 rounded hover:bg-[#00D6A0]/10 transition-colors cursor-pointer"
                title="Change compound"
              >
                Change
              </button>
              <button
                type="button"
                onClick={handleClear}
                className="text-[#94A5A6] hover:text-[#E05260] p-1 rounded hover:bg-[#E05260]/10 transition-colors cursor-pointer"
                title="Clear compound"
              >
                <X size={14} />
              </button>
            </div>
          )}
        </div>
      ) : (
        /* Search Autocomplete Mode with Clickable Dropdown Trigger */
        <div className="relative">
          <input
            ref={inputRef}
            type="text"
            value={query}
            disabled={disabled}
            onChange={(e) => {
              setQuery(e.target.value);
              setIsOpen(true);
            }}
            onFocus={() => setIsOpen(true)}
            placeholder={placeholder}
            className="bench-input pr-16 bg-[#091218] border border-[#20343C] text-[#F1F5F2] placeholder-[#60747A] focus:border-[#00D6A0]"
          />
          <div className="absolute right-1.5 top-1/2 -translate-y-1/2 flex items-center gap-1">
            {query && (
              <button
                type="button"
                onClick={() => setQuery("")}
                className="p-1 rounded text-[#94A5A6] hover:text-[#E05260] transition-colors cursor-pointer"
                title="Clear query"
              >
                <X size={13} />
              </button>
            )}
            <button
              type="button"
              onClick={() => setIsOpen((prev) => !prev)}
              className="p-1 rounded text-[#94A5A6] hover:text-[#00D6A0] transition-colors cursor-pointer"
              title="Toggle dropdown list"
            >
              <ChevronDown
                size={15}
                className={`transition-transform duration-200 ${isOpen ? "rotate-180 text-[#00D6A0]" : ""}`}
              />
            </button>
            <Search size={14} className="text-[#60747A] pointer-events-none mr-1 opacity-70" />
          </div>
        </div>
      )}

      {/* Search Autocomplete Floating Dropdown Menu (All 7,946 Dataset Drugs) */}
      {isOpen && !selectedDrug && mode === "search" && (
        <div
          onScroll={handleScroll}
          className="absolute z-50 mt-1 w-full bg-[#091218]/95 border border-[#20343C] shadow-2xl rounded-lg max-h-72 overflow-y-auto backdrop-blur-md"
        >
          {/* Header count indicator */}
          <div className="px-3 py-1.5 border-b border-[#20343C]/80 bg-[#0B141A]/90 flex items-center justify-between text-[10.5px] font-mono text-[#94A5A6] sticky top-0 z-10">
            <span>
              Showing {displayedDrugs.length} of {filteredAll.length} dataset compounds
            </span>
            {filteredAll.length > displayedDrugs.length && (
              <span className="text-[#00D6A0]">Scroll down for more</span>
            )}
          </div>

          {/* Quick Benchmark Suggestions if no query typed yet */}
          {!query.trim() && benchmarkDrugs.length > 0 && (
            <div className="p-2 border-b border-[#20343C]/80 bg-[#0B141A]/60">
              <span className="text-[10px] font-mono uppercase tracking-wider text-[#60747A] block mb-1.5 px-1">
                ⭐ Curated Benchmarks
              </span>
              <div className="flex flex-wrap gap-1">
                {benchmarkDrugs.slice(0, 10).map((d) => (
                  <button
                    key={`quick-${d.id}`}
                    type="button"
                    onClick={() => handleSelect(d)}
                    className="px-2 py-0.5 rounded text-[11px] font-mono bg-[#101C23] border border-[#20343C] text-[#8AE8CC] hover:border-[#00D6A0] hover:bg-[#00D6A0]/10 transition-colors cursor-pointer"
                  >
                    {d.name}
                  </button>
                ))}
              </div>
            </div>
          )}

          {filteredAll.length === 0 ? (
            <div className="px-3.5 py-4 text-[12px] font-mono text-[#60747A] text-center">
              No matches found across {sortedDrugs.length} indexed compounds in PrimeKG
            </div>
          ) : (
            <ul className="divide-y divide-[#20343C]/40">
              {displayedDrugs.map((drug) => (
                <li key={drug.id}>
                  <button
                    type="button"
                    onClick={() => handleSelect(drug)}
                    className="w-full px-3.5 py-2 text-left hover:bg-[#00D6A0]/10 flex items-center justify-between gap-2 transition-colors cursor-pointer group"
                  >
                    <span className="font-sans text-[13px] text-[#F1F5F2] group-hover:text-[#00D6A0] font-medium truncate">
                      {drug.name}
                    </span>
                    <span className="font-mono text-[11px] text-[#60747A] group-hover:text-[#00D6A0] shrink-0">
                      {drug.id}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}

          {/* Footer loader indicator or load more trigger */}
          {displayedDrugs.length < filteredAll.length && (
            <div className="p-2 border-t border-[#20343C]/80 text-center bg-[#0B141A]/90 sticky bottom-0">
              <button
                type="button"
                onClick={() =>
                  setVisibleCount((prev) =>
                    Math.min(prev + 200, filteredAll.length),
                  )
                }
                className="text-[11px] font-mono text-[#00D6A0] hover:underline cursor-pointer"
              >
                Load +200 more ({filteredAll.length - displayedDrugs.length} remaining)
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
