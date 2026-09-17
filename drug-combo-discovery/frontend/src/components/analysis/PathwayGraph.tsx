import React, { useMemo, useState, useCallback } from 'react';
import {
  ReactFlow,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  MarkerType,
  Handle,
  Position,
} from '@xyflow/react';
import type { Node, Edge } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Network } from 'lucide-react';
import type { ExplanationEdge } from '../../types/api';

interface PathwayGraphProps {
  topEdges: ExplanationEdge[];
  drugAName: string;
  drugBName: string;
  explanationText: string;
  onSelectEntity?: (entity: { type: 'node' | 'edge'; data: any }) => void;
}

// Custom Biological Node Component
const BiologicalNode = ({ data }: { data: any }) => {
  const typeStyles = {
    drug: {
      bg: 'bg-[#F0FDFA]',
      border: 'border-[#0D9488]',
      badge: 'bg-[#CCFBF1] text-[#0F766E]',
      text: 'text-[#0F172A]',
    },
    protein: {
      bg: 'bg-[#FFFBEB]',
      border: 'border-[#D97706]',
      badge: 'bg-[#FEF3C7] text-[#92400E]',
      text: 'text-[#0F172A]',
    },
    pathway: {
      bg: 'bg-[#F5F3FF]',
      border: 'border-[#7C3AED]',
      badge: 'bg-[#EDE9FE] text-[#5B21B6]',
      text: 'text-[#0F172A]',
    },
    disease: {
      bg: 'bg-[#ECFDF5]',
      border: 'border-[#059669]',
      badge: 'bg-[#D1FAE5] text-[#065F46]',
      text: 'text-[#0F172A]',
    },
  }[data.nodeType as 'drug' | 'protein' | 'pathway' | 'disease'] || {
    bg: 'bg-[#FFFFFF]',
    border: 'border-[#CBD5E1]',
    badge: 'bg-[#F1F5F9] text-[#475569]',
    text: 'text-[#0F172A]',
  };

  return (
    <div
      className={`px-3 py-2 rounded-md border shadow-xs min-w-[140px] max-w-[200px] cursor-pointer transition-all hover:ring-2 hover:ring-[#0D9488]/40 ${typeStyles.bg} ${typeStyles.border}`}
    >
      <Handle type="target" position={Position.Left} className="!bg-[#64748B]" />
      <div className="flex items-center justify-between mb-1">
        <span className={`text-[9px] font-mono font-semibold uppercase px-1.5 py-0.5 rounded ${typeStyles.badge}`}>
          {data.nodeType}
        </span>
        {data.isHub && (
          <span className="text-[9px] font-mono text-[#64748B]">query hub</span>
        )}
      </div>
      <div className={`text-xs font-semibold truncate ${typeStyles.text}`} title={data.label}>
        {data.label}
      </div>
      <Handle type="source" position={Position.Right} className="!bg-[#64748B]" />
    </div>
  );
};

const nodeTypes = {
  biological: BiologicalNode,
};

export const PathwayGraph: React.FC<PathwayGraphProps> = ({
  topEdges,
  drugAName,
  drugBName,
  explanationText,
  onSelectEntity,
}) => {
  const [showLabels, setShowLabels] = useState(true);

  // Compute hierarchical column coordinates: Drug -> Target/Protein -> Pathway -> Disease
  const { initialNodes, initialEdges } = useMemo(() => {
    const nodesMap = new Map<string, { type: 'drug' | 'protein' | 'pathway' | 'disease'; label: string; isHub?: boolean }>();

    // Register query drugs as primary hubs
    nodesMap.set(drugAName, { type: 'drug', label: drugAName, isHub: true });
    nodesMap.set(drugBName, { type: 'drug', label: drugBName, isHub: true });

    // Deduce node types and register entities from edges
    topEdges.forEach((e) => {
      const deduceType = (name: string, explicitType?: string): 'drug' | 'protein' | 'pathway' | 'disease' => {
        if (name === drugAName || name === drugBName) return 'drug';
        if (explicitType === 'drug') return 'drug';
        if (explicitType === 'disease') return 'disease';
        if (explicitType === 'pathway') return 'pathway';
        if (explicitType === 'protein' || explicitType === 'gene/protein') return 'protein';

        // heuristics from PrimeKG nomenclature
        if (e.relation.includes('pathway')) return 'pathway';
        if (e.relation.includes('indication') || e.relation.includes('disease')) return 'disease';
        return 'protein';
      };

      if (!nodesMap.has(e.source)) {
        nodesMap.set(e.source, {
          type: deduceType(e.source, e.source_type),
          label: e.source,
        });
      }
      if (!nodesMap.has(e.target)) {
        nodesMap.set(e.target, {
          type: deduceType(e.target, e.target_type),
          label: e.target,
        });
      }
    });

    // Group nodes by category column
    const columns: Record<string, string[]> = {
      drug: [],
      protein: [],
      pathway: [],
      disease: [],
    };

    nodesMap.forEach((info, name) => {
      columns[info.type]?.push(name);
    });

    const columnX: Record<string, number> = {
      drug: 40,
      protein: 290,
      pathway: 540,
      disease: 790,
    };

    const nodesList: Node[] = [];
    Object.entries(columns).forEach(([type, names]) => {
      const x = columnX[type] ?? 40;
      const spacingY = 75;
      const startY = 40;

      names.forEach((name, idx) => {
        const info = nodesMap.get(name)!;
        nodesList.push({
          id: name,
          type: 'biological',
          position: { x, y: startY + idx * spacingY },
          data: {
            label: name,
            nodeType: info.type,
            isHub: info.isHub,
          },
        });
      });
    });

    const edgesList: Edge[] = topEdges.map((e, idx) => {
      const importanceNorm = Math.max(0.1, Math.min(1.0, e.importance));
      const strokeWidth = 1.5 + importanceNorm * 2.5;

      return {
        id: `edge-${idx}`,
        source: e.source,
        target: e.target,
        type: 'smoothstep',
        animated: importanceNorm > 0.6,
        label: showLabels ? e.relation.replace(/_/g, ' ') : undefined,
        labelStyle: { fontSize: 10, fill: '#475569', fontFamily: 'monospace' },
        labelBgStyle: { fill: '#FFFFFF', fillOpacity: 0.9, stroke: '#E2E8F0' },
        style: {
          stroke: '#4A505A',
          strokeWidth,
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          width: 12,
          height: 12,
          color: '#4A505A',
        },
        data: e,
      };
    });

    return { initialNodes: nodesList, initialEdges: edgesList };
  }, [topEdges, drugAName, drugBName, showLabels]);

  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState(initialEdges);

  const handleNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      if (onSelectEntity) {
        onSelectEntity({ type: 'node', data: node.data });
      }
    },
    [onSelectEntity]
  );

  const handleEdgeClick = useCallback(
    (_: React.MouseEvent, edge: Edge) => {
      if (onSelectEntity) {
        onSelectEntity({ type: 'edge', data: edge.data });
      }
    },
    [onSelectEntity]
  );

  return (
    <div className="bg-[#FFFFFF] border border-[#E5E5E0] rounded-lg p-5 shadow-xs mb-6">
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
        <div>
          <div className="flex items-center gap-2">
            <Network className="w-4 h-4 text-[#0D9488]" />
            <h3 className="font-serif text-lg font-bold text-[#0F172A]">
              Mechanistic Attribution Pathway Map
            </h3>
          </div>
          <p className="text-xs text-[#717784] mt-0.5">
            Local heterogeneous subgraph isolated by gradient attribution backpropagation ({topEdges.length} top-ranked edges)
          </p>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-2.5 flex-wrap text-[11px] font-mono">
          <span className="flex items-center gap-1 text-[#0F766E]">
            <span className="w-2.5 h-2.5 rounded-sm bg-[#CCFBF1] border border-[#0D9488]" />
            Drug
          </span>
          <span className="flex items-center gap-1 text-[#92400E]">
            <span className="w-2.5 h-2.5 rounded-sm bg-[#FEF3C7] border border-[#D97706]" />
            Target/Protein
          </span>
          <span className="flex items-center gap-1 text-[#5B21B6]">
            <span className="w-2.5 h-2.5 rounded-sm bg-[#EDE9FE] border border-[#7C3AED]" />
            Pathway
          </span>
          <span className="flex items-center gap-1 text-[#065F46]">
            <span className="w-2.5 h-2.5 rounded-sm bg-[#D1FAE5] border border-[#059669]" />
            Disease
          </span>
          <button
            type="button"
            onClick={() => setShowLabels((prev) => !prev)}
            className="ml-2 px-2 py-0.5 bg-[#F1F5F9] hover:bg-[#E2E8F0] text-[#334155] rounded text-[10px] transition-colors"
          >
            {showLabels ? 'Hide Edge Labels' : 'Show Edge Labels'}
          </button>
        </div>
      </div>

      {/* Model-Generated Plain English Mechanistic Explanation */}
      <div className="bg-[#F8FAFC] border-l-4 border-[#0D9488] p-3.5 rounded-r mb-4 text-xs">
        <span className="font-semibold text-[#0F172A] block mb-1">
          Model-Generated Mechanistic Reasoning:
        </span>
        <p className="text-[#334155] leading-relaxed font-medium italic">
          "{explanationText}"
        </p>
      </div>

      {/* React Flow Interactive Canvas */}
      <div className="h-[420px] w-full border border-[#E5E5E0] rounded-md overflow-hidden relative bg-[#F8F9FA]">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={handleNodeClick}
          onEdgeClick={handleEdgeClick}
          fitView
          attributionPosition="bottom-right"
          minZoom={0.3}
          maxZoom={2.0}
        >
          <Background color="#CBD5E1" gap={16} size={1} />
          <Controls showInteractive={false} />
        </ReactFlow>

        {/* Column Guides Overlay */}
        <div className="absolute top-2 left-4 pointer-events-none flex gap-[180px] text-[10px] font-mono text-[#94A3B8] uppercase tracking-wider opacity-70">
          <span>1. Compounds</span>
          <span>2. Targets / Enzymes</span>
          <span>3. Cellular Pathways</span>
          <span>4. Indications</span>
        </div>
      </div>

      <div className="mt-3 flex items-center justify-between text-[11px] text-[#717784] font-mono">
        <span>Click any node or edge to inspect detailed biological metadata</span>
        <span>Line thickness = Attribution gradient importance score</span>
      </div>
    </div>
  );
};
