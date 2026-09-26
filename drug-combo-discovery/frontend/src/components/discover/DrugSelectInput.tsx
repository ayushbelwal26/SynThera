import React, { useState, useRef, useEffect } from "react";
import { X } from "lucide-react";
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
      <label className="bench-label block mb-1">{label}</label>

      {selectedDrug ? (
        <div className="flex items-center justify-between border-b border-[#CFC9BC] py-1.5">
          <div className="min-w-0 flex items-baseline gap-2">
            <span className="text-[14px] text-[#1A1F1C] truncate">
              {selectedDrug.name}
            </span>
            <span className="id-text shrink-0">
              {selectedDrug.id}
            </span>
          </div>
          {!disabled && (
            <button
              type="button"
              onClick={handleClear}
              className="text-[#6B746C] hover:text-[#1A1F1C] p-0.5"
              title="Clear"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      ) : (
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
          className="bench-input"
        />
      )}

      {isOpen && !selectedDrug && (
        <div className="absolute z-50 mt-0 w-full bg-[#F5F5ED] border border-[#CFC9BC] max-h-56 overflow-y-auto">
          {filtered.length === 0 ? (
            <div className="px-3 py-2.5 text-[13px] font-mono text-[#6B746C]">
              No matches ({drugs.length} indexed)
            </div>
          ) : (
            <ul>
              {filtered.map((drug) => (
                <li key={drug.id}>
                  <button
                    type="button"
                    onClick={() => handleSelect(drug)}
                    className="w-full px-3 py-2 text-left hover:bg-[#E8EDE0] flex items-center justify-between gap-2 border-b border-[#CFC9BC]/60 last:border-0"
                  >
                    <span className="font-mono text-[14px] text-[#1A1F1C] truncate">
                      {drug.name}
                    </span>
                    <span className="font-mono text-[12px] text-[#6B746C] shrink-0">
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
