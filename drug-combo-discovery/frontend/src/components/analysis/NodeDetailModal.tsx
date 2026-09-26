import React, { useEffect } from "react";
import { X } from "lucide-react";

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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#1C2421]/35 p-4">
      <div className="bg-[#F5F5ED] border border-[#CFC9BC] max-w-md w-full p-4 relative">
        <button
          type="button"
          onClick={onClose}
          className="absolute top-3 right-3 text-[#6B746F] hover:text-[#1C2421] p-1"
        >
          <X className="w-4 h-4" />
        </button>

        <p className="page-kicker mb-1">
          {isNode
            ? `Entity · ${data.nodeType || "Node"}`
            : "Edge inspector"}
        </p>

        {isNode ? (
          <div>
            <h3 className="section-title mb-3">{data.label}</h3>
            <div className="border-t border-[#CFC9BC] divide-y divide-[#CFC9BC] text-[13px]">
              <div className="flex justify-between py-2">
                <span className="meta-text">Role</span>
                <span className="text-[#1C2421] capitalize">{data.nodeType}</span>
              </div>
              <div className="flex justify-between py-2">
                <span className="meta-text">Query status</span>
                <span className="text-[#1C2421]">
                  {data.isHub ? "Query hub" : "Attribution neighbor"}
                </span>
              </div>
              <div className="flex justify-between py-2">
                <span className="meta-text">PrimeKG type</span>
                <span className="id-text text-[#1C2421]">
                  {data.nodeType === "drug"
                    ? "drug"
                    : data.nodeType === "protein"
                      ? "gene/protein"
                      : data.nodeType}
                </span>
              </div>
            </div>
            <p className="meta-text mt-3 leading-relaxed">
              Participant in the explanation subgraph mediating
              target–disease or protein–protein connectivity.
            </p>
          </div>
        ) : (
          <div>
            <h3 className="section-title mb-3 flex items-center gap-2 flex-wrap">
              <span>{data.source}</span>
              <span className="meta-text font-sans font-normal italic">
                {data.relation}
              </span>
              <span>{data.target}</span>
            </h3>
            <div className="border-t border-[#CFC9BC] divide-y divide-[#CFC9BC] text-[13px]">
              <div className="flex justify-between py-2">
                <span className="meta-text">Importance</span>
                <span className="metric-value text-[14px]">
                  {typeof data.importance === "number"
                    ? data.importance.toFixed(4)
                    : data.importance}
                </span>
              </div>
              {data.source_type && (
                <div className="flex justify-between py-2">
                  <span className="meta-text">Source type</span>
                  <span className="capitalize">{data.source_type}</span>
                </div>
              )}
              {data.target_type && (
                <div className="flex justify-between py-2">
                  <span className="meta-text">Target type</span>
                  <span className="capitalize">{data.target_type}</span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
