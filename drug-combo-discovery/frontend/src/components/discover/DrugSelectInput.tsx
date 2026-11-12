import React, { useState, useRef, useEffect } from "react";
import { X, Search } from "lucide-react";
import type { Drug } from "../../types/api";

interface DrugSelectInputProps {
  label: string;
  selectedDrug: Drug | null;
  onSelect: (drug: Drug | null) => void;
  drugs: Drug[];
  placeholder?: string;
  disabled?: boolean;
}

export const DrugSelectInput: React.FC<DrugSelectInputProps> = ({
  label,
  selectedDrug,
  onSelect,
  drugs,
  placeholder = "Search name or DrugBank ID…",
  disabled = false,
}) => {
  const [query, setQuery] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

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

  const filtered = query.trim()
    ? drugs
        .filter(
          (d) =>
            d.name.toLowerCase().includes(query.toLowerCase()) ||
            d.id.toLowerCase().includes(query.toLowerCase()),
        )
        .slice(0, 50)
    : drugs.slice(0, 20);

  const handleSelect = (drug: Drug) => {
    onSelect(drug);
    setQuery("");
    setIsOpen(false);
  };

  const handleClear = (e: React.MouseEvent) => {
    e.stopPropagation();
    onSelect(null);
    setQuery("");
    inputRef.current?.focus();
  };

  return (
    <div className="relative" ref={containerRef}>
      <div className="flex items-center justify-between mb-1.5">
        <label className="bench-label">{label}</label>
        {selectedDrug && (
          <span className="font-mono text-[10.5px] px-1.5 py-0.2 rounded bg-[var(--color-accent-soft)] text-[var(--color-accent)] font-semibold">
            SELECTED
          </span>
        )}
      </div>

      {selectedDrug ? (
        <div className="flex items-center justify-between border-b-2 border-[var(--color-accent)] py-2 px-1 bg-[var(--color-accent-soft)]/25 rounded-t transition-colors">
          <div className="min-w-0 flex items-baseline gap-2">
            <span className="text-[14.5px] font-semibold text-[var(--color-text-primary)] truncate">
              {selectedDrug.name}
            </span>
            <span className="id-text shrink-0 text-[var(--color-accent)] font-mono font-medium">
              {selectedDrug.id}
            </span>
          </div>
          {!disabled && (
            <button
              type="button"
              onClick={handleClear}
              className="text-[var(--color-text-muted)] hover:text-[var(--color-accent)] p-1 rounded hover:bg-[var(--color-accent-soft)] transition-colors cursor-pointer"
              title="Clear compound"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      ) : (
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
            className="bench-input pr-7"
          />
          <Search className="w-3.5 h-3.5 text-[var(--color-text-muted)] absolute right-1.5 top-1/2 -translate-y-1/2 pointer-events-none opacity-60" />
        </div>
      )}

      {isOpen && !selectedDrug && (
        <div className="absolute z-50 mt-1 w-full bg-[var(--color-panel)] border border-[var(--color-rule-strong)] shadow-[0_8px_24px_rgba(0,0,0,0.25)] rounded-md max-h-60 overflow-y-auto backdrop-blur-md">
          {filtered.length === 0 ? (
            <div className="px-3.5 py-3 text-[12.5px] font-mono text-[var(--color-text-muted)]">
              No matches ({drugs.length} indexed compounds)
            </div>
          ) : (
            <ul className="divide-y divide-[var(--color-rule)]/50">
              {filtered.map((drug) => (
                <li key={drug.id}>
                  <button
                    type="button"
                    onClick={() => handleSelect(drug)}
                    className="w-full px-3.5 py-2.5 text-left hover:bg-[var(--color-accent-soft)]/60 flex items-center justify-between gap-2 transition-colors cursor-pointer group"
                  >
                    <span className="font-sans text-[13.5px] text-[var(--color-text-primary)] group-hover:text-[var(--color-accent)] font-medium truncate">
                      {drug.name}
                    </span>
                    <span className="font-mono text-[11px] text-[var(--color-text-muted)] group-hover:text-[var(--color-accent)] shrink-0">
                      {drug.id}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
};
