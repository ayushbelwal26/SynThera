import React, { useEffect } from 'react';
import { X, Dna, ArrowRight } from 'lucide-react';

interface NodeDetailModalProps {
  entity: { type: 'node' | 'edge'; data: any } | null;
  onClose: () => void;
}

export const NodeDetailModal: React.FC<NodeDetailModalProps> = ({ entity, onClose }) => {
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose();
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  if (!entity) return null;

  const isNode = entity.type === 'node';
  const data = entity.data;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#0F172A]/40 backdrop-blur-xs p-4">
      <div className="bg-[#FFFFFF] border border-[#CBD5E1] rounded-lg shadow-xl max-w-md w-full p-5 relative">
        <button
          type="button"
          onClick={onClose}
          className="absolute top-4 right-4 text-[#64748B] hover:text-[#0F172A] p-1 rounded hover:bg-[#F1F5F9] transition-colors"
        >
          <X className="w-4 h-4" />
        </button>

        <div className="flex items-center gap-2 mb-3">
          <Dna className="w-4 h-4 text-[#0D9488]" />
          <span className="text-[11px] font-mono uppercase tracking-wider text-[#64748B]">
            {isNode ? `Entity Inspector: ${data.nodeType || 'Node'}` : 'Interaction Edge Inspector'}
          </span>
        </div>

        {isNode ? (
          <div>
            <h3 className="font-serif text-xl font-bold text-[#0F172A] mb-2">
              {data.label}
            </h3>
            <div className="bg-[#F8FAFC] border border-[#E2E8F0] rounded p-3 text-xs space-y-2 font-mono">
              <div className="flex justify-between">
                <span className="text-[#64748B]">Biological Role:</span>
                <span className="font-semibold text-[#0F172A] uppercase">{data.nodeType}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#64748B]">Query Status:</span>
                <span className="text-[#0F172A]">{data.isHub ? 'Combination Query Hub' : 'Attribution Neighbor'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#64748B]">PrimeKG Node Type:</span>
                <span className="text-[#0F172A]">{data.nodeType === 'drug' ? 'drug' : data.nodeType === 'protein' ? 'gene/protein' : data.nodeType}</span>
              </div>
            </div>
            <p className="text-xs text-[#475569] mt-3 leading-relaxed">
              This entity was identified as an active participant in the GNN explanation subgraph, mediating target-disease or protein-protein network connectivity.
            </p>
          </div>
        ) : (
          <div>
            <div className="flex items-center gap-2 font-semibold text-sm text-[#0F172A] mb-3">
              <span className="bg-[#F1F5F9] px-2 py-0.5 rounded border border-[#E2E8F0]">
                {data.source}
              </span>
              <ArrowRight className="w-3.5 h-3.5 text-[#64748B]" />
              <span className="bg-[#F1F5F9] px-2 py-0.5 rounded border border-[#E2E8F0]">
                {data.target}
              </span>
            </div>

            <div className="bg-[#F8FAFC] border border-[#E2E8F0] rounded p-3 text-xs space-y-2 font-mono">
              <div className="flex justify-between">
                <span className="text-[#64748B]">Relation:</span>
                <span className="font-semibold text-[#0D9488]">{data.relation}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#64748B]">Importance Score:</span>
                <span className="font-bold text-[#0F172A]">{Number(data.importance).toFixed(6)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#64748B]">Edge Attribution:</span>
                <span className="text-[#059669]">||grad_src p(class)||_2</span>
              </div>
            </div>
            <p className="text-xs text-[#475569] mt-3 leading-relaxed">
              Gradient attribution quantifies how sensitively the predicted interaction probability changes with respect to this edge's source node embeddings.
            </p>
          </div>
        )}

        <div className="mt-5 pt-3 border-t border-[#E5E5E0] flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="px-3 py-1.5 bg-[#F1F5F9] hover:bg-[#E2E8F0] text-[#0F172A] rounded text-xs font-medium transition-colors"
          >
            Close Inspector
          </button>
        </div>
      </div>
    </div>
  );
};
