import React, { useEffect, useState } from "react";
import { Outlet } from "react-router-dom";
import { OrbitalNavigation } from "../components/navigation/OrbitalNavigation";
import { CommandPalette } from "../components/navigation/CommandPalette";
import { checkHealth } from "../services/api";
import type { HealthResponse } from "../types/api";
import {
  Cpu,
  Database,
} from "lucide-react";

export const AppLayout: React.FC = () => {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [isCommandOpen, setIsCommandOpen] = useState(false);

  useEffect(() => {
    let isMounted = true;
    checkHealth()
      .then((res) => {
        if (isMounted) setHealth(res);
      })
      .catch((err) => {
        console.error("Health probe failed:", err);
      });
    return () => {
      isMounted = false;
    };
  }, []);

  // Keyboard shortcut listener for Cmd/Ctrl+K
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setIsCommandOpen((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  return (
    <div className="min-h-screen bg-[#05090D] text-[#F1F5F2] flex flex-col font-sans selection:bg-[#00D6A0]/20 selection:text-[#F1F5F2] relative">
      {/* ── Top Floating Command & Orbital Navigation Dock ── */}
      <header className="sticky top-0 z-40 w-full px-6 py-4 flex items-center justify-between gap-4 pointer-events-none">
        {/* Left: Floating Orbital Nav */}
        <div className="pointer-events-auto">
          <OrbitalNavigation onOpenCommand={() => setIsCommandOpen(true)} />
        </div>

        {/* Right: Live Environment Telemetry Capsule */}
        {(() => {
          const isEngineLive = Boolean(
            health &&
              (health.status === "ok" || health.status === "healthy") &&
              health.model_loaded !== false,
          );
          return (
            <div className="pointer-events-auto hidden md:flex items-center gap-3 bg-[#091218]/90 backdrop-blur-md border border-[#20343C] px-3.5 py-1.5 rounded-full text-[11px] font-mono shadow-xl">
              <div className="flex items-center gap-1.5">
                <span
                  className={`w-2 h-2 rounded-full ${
                    isEngineLive
                      ? "bg-[#00D6A0] shadow-[0_0_8px_rgba(0,214,160,0.6)]"
                      : "bg-[#C7A76A] animate-pulse"
                  }`}
                />
                <span className="text-[#94A5A6]">
                  {isEngineLive ? "HGT Engine Live" : "Engine Offline"}
                </span>
              </div>

              <span className="text-[#20343C]">•</span>

              <div className="flex items-center gap-1 text-[#60747A]">
                <Database size={11} className="text-[#35C9D5]" />
                <span>PrimeKG v2.1</span>
              </div>

              <span className="text-[#20343C]">•</span>

              <div className="flex items-center gap-1 text-[#60747A]">
                <Cpu size={11} className="text-[#00D6A0]" />
                <span>Cold-Split Inference</span>
              </div>
            </div>
          );
        })()}
      </header>

      {/* ── Global Command Palette Overlay ── */}
      <CommandPalette
        isOpen={isCommandOpen}
        onClose={() => setIsCommandOpen(false)}
      />

      {/* ── Main Viewport Content ── */}
      <main className="flex-1 w-full max-w-7xl mx-auto px-6 py-6 pb-20">
        <Outlet />
      </main>

      {/* ── Subtle Scientific Baseline Footer ── */}
      <footer className="w-full border-t border-[#20343C]/40 px-8 py-5 bg-[#05090D] text-[11.5px] font-mono text-[#60747A] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="text-[#94A5A6]">SynThera Computational Oncology Platform</span>
          <span>•</span>
          <span>Harvard PrimeKG Graph & DrugComb Labels</span>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-[#00D6A0]/80">Integrated Gradient Graph Attributions</span>
          <span>Non-clinical in-silico instrument</span>
        </div>
      </footer>
    </div>
  );
};
