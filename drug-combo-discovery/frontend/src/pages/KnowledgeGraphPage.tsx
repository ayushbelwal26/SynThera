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
import { PRIME_KG_SUBGRAPH } from "../services/kgData";
import type { KGNode, EntityType } from "../types/api";
import {
  Search,
  Filter,
  X,
  Database,
} from "lucide-react";

// Distinct Biological Intelligence Nodes
const PrimeKGNode = ({ data }: { data: any }) => {
  const nodeType = data.type as EntityType;

  // Visual treatments per blueprint:
  // Drug: Emerald (#00D6A0)
  // Protein: Gold (#C7A76A)
  // Pathway: Cyan (#35C9D5)
  // Disease: Antagonism / Magenta Red (#E05260)
  const styles: Record<
    string,
    { badgeBg: string; badgeText: string; border: string; glow: string }
  > = {
    drug: {
      badgeBg: "bg-[#00D6A0]/15",
      badgeText: "text-[#00D6A0]",
      border: "border-[#00D6A0]",
      glow: "shadow-[0_0_12px_rgba(0,214,160,0.2)]",
    },
    protein: {
      badgeBg: "bg-[#C7A76A]/15",
      badgeText: "text-[#C7A76A]",
      border: "border-[#C7A76A]",
      glow: "shadow-[0_0_8px_rgba(199,167,106,0.15)]",
    },
    gene: {
      badgeBg: "bg-[#C7A76A]/15",
      badgeText: "text-[#C7A76A]",
      border: "border-[#C7A76A]",
      glow: "shadow-[0_0_8px_rgba(199,167,106,0.15)]",
    },
    pathway: {
      badgeBg: "bg-[#35C9D5]/15",
      badgeText: "text-[#35C9D5]",
      border: "border-[#35C9D5]",
      glow: "shadow-[0_0_8px_rgba(53,201,213,0.15)]",
    },
    disease: {
      badgeBg: "bg-[#E05260]/15",
      badgeText: "text-[#E05260]",
      border: "border-[#E05260]",
      glow: "shadow-[0_0_8px_rgba(224,82,96,0.15)]",
    },
  };

  const style = styles[nodeType] ?? {
    badgeBg: "bg-[#20343C]",
    badgeText: "text-[#94A5A6]",
    border: "border-[#20343C]",
    glow: "shadow-none",
  };

  const isHighlighted = data.isHighlighted;

  return (
    <div
      className={`px-3 py-2 rounded-lg border min-w-[135px] max-w-[190px] cursor-pointer transition-all duration-200 bg-[#0E181F] ${
        isHighlighted
          ? `${style.border} ring-2 ring-[#00D6A0] ${style.glow} scale-105`
          : `${style.border} hover:border-[#00D6A0] hover:scale-102`
      }`}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="!bg-[#00D6A0] !w-2 !h-2"
      />
      <div className="flex items-center justify-between mb-1 gap-1">
        <span
          className={`text-[9.5px] uppercase font-mono font-semibold tracking-wider px-1.5 py-0.2 rounded ${style.badgeBg} ${style.badgeText}`}
        >
          {data.type}
        </span>
        {data.degree && (
          <span className="text-[9.5px] font-mono text-[#60747A]">
            deg: {data.degree}
          </span>
        )}
      </div>
      <div
        className="text-[12.5px] font-medium text-[#F1F5F2] truncate font-sans"
        title={data.name}
      >
        {data.name}
      </div>
      <Handle
        type="source"
        position={Position.Right}
        className="!bg-[#00D6A0] !w-2 !h-2"
      />
    </div>
  );
};

const nodeTypes = {
  primeKgNode: PrimeKGNode,
};

export const NeighborhoodPage: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState("Cyclophosphamide");
  const [selectedTypes, setSelectedTypes] = useState<Set<string>>(
    new Set(["drug", "protein", "pathway", "disease"]),
  );
  const [selectedEntity, setSelectedEntity] = useState<KGNode | null>(null);

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

  const MAX_NODES = 26;

  // Compute 1-hop biological neighbourhood
  const { flowNodes, flowEdges } = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();

    // Identify anchor nodes
    let anchorNodes = PRIME_KG_SUBGRAPH.nodes.filter(
      (n) => q && n.name.toLowerCase().includes(q),
    );
    if (anchorNodes.length === 0) {
      anchorNodes = PRIME_KG_SUBGRAPH.nodes.slice(0, 2);
    }
    const anchorIds = new Set(anchorNodes.map((n) => n.id));

    // Filter edges incident to anchors
    const incidentEdges = PRIME_KG_SUBGRAPH.edges.filter(
      (e) =>
        (anchorIds.has(e.source) || anchorIds.has(e.target)) &&
        selectedRelations.has(e.relation),
    );

    // Collect neighbour node IDs
    const neighbourIds = new Set<string>();
    incidentEdges.forEach((e) => {
      if (anchorIds.has(e.source)) neighbourIds.add(e.target);
      if (anchorIds.has(e.target)) neighbourIds.add(e.source);
    });

    const validNeighbourNodes = PRIME_KG_SUBGRAPH.nodes
      .filter((n) => neighbourIds.has(n.id) && selectedTypes.has(n.type))
      .slice(0, MAX_NODES - anchorNodes.length);

    const activeNodeIds = new Set([
      ...anchorIds,
      ...validNeighbourNodes.map((n) => n.id),
    ]);

    // Radial layout coordinates
    const centerX = 500;
    const centerY = 300;
    const radiusX = 380;
    const radiusY = 230;

    const anchorFlowNodes: Node[] = anchorNodes.map((n, i) => ({
      id: n.id,
      type: "primeKgNode",
      position: {
        x: centerX + (anchorNodes.length > 1 ? (i - (anchorNodes.length - 1) / 2) * 200 : 0),
        y: centerY,
      },
      data: { ...n, isHighlighted: true, isAnchor: true },
    }));

    const peripheryFlowNodes: Node[] = validNeighbourNodes.map((n, i) => {
      const angle = (i / Math.max(1, validNeighbourNodes.length)) * 2 * Math.PI;
      const x = centerX + radiusX * Math.cos(angle);
      const y = centerY + radiusY * Math.sin(angle);
      return {
        id: n.id,
        type: "primeKgNode",
        position: { x, y },
        data: {
          ...n,
          isHighlighted: selectedEntity ? selectedEntity.id === n.id : false,
        },
      };
    });

    const finalEdges: Edge[] = incidentEdges
      .filter((e) => activeNodeIds.has(e.source) && activeNodeIds.has(e.target))
      .map((e, idx) => ({
        id: `kg_edge_${idx}`,
        source: e.source,
        target: e.target,
        type: "default",
        style: {
          stroke: "#2C4A54",
          strokeWidth: 1.2,
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          width: 8,
          height: 8,
          color: "#2C4A54",
        },
        label: e.relation.replace(/_/g, " "),
        labelStyle: {
          fontSize: 9.5,
          fill: "#60747A",
          fontFamily: "IBM Plex Mono, monospace",
        },
        labelBgStyle: { fill: "#0E181F", fillOpacity: 0.95 },
        data: e,
      }));

    return {
      flowNodes: [...anchorFlowNodes, ...peripheryFlowNodes],
      flowEdges: finalEdges,
    };
  }, [searchQuery, selectedTypes, selectedRelations, selectedEntity]);

  const handleNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    const rawNode = PRIME_KG_SUBGRAPH.nodes.find((n) => n.id === node.id);
    if (rawNode) setSelectedEntity(rawNode);
  }, []);

  const connectedEdges = useMemo(() => {
    if (!selectedEntity) return [];
    return PRIME_KG_SUBGRAPH.edges.filter(
      (e) => e.source === selectedEntity.id || e.target === selectedEntity.id,
    );
  }, [selectedEntity]);

  return (
    <div className="space-y-8">
      {/* ── Page Header ── */}
      <div className="border-b border-[#20343C] pb-6 flex flex-col md:flex-row md:items-end justify-between gap-6">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="section-label">04 · Biological Intelligence</span>
            <span className="text-[#20343C]">•</span>
            <span className="font-mono text-[11px] text-[#94A5A6]">
              Harvard PrimeKG Multi-Relational Graph
            </span>
          </div>
          <h1 className="editorial-title text-[#F1F5F2]">
            PrimeKG Neighborhood Knowledge Graph
          </h1>
          <p className="editorial-sub max-w-2xl mt-2">
            Investigate multi-relational drug–protein–pathway–disease networks.
            Inspect 1-hop biological mechanisms driving GNN synergy predictions.
          </p>
        </div>

        {/* Anchor Entity Search */}
        <div className="w-full md:w-80">
          <label className="text-[11px] font-mono uppercase text-[#94A5A6] block mb-1">
            Anchor Entity Query
          </label>
          <div className="relative">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="e.g. Cyclophosphamide, MGMT..."
              className="st-input pl-9 pr-8"
            />
            <Search size={15} className="absolute left-3 top-3 text-[#60747A] pointer-events-none" />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery("")}
                className="absolute right-2.5 top-3 text-[#60747A] hover:text-[#00D6A0]"
              >
                <X size={14} />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* ── Filter Controls Bar ── */}
      <div className="st-panel p-5 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[11px] font-mono uppercase text-[#94A5A6] mr-2 flex items-center gap-1.5">
              <Filter size={13} className="text-[#00D6A0]" />
              Entity Filters:
            </span>
            {(["drug", "protein", "pathway", "disease"] as EntityType[]).map((t) => {
              const active = selectedTypes.has(t);
              return (
                <button
                  key={t}
                  type="button"
                  onClick={() => toggleType(t)}
                  className={`px-3 py-1 rounded-md text-[11px] font-mono capitalize border transition-all cursor-pointer ${
                    active
                      ? "bg-[#14242B] text-[#00D6A0] border-[#00D6A0]/50 font-semibold shadow-[0_0_8px_rgba(0,214,160,0.15)]"
                      : "bg-transparent text-[#60747A] border-[#20343C] hover:text-[#F1F5F2]"
                  }`}
                >
                  {t}
                </button>
              );
            })}
          </div>

          <div className="font-mono text-[11.5px] text-[#60747A] flex items-center gap-2">
            <span>Visualized:</span>
            <strong className="text-[#00D6A0]">{flowNodes.length} nodes</strong>
            <span>•</span>
            <strong className="text-[#35C9D5]">{flowEdges.length} edges</strong>
          </div>
        </div>

        {/* Relation Pills */}
        <div className="pt-2 border-t border-[#20343C]/40 flex items-center gap-1.5 flex-wrap text-xs">
          <span className="text-[10px] font-mono uppercase text-[#60747A] mr-1">
            Relations:
          </span>
          {allRelations.map((rel) => {
            const active = selectedRelations.has(rel);
            return (
              <button
                key={rel}
                type="button"
                onClick={() => toggleRelation(rel)}
                className={`font-mono text-[11px] px-2 py-0.5 rounded transition-colors cursor-pointer capitalize ${
                  active
                    ? "bg-[#14242B] text-[#35C9D5] font-medium"
                    : "text-[#60747A] hover:text-[#F1F5F2]"
                }`}
              >
                {rel.replace(/_/g, " ")}
              </button>
            );
          })}
        </div>
      </div>

      {/* ── Main Canvas & Inspector Drawer ── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* React Flow Viewport Canvas */}
        <div className="lg:col-span-8 h-[640px] border border-[#20343C] rounded-2xl overflow-hidden relative bg-[#05090D] shadow-2xl">
          <ReactFlow
            nodes={flowNodes}
            edges={flowEdges}
            nodeTypes={nodeTypes}
            onNodeClick={handleNodeClick}
            fitView
            minZoom={0.2}
            maxZoom={2.2}
          >
            <Background color="#16242B" gap={24} size={1} />
            <Controls showInteractive={false} />
          </ReactFlow>

          {/* Floating Canvas Legend */}
          <div className="absolute top-4 left-4 bg-[#091218]/90 backdrop-blur-md border border-[#20343C] px-3.5 py-2.5 rounded-xl text-[11px] font-mono shadow-xl space-y-1.5">
            <div className="text-[10px] uppercase font-bold text-[#00D6A0]">
              Biological Topology Axis
            </div>
            <div className="flex items-center gap-3">
              <span className="flex items-center gap-1 text-[#F1F5F2]">
                <span className="w-2.5 h-2.5 rounded-full bg-[#00D6A0]" />
                Drug
              </span>
              <span className="flex items-center gap-1 text-[#F1F5F2]">
                <span className="w-2.5 h-2.5 rounded-full bg-[#C7A76A]" />
                Target
              </span>
              <span className="flex items-center gap-1 text-[#F1F5F2]">
                <span className="w-2.5 h-2.5 rounded-full bg-[#35C9D5]" />
                Pathway
              </span>
              <span className="flex items-center gap-1 text-[#F1F5F2]">
                <span className="w-2.5 h-2.5 rounded-full bg-[#E05260]" />
                Disease
              </span>
            </div>
          </div>
        </div>

        {/* Entity Inspector Side Panel */}
        <div className="lg:col-span-4 st-panel p-6 space-y-5 border-l-2 border-l-[#00D6A0] sticky top-24">
          <div className="flex items-start justify-between border-b border-[#20343C] pb-3">
            <div>
              <span className="section-label">Entity Inspector</span>
              <h4 className="font-serif text-[18px] text-[#F1F5F2] mt-1 font-bold">
                {selectedEntity ? selectedEntity.name : "Select an Entity Node"}
              </h4>
            </div>
            {selectedEntity && (
              <button
                type="button"
                onClick={() => setSelectedEntity(null)}
                className="text-[#60747A] hover:text-[#F1F5F2]"
              >
                <X size={15} />
              </button>
            )}
          </div>

          {!selectedEntity ? (
            <div className="p-8 text-center space-y-2 text-[#60747A]">
              <Database size={28} className="mx-auto text-[#20343C]" />
              <p className="text-[12.5px] text-[#94A5A6]">
                Click on any node in the knowledge network to inspect its topological degree,
                identifiers, and incident relations.
              </p>
            </div>
          ) : (
            <div className="space-y-4 text-xs font-mono">
              <div className="grid grid-cols-2 gap-3">
                <div className="p-2.5 rounded-lg bg-[#091218] border border-[#20343C]">
                  <span className="text-[10px] text-[#60747A] uppercase block">Type</span>
                  <span className="font-semibold text-[#00D6A0] capitalize mt-0.5 block">
                    {selectedEntity.type}
                  </span>
                </div>
                <div className="p-2.5 rounded-lg bg-[#091218] border border-[#20343C]">
                  <span className="text-[10px] text-[#60747A] uppercase block">Degree</span>
                  <span className="font-semibold text-[#F1F5F2] mt-0.5 block">
                    {selectedEntity.degree || connectedEdges.length} connections
                  </span>
                </div>
              </div>

              <div>
                <label className="text-[10.5px] uppercase text-[#60747A] block mb-2">
                  Incident Relations ({connectedEdges.length})
                </label>
                <div className="space-y-1.5 max-h-60 overflow-y-auto text-[11px]">
                  {connectedEdges.map((e, idx) => {
                    const isSource = e.source === selectedEntity.id;
                    const partner = isSource ? e.target : e.source;

                    return (
                      <div
                        key={idx}
                        className="p-2 rounded bg-[#091218] border border-[#20343C] flex items-center justify-between"
                      >
                        <span className="truncate mr-2 font-medium text-[#F1F5F2]">
                          {partner}
                        </span>
                        <span className="px-1.5 py-0.5 rounded bg-[#101C23] text-[#35C9D5] text-[10px] uppercase shrink-0 border border-[#20343C]">
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
