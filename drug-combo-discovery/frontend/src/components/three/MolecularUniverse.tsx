import React, { useRef, useMemo } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import * as THREE from "three";

function MolecularNetwork({ particleCount = 70 }: { particleCount?: number }) {
  const pointsRef = useRef<THREE.Points>(null);
  const linesRef = useRef<THREE.LineSegments>(null);

  // Generate nodes for abstract molecular nodes
  const [positions, connections] = useMemo(() => {
    const coords: number[] = [];
    const r = 4.2;

    for (let i = 0; i < particleCount; i++) {
      const u = Math.random();
      const v = Math.random();
      const theta = u * 2.0 * Math.PI;
      const phi = Math.acos(2.0 * v - 1.0);
      const radius = Math.cbrt(Math.random()) * r;

      const x = radius * Math.sin(phi) * Math.cos(theta);
      const y = radius * Math.sin(phi) * Math.sin(theta) * 0.7; // slight oval flattening
      const z = radius * Math.cos(phi) * 0.8;
      coords.push(x, y, z);
    }

    // Connect close neighbors with fine lines (chemical bonds)
    const lineCoords: number[] = [];
    const maxDist = 1.6;

    for (let i = 0; i < particleCount; i++) {
      for (let j = i + 1; j < particleCount; j++) {
        const dx = coords[i * 3] - coords[j * 3];
        const dy = coords[i * 3 + 1] - coords[j * 3 + 1];
        const dz = coords[i * 3 + 2] - coords[j * 3 + 2];
        const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);

        if (dist < maxDist) {
          lineCoords.push(coords[i * 3], coords[i * 3 + 1], coords[i * 3 + 2]);
          lineCoords.push(coords[j * 3], coords[j * 3 + 1], coords[j * 3 + 2]);
        }
      }
    }

    return [new Float32Array(coords), new Float32Array(lineCoords)];
  }, [particleCount]);

  useFrame((state, delta) => {
    if (pointsRef.current) {
      pointsRef.current.rotation.y += delta * 0.05;
      pointsRef.current.rotation.x = Math.sin(state.clock.elapsedTime * 0.2) * 0.1;
    }
    if (linesRef.current) {
      linesRef.current.rotation.y += delta * 0.05;
      linesRef.current.rotation.x = Math.sin(state.clock.elapsedTime * 0.2) * 0.1;
    }
  });

  return (
    <group>
      {/* Molecular Atoms */}
      <points ref={pointsRef}>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            args={[positions, 3]}
          />
        </bufferGeometry>
        <pointsMaterial
          size={0.065}
          color="#00D6A0"
          transparent
          opacity={0.8}
          sizeAttenuation
        />
      </points>

      {/* Chemical Bonds */}
      <lineSegments ref={linesRef}>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            args={[connections, 3]}
          />
        </bufferGeometry>
        <lineBasicMaterial
          color="#35C9D5"
          transparent
          opacity={0.18}
          linewidth={1}
        />
      </lineSegments>
    </group>
  );
}

export const MolecularUniverse: React.FC<{
  className?: string;
  particleCount?: number;
}> = ({ className = "w-full h-full", particleCount = 75 }) => {
  return (
    <div className={`pointer-events-none relative ${className}`}>
      <Canvas
        camera={{ position: [0, 0, 5], fov: 45 }}
        gl={{ alpha: true, antialias: true, powerPreference: "high-performance" }}
        dpr={[1, 1.5]}
      >
        <ambientLight intensity={0.5} />
        <MolecularNetwork particleCount={particleCount} />
      </Canvas>
      {/* Subtle bottom vignette */}
      <div className="absolute inset-0 bg-radial from-transparent via-[#05090D]/40 to-[#05090D] pointer-events-none" />
    </div>
  );
};

