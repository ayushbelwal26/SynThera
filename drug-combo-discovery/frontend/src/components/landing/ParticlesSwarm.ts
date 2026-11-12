import * as THREE from "three";
import { GPUComputationRenderer } from "three/examples/jsm/misc/GPUComputationRenderer.js";
import { EffectComposer } from "three/examples/jsm/postprocessing/EffectComposer.js";
import { RenderPass } from "three/examples/jsm/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/examples/jsm/postprocessing/UnrealBloomPass.js";
import { ShaderPass } from "three/examples/jsm/postprocessing/ShaderPass.js";
import type { CinematicMotionState } from "./cinematicMotionTypes";

// ── CUSTOM SHADER DEFINITIONS FROM SPECIFICATION ──────────────────────────

export const GeometricDistortShader = {
  uniforms: {
    tDiffuse: { value: null },
    uGeoMode: { value: 0 },
    uGeoAmount: { value: 0.5 },
    uSegments: { value: 6.0 },
    uPixelSize: { value: 8.0 },
    uResolution: { value: new THREE.Vector2(window.innerWidth, window.innerHeight) },
  },
  vertexShader: `varying vec2 vUv; void main(){ vUv=uv; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0); }`,
  fragmentShader: `
    uniform sampler2D tDiffuse;
    uniform int uGeoMode;
    uniform float uGeoAmount;
    uniform float uSegments;
    uniform float uPixelSize;
    uniform vec2 uResolution;
    varying vec2 vUv;
    #define PI 3.14159265358979
    #define PI2 6.28318530718
    void main() {
      if (uGeoMode == 0) { gl_FragColor = texture2D(tDiffuse, vUv); return; }
      vec2 uv = vUv;
      if (uGeoMode == 1) {
        vec2 p = uv - 0.5;
        float r = length(p);
        float a = atan(p.y, p.x);
        float sliceAngle = PI2 / uSegments;
        a = mod(a, sliceAngle);
        if (a > sliceAngle * 0.5) a = sliceAngle - a;
        uv = vec2(r * cos(a), r * sin(a)) + 0.5;
      } else if (uGeoMode == 2) {
        uv.x = uv.x < 0.5 ? uv.x : 1.0 - uv.x;
      } else if (uGeoMode == 3) {
        uv.y = uv.y < 0.5 ? uv.y : 1.0 - uv.y;
      } else if (uGeoMode == 4) {
        vec2 blockSize = vec2(uPixelSize) / uResolution;
        uv = floor(uv / blockSize) * blockSize + blockSize * 0.5;
      } else if (uGeoMode == 5) {
        vec2 p = uv * 2.0 - 1.0;
        float len = length(p);
        if (len < 1.0) {
          float z = sqrt(1.0 - len * len * uGeoAmount);
          float theta = atan(len / z) * (1.0 / PI);
          uv = p * (theta / len) * 0.5 + 0.5;
        }
      } else if (uGeoMode == 6) {
        vec2 p = uv - 0.5;
        float dist = length(p);
        float factor = pow(dist, uGeoAmount > 0.5 ? 0.6 : 1.8);
        uv = normalize(p + 0.00001) * factor * 0.5 + 0.5;
      } else if (uGeoMode == 7) {
        float r = uv.y;
        float a = (uv.x - 0.5) * PI2;
        uv = vec2(r * cos(a), r * sin(a)) * 0.5 + 0.5;
      }
      gl_FragColor = texture2D(tDiffuse, clamp(uv, 0.001, 0.999));
    }
  `,
};

export const ColorGradeCompositeShader = {
  uniforms: {
    tDiffuse: { value: null },
    bgColor: { value: new THREE.Color("#020409") },
    uBrightness: { value: 0.0 },
    uContrast: { value: 1.08 },
    uSaturation: { value: 1.12 },
    uHueShift: { value: 0.0 },
    uExposure: { value: 1.08 },
    uToneMap: { value: 1 }, // 1 = ACES
    uTintColor: { value: new THREE.Color(0xffffff) },
    uTintShadow: { value: new THREE.Color(0x000000) },
    uTintAmt: { value: 0.0 },
    uInvert: { value: 0.0 },
    uSolarize: { value: 0.0 },
    uPosterize: { value: 0.0 },
    uGlobalAlpha: { value: 1.0 },
  },
  vertexShader: `varying vec2 vUv; void main(){ vUv=uv; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0); }`,
  fragmentShader: `
    uniform sampler2D tDiffuse;
    uniform vec3 bgColor;
    uniform float uBrightness;
    uniform float uContrast;
    uniform float uSaturation;
    uniform float uHueShift;
    uniform float uExposure;
    uniform int uToneMap;
    uniform vec3 uTintColor;
    uniform vec3 uTintShadow;
    uniform float uTintAmt;
    uniform float uInvert;
    uniform float uSolarize;
    uniform float uPosterize;
    uniform float uGlobalAlpha;
    varying vec2 vUv;

    vec3 rotateHue(vec3 col, float h) {
      float ang = h * 6.28318530718;
      float c = cos(ang), s = sin(ang);
      float sq = 0.57735026919;
      return col * c + cross(vec3(sq,sq,sq), col) * s + vec3(sq,sq,sq) * dot(vec3(sq,sq,sq), col) * (1.0 - c);
    }
    vec3 acesToneMap(vec3 x){
      return clamp((x*(2.51*x+0.03))/(x*(2.43*x+0.59)+0.14),0.,1.);
    }
    vec3 reinhardToneMap(vec3 x){ return x/(x+1.); }
    vec3 filmicToneMap(vec3 x){
      vec3 X=max(vec3(0.),x-0.004);
      return (X*(6.2*X+0.5))/(X*(6.2*X+1.7)+0.06);
    }

    void main() {
      vec4 texel = texture2D(tDiffuse, vUv);
      vec3 particleRgb = texel.rgb * uGlobalAlpha;

      // Soft center-focused radial vignette to frame hero typography
      vec2 centerVec = vUv - vec2(0.5);
      float radial = clamp(1.0 - dot(centerVec, centerVec) * 0.45, 0.72, 1.0);
      vec3 col = particleRgb + bgColor * radial;

      col *= uExposure;
      if (uToneMap == 1) col = acesToneMap(col);
      else if (uToneMap == 2) col = reinhardToneMap(col);
      else if (uToneMap == 3) col = filmicToneMap(col);

      col = col + uBrightness;
      col = (col - 0.5) * uContrast + 0.5;

      float lum = dot(col, vec3(0.2126, 0.7152, 0.0722));
      col = mix(vec3(lum), col, uSaturation);

      if (uHueShift != 0.0) col = rotateHue(col, uHueShift);

      if (uTintAmt > 0.0) {
        float lumDt = dot(col, vec3(0.2126, 0.7152, 0.0722));
        vec3 duotone = mix(uTintShadow, uTintColor, lumDt);
        col = mix(col, duotone, uTintAmt);
      }
      if (uSolarize > 0.0) {
        float lumS = dot(col, vec3(0.2126, 0.7152, 0.0722));
        float mask = step(uSolarize, lumS);
        col = mix(col, 1.0 - col, mask);
      }
      if (uInvert > 0.5) col = 1.0 - col;
      if (uPosterize >= 2.0) {
        float bands = uPosterize;
        col = floor(col * bands + 0.5) / bands;
      }

      gl_FragColor = vec4(clamp(col, 0.0, 1.0), 1.0);
    }
  `,
};

export const LiquidMarbleShader = {
  uniforms: {
    tDiffuse: { value: null },
    time: { value: 0.0 },
    strength: { value: 0.0 },
    speed: { value: 0.5 },
    scale: { value: 3.0 },
  },
  vertexShader: `varying vec2 vUv; void main(){ vUv=uv; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0); }`,
  fragmentShader: `
    uniform sampler2D tDiffuse;
    uniform float time;
    uniform float strength;
    uniform float speed;
    uniform float scale;
    varying vec2 vUv;
    float hash(vec2 p){ return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453); }
    float noise(vec2 p){
      vec2 i=floor(p); vec2 f=fract(p);
      vec2 u=f*f*(3.0-2.0*f);
      return mix(mix(hash(i),hash(i+vec2(1,0)),u.x),mix(hash(i+vec2(0,1)),hash(i+vec2(1,1)),u.x),u.y);
    }
    vec2 fbm2(vec2 p){
      float f=0.0; float a=0.5;
      for(int i=0;i<5;i++){ f+=a*noise(p); p*=2.0; a*=0.5; }
      return vec2(f, noise(p+vec2(3.7,1.3)));
    }
    void main(){
      if(strength==0.0){ gl_FragColor=texture2D(tDiffuse,vUv); return; }
      vec2 p = vUv * scale;
      float t = time * speed;
      vec2 q = fbm2(p + t);
      vec2 r = fbm2(p + q + vec2(1.7+t*0.15, 9.2+t*0.05));
      vec2 warp = fbm2(p + r);
      vec2 sampledUv = clamp(vUv + (warp - 0.5) * strength * 0.4, 0.001, 0.999);
      gl_FragColor = texture2D(tDiffuse, sampledUv);
    }
  `,
};

export const TwirlShader = {
  uniforms: {
    tDiffuse: { value: null },
    angle: { value: 0.0 },
    radius: { value: 0.5 },
    center: { value: new THREE.Vector2(0.5, 0.5) },
  },
  vertexShader: `varying vec2 vUv; void main(){ vUv=uv; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0); }`,
  fragmentShader: `
    uniform sampler2D tDiffuse;
    uniform float angle;
    uniform float radius;
    uniform vec2 center;
    varying vec2 vUv;
    void main(){
      vec2 delta = vUv - center;
      float dist = length(delta);
      float twirlAngle = angle * max(0.0, (radius - dist) / radius);
      float c = cos(twirlAngle), s = sin(twirlAngle);
      vec2 rotated = vec2(c*delta.x - s*delta.y, s*delta.x + c*delta.y);
      gl_FragColor = texture2D(tDiffuse, clamp(center + rotated, 0.001, 0.999));
    }
  `,
};

export const WaveWarpShader = {
  uniforms: {
    tDiffuse: { value: null },
    time: { value: 0.0 },
    freqX: { value: 10.0 },
    freqY: { value: 10.0 },
    amplitude: { value: 0.0 },
    speed: { value: 1.0 },
  },
  vertexShader: `varying vec2 vUv; void main(){ vUv=uv; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0); }`,
  fragmentShader: `
    uniform sampler2D tDiffuse;
    uniform float time;
    uniform float freqX;
    uniform float freqY;
    uniform float amplitude;
    uniform float speed;
    varying vec2 vUv;
    void main(){
      if(amplitude==0.0){ gl_FragColor=texture2D(tDiffuse,vUv); return; }
      float t = time * speed;
      vec2 displaced = vUv + vec2(
        sin(vUv.y * freqX + t) * amplitude,
        cos(vUv.x * freqY + t) * amplitude
      );
      gl_FragColor = texture2D(tDiffuse, clamp(displaced, 0.001, 0.999));
    }
  `,
};

export const FluidChromaShader = {
  uniforms: {
    tDiffuse: { value: null },
    time: { value: 0.0 },
    strength: { value: 0.0 },
    dispersion: { value: 0.02 },
    speed: { value: 0.5 },
  },
  vertexShader: `varying vec2 vUv; void main(){ vUv=uv; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0); }`,
  fragmentShader: `
    uniform sampler2D tDiffuse;
    uniform float time;
    uniform float strength;
    uniform float dispersion;
    uniform float speed;
    varying vec2 vUv;
    void main() {
      if(strength == 0.0) { gl_FragColor = texture2D(tDiffuse, vUv); return; }
      float t = time * speed;
      vec2 p = vUv - 0.5;
      float x1 = sin(p.y * 3.1 + t * 0.7) * cos(p.x * 2.1 + t * 0.9);
      float y1 = cos(p.x * 3.4 - t * 0.6) * sin(p.y * 2.3 - t * 0.8);
      float x2 = sin(p.y * 5.2 - t * 1.2 + x1) * cos(p.x * 4.1 + t * 1.1 + y1);
      float y2 = cos(p.x * 5.5 + t * 1.3 - x1) * sin(p.y * 4.3 - t * 1.0 - y1);
      vec2 dir = vec2(x2, y2) * strength * 0.2;
      float rCol = texture2D(tDiffuse, clamp(vUv + dir * (1.0 + dispersion * 2.0), 0.001, 0.999)).r;
      float gCol = texture2D(tDiffuse, clamp(vUv + dir, 0.001, 0.999)).g;
      float bCol = texture2D(tDiffuse, clamp(vUv + dir * (1.0 - dispersion * 2.0), 0.001, 0.999)).b;
      float sheen = dot(dir, vec2(0.5)) * 2.0;
      vec3 iridescence = vec3(
        0.5 + 0.5 * sin(sheen * 10.0 + 0.0),
        0.5 + 0.5 * sin(sheen * 10.0 + 2.0),
        0.5 + 0.5 * sin(sheen * 10.0 + 4.0)
      ) * 0.15 * strength;
      gl_FragColor = vec4(vec3(rCol, gCol, bCol) + iridescence, 1.0);
    }
  `,
};

export const BgCompositeShader = {
  uniforms: {
    tDiffuse: { value: null },
    bgColor: { value: new THREE.Color("#020409") },
  },
  vertexShader: `varying vec2 vUv; void main(){ vUv=uv; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0); }`,
  fragmentShader: `
    uniform sampler2D tDiffuse;
    uniform vec3 bgColor;
    varying vec2 vUv;
    void main() {
      vec4 texel = texture2D(tDiffuse, vUv);
      float alpha = clamp(max(texel.r, max(texel.g, texel.b)), 0.0, 1.0);
      gl_FragColor = vec4(texel.rgb + bgColor * (1.0 - alpha), 1.0);
    }
  `,
};

function createSeededRng(seed: number) {
  let state = seed >>> 0;
  return () => {
    state |= 0;
    state = (state + 0x6d2b79f5) | 0;
    let t = Math.imul(state ^ (state >>> 15), 1 | state);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export class ParticlesSwarm {
  public count: number;
  private container: HTMLElement;
  private speedMult = 1.0;

  private scene: THREE.Scene;
  private camera: THREE.PerspectiveCamera;
  private renderer: THREE.WebGLRenderer;
  private composer: EffectComposer;
  private bloomPass: UnrealBloomPass;
  private colorGradePass: ShaderPass;

  private swarmGroup: THREE.Group;
  private geometry: THREE.BufferGeometry;
  private material: THREE.MeshBasicMaterial;
  private mesh: THREE.InstancedMesh;

  private targetTex: THREE.DataTexture;
  private gpuCompute: GPUComputationRenderer;
  private positionVariable: ReturnType<GPUComputationRenderer["addVariable"]>;
  private velocityVariable: ReturnType<GPUComputationRenderer["addVariable"]>;
  private velocityUniforms: Record<string, THREE.IUniform>;

  private clock: THREE.Clock;
  private raycaster: THREE.Raycaster;
  private mouse: THREE.Vector2;
  private dummyPlane: THREE.Plane;
  private intersectPoint: THREE.Vector3;
  private lookTargetVec: THREE.Vector3;

  private motionStateRef: { current: CinematicMotionState } | null = null;
  private rafId: number | null = null;
  private disposed = false;

  public physicsOverrides: {
    gravity: THREE.Vector3 | null;
    shockwaveCenter: THREE.Vector3 | null;
    shockwaveForce: number | null;
    shockwaveRadius: number | null;
    stiffness: number | null;
    damping: number | null;
    noiseStrength: number | null;
  } = {
    gravity: null,
    shockwaveCenter: null,
    shockwaveForce: null,
    shockwaveRadius: null,
    stiffness: null,
    damping: null,
    noiseStrength: null,
  };

  // Precomputed deterministic offsets for realistic volumetric distribution
  private jitterX: Float32Array;
  private jitterY: Float32Array;
  private jitterZ: Float32Array;

  // SynThera palette colors
  private pColor = new THREE.Color();
  private cElectricBlue = new THREE.Color("#1d6fff");
  private cCyan = new THREE.Color("#35c9d5");
  private cEmerald = new THREE.Color("#00d6a0");
  private cMint = new THREE.Color("#8ae8cc");
  private cIceWhite = new THREE.Color("#e8f8ff");
  private cDarkNavy = new THREE.Color("#0c2340");
  private tmpColorA = new THREE.Color();
  private tmpColorB = new THREE.Color();

  constructor(
    container: HTMLElement,
    motionStateRef: { current: CinematicMotionState },
    count = 20000
  ) {
    this.count = count;
    this.container = container;
    this.motionStateRef = motionStateRef;

    const width = container.clientWidth || window.innerWidth;
    const height = container.clientHeight || window.innerHeight;

    // 1. SETUP
    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(58, width / height, 0.1, 2000);
    this.camera.position.set(0, 0, 104);

    this.swarmGroup = new THREE.Group();
    this.scene.add(this.swarmGroup);

    this.renderer = new THREE.WebGLRenderer({
      antialias: true,
      powerPreference: "high-performance",
    });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
    this.renderer.setSize(width, height);
    this.renderer.setClearColor(0x000000, 1);
    this.container.appendChild(this.renderer.domElement);

    // 2. POST PROCESSING (UnrealBloomPass + ColorGradeCompositeShader)
    this.composer = new EffectComposer(this.renderer);
    this.composer.addPass(new RenderPass(this.scene, this.camera));

    this.bloomPass = new UnrealBloomPass(
      new THREE.Vector2(width, height),
      0.48,
      0.3,
      0.22
    );
    this.composer.addPass(this.bloomPass);

    this.colorGradePass = new ShaderPass(ColorGradeCompositeShader);
    this.colorGradePass.renderToScreen = true;
    this.composer.addPass(this.colorGradePass);

    // 3. OBJECTS & INSTANCED TETRAHEDRON GEOMETRY
    const rng = createSeededRng(20261112);
    this.geometry = new THREE.TetrahedronGeometry(0.24).clone();

    const W = Math.ceil(Math.sqrt(this.count));
    const H = W;
    const references = new Float32Array(this.count * 2);
    const scales = new Float32Array(this.count);
    const opacities = new Float32Array(this.count);

    this.jitterX = new Float32Array(this.count);
    this.jitterY = new Float32Array(this.count);
    this.jitterZ = new Float32Array(this.count);

    const dnaEnd = Math.floor(this.count * 0.64);
    const nebulaEnd = Math.floor(this.count * 0.88);

    for (let i = 0; i < this.count; i++) {
      references[i * 2] = ((i % W) + 0.5) / W;
      references[i * 2 + 1] = (Math.floor(i / W) + 0.5) / H;

      if (i < dnaEnd) {
        // Central DNA Double Helix: crisp, prominent, luminous
        scales[i] = 0.62 + rng() * 0.65;
        opacities[i] = 0.65 + rng() * 0.35;
        this.jitterX[i] = (rng() - 0.5) * 1.0;
        this.jitterY[i] = (rng() - 0.5) * 0.7;
        this.jitterZ[i] = (rng() - 0.5) * 1.0;
      } else if (i < nebulaEnd) {
        // Space-filling cosmic particle clouds: soft, atmospheric, volumetric depth
        scales[i] = 0.45 + rng() * 0.55;
        opacities[i] = 0.3 + rng() * 0.35;
        this.jitterX[i] = (rng() - 0.5) * 4.0;
        this.jitterY[i] = (rng() - 0.5) * 3.0;
        this.jitterZ[i] = (rng() - 0.5) * 4.0;
      } else {
        // Distant twinkling stars & quantum field pinpoints
        scales[i] = 0.35 + rng() * 0.45;
        opacities[i] = 0.45 + rng() * 0.45;
        this.jitterX[i] = 0;
        this.jitterY[i] = 0;
        this.jitterZ[i] = 0;
      }
    }

    this.geometry.setAttribute("reference", new THREE.InstancedBufferAttribute(references, 2));
    this.geometry.setAttribute("instanceScale", new THREE.InstancedBufferAttribute(scales, 1));
    this.geometry.setAttribute("instanceOpacity", new THREE.InstancedBufferAttribute(opacities, 1));

    // 4. GPGPU Shader compiler
    this.material = new THREE.MeshBasicMaterial({ color: 0xffffff });
    const applyGPGPU = (mat: THREE.MeshBasicMaterial) => {
      mat.onBeforeCompile = (shader) => {
        shader.uniforms.texturePosition = { value: null };
        shader.uniforms.gpgpuEnabled = { value: 1.0 };
        mat.userData.shader = shader;

        shader.vertexShader =
          `
          attribute vec2 reference;
          attribute float instanceScale;
          attribute float instanceOpacity;
          varying float vInstanceOpacity;
          uniform sampler2D texturePosition;
          uniform float gpgpuEnabled;
        ` + shader.vertexShader;

        shader.vertexShader = shader.vertexShader.replace(
          "#include <project_vertex>",
          `
          vec4 mvPosition = vec4( transformed, 1.0 );
          #ifdef USE_BATCHING
            mvPosition = batchingMatrix * mvPosition;
          #endif
          #ifdef USE_INSTANCING
            mvPosition.xyz *= instanceScale;
            vInstanceOpacity = instanceOpacity;
            mat4 m = instanceMatrix;
            if (gpgpuEnabled > 0.5) {
              m[3] = vec4(0.0, 0.0, 0.0, 1.0);
            }
            mvPosition = m * mvPosition;
            if (gpgpuEnabled > 0.5) {
              mvPosition.xyz += texture2D(texturePosition, reference).xyz;
            } else {
              mvPosition.xyz += vec3(instanceMatrix[3][0], instanceMatrix[3][1], instanceMatrix[3][2]);
            }
          #endif
          mvPosition = modelViewMatrix * mvPosition;
          gl_Position = projectionMatrix * mvPosition;
          `
        );

        shader.fragmentShader =
          `
          varying float vInstanceOpacity;
        ` + shader.fragmentShader;

        shader.fragmentShader = shader.fragmentShader.replace(
          "#include <color_fragment>",
          `
          #include <color_fragment>
          diffuseColor.a *= vInstanceOpacity;
          `
        );
      };
      mat.needsUpdate = true;
    };
    applyGPGPU(this.material);

    this.mesh = new THREE.InstancedMesh(this.geometry, this.material, this.count);
    this.mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    this.mesh.frustumCulled = false;

    const dummy = new THREE.Object3D();
    for (let i = 0; i < this.count; i++) {
      dummy.position.set(0, 0, 0);
      dummy.rotation.set(rng() * Math.PI * 2, rng() * Math.PI * 2, rng() * Math.PI * 2);
      dummy.updateMatrix();
      this.mesh.setMatrixAt(i, dummy.matrix);
      this.mesh.setColorAt(i, this.cCyan);
    }
    this.mesh.instanceMatrix.needsUpdate = true;
    if (this.mesh.instanceColor) this.mesh.instanceColor.needsUpdate = true;

    this.swarmGroup.add(this.mesh);

    // 5. GPGPU PHYSICS ENGINE CORE
    this.targetTex = new THREE.DataTexture(
      new Float32Array(W * H * 4),
      W,
      H,
      THREE.RGBAFormat,
      THREE.FloatType
    );

    this.gpuCompute = new GPUComputationRenderer(W, H, this.renderer);
    if (!this.renderer.capabilities.isWebGL2) {
      this.gpuCompute.setDataType(THREE.HalfFloatType);
    }

    const dtPosition = this.gpuCompute.createTexture();
    const dtVelocity = this.gpuCompute.createTexture();

    const posArray = dtPosition.image.data as Float32Array;
    const velArray = dtVelocity.image.data as Float32Array;
    for (let i = 0; i < W * H; i++) {
      const idx = i * 4;
      posArray[idx] = (rng() - 0.5) * 100;
      posArray[idx + 1] = (rng() - 0.5) * 100;
      posArray[idx + 2] = (rng() - 0.5) * 100;
      posArray[idx + 3] = 1.0;

      velArray[idx] = 0.0;
      velArray[idx + 1] = 0.0;
      velArray[idx + 2] = 0.0;
      velArray[idx + 3] = 0.0;
    }

    const posShader = `
      void main() {
        vec2 uv = gl_FragCoord.xy / resolution.xy;
        vec3 pos = texture2D(texturePosition, uv).xyz;
        vec3 vel = texture2D(textureVelocity, uv).xyz;
        pos += vel * 0.016;
        gl_FragColor = vec4(pos, 1.0);
      }
    `;

    const velShader = `
      uniform float uTime;
      uniform float uDeltaTime;
      uniform float uStiffness;
      uniform float uDamping;
      uniform float uNoiseStrength;
      uniform int uPhysicsMode;
      uniform int uMouseMode;
      uniform float uMouseInfluence;
      uniform vec3 uMouse3D;
      uniform sampler2D textureTarget;
      uniform vec3 uGravity;
      uniform vec3 uShockwaveCenter;
      uniform float uShockwaveForce;
      uniform float uShockwaveRadius;

      vec3 mod289(vec3 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
      vec4 mod289(vec4 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
      vec4 permute(vec4 x) { return mod289(((x*34.0)+1.0)*x); }
      vec4 taylorInvSqrt(vec4 r) { return 1.79284291400159 - 0.85373472095314 * r; }

      float snoise(vec3 v) {
        const vec2 C = vec2(1.0/6.0, 1.0/3.0);
        const vec4 D = vec4(0.0, 0.5, 1.0, 2.0);
        vec3 i = floor(v + dot(v, vec3(C.y)));
        vec3 x0 = v - i + dot(i, vec3(C.x));
        vec3 g = step(x0.yzx, x0.xyz);
        vec3 l = 1.0 - g;
        vec3 i1 = min(g.xyz, l.zxy);
        vec3 i2 = max(g.xyz, l.zxy);
        vec3 x1 = x0 - i1 + vec3(C.x);
        vec3 x2 = x0 - i2 + vec3(C.y);
        vec3 x3 = x0 - D.yyy;
        i = mod289(i);
        vec4 p = permute(permute(permute(
          i.z + vec4(0.0, i1.z, i2.z, 1.0))
          + i.y + vec4(0.0, i1.y, i2.y, 1.0))
          + i.x + vec4(0.0, i1.x, i2.x, 1.0));
        float n_ = 0.142857142857;
        vec3 ns = n_ * D.wyz - D.xzx;
        vec4 j = p - 49.0 * floor(p * ns.z);
        vec4 x_ = floor(j * ns.z);
        vec4 y_ = floor(j - 7.0 * x_);
        vec4 x = x_ *ns.x + ns.yyyy;
        vec4 y = y_ *ns.x + ns.yyyy;
        vec4 h = 1.0 - abs(x) - abs(y);
        vec4 b0 = vec4(x.xy, y.xy);
        vec4 b1 = vec4(x.zw, y.zw);
        vec4 s0 = floor(b0)*2.0 + 1.0;
        vec4 s1 = floor(b1)*2.0 + 1.0;
        vec4 sh = -step(h, vec4(0.0));
        vec4 a0 = b0.xzyw + s0.xzyw*sh.xxyy;
        vec4 a1 = b1.xzyw + s1.xzyw*sh.zzww;
        vec3 p0 = vec3(a0.xy, h.x);
        vec3 p1 = vec3(a0.zw, h.y);
        vec3 p2 = vec3(a1.xy, h.z);
        vec3 p3 = vec3(a1.zw, h.w);
        vec4 norm = taylorInvSqrt(vec4(dot(p0,p0), dot(p1,p1), dot(p2, p2), dot(p3,p3)));
        p0 *= norm.x; p1 *= norm.y; p2 *= norm.z; p3 *= norm.w;
        vec4 m = max(0.6 - vec4(dot(x0,x0), dot(x1,x1), dot(x2,x2), dot(x3,x3)), 0.0);
        m = m * m;
        return 42.0 * dot(m*m, vec4(dot(p0,x0), dot(p1,x1), dot(p2,x2), dot(p3,x3)));
      }

      vec3 curlNoise(vec3 p) {
        const float e = 0.05;
        float dx = snoise(vec3(p.x + e, p.y, p.z)) - snoise(vec3(p.x - e, p.y, p.z));
        float dy = snoise(vec3(p.x, p.y + e, p.z)) - snoise(vec3(p.x, p.y - e, p.z));
        float dz = snoise(vec3(p.x, p.y, p.z + e)) - snoise(vec3(p.x, p.y, p.z - e));
        return vec3(dy - dz, dz - dx, dx - dy) / (2.0 * e);
      }

      void main() {
        vec2 uv = gl_FragCoord.xy / resolution.xy;
        vec3 pos = texture2D(texturePosition, uv).xyz;
        vec3 vel = texture2D(textureVelocity, uv).xyz;
        vec3 target = texture2D(textureTarget, uv).xyz;

        vec3 force = vec3(0.0);

        // 1. Target Attraction / Spring Force
        if (uPhysicsMode == 0) {
          vec3 desiredVel = (target - pos) * 10.0;
          force += (desiredVel - vel) * 20.0;
        } else {
          vec3 springForce = -uStiffness * (pos - target);
          force += springForce;
        }

        // 2. Mouse Force
        if (uMouseMode > 0) {
          float d = distance(pos, uMouse3D);
          float radius = uMouseInfluence * 15.0;
          if (d < radius && d > 0.1) {
            float strength = (1.0 - d / radius);
            vec3 mouseDir = normalize(pos - uMouse3D);
            if (uMouseMode == 1) {
              force -= mouseDir * strength * 150.0;
            } else if (uMouseMode == 2) {
              force += mouseDir * strength * 150.0;
            } else if (uMouseMode == 3) {
              vec3 up = vec3(0.0, 1.0, 0.0);
              vec3 tangent = normalize(cross(mouseDir, up));
              force += tangent * strength * 150.0;
            }
          }
        }

        // 3. Curl Noise / Turbulence
        if (uNoiseStrength > 0.0) {
          float scale = 0.05;
          vec3 noiseOffset = curlNoise(pos * scale + vec3(0.0, 0.0, uTime * 0.2));
          force += noiseOffset * (uNoiseStrength * 18.0);
        }

        // 4. Gravity Override
        force += uGravity * 100.0;

        // 5. Shockwave (Radial Explosion)
        if (uShockwaveForce > 0.0) {
          float d = distance(pos, uShockwaveCenter);
          if (d < uShockwaveRadius && d > 0.1) {
            float shockStrength = (1.0 - (d / uShockwaveRadius)) * uShockwaveForce;
            vec3 shockDir = normalize(pos - uShockwaveCenter);
            force += shockDir * shockStrength * 500.0;
          }
        }

        vel += force * uDeltaTime;
        vel *= (1.0 - uDamping);

        float maxVel = 50.0;
        if (length(vel) > maxVel) {
          vel = normalize(vel) * maxVel;
        }

        gl_FragColor = vec4(vel, 1.0);
      }
    `;

    this.positionVariable = this.gpuCompute.addVariable("texturePosition", posShader, dtPosition);
    this.velocityVariable = this.gpuCompute.addVariable("textureVelocity", velShader, dtVelocity);

    this.gpuCompute.setVariableDependencies(this.positionVariable, [
      this.positionVariable,
      this.velocityVariable,
    ]);
    this.gpuCompute.setVariableDependencies(this.velocityVariable, [
      this.positionVariable,
      this.velocityVariable,
    ]);

    this.velocityUniforms = this.velocityVariable.material.uniforms;
    this.velocityUniforms.uTime = { value: 0.0 };
    this.velocityUniforms.uDeltaTime = { value: 0.016 };
    this.velocityUniforms.uPhysicsMode = { value: 1 }; // Spring physics for smooth organic convergence
    this.velocityUniforms.uMouseMode = { value: 3 }; // Vortex mouse interaction
    this.velocityUniforms.uMouseInfluence = { value: 2.2 };
    this.velocityUniforms.uMouse3D = { value: new THREE.Vector3() };
    this.velocityUniforms.textureTarget = { value: this.targetTex };
    this.velocityUniforms.uStiffness = { value: 2.4 };
    this.velocityUniforms.uDamping = { value: 0.09 };
    this.velocityUniforms.uNoiseStrength = { value: 0.0 };
    this.velocityUniforms.uGravity = { value: new THREE.Vector3() };
    this.velocityUniforms.uShockwaveCenter = { value: new THREE.Vector3() };
    this.velocityUniforms.uShockwaveForce = { value: 0.0 };
    this.velocityUniforms.uShockwaveRadius = { value: 0.0 };

    const initErr = this.gpuCompute.init();
    if (initErr !== null) {
      throw new Error(`GPUComputationRenderer init failed: ${initErr}`);
    }

    this.clock = new THREE.Clock();
    this.raycaster = new THREE.Raycaster();
    this.mouse = new THREE.Vector2(999, 999);
    this.dummyPlane = new THREE.Plane(new THREE.Vector3(0, 0, 1), 0);
    this.intersectPoint = new THREE.Vector3();
    this.lookTargetVec = new THREE.Vector3();

    window.addEventListener("pointermove", this.handlePointerMove);
    window.addEventListener("resize", this.handleResize);

    // Initial update of targets
    this.updateGPGPUTargets(0);
    this.animate();
  }

  public setPhysics(options: {
    gravity?: THREE.Vector3;
    shockwave?: { center?: THREE.Vector3; force?: number; radius?: number };
    stiffness?: number;
    drag?: number;
    turbulence?: number;
  }) {
    if (!options) return;
    if (options.gravity) {
      if (!this.physicsOverrides.gravity) this.physicsOverrides.gravity = new THREE.Vector3();
      this.physicsOverrides.gravity.copy(options.gravity);
    }
    if (options.shockwave) {
      if (options.shockwave.center) {
        if (!this.physicsOverrides.shockwaveCenter)
          this.physicsOverrides.shockwaveCenter = new THREE.Vector3();
        this.physicsOverrides.shockwaveCenter.copy(options.shockwave.center);
      }
      if (options.shockwave.force !== undefined)
        this.physicsOverrides.shockwaveForce = options.shockwave.force;
      if (options.shockwave.radius !== undefined)
        this.physicsOverrides.shockwaveRadius = options.shockwave.radius;
    }
    if (options.stiffness !== undefined) this.physicsOverrides.stiffness = options.stiffness;
    if (options.drag !== undefined) this.physicsOverrides.damping = options.drag;
    if (options.turbulence !== undefined)
      this.physicsOverrides.noiseStrength = options.turbulence;
  }

  public setEffects(options: {
    glowIntensity?: number;
    glowThreshold?: number;
    bgColor?: string;
  }) {
    if (!options) return;
    if (options.glowIntensity !== undefined && this.bloomPass) {
      this.bloomPass.strength = options.glowIntensity;
    }
    if (options.glowThreshold !== undefined && this.bloomPass) {
      this.bloomPass.threshold = options.glowThreshold;
    }
    if (options.bgColor !== undefined) {
      if (this.colorGradePass) {
        this.colorGradePass.uniforms["bgColor"].value.set(options.bgColor);
      }
    }
  }

  private handlePointerMove = (e: PointerEvent) => {
    this.mouse.x = (e.clientX / window.innerWidth) * 2 - 1;
    this.mouse.y = -(e.clientY / window.innerHeight) * 2 + 1;
  };

  private handleResize = () => {
    if (this.disposed) return;
    const width = this.container.clientWidth || window.innerWidth;
    const height = this.container.clientHeight || window.innerHeight;
    if (width === 0 || height === 0) return;

    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
    this.renderer.setSize(width, height);
    this.composer.setSize(width, height);
    this.bloomPass.setSize(width, height);
  };

  /**
   * Dual-population particle target generation:
   * 1. Core Subject (64%): Central B-DNA Double Helix with Strand 1 (Electric Blue -> Cyan),
   *    Strand 2 (Cyan -> Emerald), and 76 base-pair rungs with luminous Ice-White H-bond centers.
   * 2. Cosmic Space Filling (24%): 6 scientific nebula clouds softly drifting in 3D outer space.
   * 3. Stellar Background (12%): Distant twinkling quantum field stars on a sphere.
   */
  public updateGPGPUTargets(time: number) {
    const data = this.targetTex.image.data as Float32Array;
    const W = Math.ceil(Math.sqrt(this.count));
    const totalTexels = W * W;

    // Helper pseudo-random & bell-curve generators from specification
    const rnd = (n: number) => {
      const x = Math.sin(n * 127.1 + 311.7) * 43758.5453;
      return x - Math.floor(x);
    };
    const g = (n: number) => (rnd(n) + rnd(n + 11.3) + rnd(n + 27.9) - 1.5) * 1.33;

    // DNA helix dimensions (centered as primary visual subject)
    const rad = 17.0;
    const hgt = 106.0;
    const turns = 2.85;
    const spd = 0.22;
    const breathe = 1.25;
    const TWO_PI = 6.2831853;
    const GROOVE_OFFSET = 2.38; // ~136° B-DNA groove phase offset

    const dnaEnd = Math.floor(this.count * 0.64);
    const s1End = Math.floor(dnaEnd * 0.36);
    const s2End = Math.floor(dnaEnd * 0.72);
    const numRungs = 76;
    const rungParticles = dnaEnd - s2End;
    const perRung = Math.max(1, Math.floor(rungParticles / numRungs));
    const rotT = time * spd;

    const nebulaEnd = Math.floor(this.count * 0.88);
    const SPREAD = 42.0;
    // 6 scientific nebula gas cloud anchor centers filling peripheral space
    const cxs = [-55, 52, -38, 48, 0, -45];
    const cys = [24, -26, -34, 28, 45, -15];
    const czs = [-45, 40, 50, -50, -30, 25];

    // Scroll-controlled helix-to-particles merging factor (0 = pristine helix, 1 = merged into ambient swarm)
    const blend = this.motionStateRef
      ? Math.min(1.0, Math.max(0.0, this.motionStateRef.current.helixBlend ?? 0.0))
      : 0.0;

    for (let i = 0; i < totalTexels; i++) {
      const idx = i * 4;

      if (i >= this.count) {
        data[idx] = 999999.0;
        data[idx + 1] = 999999.0;
        data[idx + 2] = 999999.0;
        data[idx + 3] = 1.0;
        continue;
      }

      let tx = 0;
      let ty = 0;
      let tz = 0;

      if (i < dnaEnd) {
        // ── 1. PRIMARY DNA DOUBLE HELIX (CENTERED SUBJECT) ─────────────────
        if (i < s1End) {
          // Strand 1 (Electric Blue -> Cyan)
          const st = i / s1End;
          const yp = (st - 0.5) * hgt;
          const ang = st * turns * TWO_PI + rotT;
          const r = rad + breathe * Math.sin(st * TWO_PI * 2 + time * 1.3);

          tx = Math.cos(ang) * r + this.jitterX[i];
          ty = yp + this.jitterY[i];
          tz = Math.sin(ang) * r + this.jitterZ[i];

          const wave = 0.5 + 0.5 * Math.sin(st * 24.0 - time * 1.4);
          this.pColor.copy(this.cElectricBlue).lerp(this.cCyan, wave);
          if (wave > 0.86) {
            this.pColor.lerp(this.cIceWhite, (wave - 0.86) * 4.6);
          }
        } else if (i < s2End) {
          // Strand 2 (Cyan -> SynThera Emerald)
          const li = i - s1End;
          const s2Count = s2End - s1End;
          const st = li / s2Count;
          const yp = (st - 0.5) * hgt;
          const ang = st * turns * TWO_PI + GROOVE_OFFSET + rotT;
          const r = rad + breathe * Math.sin(st * TWO_PI * 2 + time * 1.3);

          tx = Math.cos(ang) * r + this.jitterX[i];
          ty = yp + this.jitterY[i];
          tz = Math.sin(ang) * r + this.jitterZ[i];

          const wave = 0.5 + 0.5 * Math.sin(st * 24.0 + time * 1.25);
          this.pColor.copy(this.cCyan).lerp(this.cEmerald, wave);
          if (wave > 0.86) {
            this.pColor.lerp(this.cIceWhite, (wave - 0.86) * 4.5);
          }
        } else {
          // Base-Pair Rungs with Ice-White Hydrogen Bonds
          const li = i - s2End;
          const rungIdx = Math.min(numRungs - 1, Math.floor(li / perRung));
          const posR = (li % perRung) / Math.max(1, perRung - 1);
          const rSt = (rungIdx + 0.5) / numRungs;
          const rY = (rSt - 0.5) * hgt;
          const rAng = rSt * turns * TWO_PI + rotT;
          const rRad = rad + breathe * Math.sin(rSt * TWO_PI * 2 + time * 1.3);

          const x1 = Math.cos(rAng) * rRad;
          const z1 = Math.sin(rAng) * rRad;
          const x2 = Math.cos(rAng + GROOVE_OFFSET) * rRad;
          const z2 = Math.sin(rAng + GROOVE_OFFSET) * rRad;

          tx = x1 + (x2 - x1) * posR + this.jitterX[i] * 0.6;
          ty = rY + this.jitterY[i] * 0.6;
          tz = z1 + (z2 - z1) * posR + this.jitterZ[i] * 0.6;

          const baseColor = rungIdx % 2 === 0 ? this.cMint : this.cCyan;
          const centerGlow = Math.pow(Math.sin(posR * Math.PI), 2.2);
          this.tmpColorA.copy(baseColor).lerp(this.cElectricBlue, 0.2);
          this.pColor.copy(this.tmpColorA).lerp(this.cIceWhite, centerGlow * 0.78);
        }

        // When scrolling down, smoothly merge DNA particles into the ambient nebula cloud
        if (blend > 0.001) {
          const ni = i;
          const c = ni % 6;
          let nx = cxs[c] + g(ni) * SPREAD * 1.35;
          let ny = cys[c] + g(ni + 120) * SPREAD * 0.8;
          let nz = czs[c] + g(ni + 240) * SPREAD * 1.35;

          ny += Math.sin(time * 0.38 + ni * 0.012) * 2.2;
          nx += Math.cos(time * 0.28 + ni * 0.018) * 2.2;

          const ca = time * 0.04;
          const mx = nx * Math.cos(ca) - nz * Math.sin(ca) + this.jitterX[i];
          const my = ny + this.jitterY[i];
          const mz = nx * Math.sin(ca) + nz * Math.cos(ca) + this.jitterZ[i];

          tx = (1.0 - blend) * tx + blend * mx;
          ty = (1.0 - blend) * ty + blend * my;
          tz = (1.0 - blend) * tz + blend * mz;

          if (blend > 0.05) {
            const ambientTone =
              c === 0
                ? this.cElectricBlue
                : c === 1
                ? this.cCyan
                : c === 2
                ? this.cDarkNavy
                : c === 3
                ? this.cEmerald
                : this.cMint;
            this.pColor.lerp(ambientTone, blend * 0.65);
          }
        }
      } else if (i < nebulaEnd) {
        // ── 2. SPACE-FILLING VOLUMETRIC NEBULA CLOUDS ──────────────────────
        const ni = i - dnaEnd;
        const c = ni % 6;
        let nx = cxs[c] + g(ni) * SPREAD * 1.35;
        let ny = cys[c] + g(ni + 120) * SPREAD * 0.8;
        let nz = czs[c] + g(ni + 240) * SPREAD * 1.35;

        // Gentle organic drifting motion
        ny += Math.sin(time * 0.38 + ni * 0.012) * 2.2;
        nx += Math.cos(time * 0.28 + ni * 0.018) * 2.2;

        // Ambient slow cosmic rotation around center
        const ca = time * 0.04;
        tx = nx * Math.cos(ca) - nz * Math.sin(ca) + this.jitterX[i];
        ty = ny + this.jitterY[i];
        tz = nx * Math.sin(ca) + nz * Math.cos(ca) + this.jitterZ[i];

        // SynThera deep space aesthetic palette
        if (c === 0) {
          this.pColor.copy(this.cElectricBlue).lerp(this.cCyan, rnd(ni * 4.3));
        } else if (c === 1) {
          this.pColor.copy(this.cCyan).lerp(this.cIceWhite, 0.2 + rnd(ni * 5.1) * 0.4);
        } else if (c === 2) {
          this.pColor.copy(this.cDarkNavy).lerp(this.cElectricBlue, 0.4 + rnd(ni * 3.7) * 0.5);
        } else if (c === 3) {
          this.pColor.copy(this.cEmerald).lerp(this.cCyan, rnd(ni * 6.2));
        } else if (c === 4) {
          this.pColor.copy(this.cCyan).lerp(this.cMint, rnd(ni * 7.1));
        } else {
          this.pColor.copy(this.cMint).lerp(this.cIceWhite, 0.35);
        }
      } else {
        // ── 3. DISTANT QUANTUM / STELLAR FIELD PINPOINTS ───────────────────
        const si = i - nebulaEnd;
        const u = rnd(si * 1.7) * Math.PI * 2;
        const v = Math.acos(2 * rnd(si * 2.9) - 1);
        const r = 145 + rnd(si * 4.1) * 85;

        tx = r * Math.sin(v) * Math.cos(u);
        ty = r * Math.sin(v) * Math.sin(u);
        tz = r * Math.cos(v);

        // Twinkling white & electric cyan stars
        const tw = 0.55 + 0.45 * Math.sin(time * 2.1 + si * 0.8);
        this.tmpColorB.copy(this.cIceWhite).lerp(this.cCyan, 0.25);
        this.pColor.copy(this.tmpColorB).multiplyScalar(tw);
      }

      data[idx] = tx;
      data[idx + 1] = ty;
      data[idx + 2] = tz;
      data[idx + 3] = 1.0;

      this.mesh.setColorAt(i, this.pColor);
    }

    if (this.mesh.instanceColor) {
      this.mesh.instanceColor.needsUpdate = true;
    }
    this.targetTex.needsUpdate = true;
  }

  private applyScrollState() {
    if (!this.motionStateRef) return;
    const s = this.motionStateRef.current;

    this.swarmGroup.position.set(s.objX, s.objY, s.objZ);
    this.swarmGroup.rotation.set(s.rotX, s.rotY, s.rotZ);
    this.swarmGroup.scale.setScalar(s.scale);

    this.camera.position.set(s.camX, s.camY, s.camZ);
    this.lookTargetVec.set(s.lookX, s.lookY, s.lookZ);
    this.camera.lookAt(this.lookTargetVec);

    const effTurbulence =
      this.physicsOverrides.noiseStrength !== null
        ? this.physicsOverrides.noiseStrength
        : s.turbulence;
    const effStiffness =
      this.physicsOverrides.stiffness !== null
        ? this.physicsOverrides.stiffness
        : s.stiffness;

    this.velocityUniforms.uNoiseStrength.value = effTurbulence;
    this.velocityUniforms.uStiffness.value = effStiffness;
    this.bloomPass.strength = s.bloomIntensity;
    this.colorGradePass.uniforms["uGlobalAlpha"].value = s.brightness;
  }

  private animate = () => {
    if (this.disposed) return;
    this.rafId = requestAnimationFrame(this.animate);

    if (document.hidden) {
      this.clock.getDelta();
      return;
    }

    const delta = Math.min(this.clock.getDelta(), 0.05);
    const time = this.clock.getElapsedTime() * this.speedMult;

    this.applyScrollState();

    // 3D pointer tracking
    this.raycaster.setFromCamera(this.mouse, this.camera);
    this.raycaster.ray.intersectPlane(this.dummyPlane, this.intersectPoint);
    this.swarmGroup.worldToLocal(this.intersectPoint);
    this.velocityUniforms.uMouse3D.value.copy(this.intersectPoint);

    this.updateGPGPUTargets(time);

    this.velocityUniforms.uTime.value = time;
    this.velocityUniforms.uDeltaTime.value = delta || 0.016;

    this.gpuCompute.compute();

    const posTexture = this.gpuCompute.getCurrentRenderTarget(this.positionVariable).texture;
    if (this.material.userData.shader) {
      this.material.userData.shader.uniforms.texturePosition.value = posTexture;
      this.material.userData.shader.uniforms.gpgpuEnabled.value = 1.0;
    }

    this.composer.render(delta);
  };

  dispose() {
    this.disposed = true;
    if (this.rafId !== null) {
      cancelAnimationFrame(this.rafId);
      this.rafId = null;
    }
    window.removeEventListener("pointermove", this.handlePointerMove);
    window.removeEventListener("resize", this.handleResize);

    this.scene.remove(this.swarmGroup);
    this.geometry.dispose();
    this.material.dispose();
    this.targetTex.dispose();
    this.gpuCompute.dispose();
    this.composer.dispose();
    this.renderer.dispose();

    if (this.renderer.domElement.parentNode === this.container) {
      this.container.removeChild(this.renderer.domElement);
    }
  }
}
