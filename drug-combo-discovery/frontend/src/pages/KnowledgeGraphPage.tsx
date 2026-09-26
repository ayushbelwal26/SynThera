import React, { useState, useMemo, useCallback } from "react";
import {
  ReactFlow,
  Controls,
  Background,
  MarkerType,
  Handle,
  Position,
} from "@xyflow/react";
import type { Node, Edge } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Network, Search, Filter, X, Dna } from "lucide-react";
import { PRIME_KG_SUBGRAPH } from "../services/kgData";
import type { KGNode, EntityType } from "../types/api";

// Custom Biological Node for KG Explorer (matches PathwayGraph design language)
const KGExplorerNode = ({ data }: { data: any }) => {
  const typeStyles = {
    drug: {
      bg: "bg-[#E8F0ED]",
      border: "border-[#2F6B5E]",
      badge: "bg-[#D4E5DF] text-[#25564B]",
    },
    protein: {
      bg: "bg-[#F7F0E4]",
      border: "border-[#B8893D]",
      badge: "bg-[#F5EFE4] text-[#7A5A28]",
    },
    gene: {
      bg: "bg-[#F7F0E4]",
      border: "border-[#B8893D]",
      badge: "bg-[#F5EFE4] text-[#7A5A28]",
    },
    pathway: {
      bg: "bg-[#F3F0F7]",
      border: "border-[#8B7BA8]",
      badge: "bg-[#EDE8F3] text-[#6B5B8A]",
    },
    disease: {
      bg: "bg-[#E6F2F2]",
      border: "border-[#4A8B8A]",
      badge: "bg-[#D4E8E8] text-[#2F5E5D]",
    },
  }[data.type as EntityType] || {
    bg: "bg-[#FFFEFB]",
    border: "border-[#D8D5CE]",
    badge: "bg-[#EEEBE5] text-[#5A635E]",
  };

  const isHighlighted = data.isHighlighted;

  return (
    <div
      className={`px-3 py-2 rounded-md border shadow-xs min-w-[130px] max-w-[190px] cursor-pointer transition-all ${
        isHighlighted
          ? "ring-2 ring-[#2F6B5E] scale-105 shadow-md " + typeStyles.bg
          : "hover:ring-1 hover:ring-[#2F6B5E]/40 " + typeStyles.bg
      } ${typeStyles.border}`}
    >
      <Handle type="target" position={Position.Top} className="!bg-[#6B746F]" />
      <div className="flex items-center justify-between mb-1">
        <span
          className={`text-[9px] font-mono font-semibold uppercase px-1.5 py-0.5 rounded ${typeStyles.badge}`}
        >
          {data.type}
        </span>
        {data.degree && (
          <span className="text-[9px] font-mono text-[#6B746F]">
            deg: {data.degree}
          </span>
        )}
      </div>
      <div
        className="text-xs font-semibold text-[#1C2421] truncate"
        title={data.name}
      >
        {data.name}
      </div>
      <Handle
        type="source"
        position={Position.Bottom}
        className="!bg-[#6B746F]"
      />
    </div>
  );
};

const nodeTypes = {
  kgNode: KGExplorerNode,
};

export const KnowledgeGraphPage: React.FC = () => {
  // Pre-populate with Cyclophosphamide so the page opens on the demo anchor drug's
  // 1-hop neighborhood rather than an arbitrary full-graph slice.
  const [searchQuery, setSearchQuery] = useState("Cyclophosphamide");
  const [selectedTypes, setSelectedTypes] = useState<Set<string>>(
    new Set(["drug", "protein", "pathway", "disease"]),
  );
  const [selectedEntity, setSelectedEntity] = useState<KGNode | null>(null);

  // Available relation types
  const allRelations = useMemo(() => {
    const set = new Set<string>();
    PRIME_KG_SUBGRAPH.edges.forEach((e) => set.add(e.relation));
    return Array.from(set);
  }, []);

  const [selectedRelations, setSelectedRelations] = useState<Set<string>>(
    new Set(allRelations),
  );

  const toggleType = (t: string) => {
    setSelectedTypes((prev) => {
      const next = new Set(prev);
      if (next.has(t)) {
        if (next.size > 1) next.delete(t);
      } else {
        next.add(t);
      }
      return next;
    });
  };

  const toggleRelation = (r: string) => {
    setSelectedRelations((prev) => {
      const next = new Set(prev);
      if (next.has(r)) {
        if (next.size > 1) next.delete(r);
      } else {
        next.add(r);
      }
      return next;
    });
  };

  // ---------------------------------------------------------------------------
  // Neighbourhood computation — when a search query is active, resolve the
  // 1-hop neighborhood of all matching anchor nodes (anchor + immediate
  // neighbors) capped at MAX_NEIGHBOURHOOD_NODES for readability.
  // Returns null when search is empty (→ show full subgraph).
  // ---------------------------------------------------------------------------
  const MAX_NEIGHBOURHOOD_NODES = 25;

  const neighbourhoodNodeIds = useMemo<Set<string> | null>(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return null; // no filter — show full graph

    // Find all nodes whose name matches the query
    const anchorIds = new Set<string>(
      PRIME_KG_SUBGRAPH.nodes
        .filter((n) => n.name.toLowerCase().includes(q))
        .map((n) => n.id),
    );
    if (anchorIds.size === 0) return new Set(); // no match → empty graph

    // Collect 1-hop neighbors via edge traversal
    const neighbourhood = new Set<string>(anchorIds);
    PRIME_KG_SUBGRAPH.edges.forEach((e) => {
      if (anchorIds.has(e.source)) neighbourhood.add(e.target);
      if (anchorIds.has(e.target)) neighbourhood.add(e.source);
    });

    // Cap at MAX_NEIGHBOURHOOD_NODES — keep anchors, then fill neighbors
    if (neighbourhood.size > MAX_NEIGHBOURHOOD_NODES) {
      const capped = new Set<string>(anchorIds);
      for (const id of neighbourhood) {
        if (capped.size >= MAX_NEIGHBOURHOOD_NODES) break;
        capped.add(id);
      }
      return capped;
    }
    return neighbourhood;
  }, [searchQuery]);

  // Filter and arrange nodes
  const { flowNodes, flowEdges } = useMemo(() => {
    // 1. Filter edges by selected relation
    const validEdges = PRIME_KG_SUBGRAPH.edges.filter((e) =>
      selectedRelations.has(e.relation),
    );

    // 2. Identify nodes incident to valid edges and matching type
    const incidentNodeIds = new Set<string>();
    validEdges.forEach((e) => {
      incidentNodeIds.add(e.source);
      incidentNodeIds.add(e.target);
    });

    let validNodes = PRIME_KG_SUBGRAPH.nodes.filter(
      (n) => incidentNodeIds.has(n.id) && selectedTypes.has(n.type),
    );

    // 3. When a search is active, restrict to 1-hop neighbourhood
    if (neighbourhoodNodeIds !== null) {
      validNodes = validNodes.filter((n) => neighbourhoodNodeIds.has(n.id));
    }

    const validNodeIdSet = new Set(validNodes.map((n) => n.id));

    // Refine edges so both endpoints are in the visible node set
    const finalEdges = validEdges.filter(
      (e) => validNodeIdSet.has(e.source) && validNodeIdSet.has(e.target),
    );

    // Circular / layered layout — anchor drug placed at center
    const q = searchQuery.trim().toLowerCase();
    const anchorNodes = validNodes.filter(
      (n) => q && n.name.toLowerCase().includes(q),
    );
    const peripheryNodes = validNodes.filter(
      (n) => !anchorNodes.find((a) => a.id === n.id),
    );

    // Place anchor(s) at center, periphery in orbit
    const total = peripheryNodes.length;
    const radiusX = 380;
    const radiusY = 240;
    const centerX = 500;
    const centerY = 300;

    const anchorFlow: Node[] = anchorNodes.map((n, i) => ({
      id: n.id,
      type: "kgNode",
      position: {
        x:
          centerX +
          (anchorNodes.length > 1
            ? (i - (anchorNodes.length - 1) / 2) * 220
            : 0),
        y: centerY,
      },
      data: { ...n, isHighlighted: true, isAnchor: true },
    }));

    const peripheryFlow: Node[] = peripheryNodes.map((n, i) => {
      const angle = (i / Math.max(1, total)) * 2 * Math.PI;
      const x = centerX + radiusX * Math.cos(angle);
      const y = centerY + radiusY * Math.sin(angle);
      return {
        id: n.id,
        type: "kgNode",
        position: { x, y },
        data: {
          ...n,
          isHighlighted: selectedEntity ? selectedEntity.id === n.id : false,
        },
      };
    });

    const nodesList: Node[] = [...anchorFlow, ...peripheryFlow];

    const edgesList: Edge[] = finalEdges.map((e, idx) => {
      const isAnchorEdge = anchorNodes.some(
        (a) => a.id === e.source || a.id === e.target,
      );
      return {
        id: `kg-edge-${idx}`,
        source: e.source,
        target: e.target,
        type: "default",
        style: {
          stroke: isAnchorEdge ? "#2F6B5E" : "#8A918C",
          strokeWidth: isAnchorEdge ? 2 : 1.2,
          opacity: isAnchorEdge ? 1 : 0.6,
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          width: 10,
          height: 10,
          color: isAnchorEdge ? "#2F6B5E" : "#8A918C",
        },
        data: e,
        label: e.relation.replace(/_/g, " "),
        labelStyle: { fontSize: 9, fill: "#6B746F", fontFamily: "Inter, system-ui, sans-serif" },
        labelBgStyle: { fill: "#F3F1EC", fillOpacity: 0.85 },
      };
    });

    return { flowNodes: nodesList, flowEdges: edgesList };
  }, [
    selectedTypes,
    selectedRelations,
    searchQuery,
    selectedEntity,
    neighbourhoodNodeIds,
  ]);

  const handleNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    const rawNode = PRIME_KG_SUBGRAPH.nodes.find((n) => n.id === node.id);
    if (rawNode) setSelectedEntity(rawNode);
  }, []);

  // Connected neighbors of selected entity
  const connectedEdges = useMemo(() => {
    if (!selectedEntity) return [];
    return PRIME_KG_SUBGRAPH.edges.filter(
      (e) => e.source === selectedEntity.id || e.target === selectedEntity.id,
    );
  }, [selectedEntity]);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="border-b border-[#E5E2DC] pb-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <Network className="w-5 h-5 text-[#2F6B5E]" />
            <h2 className="text-2xl font-semibold text-[#1C2421]">
              PrimeKG Knowledge Graph Explorer
            </h2>
          </div>
          <p className="text-xs text-[#7A827C] mt-0.5">
            Exploratory topology of verified precision oncology relationships
            across Drugs, Targets, Pathways, and Indications
          </p>
        </div>

        {/* Search Bar */}
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 text-[#8A918C] absolute inset-y-0 left-3 my-auto pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search entity (e.g. Cyclophosphamide, MGMT)..."
            className="w-full pl-9 pr-8 py-2 bg-[#FFFEFB] border border-[#D8D5CE] focus:border-[#2F6B5E] rounded-md text-xs text-[#1C2421] outline-none"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => setSearchQuery("")}
              title="Clear search — shows full subgraph"
              className="absolute inset-y-0 right-2 my-auto text-[#8A918C] hover:text-[#1C2421]"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
          {/* Neighbourhood mode badge */}
          {searchQuery.trim() && (
            <span className="absolute -bottom-5 left-0 text-[10px] font-mono text-[#2F6B5E]">
              Showing 1-hop neighbourhood · clear to see full slice
            </span>
          )}
        </div>
      </div>

      {/* Prominent Scientific Scope Banner */}
      <div className="bg-[#F3F1EC] border border-[#D8D5CE] rounded-md px-4 py-2.5 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs text-[#3D4742]">
        <div className="flex items-center gap-2">
          <Dna className="w-4 h-4 text-[#2F6B5E] shrink-0" />
          <span>
            <strong>Curated Subgraph Scope: </strong>
            Showing a curated oncology subgraph (8 reference compounds, 76
            biological entities, 120 verified edges) extracted from PrimeKG —
            not the full PrimeKG index.
          </span>
        </div>
        <span className="text-[11px] font-mono text-[#6B746F] shrink-0 bg-[#EEEBE5] px-2 py-0.5 rounded border border-[#E5E2DC]">
          Static Slice &bull; Live Graph API planned
        </span>
      </div>

      {/* Filter Bar: Node Types & Relation Types */}
      <div className="syn-card rounded-lg p-4 space-y-3 text-xs">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-2.5 flex-wrap">
            <span className="font-semibold text-[#5A635E] uppercase tracking-wide text-[11px] flex items-center gap-1.5">
              <Filter className="w-3.5 h-3.5 text-[#2F6B5E]" />
              Entity Types:
            </span>
            {(["drug", "protein", "pathway", "disease"] as EntityType[]).map(
              (t) => {
                const isChecked = selectedTypes.has(t);
                return (
                  <button
                    key={t}
                    type="button"
                    onClick={() => toggleType(t)}
                    className={`px-2.5 py-1 rounded font-mono uppercase tracking-wide border transition-all cursor-pointer ${
                      isChecked
                        ? t === "drug"
                          ? "bg-[#D4E5DF] text-[#25564B] border-[#2F6B5E]"
                          : t === "protein"
                            ? "bg-[#F5EFE4] text-[#7A5A28] border-[#B8893D]"
                            : t === "pathway"
                              ? "bg-[#EDE8F3] text-[#6B5B8A] border-[#8B7BA8]"
                              : "bg-[#D4E8E8] text-[#2F5E5D] border-[#4A8B8A]"
                        : "bg-[#F3F1EC] text-[#8A918C] border-[#E5E2DC]"
                    }`}
                  >
                    {t}
                  </button>
                );
              },
            )}
          </div>

          <div className="flex items-center gap-2 text-[11px] font-mono text-[#6B746F]">
            <span>Displaying:</span>
            <strong className="text-[#1C2421]">{flowNodes.length} nodes</strong>
            <span>&bull;</span>
            <strong className="text-[#1C2421]">{flowEdges.length} edges</strong>
          </div>
        </div>

        {/* Relation Filter Tags */}
        <div className="flex items-center gap-2 flex-wrap pt-2 border-t border-[#EEEBE5]">
          <span className="font-semibold text-[#5A635E] text-[11px] uppercase tracking-wide">
            Relations:
          </span>
          {allRelations.map((rel) => {
            const isChecked = selectedRelations.has(rel);
            return (
              <button
                key={rel}
                type="button"
                onClick={() => toggleRelation(rel)}
                className={`text-[10px] font-mono px-2 py-0.5 rounded border transition-colors cursor-pointer ${
                  isChecked
                    ? "bg-[#E8F0ED] text-[#25564B] border-[#B5CFC6]"
                    : "bg-[#F3F1EC] text-[#8A918C] border-[#E5E2DC]"
                }`}
              >
                {rel.replace(/_/g, " ")}
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Canvas & Inspector Split */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        <div className="lg:col-span-3 h-[580px] border border-[#D0CDC5] rounded-lg overflow-hidden relative bg-[#F3F1EC] shadow-[0_1px_2px_rgba(28,36,33,0.04),0_4px_14px_rgba(28,36,33,0.07)]">
          <ReactFlow
            nodes={flowNodes}
            edges={flowEdges}
            nodeTypes={nodeTypes}
            onNodeClick={handleNodeClick}
            fitView
            minZoom={0.2}
            maxZoom={2.5}
          >
            <Background color="#D8D5CE" gap={16} size={1} />
            <Controls showInteractive={false} />
          </ReactFlow>

          {flowNodes.length === 0 && (
            <div className="absolute inset-0 flex flex-col items-center justify-center p-8 text-center bg-[#FFFEFB]/95 z-10">
              <p className="text-sm font-semibold text-[#1C2421] mb-1">
                No matching entities in the curated oncology slice
              </p>
              <p className="text-xs text-[#6B746F] max-w-md leading-normal mb-4">
                The explorer currently bundles a curated reference slice (8
                compounds, 76 entities, 120 verified edges) extracted from
                PrimeKG. The full PrimeKG index contains 7,946 drugs and 19,585
                proteins; a live backend subgraph streaming endpoint would be
                required to query the complete 4.3M-edge graph.
              </p>
              <button
                type="button"
                onClick={() => {
                  setSearchQuery("Cyclophosphamide");
                  setSelectedTypes(
                    new Set(["drug", "protein", "pathway", "disease"]),
                  );
                  setSelectedRelations(new Set(allRelations));
                }}
                className="px-3 py-1.5 bg-[#2F6B5E] hover:bg-[#25564B] text-[#FFFEFB] rounded text-xs font-semibold cursor-pointer"
              >
                Reset to Default View
              </button>
            </div>
          )}

          <div className="absolute bottom-3 left-3 bg-[#FFFEFB]/90 border border-[#E5E2DC] px-2.5 py-1 rounded text-[11px] font-mono text-[#6B746F] pointer-events-none">
            Click any node to open metadata inspection panel
          </div>
        </div>

        {/* Entity Inspector Drawer */}
        <div className="syn-card rounded-lg p-4 flex flex-col">
          <div className="flex items-center justify-between border-b border-[#E5E2DC] pb-3 mb-4">
            <h3 className="text-sm font-semibold text-[#1C2421] uppercase tracking-wide">
              Entity Inspector
            </h3>
            {selectedEntity && (
              <button
                type="button"
                onClick={() => setSelectedEntity(null)}
                className="text-[#8A918C] hover:text-[#1C2421]"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          {!selectedEntity ? (
            <div className="flex-1 flex flex-col items-center justify-center text-center p-6 text-[#8A918C]">
              <Dna className="w-8 h-8 text-[#D8D5CE] mb-2" />
              <p className="text-xs">
                Select an entity in the graph to inspect its topological degree,
                annotations, and connected interactions.
              </p>
            </div>
          ) : (
            <div className="space-y-4 text-xs overflow-y-auto max-h-[500px]">
              <div>
                <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-[#EEEBE5] text-[#6B746F] border border-[#E5E2DC]">
                  {selectedEntity.type}
                </span>
                <h4 className="text-lg font-semibold text-[#1C2421] mt-1.5">
                  {selectedEntity.name}
                </h4>
              </div>

              <div className="bg-[#F3F1EC] border border-[#E5E2DC] rounded p-3 font-mono space-y-1.5">
                <div className="flex justify-between">
                  <span className="text-[#6B746F]">Entity ID:</span>
                  <span className="font-semibold text-[#1C2421]">
                    {selectedEntity.id}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#6B746F]">Network Degree:</span>
                  <span className="font-bold text-[#2F6B5E]">
                    {selectedEntity.degree || connectedEdges.length}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#6B746F]">Namespace:</span>
                  <span className="text-[#1C2421]">PrimeKG Harmonized</span>
                </div>
              </div>

              <div>
                <span className="font-semibold text-[#3D4742] uppercase tracking-wide text-[11px] block mb-2">
                  Connected Relationships ({connectedEdges.length}):
                </span>
                <div className="space-y-2 max-h-56 overflow-y-auto divide-y divide-[#EEEBE5]">
                  {connectedEdges.map((e, idx) => {
                    const isSource = e.source === selectedEntity.id;
                    const partner = isSource ? e.target : e.source;
                    return (
                      <div
                        key={idx}
                        className="pt-1.5 flex items-center justify-between text-xs"
                      >
                        <div className="truncate mr-2">
                          <span className="font-medium text-[#1C2421]">
                            {partner}
                          </span>
                        </div>
                        <span className="font-mono text-[10px] text-[#2F6B5E] bg-[#E8F0ED] px-1.5 py-0.5 rounded shrink-0">
                          {e.relation}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
