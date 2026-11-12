import React, { useRef, useMemo } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import * as THREE from "three";

interface ConvergenceSceneProps {
  progress?: number; // 0 (isolated) -> 1 (converged network)
}

function ConvergingMolecules({ progress = 0.5 }: ConvergenceSceneProps) {
  const groupRef = useRef<THREE.Group>(null);
  const leftCluster = useRef<THREE.Group>(null);
  const rightCluster = useRef<THREE.Group>(null);
  const bridgingLinesRef = useRef<THREE.LineSegments>(null);

  // Generate 2 compound clusters
  const [molA, molB, bridgeCoords] = useMemo(() => {
    const aPts: number[] = [];
    const bPts: number[] = [];
    const bridges: number[] = [];

    const n = 18;
    for (let i = 0; i < n; i++) {
      const theta = Math.random() * 2 * Math.PI;
      const phi = Math.acos(2 * Math.random() - 1);
      const r = 0.6 + Math.random() * 0.45;

      aPts.push(r * Math.sin(phi) * Math.cos(theta), r * Math.sin(phi) * Math.sin(theta), r * Math.cos(phi));

      const r2 = 0.6 + Math.random() * 0.45;
      bPts.push(r2 * Math.sin(phi) * Math.cos(theta), r2 * Math.sin(phi) * Math.sin(theta), r2 * Math.cos(phi));
    }

    // Cross-connecting bonds between Drug A and Drug B
    for (let i = 0; i < 12; i++) {
      bridges.push(
        aPts[i * 3],
        aPts[i * 3 + 1],
        aPts[i * 3 + 2],
        bPts[i * 3],
        bPts[i * 3 + 1],
        bPts[i * 3 + 2],
      );
    }

    return [new Float32Array(aPts), new Float32Array(bPts), new Float32Array(bridges)];
  }, []);

  useFrame((_, delta) => {
    if (groupRef.current) {
      groupRef.current.rotation.y += delta * 0.12;
    }
  });

  // Calculate distance based on scroll progress: Starts far (-2.0, +2.0), converges to (-0.55, +0.55)
  const separation = THREE.MathUtils.lerp(2.2, 0.6, Math.min(1, Math.max(0, progress)));
  const bridgeAlpha = THREE.MathUtils.lerp(0.05, 0.75, Math.min(1, Math.max(0, progress)));

  return (
    <group ref={groupRef}>
      {/* Molecule A (e.g. Temozolomide) */}
      <group ref={leftCluster} position={[-separation, 0, 0]}>
        <points>
          <bufferGeometry>
            <bufferAttribute attach="attributes-position" args={[molA, 3]} />
          </bufferGeometry>
          <pointsMaterial size={0.11} color="#00D6A0" transparent opacity={0.95} />
        </points>
      </group>

      {/* Molecule B (e.g. Cyclophosphamide) */}
      <group ref={rightCluster} position={[separation, 0, 0]}>
        <points>
          <bufferGeometry>
            <bufferAttribute attach="attributes-position" args={[molB, 3]} />
          </bufferGeometry>
          <pointsMaterial size={0.11} color="#35C9D5" transparent opacity={0.95} />
        </points>
      </group>

      {/* Emergent Synthetic Lethality Bridge */}
      <lineSegments ref={bridgingLinesRef}>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[bridgeCoords, 3]} />
        </bufferGeometry>
        <lineBasicMaterial color="#8AE8CC" transparent opacity={bridgeAlpha} />
      </lineSegments>
    </group>
  );
}

export const MolecularConvergenceCanvas: React.FC<{ progress?: number }> = ({
  progress = 0.5,
}) => {
  return (
    <div className="w-full h-full relative select-none">
      <Canvas
        camera={{ position: [0, 0, 4.8], fov: 45 }}
        gl={{ alpha: true, antialias: true }}
        dpr={[1, 1.5]}
      >
        <ambientLight intensity={0.7} />
        <pointLight position={[5, 5, 5]} intensity={1.0} color="#00D6A0" />
        <ConvergingMolecules progress={progress} />
      </Canvas>
    </div>
  );
};

