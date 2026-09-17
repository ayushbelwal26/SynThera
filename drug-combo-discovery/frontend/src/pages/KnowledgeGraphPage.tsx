import React, { useState, useMemo, useCallback } from 'react';
import {
  ReactFlow,
  Controls,
  Background,
  MarkerType,
  Handle,
  Position,
} from '@xyflow/react';
import type { Node, Edge } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import {
  Network,
  Search,
  Filter,
  X,
  Dna,
} from 'lucide-react';
import { PRIME_KG_SUBGRAPH } from '../services/kgData';
import type { KGNode, EntityType } from '../types/api';

// Custom Biological Node for KG Explorer (matches PathwayGraph design language)
const KGExplorerNode = ({ data }: { data: any }) => {
  const typeStyles = {
    drug: {
      bg: 'bg-[#F0FDFA]',
      border: 'border-[#0D9488]',
      badge: 'bg-[#CCFBF1] text-[#0F766E]',
    },
    protein: {
      bg: 'bg-[#FFFBEB]',
      border: 'border-[#D97706]',
      badge: 'bg-[#FEF3C7] text-[#92400E]',
    },
    gene: {
      bg: 'bg-[#FFFBEB]',
      border: 'border-[#D97706]',
      badge: 'bg-[#FEF3C7] text-[#92400E]',
    },
    pathway: {
      bg: 'bg-[#F5F3FF]',
      border: 'border-[#7C3AED]',
      badge: 'bg-[#EDE9FE] text-[#5B21B6]',
    },
    disease: {
      bg: 'bg-[#ECFDF5]',
      border: 'border-[#059669]',
      badge: 'bg-[#D1FAE5] text-[#065F46]',
    },
  }[data.type as EntityType] || {
    bg: 'bg-[#FFFFFF]',
    border: 'border-[#CBD5E1]',
    badge: 'bg-[#F1F5F9] text-[#475569]',
  };

  const isHighlighted = data.isHighlighted;

  return (
    <div
      className={`px-3 py-2 rounded-md border shadow-xs min-w-[130px] max-w-[190px] cursor-pointer transition-all ${
        isHighlighted
          ? 'ring-2 ring-[#0D9488] scale-105 shadow-md ' + typeStyles.bg
          : 'hover:ring-1 hover:ring-[#0D9488]/40 ' + typeStyles.bg
      } ${typeStyles.border}`}
    >
      <Handle type="target" position={Position.Top} className="!bg-[#64748B]" />
      <div className="flex items-center justify-between mb-1">
        <span className={`text-[9px] font-mono font-semibold uppercase px-1.5 py-0.5 rounded ${typeStyles.badge}`}>
          {data.type}
        </span>
        {data.degree && (
          <span className="text-[9px] font-mono text-[#64748B]">
            deg: {data.degree}
          </span>
        )}
      </div>
      <div className="text-xs font-semibold text-[#0F172A] truncate" title={data.name}>
        {data.name}
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-[#64748B]" />
    </div>
  );
};

const nodeTypes = {
  kgNode: KGExplorerNode,
};

export const KnowledgeGraphPage: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTypes, setSelectedTypes] = useState<Set<string>>(
    new Set(['drug', 'protein', 'pathway', 'disease'])
  );
  const [selectedEntity, setSelectedEntity] = useState<KGNode | null>(null);

  // Available relation types
  const allRelations = useMemo(() => {
    const set = new Set<string>();
    PRIME_KG_SUBGRAPH.edges.forEach((e) => set.add(e.relation));
    return Array.from(set);
  }, []);

  const [selectedRelations, setSelectedRelations] = useState<Set<string>>(
    new Set(allRelations)
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

  // Filter and arrange nodes
  const { flowNodes, flowEdges } = useMemo(() => {
    // 1. Filter edges by selected relation
    const validEdges = PRIME_KG_SUBGRAPH.edges.filter((e) =>
      selectedRelations.has(e.relation)
    );

    // 2. Identify nodes incident to valid edges and matching type
    const incidentNodeIds = new Set<string>();
    validEdges.forEach((e) => {
      incidentNodeIds.add(e.source);
      incidentNodeIds.add(e.target);
    });

    const validNodes = PRIME_KG_SUBGRAPH.nodes.filter(
      (n) => incidentNodeIds.has(n.id) && selectedTypes.has(n.type)
    );

    const validNodeIdSet = new Set(validNodes.map((n) => n.id));

    // Refine edges so both endpoints are in validNodeIdSet
    const finalEdges = validEdges.filter(
      (e) => validNodeIdSet.has(e.source) && validNodeIdSet.has(e.target)
    );

    // Circular / layered layout
    const total = validNodes.length;
    const radiusX = 420;
    const radiusY = 260;
    const centerX = 500;
    const centerY = 320;

    const nodesList: Node[] = validNodes.map((n, i) => {
      const angle = (i / Math.max(1, total)) * 2 * Math.PI;
      const x = centerX + radiusX * Math.cos(angle);
      const y = centerY + radiusY * Math.sin(angle);

      const isMatch =
        searchQuery.trim() !== '' &&
        n.name.toLowerCase().includes(searchQuery.toLowerCase());

      return {
        id: n.id,
        type: 'kgNode',
        position: { x, y },
        data: {
          ...n,
          isHighlighted: isMatch || (selectedEntity && selectedEntity.id === n.id),
        },
      };
    });

    const edgesList: Edge[] = finalEdges.map((e, idx) => ({
      id: `kg-edge-${idx}`,
      source: e.source,
      target: e.target,
      type: 'default',
      style: { stroke: '#94A3B8', strokeWidth: 1.2 },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        width: 10,
        height: 10,
        color: '#94A3B8',
      },
      data: e,
    }));

    return { flowNodes: nodesList, flowEdges: edgesList };
  }, [selectedTypes, selectedRelations, searchQuery, selectedEntity]);

  const handleNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    const rawNode = PRIME_KG_SUBGRAPH.nodes.find((n) => n.id === node.id);
    if (rawNode) setSelectedEntity(rawNode);
  }, []);

  // Connected neighbors of selected entity
  const connectedEdges = useMemo(() => {
    if (!selectedEntity) return [];
    return PRIME_KG_SUBGRAPH.edges.filter(
      (e) => e.source === selectedEntity.id || e.target === selectedEntity.id
    );
  }, [selectedEntity]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="border-b border-[#E5E5E0] pb-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <Network className="w-5 h-5 text-[#0D9488]" />
            <h2 className="font-serif text-2xl font-bold text-[#0F172A]">
              PrimeKG Knowledge Graph Explorer
            </h2>
          </div>
          <p className="text-xs text-[#717784] mt-0.5">
            Exploratory topology of verified precision oncology relationships across Drugs, Targets, Pathways, and Indications
          </p>
        </div>

        {/* Search Bar */}
        <div className="relative w-full sm:w-72">
          <Search className="w-4 h-4 text-[#94A3B8] absolute inset-y-0 left-3 my-auto pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search entity (e.g. Temozolomide, MGMT)..."
            className="w-full pl-9 pr-8 py-2 bg-[#FFFFFF] border border-[#CBD5E1] focus:border-[#0D9488] rounded-md text-xs text-[#0F172A] outline-none"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => setSearchQuery('')}
              className="absolute inset-y-0 right-2 my-auto text-[#94A3B8] hover:text-[#0F172A]"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Prominent Scientific Scope Banner */}
      <div className="bg-[#F8FAFC] border border-[#CBD5E1] rounded-md px-4 py-2.5 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs text-[#334155]">
        <div className="flex items-center gap-2">
          <Dna className="w-4 h-4 text-[#0D9488] shrink-0" />
          <span>
            <strong>Curated Subgraph Scope: </strong>
            Showing a curated oncology subgraph (8 reference compounds, 76 biological entities, 120 verified edges) extracted from PrimeKG — not the full PrimeKG index.
          </span>
        </div>
        <span className="text-[11px] font-mono text-[#64748B] shrink-0 bg-[#F1F5F9] px-2 py-0.5 rounded border border-[#E2E8F0]">
          Static Slice &bull; Live Graph API planned
        </span>
      </div>

      {/* Filter Bar: Node Types & Relation Types */}
      <div className="bg-[#FFFFFF] border border-[#E5E5E0] rounded-lg p-4 shadow-xs space-y-3 text-xs">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-2.5 flex-wrap">
            <span className="font-semibold text-[#475569] uppercase tracking-wider text-[11px] flex items-center gap-1.5">
              <Filter className="w-3.5 h-3.5 text-[#0D9488]" />
              Entity Types:
            </span>
            {(['drug', 'protein', 'pathway', 'disease'] as EntityType[]).map((t) => {
              const isChecked = selectedTypes.has(t);
              return (
                <button
                  key={t}
                  type="button"
                  onClick={() => toggleType(t)}
                  className={`px-2.5 py-1 rounded font-mono uppercase tracking-wide border transition-all cursor-pointer ${
                    isChecked
                      ? t === 'drug'
                        ? 'bg-[#CCFBF1] text-[#0F766E] border-[#0D9488]'
                        : t === 'protein'
                        ? 'bg-[#FEF3C7] text-[#92400E] border-[#D97706]'
                        : t === 'pathway'
                        ? 'bg-[#EDE9FE] text-[#5B21B6] border-[#7C3AED]'
                        : 'bg-[#D1FAE5] text-[#065F46] border-[#059669]'
                      : 'bg-[#F8FAFC] text-[#94A3B8] border-[#E2E8F0]'
                  }`}
                >
                  {t}
                </button>
              );
            })}
          </div>

          <div className="flex items-center gap-2 text-[11px] font-mono text-[#64748B]">
            <span>Displaying:</span>
            <strong className="text-[#0F172A]">{flowNodes.length} nodes</strong>
            <span>&bull;</span>
            <strong className="text-[#0F172A]">{flowEdges.length} edges</strong>
          </div>
        </div>

        {/* Relation Filter Tags */}
        <div className="flex items-center gap-2 flex-wrap pt-2 border-t border-[#F1F5F9]">
          <span className="font-semibold text-[#475569] text-[11px] uppercase tracking-wider">
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
                    ? 'bg-[#F0FDFA] text-[#0F766E] border-[#99F6E4]'
                    : 'bg-[#F8FAFC] text-[#94A3B8] border-[#E2E8F0]'
                }`}
              >
                {rel.replace(/_/g, ' ')}
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Canvas & Inspector Split */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-3 h-[580px] border border-[#E5E5E0] rounded-lg overflow-hidden relative bg-[#F8F9FA] shadow-xs">
          <ReactFlow
            nodes={flowNodes}
            edges={flowEdges}
            nodeTypes={nodeTypes}
            onNodeClick={handleNodeClick}
            fitView
            minZoom={0.2}
            maxZoom={2.5}
          >
            <Background color="#CBD5E1" gap={16} size={1} />
            <Controls showInteractive={false} />
          </ReactFlow>

          {flowNodes.length === 0 && (
            <div className="absolute inset-0 flex flex-col items-center justify-center p-8 text-center bg-[#FFFFFF]/95 z-10">
              <p className="font-serif text-sm font-bold text-[#0F172A] mb-1">
                No matching entities in the curated oncology slice
              </p>
              <p className="text-xs text-[#64748B] max-w-md leading-relaxed mb-4">
                The explorer currently bundles a curated reference slice (8 compounds, 76 entities, 120 verified edges) extracted from PrimeKG. The full PrimeKG index contains 7,946 drugs and 19,585 proteins; a live backend subgraph streaming endpoint would be required to query the complete 4.3M-edge graph.
              </p>
              <button
                type="button"
                onClick={() => {
                  setSearchQuery('');
                  setSelectedTypes(new Set(['drug', 'protein', 'pathway', 'disease']));
                  setSelectedRelations(new Set(allRelations));
                }}
                className="px-3 py-1.5 bg-[#0D9488] hover:bg-[#0F766E] text-[#FFFFFF] rounded text-xs font-semibold cursor-pointer"
              >
                Reset Search & Restore Full Slice
              </button>
            </div>
          )}

          <div className="absolute bottom-3 left-3 bg-[#FFFFFF]/90 border border-[#E2E8F0] px-2.5 py-1 rounded text-[11px] font-mono text-[#64748B] pointer-events-none">
            Click any node to open metadata inspection panel
          </div>
        </div>

        {/* Entity Inspector Drawer */}
        <div className="bg-[#FFFFFF] border border-[#E5E5E0] rounded-lg p-5 shadow-xs flex flex-col">
          <div className="flex items-center justify-between border-b border-[#E5E5E0] pb-3 mb-4">
            <h3 className="font-serif text-sm font-bold text-[#0F172A] uppercase tracking-wider">
              Entity Inspector
            </h3>
            {selectedEntity && (
              <button
                type="button"
                onClick={() => setSelectedEntity(null)}
                className="text-[#94A3B8] hover:text-[#0F172A]"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          {!selectedEntity ? (
            <div className="flex-1 flex flex-col items-center justify-center text-center p-6 text-[#94A3B8]">
              <Dna className="w-8 h-8 text-[#CBD5E1] mb-2" />
              <p className="text-xs">
                Select an entity in the graph to inspect its topological degree, annotations, and connected interactions.
              </p>
            </div>
          ) : (
            <div className="space-y-4 text-xs overflow-y-auto max-h-[500px]">
              <div>
                <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-[#F1F5F9] text-[#64748B] border border-[#E2E8F0]">
                  {selectedEntity.type}
                </span>
                <h4 className="font-serif text-lg font-bold text-[#0F172A] mt-1.5">
                  {selectedEntity.name}
                </h4>
              </div>

              <div className="bg-[#F8FAFC] border border-[#E2E8F0] rounded p-3 font-mono space-y-1.5">
                <div className="flex justify-between">
                  <span className="text-[#64748B]">Entity ID:</span>
                  <span className="font-semibold text-[#0F172A]">{selectedEntity.id}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#64748B]">Network Degree:</span>
                  <span className="font-bold text-[#0D9488]">{selectedEntity.degree || connectedEdges.length}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#64748B]">Namespace:</span>
                  <span className="text-[#0F172A]">PrimeKG Harmonized</span>
                </div>
              </div>

              <div>
                <span className="font-semibold text-[#334155] uppercase tracking-wider text-[11px] block mb-2">
                  Connected Relationships ({connectedEdges.length}):
                </span>
                <div className="space-y-2 max-h-56 overflow-y-auto divide-y divide-[#F1F5F9]">
                  {connectedEdges.map((e, idx) => {
                    const isSource = e.source === selectedEntity.id;
                    const partner = isSource ? e.target : e.source;
                    return (
                      <div key={idx} className="pt-1.5 flex items-center justify-between text-xs">
                        <div className="truncate mr-2">
                          <span className="font-medium text-[#0F172A]">{partner}</span>
                        </div>
                        <span className="font-mono text-[10px] text-[#0D9488] bg-[#F0FDFA] px-1.5 py-0.5 rounded shrink-0">
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
