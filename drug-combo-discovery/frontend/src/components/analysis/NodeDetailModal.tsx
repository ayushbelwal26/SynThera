import React, { useEffect } from "react";
import { X, Network } from "lucide-react";

interface NodeDetailModalProps {
  entity: { type: "node" | "edge"; data: any } | null;
  onClose: () => void;
}

export const NodeDetailModal: React.FC<NodeDetailModalProps> = ({
  entity,
  onClose,
}) => {
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  if (!entity) return null;

  const isNode = entity.type === "node";
  const data = entity.data;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#041A1E]/60 backdrop-blur-sm p-4">
      <div className="bg-[var(--color-surface)] border border-[var(--color-rule-strong)] shadow-[0_12px_40px_rgba(0,0,0,0.3)] rounded-xl max-w-md w-full p-5 relative">
        <button
          type="button"
          onClick={onClose}
          className="absolute top-4 right-4 text-[var(--color-text-muted)] hover:text-[var(--color-accent)] p-1 rounded-md hover:bg-[var(--color-panel)] transition-colors cursor-pointer"
        >
          <X className="w-4 h-4" />
        </button>

        <p className="page-kicker flex items-center gap-1.5 mb-1 text-[var(--color-accent)] font-mono text-[11px]">
          <Network size={12} />
          <span>
            {isNode
              ? `Entity Inspector · ${data.nodeType || "Node"}`
              : "Edge Attribution Inspector"}
          </span>
        </p>

        {isNode ? (
          <div>
            <h3 className="section-title mb-4 text-[20px] font-bold">
              {data.label}
            </h3>
            <div className="border border-[var(--color-rule)] rounded-lg divide-y divide-[var(--color-rule)]/60 text-[13px] bg-[var(--color-panel)]">
              <div className="flex justify-between p-2.5">
                <span className="bench-label">Biological Role</span>
                <span className="font-mono capitalize font-bold text-[var(--color-accent)]">
                  {data.nodeType}
                </span>
              </div>
              <div className="flex justify-between p-2.5">
                <span className="bench-label">Query Status</span>
                <span className="font-mono text-[var(--color-text-primary)]">
                  {data.isHub ? "Primary Hub" : "Attribution Neighbor"}
                </span>
              </div>
              <div className="flex justify-between p-2.5">
                <span className="bench-label">PrimeKG Domain</span>
                <span className="font-mono text-[var(--color-text-primary)]">
                  {data.nodeType === "drug"
                    ? "Compound"
                    : data.nodeType === "protein"
                      ? "Gene / Protein"
                      : data.nodeType}
                </span>
              </div>
            </div>
            <p className="meta-text mt-3.5 leading-relaxed text-[var(--color-text-secondary)]">
              Participant in the local explanation subgraph mediating
              target–disease pathways and multi-hop connectivity.
            </p>
          </div>
        ) : (
          <div>
            <h3 className="section-title mb-4 text-[18px] font-bold flex items-center gap-2 flex-wrap">
              <span>{data.source}</span>
              <span className="font-sans font-normal italic text-[var(--color-accent)] text-[14px]">
                {data.relation}
              </span>
              <span>{data.target}</span>
            </h3>
            <div className="border border-[var(--color-rule)] rounded-lg divide-y divide-[var(--color-rule)]/60 text-[13px] bg-[var(--color-panel)]">
              <div className="flex justify-between p-2.5 items-center">
                <span className="bench-label">Attribution Weight</span>
                <span className="font-mono metric-value text-[15px] text-[var(--color-accent)] font-bold">
                  {typeof data.importance === "number"
                    ? data.importance.toFixed(4)
                    : data.importance}
                </span>
              </div>
              {data.source_type && (
                <div className="flex justify-between p-2.5">
                  <span className="bench-label">Source Type</span>
                  <span className="font-mono capitalize text-[var(--color-text-primary)]">
                    {data.source_type}
                  </span>
                </div>
              )}
              {data.target_type && (
                <div className="flex justify-between p-2.5">
                  <span className="bench-label">Target Type</span>
                  <span className="font-mono capitalize text-[var(--color-text-primary)]">
                    {data.target_type}
                  </span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
