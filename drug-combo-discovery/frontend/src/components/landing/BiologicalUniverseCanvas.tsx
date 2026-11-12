import React, { useRef, useMemo, useState } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import * as THREE from "three";

interface NodeData {
  id: string;
  name: string;
  type: "drug" | "protein" | "pathway" | "disease";
  pos: [number, number, number];
  color: string;
}

const NETWORK_ENTITIES: NodeData[] = [
  { id: "1", name: "Temozolomide", type: "drug", pos: [-2.2, 0.4, 0], color: "#00D6A0" },
  { id: "2", name: "Cyclophosphamide", type: "drug", pos: [-1.8, -1.2, 0.5], color: "#00D6A0" },
  { id: "3", name: "MGMT", type: "protein", pos: [-0.6, 1.2, -0.4], color: "#C7A76A" },
  { id: "4", name: "ALDH1A1", type: "protein", pos: [-0.4, -0.7, 0.8], color: "#C7A76A" },
  { id: "5", name: "EGFR", type: "protein", pos: [0.8, 1.5, 0.2], color: "#C7A76A" },
  { id: "6", name: "O6-Methylguanine DNA Repair", type: "pathway", pos: [1.2, 0.2, -0.8], color: "#35C9D5" },
  { id: "7", name: "Cellular Apoptosis", type: "pathway", pos: [1.6, -1.1, 0.4], color: "#35C9D5" },
  { id: "8", name: "Glioblastoma Multiforme", type: "disease", pos: [2.5, 0.6, 0.3], color: "#E05260" },
  { id: "9", name: "NSCLC", type: "disease", pos: [2.8, -0.8, -0.5], color: "#E05260" },
];

function InteractiveConstellation({
  onHoverNode,
}: {
  onHoverNode: (node: NodeData | null) => void;
}) {
  const groupRef = useRef<THREE.Group>(null);

  // Compute connections
  const lineCoords = useMemo(() => {
    const coords: number[] = [];
    const edges = [
      [0, 2], [1, 3], [2, 5], [3, 6], [4, 5], [5, 7], [6, 7], [4, 8], [6, 8]
    ];

    edges.forEach(([i, j]) => {
      const p1 = NETWORK_ENTITIES[i].pos;
      const p2 = NETWORK_ENTITIES[j].pos;
      coords.push(p1[0], p1[1], p1[2], p2[0], p2[1], p2[2]);
    });

    return new Float32Array(coords);
  }, []);

  useFrame((_, delta) => {
    if (groupRef.current) {
      groupRef.current.rotation.y += delta * 0.06;
    }
  });

  return (
    <group ref={groupRef}>
      {/* Node Spheres */}
      {NETWORK_ENTITIES.map((node) => (
        <mesh
          key={node.id}
          position={node.pos}
          onPointerOver={(e) => {
            e.stopPropagation();
            onHoverNode(node);
          }}
          onPointerOut={() => onHoverNode(null)}
        >
          <sphereGeometry args={[0.13, 16, 16]} />
          <meshStandardMaterial
            color={node.color}
            emissive={node.color}
            emissiveIntensity={0.6}
            roughness={0.2}
          />
        </mesh>
      ))}

      {/* Relational Edge Lines */}
      <lineSegments>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[lineCoords, 3]} />
        </bufferGeometry>
        <lineBasicMaterial color="#35C9D5" transparent opacity={0.28} linewidth={1} />
      </lineSegments>
    </group>
  );
}

export const BiologicalUniverseCanvas: React.FC = () => {
  const [activeNode, setActiveNode] = useState<NodeData | null>(null);

  return (
    <div className="w-full h-full relative">
      <Canvas
        camera={{ position: [0, 0, 6], fov: 45 }}
        gl={{ alpha: true, antialias: true }}
        dpr={[1, 1.75]}
      >
        <ambientLight intensity={0.8} />
        <pointLight position={[10, 10, 10]} intensity={1.5} color="#00D6A0" />
        <InteractiveConstellation onHoverNode={setActiveNode} />
      </Canvas>

      {/* Dynamic Hover Tooltip Overlay */}
      {activeNode && (
        <div className="absolute bottom-6 left-1/2 -translate-x-1/2 pointer-events-none bg-[#101C23]/95 border border-[#20343C] px-4 py-2.5 rounded-xl shadow-2xl backdrop-blur-md flex items-center gap-3 animate-in fade-in duration-150">
          <span
            className="w-2.5 h-2.5 rounded-full"
            style={{ backgroundColor: activeNode.color }}
          />
          <div>
            <div className="font-serif text-[15px] font-bold text-[#F1F5F2]">
              {activeNode.name}
            </div>
            <div className="text-[10px] font-mono uppercase tracking-wider text-[#94A5A6]">
              PrimeKG {activeNode.type} Entity
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

