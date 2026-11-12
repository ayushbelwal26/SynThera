import React, { useRef, useMemo } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import * as THREE from "three";

interface HeroMolecularSceneProps {
  interactive?: boolean;
}

function MolecularGalaxy() {
  const groupRef = useRef<THREE.Group>(null);
  const coreRef = useRef<THREE.Points>(null);
  const haloRef = useRef<THREE.Points>(null);
  const bondsRef = useRef<THREE.LineSegments>(null);

  // Biological nodes with varying radii (Drug, Target, Ligand clusters)
  const [corePositions, coreColors, haloPositions, bonds] = useMemo(() => {
    const cCoords: number[] = [];
    const cCols: number[] = [];
    const hCoords: number[] = [];
    const bCoords: number[] = [];

    const emerald = new THREE.Color("#00D6A0");
    const cyan = new THREE.Color("#35C9D5");
    const gold = new THREE.Color("#C7A76A");
    const mint = new THREE.Color("#8AE8CC");

    const coreCount = 95;
    const r = 2.8;

    for (let i = 0; i < coreCount; i++) {
      const u = Math.random();
      const v = Math.random();
      const theta = u * 2.0 * Math.PI;
      const phi = Math.acos(2.0 * v - 1.0);
      const radius = Math.cbrt(Math.random()) * r;

      const x = radius * Math.sin(phi) * Math.cos(theta);
      const y = radius * Math.sin(phi) * Math.sin(theta) * 0.75;
      const z = radius * Math.cos(phi) * 0.9;

      cCoords.push(x, y, z);

      // Color coding mimicking biological taxonomy
      const rand = Math.random();
      const chosenColor = rand > 0.6 ? emerald : rand > 0.3 ? cyan : rand > 0.15 ? mint : gold;
      cCols.push(chosenColor.r, chosenColor.g, chosenColor.b);
    }

    // Connect close neighbors
    const maxDist = 1.45;
    for (let i = 0; i < coreCount; i++) {
      for (let j = i + 1; j < coreCount; j++) {
        const dx = cCoords[i * 3] - cCoords[j * 3];
        const dy = cCoords[i * 3 + 1] - cCoords[j * 3 + 1];
        const dz = cCoords[i * 3 + 2] - cCoords[j * 3 + 2];
        const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);

        if (dist < maxDist) {
          bCoords.push(cCoords[i * 3], cCoords[i * 3 + 1], cCoords[i * 3 + 2]);
          bCoords.push(cCoords[j * 3], cCoords[j * 3 + 1], cCoords[j * 3 + 2]);
        }
      }
    }

    // Background floating orbital halo particles
    const haloCount = 180;
    for (let i = 0; i < haloCount; i++) {
      const theta = Math.random() * 2 * Math.PI;
      const phi = Math.acos(2 * Math.random() - 1);
      const dist = 3.2 + Math.random() * 2.8;

      hCoords.push(
        dist * Math.sin(phi) * Math.cos(theta),
        dist * Math.sin(phi) * Math.sin(theta) * 0.6,
        dist * Math.cos(phi),
      );
    }

    return [
      new Float32Array(cCoords),
      new Float32Array(cCols),
      new Float32Array(hCoords),
      new Float32Array(bCoords),
    ];
  }, []);

  useFrame((state, delta) => {
    const t = state.clock.getElapsedTime();

    if (groupRef.current) {
      // Gentle orbital oscillation responding to mouse pointer
      const targetX = (state.pointer.x * Math.PI) / 8;
      const targetY = (state.pointer.y * Math.PI) / 8;

      groupRef.current.rotation.y += delta * 0.08;
      groupRef.current.rotation.x = THREE.MathUtils.lerp(
        groupRef.current.rotation.x,
        targetY * 0.35 + Math.sin(t * 0.25) * 0.08,
        0.05,
      );
      groupRef.current.rotation.z = THREE.MathUtils.lerp(
        groupRef.current.rotation.z,
        targetX * 0.25,
        0.05,
      );
    }

    if (haloRef.current) {
      haloRef.current.rotation.y -= delta * 0.03;
    }
  });

  return (
    <group ref={groupRef}>
      {/* Primary Biological Nodes */}
      <points ref={coreRef}>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[corePositions, 3]} />
          <bufferAttribute attach="attributes-color" args={[coreColors, 3]} />
        </bufferGeometry>
        <pointsMaterial
          size={0.085}
          vertexColors
          transparent
          opacity={0.95}
          sizeAttenuation
        />
      </points>

      {/* Intermolecular Bond Lattice */}
      <lineSegments ref={bondsRef}>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[bonds, 3]} />
        </bufferGeometry>
        <lineBasicMaterial color="#35C9D5" transparent opacity={0.22} />
      </lineSegments>

      {/* Atmospheric Halo Particles */}
      <points ref={haloRef}>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[haloPositions, 3]} />
        </bufferGeometry>
        <pointsMaterial size={0.035} color="#00D6A0" transparent opacity={0.35} sizeAttenuation />
      </points>
    </group>
  );
}

export const HeroMolecularScene: React.FC<HeroMolecularSceneProps> = () => {
  return (
    <div className="w-full h-full relative cursor-grab active:cursor-grabbing select-none">
      <Canvas
        camera={{ position: [0, 0, 5.5], fov: 42 }}
        gl={{ alpha: true, antialias: true, powerPreference: "high-performance" }}
        dpr={[1, 1.75]}
      >
        <ambientLight intensity={0.65} />
        <pointLight position={[10, 10, 10]} intensity={1.2} color="#00D6A0" />
        <pointLight position={[-10, -10, -10]} intensity={0.8} color="#35C9D5" />
        <MolecularGalaxy />
      </Canvas>
      {/* Soft gradient edge fade */}
      <div className="absolute inset-0 bg-radial from-transparent via-transparent to-[#05090D] pointer-events-none" />
    </div>
  );
};

