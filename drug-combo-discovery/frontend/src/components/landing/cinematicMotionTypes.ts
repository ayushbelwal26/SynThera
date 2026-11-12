export interface CinematicMotionState {
  // Swarm Group world transform (centered by default)
  objX: number;
  objY: number;
  objZ: number;
  rotX: number;
  rotY: number;
  rotZ: number;
  scale: number;
  // Camera composition
  camX: number;
  camY: number;
  camZ: number;
  lookX: number;
  lookY: number;
  lookZ: number;
  // GPGPU physics & post-processing uniforms driven by GSAP ScrollTrigger
  helixBlend: number; // 0 = crystalline DNA double helix, 1 = smoothly merged into ambient particle field
  turbulence: number; // 0 = cohesive helix & nebula, >0 = curl-noise dispersion
  stiffness: number; // GPGPU spring return stiffness
  bloomIntensity: number; // UnrealBloomPass strength
  brightness: number; // Overall composite luminosity multiplier
}

export const INITIAL_CINEMATIC_STATE: CinematicMotionState = {
  // Hero — Central DNA double helix surrounded by volumetric particle nebula
  objX: 0,
  objY: -1,
  objZ: 0,
  rotX: 0.12,
  rotY: 0.0,
  rotZ: -0.18,
  scale: 1.0,
  camX: 0,
  camY: 0,
  camZ: 104,
  lookX: 0,
  lookY: 0,
  lookZ: 0,
  helixBlend: 0.0,
  turbulence: 0.0,
  stiffness: 2.4,
  bloomIntensity: 0.48,
  brightness: 1.0,
};
