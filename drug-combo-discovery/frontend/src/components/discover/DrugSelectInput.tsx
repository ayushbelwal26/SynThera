import React, { useState, useRef, useEffect } from 'react';
import { Search, X, Dna } from 'lucide-react';
import type { Drug } from '../../types/api';

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
  placeholder = 'Search by compound name or DrugBank ID (e.g. DB00853)...',
  disabled = false,
}) => {
  const [query, setQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Filter top matches
  const filtered = query.trim()
    ? drugs
        .filter(
          (d) =>
            d.name.toLowerCase().includes(query.toLowerCase()) ||
            d.id.toLowerCase().includes(query.toLowerCase())
        )
        .slice(0, 50)
    : drugs.slice(0, 20);

  const handleSelect = (drug: Drug) => {
    onSelect(drug);
    setQuery('');
    setIsOpen(false);
  };

  const handleClear = (e: React.MouseEvent) => {
    e.stopPropagation();
    onSelect(null);
    setQuery('');
    if (inputRef.current) {
      inputRef.current.focus();
    }
  };

  return (
    <div className="relative" ref={containerRef}>
      <label className="block text-xs font-semibold text-[#334155] uppercase tracking-wider mb-1.5">
        {label}
      </label>

      {selectedDrug ? (
        <div className="flex items-center justify-between bg-[#FFFFFF] border border-[#CBD5E1] rounded-md px-3.5 py-2.5 shadow-xs">
          <div className="flex items-center gap-2.5 min-w-0">
            <Dna className="w-4 h-4 text-[#0D9488] shrink-0" />
            <span className="font-semibold text-sm text-[#0F172A] truncate">
              {selectedDrug.name}
            </span>
            <span className="font-mono text-[11px] bg-[#F1F5F9] text-[#475569] px-2 py-0.5 rounded border border-[#E2E8F0] shrink-0">
              {selectedDrug.id}
            </span>
          </div>
          {!disabled && (
            <button
              type="button"
              onClick={handleClear}
              className="text-[#94A3B8] hover:text-[#0F172A] p-1 rounded hover:bg-[#F1F5F9] transition-colors"
              title="Clear selection"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      ) : (
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Search className="w-4 h-4 text-[#94A3B8]" />
          </div>
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
            className="w-full pl-9 pr-8 py-2.5 bg-[#FFFFFF] border border-[#CBD5E1] focus:border-[#0D9488] focus:ring-1 focus:ring-[#0D9488] rounded-md text-sm text-[#0F172A] placeholder-[#94A3B8] outline-none transition-all"
          />
          {query && (
            <button
              type="button"
              onClick={() => setQuery('')}
              className="absolute inset-y-0 right-0 pr-2.5 flex items-center text-[#94A3B8] hover:text-[#0F172A]"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      )}

      {/* Autocomplete Dropdown */}
      {isOpen && !selectedDrug && (
        <div className="absolute z-50 mt-1 w-full bg-[#FFFFFF] border border-[#CBD5E1] rounded-md shadow-lg max-h-60 overflow-y-auto">
          {filtered.length === 0 ? (
            <div className="px-4 py-3 text-xs text-[#717784] font-mono">
              No matching compounds found in PrimeKG index ({drugs.length} total).
            </div>
          ) : (
            <ul className="divide-y divide-[#F1F5F9]">
              {filtered.map((drug) => (
                <li key={drug.id}>
                  <button
                    type="button"
                    onClick={() => handleSelect(drug)}
                    className="w-full px-3.5 py-2 text-left hover:bg-[#F8FAFC] flex items-center justify-between text-xs transition-colors"
                  >
                    <span className="font-medium text-[#1E293B] truncate mr-2">
                      {drug.name}
                    </span>
                    <span className="font-mono text-[10px] text-[#64748B] bg-[#F1F5F9] px-1.5 py-0.5 rounded shrink-0">
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
