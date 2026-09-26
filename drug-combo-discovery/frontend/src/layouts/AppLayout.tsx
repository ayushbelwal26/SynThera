import React, { useEffect, useState } from "react";
import { Outlet } from "react-router-dom";
import { Navigation } from "./Navigation";
import { checkHealth } from "../services/api";
import type { HealthResponse } from "../types/api";
import { Cpu, Activity, AlertCircle } from "lucide-react";

export const AppLayout: React.FC = () => {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    checkHealth()
      .then((res) => {
        if (isMounted) {
          setHealth(res);
          setHealthError(null);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setHealthError(err.message);
        }
      });
    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <div className="min-h-screen flex flex-col bg-[#F6F4EF] text-[#1C2421]">
      <header className="bg-[#FFFEFB] border-b border-[#E5E2DC] px-6 py-2.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-md bg-[#2F6B5E] flex items-center justify-center text-[#FFFEFB] font-bold text-xl shadow-xs">
            Ψ
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-semibold tracking-tight text-[#2F6B5E]">
                Synthera
              </h1>
              <span className="font-mono text-[10px] uppercase px-1.5 py-0.5 rounded bg-[#EEEBE5] text-[#6B746F] border border-[#E5E2DC]">
                v1.0.0 &bull; Research
              </span>
            </div>
            <p className="text-[11px] text-[#7A827C] font-medium leading-snug">
              Explainable Drug Combination Discovery & Mechanistic Verification
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 font-mono text-xs">
          {health ? (
            <div className="flex items-center gap-2.5 bg-[#F3F1EC] border border-[#E5E2DC] px-3 py-1.5 rounded-md text-[#5A635E]">
              <span className="flex items-center gap-1.5 text-[#3D7A6C] font-medium">
                <span className="w-2 h-2 rounded-full bg-[#3D7A6C] animate-pulse" />
                Backend Operational
              </span>
              <span className="text-[#D8D5CE]">&bull;</span>
              <span className="flex items-center gap-1 text-[#1C2421]">
                <Cpu className="w-3.5 h-3.5 text-[#6B746F]" />
                {health.device.toUpperCase()}
              </span>
              <span className="text-[#D8D5CE]">&bull;</span>
              <span className="text-[#6B746F]">
                {health.total_drugs.toLocaleString()} drugs /{" "}
                {health.total_cell_lines} lines
              </span>
            </div>
          ) : healthError ? (
            <div className="flex items-center gap-1.5 bg-[#F7EBEB] border border-[#E8C5C5] px-2.5 py-1 rounded text-[#8B4040] text-[11px]">
              <AlertCircle className="w-3.5 h-3.5 text-[#C45C5C]" />
              Offline
            </div>
          ) : (
            <div className="flex items-center gap-1.5 text-[11px] text-[#8A918C]">
              <Activity className="w-3.5 h-3.5 animate-spin" />
              Loading…
            </div>
          )}
        </div>
      </header>

      <Navigation />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-4">
        <Outlet />
      </main>

      <footer className="bg-[#FFFEFB] border-t border-[#E5E2DC] px-6 py-3 mt-auto">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between text-[11px] text-[#7A827C] font-mono gap-2">
          <div>Synthera &bull; PrimeKG &bull; HGT</div>
          <div>Faithfulness &bull; PubMed</div>
        </div>
      </footer>
    </div>
  );
};
