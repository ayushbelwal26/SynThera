import type { ExplanationEdge } from "../../types/api";
import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";

interface GraphEvidenceTableProps {
  edges: ExplanationEdge[];
  explanationText?: string;
}

export const GraphEvidenceTable: React.FC<GraphEvidenceTableProps> = ({
  edges,
  explanationText,
}) => {
  const maxW = Math.max(...edges.map((e) => e.importance || 0), 0.001);

  if (!edges.length) {
    return (
      <p className="meta-text">
        No attributed edges returned for this combination.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      {explanationText && (
        <div className="p-3 rounded bg-[var(--color-surface)] border border-[var(--color-rule)] text-[13.5px] text-[var(--color-text-secondary)] leading-relaxed">
          {explanationText}
        </div>
      )}

      <div className="overflow-x-auto rounded-lg border border-[var(--color-rule)] bg-[var(--color-panel)]">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-[var(--color-rule)] bg-[var(--color-surface)]">
              <th className="bench-label py-2.5 px-3 font-semibold">
                Source Entity
              </th>
              <th className="bench-label py-2.5 px-3 font-semibold">
                Biological Relation
              </th>
              <th className="bench-label py-2.5 px-3 font-semibold">
                Target Entity
              </th>
              <th className="bench-label py-2.5 px-3 font-semibold w-[28%]">
                Attribution Gradient
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--color-rule)]/60 font-mono text-[12.5px]">
            {edges.slice(0, 12).map((e, i) => {
              const w = e.importance || 0;
              return (
                <tr
                  key={i}
                  className="hover:bg-[var(--color-accent-soft)]/20 transition-colors"
                >
                  <td className="py-2.5 px-3 text-[var(--color-text-primary)] font-semibold">
                    {e.source}
                  </td>
                  <td className="py-2.5 px-3 text-[var(--color-accent)] font-sans italic">
                    {e.relation.replace(/_/g, " ")}
                  </td>
                  <td className="py-2.5 px-3 text-[var(--color-text-primary)] font-semibold">
                    {e.target}
                  </td>
                  <td className="py-2.5 px-3">
                    <div className="flex items-center gap-2.5">
                      <div className="flex-1 h-2 rounded-full bg-[var(--color-surface)] border border-[var(--color-rule)] overflow-hidden">
                        <div
                          className="h-full rounded-full bg-[var(--color-accent)] shadow-[0_0_8px_var(--color-accent-glow)] transition-all duration-500"
                          style={{ width: `${(w / maxW) * 100}%` }}
                        />
                      </div>
                      <span className="font-mono text-[12px] font-bold text-[var(--color-text-primary)] w-10 text-right">
                        {w.toFixed(2)}
                      </span>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="flex justify-end">
        <Link
          to="/graph"
          className="inline-flex items-center gap-1.5 text-[12.5px] font-mono text-[var(--color-accent)] hover:underline"
        >
          <span>Explore full PrimeKG graph neighborhood</span>
          <ArrowRight size={13} />
        </Link>
      </div>
    </div>
  );
};
