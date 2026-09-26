import React, { useEffect, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { Navigation } from "./Navigation";
import { checkHealth } from "../services/api";
import type { HealthResponse } from "../types/api";

function registerLabel(pathname: string, search: string): string {
  if (pathname.startsWith("/analysis")) return "03 · Result inspector";
  if (pathname.startsWith("/evidence")) return "03 · Literature index";
  if (pathname.startsWith("/graph")) return "04 · Neighborhood";
  if (pathname.startsWith("/discover") && search.includes("mode=indication")) {
    return "02 · Indication search";
  }
  return "01 · Pair analysis";
}

export const AppLayout: React.FC = () => {
  const location = useLocation();
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
        if (isMounted) setHealthError(err.message);
      });
    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <div className="min-h-screen flex bg-[#F5F5ED] text-[#1A1F1C]">
      <aside className="w-[210px] shrink-0 border-r border-[#CFC9BC] bg-[#E8EDE0] flex flex-col min-h-screen sticky top-0 self-start">
        <div className="px-4 pt-6 pb-2">
          <h1 className="font-serif text-[24px] leading-none text-[#1A1F1C] font-semibold">
            SynThera
          </h1>
          <p className="page-kicker mt-2">Combination bench</p>
        </div>

        <Navigation />

        <div className="mt-auto px-4 py-4 border-t border-[#CFC9BC]">
          <p className="page-kicker mb-1.5">Model</p>
          <p className="id-text leading-relaxed text-[11px]">
            HGT over PrimeKG
            <br />
            {health
              ? `${health.device} · ${health.total_drugs.toLocaleString()} drugs · ${health.total_cell_lines} lines`
              : healthError
                ? "Offline · check VITE_API_BASE_URL"
                : "Checking…"}
            <br />
            <span className="text-[#6B746C]">Not clinical output</span>
          </p>
        </div>
      </aside>

      <div className="flex-1 min-w-0 flex flex-col min-h-screen">
        <div className="border-b border-[#CFC9BC] px-6 py-2.5 flex items-center justify-between gap-4 bg-[#F5F5ED]">
          <span className="bench-register">
            {registerLabel(location.pathname, location.search)}
          </span>
          <span className="bench-register hidden sm:inline">
            PrimeKG · HGT
          </span>
        </div>

        <main className="flex-1 px-6 py-5 lg:px-8 lg:py-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
