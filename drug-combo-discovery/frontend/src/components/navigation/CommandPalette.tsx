import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useApp } from "../../services/AppContext";
import type { Drug, PredictionResult } from "../../types/api";
import {
  Search,
  FlaskConical,
  Target,
  BookOpen,
  GitFork,
  ArrowRight,
  Database,
  Layers,
  X,
} from "lucide-react";

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({
  isOpen,
  onClose,
}) => {
  const navigate = useNavigate();
  const { drugs, recentPredictions, setCurrentPrediction } = useApp();
  const [query, setQuery] = useState("");

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        if (isOpen) {
          onClose();
        } else {
          // Open triggered by parent state or keyboard event
        }
      }
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const q = query.trim().toLowerCase();

  const navigationOptions = [
    { label: "Bench — Drug Pair Analysis", path: "/bench", num: "01", icon: FlaskConical },
    { label: "Indication — Disease Discovery", path: "/indication", num: "02", icon: Target },
    { label: "Literature — PubMed Evidence", path: "/literature", num: "03", icon: BookOpen },
    { label: "Neighborhood — Knowledge Graph", path: "/neighborhood", num: "04", icon: GitFork },
  ].filter((item) => !q || item.label.toLowerCase().includes(q));

  const matchedDrugs = (drugs || [])
    .filter(
      (d: Drug) =>
        q && (d.name.toLowerCase().includes(q) || d.id.toLowerCase().includes(q)),
    )
    .slice(0, 5);

  const matchedRecent = (recentPredictions || []).filter(
    (p: PredictionResult) =>
      !q ||
      p.drug_a_name.toLowerCase().includes(q) ||
      p.drug_b_name.toLowerCase().includes(q) ||
      p.cell_line.toLowerCase().includes(q),
  );

  const handleSelectNav = (path: string) => {
    navigate(path);
    onClose();
  };

  const handleSelectPrediction = (p: PredictionResult) => {
    setCurrentPrediction(p);
    navigate(`/results/${p.drug_a}_${p.drug_b}_${p.cell_line}`);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4 bg-[#05090D]/80 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="w-full max-w-xl bg-[#101C23] border border-[#20343C] rounded-xl shadow-2xl overflow-hidden flex flex-col max-h-[75vh]">
        {/* Command Search Input */}
        <div className="flex items-center gap-3 px-4 py-3.5 border-b border-[#20343C] bg-[#0E181F]">
          <Search size={18} className="text-[#00D6A0] shrink-0" />
          <input
            type="text"
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search oncology modules, compounds, indications (Cmd+K)..."
            className="flex-1 bg-transparent text-[14px] text-[#F1F5F2] placeholder-[#60747A] outline-none font-sans"
          />
          <button
            type="button"
            onClick={onClose}
            className="p-1 text-[#60747A] hover:text-[#F1F5F2] rounded cursor-pointer"
          >
            <X size={16} />
          </button>
        </div>

        {/* Content Results */}
        <div className="overflow-y-auto p-2 space-y-3 divide-y divide-[#20343C]/40">
          {/* Navigation Items */}
          <div>
            <div className="px-3 py-1.5 text-[10px] font-mono text-[#60747A] uppercase tracking-wider">
              Research Workspaces
            </div>
            <div className="space-y-0.5">
              {navigationOptions.map((item) => {
                const Icon = item.icon;
                return (
                  <button
                    key={item.path}
                    type="button"
                    onClick={() => handleSelectNav(item.path)}
                    className="w-full text-left flex items-center justify-between px-3 py-2 rounded-lg hover:bg-[#14242B] text-[13px] text-[#F1F5F2] transition-colors cursor-pointer group"
                  >
                    <div className="flex items-center gap-2.5">
                      <Icon size={15} className="text-[#00D6A0]" />
                      <span>{item.label}</span>
                    </div>
                    <span className="font-mono text-[11px] text-[#60747A] group-hover:text-[#35C9D5]">
                      {item.num}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Matched Drugs */}
          {matchedDrugs.length > 0 && (
            <div className="pt-2">
              <div className="px-3 py-1.5 text-[10px] font-mono text-[#60747A] uppercase tracking-wider flex items-center gap-1.5">
                <Database size={11} className="text-[#35C9D5]" />
                PrimeKG Compound Catalog
              </div>
              <div className="space-y-0.5">
                {matchedDrugs.map((d: Drug) => (
                  <button
                    key={d.id}
                    type="button"
                    onClick={() => {
                      navigate(`/bench?drug=${d.id}`);
                      onClose();
                    }}
                    className="w-full text-left flex items-center justify-between px-3 py-2 rounded-lg hover:bg-[#14242B] text-[13px] text-[#F1F5F2] transition-colors cursor-pointer"
                  >
                    <span className="font-medium text-[#F1F5F2]">{d.name}</span>
                    <span className="font-mono text-[11px] text-[#60747A]">{d.id}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Recent Combinations */}
          {matchedRecent.length > 0 && (
            <div className="pt-2">
              <div className="px-3 py-1.5 text-[10px] font-mono text-[#60747A] uppercase tracking-wider flex items-center gap-1.5">
                <Layers size={11} className="text-[#00D6A0]" />
                Recent Evaluated Pairs
              </div>
              <div className="space-y-0.5">
                {matchedRecent.slice(0, 3).map((p: PredictionResult, idx: number) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => handleSelectPrediction(p)}
                    className="w-full text-left flex items-center justify-between px-3 py-2 rounded-lg hover:bg-[#14242B] text-[13px] text-[#F1F5F2] transition-colors cursor-pointer"
                  >
                    <div>
                      <span className="text-[#F1F5F2]">
                        {p.drug_a_name} + {p.drug_b_name}
                      </span>
                      <span className="font-mono text-[11px] text-[#60747A] ml-2">
                        {p.cell_line}
                      </span>
                    </div>
                    <ArrowRight size={13} className="text-[#60747A]" />
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer shortcuts */}
        <div className="px-4 py-2 border-t border-[#20343C] bg-[#0E181F] flex items-center justify-between text-[11px] font-mono text-[#60747A]">
          <div className="flex items-center gap-3">
            <span>↑↓ to navigate</span>
            <span>↵ to select</span>
          </div>
          <span>ESC to close</span>
        </div>
      </div>
    </div>
  );
};
