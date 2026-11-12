import React, { useEffect, useRef, useState } from "react";
import { ParticlesSwarm } from "./ParticlesSwarm";
import { StaticMolecularFallback } from "./StaticMolecularFallback";
import type { CinematicMotionState } from "./cinematicMotionTypes";

export interface CinematicMolecularCanvasProps {
  motionStateRef: React.MutableRefObject<CinematicMotionState>;
  requestRenderRef: React.MutableRefObject<(() => void) | null>;
  isMobile?: boolean;
}

export const CinematicMolecularCanvas: React.FC<CinematicMolecularCanvasProps> = ({
  motionStateRef,
  requestRenderRef,
  isMobile = false,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const swarmRef = useRef<ParticlesSwarm | null>(null);
  const [hasError, setHasError] = useState(false);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    try {
      // 18,000 instanced tetrahedron particles on desktop; 6,500 on mobile for high framerates
      const particleCount = isMobile ? 6500 : 18000;
      const swarm = new ParticlesSwarm(el, motionStateRef, particleCount);
      swarmRef.current = swarm;

      requestRenderRef.current = () => {
        // Continuous GPGPU physics engine smoothly synchronizes with GSAP ticks
      };
    } catch (err) {
      console.warn("GPGPU Particle Swarm initialization error, falling back to vector DNA:", err);
      Promise.resolve().then(() => setHasError(true));
    }

    return () => {
      swarmRef.current?.dispose();
      swarmRef.current = null;
      if (requestRenderRef.current) {
        requestRenderRef.current = null;
      }
    };
  }, [isMobile, motionStateRef, requestRenderRef]);

  if (hasError) {
    return <StaticMolecularFallback />;
  }

  return (
    <div
      ref={containerRef}
      aria-hidden="true"
      className="pointer-events-none fixed inset-0 z-0 overflow-hidden bg-[#020409]"
    />
  );
};

export default CinematicMolecularCanvas;
