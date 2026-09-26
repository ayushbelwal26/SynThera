import React, { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useApp } from "../services/AppContext";
import type { LiteratureCitation } from "../types/api";

interface AugmentedCitation extends LiteratureCitation {
  combination: string;
  cellLine: string;
}

export const EvidencePage: React.FC = () => {
  const navigate = useNavigate();
  const { currentPrediction, recentPredictions } = useApp();
  const [filter, setFilter] = useState("");

  const allCitations = useMemo(() => {
    const list: AugmentedCitation[] = [];
    const seen = new Set<string>();

    const push = (c: LiteratureCitation, combo: string, cell: string) => {
      const key = `${c.pmid}_${combo}`;
      if (seen.has(key)) return;
      seen.add(key);
      list.push({ ...c, combination: combo, cellLine: cell });
    };

    if (currentPrediction?.supporting_literature) {
      currentPrediction.supporting_literature.forEach((c) =>
        push(
          c,
          `${currentPrediction.drug_a_name} + ${currentPrediction.drug_b_name}`,
          currentPrediction.cell_line,
        ),
      );
    }
    recentPredictions.forEach((p) => {
      p.supporting_literature?.forEach((c) =>
        push(c, `${p.drug_a_name} + ${p.drug_b_name}`, p.cell_line),
      );
    });
    return list;
  }, [currentPrediction, recentPredictions]);

  const filtered = useMemo(() => {
    const q = filter.trim().toLowerCase();
    if (!q) return allCitations;
    return allCitations.filter(
      (c) =>
        c.pmid?.toLowerCase().includes(q) ||
        c.title?.toLowerCase().includes(q) ||
        c.journal?.toLowerCase().includes(q) ||
        c.combination.toLowerCase().includes(q) ||
        c.snippet?.toLowerCase().includes(q) ||
        c.match_reason?.toLowerCase().includes(q),
    );
  }, [allCitations, filter]);

  return (
    <div>
      <p className="page-kicker">Literature</p>
      <h2 className="page-title">Matched PubMed records</h2>
      <p className="page-lede">
        Each entry is tied to the pair record whose retained edges it matched.
        Filter by drug, gene, PMID, or phrase.
      </p>

      <div className="mt-5 bench-panel">
        <div className="flex items-end justify-between gap-4">
          <div className="flex-1">
            <label className="bench-label block mb-1">Filter</label>
            <input
              type="text"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder="e.g. EGFR, taxane, 30341984"
              className="bench-input"
            />
          </div>
          <span className="meta-text shrink-0 pb-1.5">
            {filtered.length} {filtered.length === 1 ? "entry" : "entries"}
          </span>
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="py-8">
          <p className="meta-text mb-3">
            {allCitations.length === 0
              ? "No literature indexed yet. Score a pair on the Bench to retrieve PubMed matches."
              : "No entries match this filter."}
          </p>
          {allCitations.length === 0 && (
            <button
              type="button"
              onClick={() => navigate("/discover")}
              className="bench-btn"
            >
              Open bench
            </button>
          )}
        </div>
      ) : (
        <div className="mt-2 divide-y divide-[#CFC9BC] border-y border-[#CFC9BC]">
          {filtered.map((cite, idx) => (
            <article
              key={`${cite.pmid}_${idx}`}
              className="py-4 grid grid-cols-1 md:grid-cols-12 gap-3"
            >
              <div className="md:col-span-3 space-y-0.5">
                <a
                  href={cite.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="id-text text-[#1A1F1C] underline underline-offset-2 decoration-[#CFC9BC] hover:decoration-[#1A535C]"
                >
                  PMID {cite.pmid}
                </a>
                {cite.journal && <div className="meta-text">{cite.journal}</div>}
                {cite.year && <div className="meta-text">{cite.year}</div>}
                <div className="meta-text pt-1">{cite.combination}</div>
              </div>
              <div className="md:col-span-9">
                <h3 className="font-serif text-[16px] text-[#1A1F1C] font-semibold leading-snug">
                  {cite.title}
                </h3>
                {cite.snippet && (
                  <p className="mt-1.5 text-[13px] text-[#4A524C] italic leading-relaxed">
                    “{cite.snippet}”
                  </p>
                )}
                {cite.match_reason && (
                  <p className="meta-text mt-1.5">{cite.match_reason}</p>
                )}
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
};
