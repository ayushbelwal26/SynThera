import React, { useMemo, useState, useCallback } from "react";
import {
  ReactFlow,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  MarkerType,
  Handle,
  Position,
} from "@xyflow/react";
import type { Node, Edge } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Network } from "lucide-react";
import type { ExplanationEdge } from "../../types/api";

interface PathwayGraphProps {
  topEdges: ExplanationEdge[];
  drugAName: string;
  drugBName: string;
  explanationText: string;
  onSelectEntity?: (entity: { type: "node" | "edge"; data: any }) => void;
}

// Custom Biological Node Component
const BiologicalNode = ({ data }: { data: any }) => {
  const typeStyles = {
    drug: {
      bg: "bg-[#E8F0ED]",
      border: "border-[#2F6B5E]",
      badge: "bg-[#D4E5DF] text-[#25564B]",
      text: "text-[#1C2421]",
    },
    protein: {
      bg: "bg-[#F7F0E4]",
      border: "border-[#B8893D]",
      badge: "bg-[#F5EFE4] text-[#7A5A28]",
      text: "text-[#1C2421]",
    },
    pathway: {
      bg: "bg-[#F3F0F7]",
      border: "border-[#8B7BA8]",
      badge: "bg-[#EDE8F3] text-[#6B5B8A]",
      text: "text-[#1C2421]",
    },
    disease: {
      bg: "bg-[#E6F2F2]",
      border: "border-[#4A8B8A]",
      badge: "bg-[#D4E8E8] text-[#2F5E5D]",
      text: "text-[#1C2421]",
    },
  }[data.nodeType as "drug" | "protein" | "pathway" | "disease"] || {
    bg: "bg-[#FFFEFB]",
    border: "border-[#D8D5CE]",
    badge: "bg-[#EEEBE5] text-[#5A635E]",
    text: "text-[#1C2421]",
  };

  return (
    <div
      className={`px-3 py-2 rounded-md border shadow-xs min-w-[140px] max-w-[200px] cursor-pointer transition-all hover:ring-2 hover:ring-[#2F6B5E]/40 ${typeStyles.bg} ${typeStyles.border}`}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="!bg-[#6B746F]"
      />
      <div className="flex items-center justify-between mb-1">
        <span
          className={`text-[9px] font-mono font-semibold uppercase px-1.5 py-0.5 rounded ${typeStyles.badge}`}
        >
          {data.nodeType}
        </span>
        {data.isHub && (
          <span className="text-[9px] font-mono text-[#6B746F]">query hub</span>
        )}
      </div>
      <div
        className={`text-xs font-semibold truncate ${typeStyles.text}`}
        title={data.label}
      >
        {data.label}
      </div>
      <Handle
        type="source"
        position={Position.Right}
        className="!bg-[#6B746F]"
      />
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
    const nodesMap = new Map<
      string,
      {
        type: "drug" | "protein" | "pathway" | "disease";
        label: string;
        isHub?: boolean;
      }
    >();

    // Register query drugs as primary hubs
    nodesMap.set(drugAName, { type: "drug", label: drugAName, isHub: true });
    nodesMap.set(drugBName, { type: "drug", label: drugBName, isHub: true });

    // Deduce node types and register entities from edges
    topEdges.forEach((e) => {
      const deduceType = (
        name: string,
        explicitType?: string,
      ): "drug" | "protein" | "pathway" | "disease" => {
        if (name === drugAName || name === drugBName) return "drug";
        if (explicitType === "drug") return "drug";
        if (explicitType === "disease") return "disease";
        if (explicitType === "pathway") return "pathway";
        if (explicitType === "protein" || explicitType === "gene/protein")
          return "protein";

        // heuristics from PrimeKG nomenclature
        if (e.relation.includes("pathway")) return "pathway";
        if (e.relation.includes("indication") || e.relation.includes("disease"))
          return "disease";
        return "protein";
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
          type: "biological",
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
        type: "smoothstep",
        animated: importanceNorm > 0.6,
        label: showLabels ? e.relation.replace(/_/g, " ") : undefined,
        labelStyle: { fontSize: 10, fill: "#5A635E", fontFamily: "Inter, system-ui, sans-serif" },
        labelBgStyle: { fill: "#FFFEFB", fillOpacity: 0.9, stroke: "#E5E2DC" },
        style: {
          stroke: "#8A918C",
          strokeWidth,
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          width: 12,
          height: 12,
          color: "#8A918C",
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
        onSelectEntity({ type: "node", data: node.data });
      }
    },
    [onSelectEntity],
  );

  const handleEdgeClick = useCallback(
    (_: React.MouseEvent, edge: Edge) => {
      if (onSelectEntity) {
        onSelectEntity({ type: "edge", data: edge.data });
      }
    },
    [onSelectEntity],
  );

  return (
    <div className="syn-card rounded-lg p-4 mb-4">
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
        <div>
          <div className="flex items-center gap-2">
            <Network className="w-4 h-4 text-[#2F6B5E]" />
            <h3 className="text-lg font-semibold text-[#1C2421]">
              Mechanistic Attribution Pathway Map
            </h3>
          </div>
          <p className="text-xs text-[#7A827C] mt-0.5">
            Local heterogeneous subgraph isolated by gradient attribution
            backpropagation ({topEdges.length} top-ranked edges)
          </p>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-2.5 flex-wrap text-[11px] font-mono">
          <span className="flex items-center gap-1 text-[#25564B]">
            <span className="w-2.5 h-2.5 rounded-sm bg-[#D4E5DF] border border-[#2F6B5E]" />
            Drug
          </span>
          <span className="flex items-center gap-1 text-[#7A5A28]">
            <span className="w-2.5 h-2.5 rounded-sm bg-[#F5EFE4] border border-[#B8893D]" />
            Target/Protein
          </span>
          <span className="flex items-center gap-1 text-[#6B5B8A]">
            <span className="w-2.5 h-2.5 rounded-sm bg-[#EDE8F3] border border-[#8B7BA8]" />
            Pathway
          </span>
          <span className="flex items-center gap-1 text-[#2F5E5D]">
            <span className="w-2.5 h-2.5 rounded-sm bg-[#D4E8E8] border border-[#4A8B8A]" />
            Disease
          </span>
          <button
            type="button"
            onClick={() => setShowLabels((prev) => !prev)}
            className="ml-2 px-2 py-0.5 bg-[#EEEBE5] hover:bg-[#E5E2DC] text-[#3D4742] rounded text-[10px] transition-colors"
          >
            {showLabels ? "Hide Edge Labels" : "Show Edge Labels"}
          </button>
        </div>
      </div>

      {/* Model-Generated Plain English Mechanistic Explanation */}
      <div className="bg-[#F3F1EC] border-l-4 border-[#2F6B5E] p-3.5 rounded-r mb-4 text-xs">
        <span className="font-semibold text-[#1C2421] block mb-1">
          Model-Generated Mechanistic Reasoning:
        </span>
        <p className="text-[#3D4742] leading-normal font-medium italic">
          "{explanationText}"
        </p>
      </div>

      {/* React Flow Interactive Canvas */}
      <div className="h-[420px] w-full border border-[#E5E2DC] rounded-md overflow-hidden relative bg-[#F3F1EC]">
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
          <Background color="#D8D5CE" gap={16} size={1} />
          <Controls showInteractive={false} />
        </ReactFlow>

        {/* Column Guides Overlay */}
        <div className="absolute top-2 left-4 pointer-events-none flex gap-[180px] text-[10px] font-mono text-[#8A918C] uppercase tracking-wide opacity-70">
          <span>1. Compounds</span>
          <span>2. Targets / Enzymes</span>
          <span>3. Cellular Pathways</span>
          <span>4. Indications</span>
        </div>
      </div>

      <div className="mt-3 flex items-center justify-between text-[11px] text-[#7A827C] font-mono">
        <span>
          Click any node or edge to inspect detailed biological metadata
        </span>
        <span>Line thickness = Attribution gradient importance score</span>
      </div>
    </div>
  );
};
