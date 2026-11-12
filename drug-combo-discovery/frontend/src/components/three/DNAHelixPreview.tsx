import React, { useRef, useMemo } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import * as THREE from "three";

function DoubleHelix() {
  const groupRef = useRef<THREE.Group>(null);

  const [pointsA, pointsB, rungs] = useMemo(() => {
    const pA: number[] = [];
    const pB: number[] = [];
    const rCoords: number[] = [];

    const turns = 2.5;
    const length = 4.2;
    const radius = 0.95;
    const steps = 38;

    for (let i = 0; i <= steps; i++) {
      const t = (i / steps) * turns * 2 * Math.PI;
      const y = (i / steps) * length - length / 2;

      const x1 = Math.cos(t) * radius;
      const z1 = Math.sin(t) * radius;

      const x2 = Math.cos(t + Math.PI) * radius;
      const z2 = Math.sin(t + Math.PI) * radius;

      pA.push(x1, y, z1);
      pB.push(x2, y, z2);

      if (i % 2 === 0) {
        rCoords.push(x1, y, z1, x2, y, z2);
      }
    }

    return [
      new Float32Array(pA),
      new Float32Array(pB),
      new Float32Array(rCoords),
    ];
  }, []);

  useFrame((_, delta) => {
    if (groupRef.current) {
      groupRef.current.rotation.y += delta * 0.45;
    }
  });

  return (
    <group ref={groupRef} rotation={[0.2, 0, 0.15]}>
      {/* Strand A */}
      <points>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[pointsA, 3]} />
        </bufferGeometry>
        <pointsMaterial size={0.09} color="#00D6A0" transparent opacity={0.9} />
      </points>

      {/* Strand B */}
      <points>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[pointsB, 3]} />
        </bufferGeometry>
        <pointsMaterial size={0.09} color="#35C9D5" transparent opacity={0.9} />
      </points>

      {/* Base pair hydrogen rungs */}
      <lineSegments>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[rungs, 3]} />
        </bufferGeometry>
        <lineBasicMaterial color="#8AE8CC" transparent opacity={0.3} />
      </lineSegments>
    </group>
  );
}

export const DNAHelixPreview: React.FC<{ className?: string }> = ({
  className = "w-full h-full",
}) => {
  return (
    <div className={`relative ${className}`}>
      <Canvas
        camera={{ position: [0, 0, 4.5], fov: 45 }}
        gl={{ alpha: true, antialias: true }}
        dpr={[1, 1.5]}
      >
        <ambientLight intensity={0.6} />
        <DoubleHelix />
      </Canvas>
    </div>
  );
};

