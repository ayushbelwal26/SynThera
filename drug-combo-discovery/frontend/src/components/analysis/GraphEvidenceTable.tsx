import type { ExplanationEdge } from "../../types/api";
import { Link } from "react-router-dom";

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
        No attributed edges returned for this record.
      </p>
    );
  }

  return (
    <div>
      {explanationText && (
        <p className="text-[14px] text-[#4A524C] leading-relaxed mb-4 max-w-2xl">
          {explanationText}
        </p>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-[#CFC9BC]">
              <th className="bench-label py-2.5 pr-3 font-medium">Source</th>
              <th className="bench-label py-2.5 pr-3 font-medium">Relation</th>
              <th className="bench-label py-2.5 pr-3 font-medium">Target</th>
              <th className="bench-label py-2.5 font-medium w-[28%]">Weight</th>
            </tr>
          </thead>
          <tbody>
            {edges.slice(0, 12).map((e, i) => {
              const w = e.importance || 0;
              return (
                <tr key={i} className="border-b border-[#CFC9BC]/70">
                  <td className="py-3 pr-3 font-mono text-[13px] text-[#1A1F1C]">
                    {e.source}
                  </td>
                  <td className="py-3 pr-3 font-sans text-[13px] italic text-[#4A524C]">
                    {e.relation}
                  </td>
                  <td className="py-3 pr-3 font-mono text-[13px] text-[#1A1F1C]">
                    {e.target}
                  </td>
                  <td className="py-3">
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-2 bg-[#E8EDE0]">
                        <div
                          className="h-full bg-[#1A535C]"
                          style={{ width: `${(w / maxW) * 100}%` }}
                        />
                      </div>
                      <span className="font-mono text-[13px] text-[#4A524C] w-11 text-right">
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

      <Link
        to="/graph"
        className="inline-block mt-3 text-[12px] text-[#1A535C] hover:underline"
      >
        Explore this neighborhood →
      </Link>
    </div>
  );
};
