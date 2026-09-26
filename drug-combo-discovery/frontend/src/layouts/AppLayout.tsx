import React, { useEffect, useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Navigation } from './Navigation';
import { checkHealth } from '../services/api';
import type { HealthResponse } from '../types/api';
import { AlertCircle } from 'lucide-react';

export const AppLayout: React.FC = () => {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    checkHealth()
      .then((res) => { if (isMounted) { setHealth(res); setHealthError(null); } })
      .catch((err) => { if (isMounted) setHealthError(err.message); });
    return () => { isMounted = false; };
  }, []);

  return (
    <div className="min-h-screen flex flex-col" style={{ backgroundColor: 'var(--bg)' }}>
      {/* App Header */}
      <header style={{
        backgroundColor: 'var(--surface)',
        borderBottom: '1px solid var(--border)',
      }}>
        <div className="max-w-screen-xl mx-auto px-5 sm:px-8 h-14 flex items-center justify-between gap-4">
          {/* Brand */}
          <div className="flex items-center gap-2.5 shrink-0">
            <div style={{
              width: 30, height: 30,
              backgroundColor: 'var(--text-primary)',
              borderRadius: 6,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: 'var(--accent)',
              fontFamily: 'var(--font-serif)',
              fontWeight: 700,
              fontSize: 17,
              letterSpacing: '-0.02em',
              flexShrink: 0,
            }}>
              Ψ
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span style={{
                  fontFamily: 'var(--font-serif)',
                  fontWeight: 700,
                  fontSize: 18,
                  color: 'var(--text-primary)',
                  letterSpacing: '-0.02em',
                  lineHeight: 1,
                }}>
                  SynThera
                </span>
                <span style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: 10,
                  color: 'var(--text-muted)',
                  backgroundColor: 'var(--surface-subtle)',
                  border: '1px solid var(--border)',
                  borderRadius: 4,
                  padding: '2px 6px',
                  letterSpacing: '0.04em',
                }}>
                  RESEARCH
                </span>
              </div>
              <p style={{ fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.2, marginTop: 1 }}>
                Drug Combination Discovery
              </p>
            </div>
          </div>

          {/* System Status */}
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11 }}>
            {health ? (
              <div style={{
                display: 'flex', alignItems: 'center', gap: 10,
                backgroundColor: 'var(--surface-subtle)',
                border: '1px solid var(--border)',
                borderRadius: 6, padding: '5px 10px',
                color: 'var(--text-secondary)',
              }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: 5, color: 'var(--synergy)', fontWeight: 600 }}>
                  <span style={{
                    width: 6, height: 6, borderRadius: '50%',
                    backgroundColor: 'var(--synergy)', display: 'inline-block'
                  }} />
                  Online
                </span>
                <span style={{ color: 'var(--border-strong)' }}>·</span>
                <span style={{ color: 'var(--text-muted)' }}>
                  {health.device.toUpperCase()} · {health.total_drugs.toLocaleString()} compounds
                </span>
              </div>
            ) : healthError ? (
              <div style={{
                display: 'flex', alignItems: 'center', gap: 6,
                backgroundColor: 'var(--error-subtle)',
                border: '1px solid var(--error-border)',
                borderRadius: 6, padding: '5px 10px',
                color: 'var(--error)',
              }}>
                <AlertCircle size={12} />
                <span>Backend offline</span>
              </div>
            ) : (
              <div style={{ color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{
                  width: 6, height: 6, borderRadius: '50%',
                  backgroundColor: 'var(--border-strong)', display: 'inline-block'
                }} />
                Connecting…
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Navigation */}
      <Navigation />

      {/* Page content */}
      <main className="flex-1 max-w-screen-xl w-full mx-auto px-5 sm:px-8 py-7">
        <Outlet />
      </main>

      {/* Footer */}
      <footer style={{
        backgroundColor: 'var(--surface)',
        borderTop: '1px solid var(--border)',
        padding: '14px 32px',
      }}>
        <div className="max-w-screen-xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2"
          style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
          <span>SynThera · PrimeKG · HGT Neural Network · DrugComb</span>
          <span>Dual In-Silico Faithfulness · NCBI PubMed</span>
        </div>
      </footer>
    </div>
  );
};
