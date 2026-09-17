import React, { useEffect, useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Navigation } from './Navigation';
import { checkHealth } from '../services/api';
import type { HealthResponse } from '../types/api';
import { Cpu, Activity, AlertCircle } from 'lucide-react';

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
    <div className="min-h-screen flex flex-col bg-[#FBFBF9] text-[#0F172A]">
      {/* Top Research Header */}
      <header className="bg-[#FFFFFF] border-b border-[#E5E5E0] px-6 py-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-md bg-[#181A1E] flex items-center justify-center text-[#0D9488] font-serif font-bold text-xl shadow-xs">
            Ψ
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-serif text-xl font-bold tracking-tight text-[#0F172A]">
                Synthera
              </h1>
              <span className="font-mono text-[10px] uppercase px-1.5 py-0.5 rounded bg-[#F1F5F9] text-[#64748B] border border-[#E2E8F0]">
                v1.0.0 &bull; Research
              </span>
            </div>
            <p className="text-[11px] text-[#717784] font-medium leading-tight">
              Explainable Drug Combination Discovery & Mechanistic Verification in Multi-Drug Resistant Oncology
            </p>
          </div>
        </div>

        {/* Live System Status */}
        <div className="flex items-center gap-2 font-mono text-xs">
          {health ? (
            <div className="flex items-center gap-2.5 bg-[#F8FAFC] border border-[#E2E8F0] px-3 py-1.5 rounded-md text-[#475569]">
              <span className="flex items-center gap-1.5 text-[#059669] font-medium">
                <span className="w-2 h-2 rounded-full bg-[#059669] animate-pulse" />
                Backend Operational
              </span>
              <span className="text-[#CBD5E1]">&bull;</span>
              <span className="flex items-center gap-1 text-[#0F172A]">
                <Cpu className="w-3.5 h-3.5 text-[#64748B]" />
                {health.device.toUpperCase()}
              </span>
              <span className="text-[#CBD5E1]">&bull;</span>
              <span className="text-[#64748B]">
                {health.total_drugs.toLocaleString()} drugs / {health.total_cell_lines} lines
              </span>
            </div>
          ) : healthError ? (
            <div className="flex items-center gap-1.5 bg-[#FEF2F2] border border-[#FECACA] px-2.5 py-1 rounded text-[#991B1B] text-[11px]">
              <AlertCircle className="w-3.5 h-3.5 text-[#DC2626]" />
              Analysis Service Offline (Check VITE_API_BASE_URL)
            </div>
          ) : (
            <div className="flex items-center gap-1.5 text-[11px] text-[#94A3B8]">
              <Activity className="w-3.5 h-3.5 animate-spin" />
              Polling service status...
            </div>
          )}
        </div>
      </header>

      {/* Primary Navigation Tabs */}
      <Navigation />

      {/* Main Content Viewport */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6">
        <Outlet />
      </main>

      {/* Scientific Provenance Footer */}
      <footer className="bg-[#FFFFFF] border-t border-[#E5E5E0] px-6 py-4 mt-auto">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between text-[11px] text-[#717784] font-mono gap-2">
          <div>
            Synthera Biocomputational System &bull; PrimeKG Heterogeneous Knowledge Graph &bull; Heterogeneous Graph Transformer (HGT)
          </div>
          <div>
            Dual In-Silico Faithfulness (Necessity & Sufficiency) &bull; NCBI PubMed E-Utilities
          </div>
        </div>
      </footer>
    </div>
  );
};
