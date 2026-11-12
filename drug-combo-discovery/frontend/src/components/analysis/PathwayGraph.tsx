import React, { useMemo, useState, useCallback, useEffect } from "react";
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
import { Network, Sparkles, Eye, EyeOff } from "lucide-react";
import type { ExplanationEdge } from "../../types/api";

interface PathwayGraphProps {
  topEdges: ExplanationEdge[];
  drugAName: string;
  drugBName: string;
  explanationText: string;
  onSelectEntity?: (entity: { type: "node" | "edge"; data: any }) => void;
}

// Custom Biological Node Component — themed with CSS variables
const BiologicalNode = ({ data }: { data: any }) => {
  const nodeType = data.nodeType as "drug" | "protein" | "pathway" | "disease";

  const typeConfig: Record<
    string,
    { badgeBg: string; badgeText: string; borderColor: string; glow: string }
  > = {
    drug: {
      badgeBg: "bg-[#00D6A0]/15",
      badgeText: "text-[#00D6A0] font-bold",
      borderColor: "border-[#00D6A0]",
      glow: "shadow-[0_0_12px_rgba(0,214,160,0.2)]",
    },
    protein: {
      badgeBg: "bg-[#C7A76A]/15",
      badgeText: "text-[#C7A76A] font-semibold",
      borderColor: "border-[#C7A76A]",
      glow: "shadow-none",
    },
    pathway: {
      badgeBg: "bg-[#35C9D5]/15",
      badgeText: "text-[#35C9D5] font-semibold",
      borderColor: "border-[#35C9D5]",
      glow: "shadow-none",
    },
    disease: {
      badgeBg: "bg-[#E05260]/15",
      badgeText: "text-[#E05260] font-semibold",
      borderColor: "border-[#E05260]",
      glow: "shadow-none",
    },
  };

  const config = typeConfig[nodeType] ?? {
    badgeBg: "bg-[var(--color-panel)]",
    badgeText: "text-[var(--color-text-muted)]",
    borderColor: "border-[var(--color-rule)]",
    glow: "shadow-none",
  };

  return (
    <div
      className={`px-3 py-2 min-w-[135px] max-w-[195px] rounded-md cursor-pointer transition-all duration-200 bg-[var(--color-surface)] border ${config.borderColor} ${config.glow} hover:scale-105 hover:border-[var(--color-accent)] hover:shadow-[0_0_16px_var(--color-accent-glow)]`}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="!bg-[var(--color-accent)] !w-2 !h-2"
      />
      <div className="flex items-center justify-between mb-1 gap-1">
        <span
          className={`text-[9.5px] uppercase tracking-wider px-1.5 py-0.2 rounded font-mono ${config.badgeBg} ${config.badgeText}`}
        >
          {data.nodeType}
        </span>
        {data.isHub && (
          <span className="text-[9px] font-mono font-bold uppercase text-[var(--color-accent)] bg-[var(--color-accent-soft)] px-1 rounded">
            Hub
          </span>
        )}
      </div>
      <div
        className="text-[12.5px] font-medium text-[var(--color-text-primary)] truncate font-sans"
        title={data.label}
      >
        {data.label}
      </div>
      <Handle
        type="source"
        position={Position.Right}
        className="!bg-[var(--color-accent)] !w-2 !h-2"
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
    (topEdges || []).forEach((e) => {
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

    const maxImportance = Math.max(
      ...(topEdges || []).map((e) => Math.abs(e.importance || 0)),
      1e-6,
    );

    const edgesList: Edge[] = (topEdges || []).map((e, idx) => {
      const importanceNorm = Math.max(
        0.1,
        Math.min(1.0, Math.abs(e.importance || 0) / maxImportance),
      );
      const strokeWidth = 1.5 + importanceNorm * 2.5;
      const isHighImportance = importanceNorm > 0.5;

      return {
        id: `edge-${idx}`,
        source: e.source,
        target: e.target,
        type: "smoothstep",
        animated: isHighImportance,
        label: showLabels ? e.relation.replace(/_/g, " ") : undefined,
        labelStyle: {
          fontSize: 10,
          fill: "var(--color-text-muted)",
          fontFamily: "var(--font-sans)",
        },
        labelBgStyle: {
          fill: "var(--color-panel)",
          fillOpacity: 0.95,
          stroke: "var(--color-rule)",
        },
        style: {
          stroke: isHighImportance
            ? "var(--color-accent)"
            : "var(--color-rule-strong)",
          strokeWidth,
          opacity: isHighImportance ? 1 : 0.65,
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          width: 12,
          height: 12,
          color: isHighImportance
            ? "var(--color-accent)"
            : "var(--color-rule-strong)",
        },
        data: e,
      };
    });

    return { initialNodes: nodesList, initialEdges: edgesList };
  }, [topEdges, drugAName, drugBName, showLabels]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  useEffect(() => {
    setNodes(initialNodes);
    setEdges(initialEdges);
  }, [initialNodes, initialEdges, setNodes, setEdges]);

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
    <div className="p-4 space-y-4">
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <Network className="w-4 h-4 text-[var(--color-accent)]" />
            <h3 className="section-title text-[16px]">
              Attribution Pathway Map
            </h3>
          </div>
          <p className="meta-text mt-0.5">
            Local PrimeKG explanation subgraph · {(topEdges || []).length}{" "}
            attributed edges
          </p>
        </div>

        <div className="flex items-center gap-3 flex-wrap text-[11px] text-[var(--color-text-muted)]">
          {/* Legend pills */}
          <span className="flex items-center gap-1.5 font-mono">
            <span className="w-2 h-2 rounded-full bg-[#00D6A0] shadow-[0_0_6px_#00D6A0]" />
            Drug
          </span>
          <span className="flex items-center gap-1.5 font-mono">
            <span className="w-2 h-2 rounded-full bg-[#C7A76A]" />
            Protein
          </span>
          <span className="flex items-center gap-1.5 font-mono">
            <span className="w-2 h-2 rounded-full bg-[#35C9D5]" />
            Pathway
          </span>
          <span className="flex items-center gap-1.5 font-mono">
            <span className="w-2 h-2 rounded-full bg-[#E05260]" />
            Disease
          </span>

          <button
            type="button"
            onClick={() => setShowLabels((prev) => !prev)}
            className="flex items-center gap-1 ml-2 font-mono text-[11px] text-[var(--color-accent)] hover:underline cursor-pointer"
          >
            {showLabels ? <EyeOff size={12} /> : <Eye size={12} />}
            <span>{showLabels ? "Hide edge labels" : "Show edge labels"}</span>
          </button>
        </div>
      </div>

      {/* Mechanistic reasoning callout */}
      {explanationText && (
        <div className="p-3.5 rounded-lg border-l-4 border-l-[var(--color-accent)] bg-[var(--color-accent-soft)] text-[13.5px]">
          <div className="flex items-center gap-1.5 font-mono text-[11px] font-bold uppercase text-[var(--color-accent)] mb-1">
            <Sparkles size={12} />
            <span>PrimeKG Mechanistic Reasoning</span>
          </div>
          <p className="leading-relaxed text-[var(--color-text-secondary)]">
            {explanationText}
          </p>
        </div>
      )}

      {/* ReactFlow canvas */}
      <div className="h-[500px] w-full rounded-lg overflow-hidden relative border border-[var(--color-rule)] bg-[var(--color-surface)] shadow-inner">
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
          <Background color="var(--color-rule)" gap={16} size={1} />
          <Controls showInteractive={false} />
        </ReactFlow>

        {/* Axis layout tag */}
        <div className="absolute top-3 left-3 pointer-events-none z-10 flex items-center gap-2 text-[10.5px] font-mono px-3 py-1 rounded-md bg-[var(--color-panel)] border border-[var(--color-rule)] text-[var(--color-text-muted)] shadow-md">
          <span className="font-bold text-[var(--color-accent)]">
            Flow Axis:
          </span>
          <span>Compounds</span>
          <span>→</span>
          <span>Targets</span>
          <span>→</span>
          <span>Pathways</span>
          <span>→</span>
          <span>Indications</span>
        </div>
      </div>

      <div className="flex items-center justify-between text-[11px] text-[var(--color-text-muted)]">
        <span>
          Click any node or relation edge to inspect attribute weight details
        </span>
        <span className="font-mono">
          Pulsing edges = Top gradient importance
        </span>
      </div>
    </div>
  );
};
