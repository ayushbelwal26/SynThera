import React, { Suspense, lazy, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useGSAP } from "@gsap/react";
import { LandingNav } from "../components/landing/LandingNav";
import { StaticMolecularFallback } from "../components/landing/StaticMolecularFallback";
import {
  INITIAL_CINEMATIC_STATE,
  type CinematicMotionState,
} from "../components/landing/cinematicMotionTypes";
import {
  ArrowRight,
  Microscope,
  Target,
  FileSearch,
  Network,
  CheckCircle2,
  ShieldCheck,
  GitBranch,
  ChevronRight,
} from "lucide-react";

gsap.registerPlugin(ScrollTrigger, useGSAP);

const CinematicMolecularCanvas = lazy(
  () => import("../components/landing/CinematicMolecularCanvas")
);

export const LandingPage: React.FC = () => {
  const pageRef = useRef<HTMLDivElement>(null);
  const motionStateRef = useRef<CinematicMotionState>({ ...INITIAL_CINEMATIC_STATE });
  const requestRenderRef = useRef<(() => void) | null>(null);

  const [reducedMotion, setReducedMotion] = useState<boolean>(() => {
    if (typeof window === "undefined") return true;
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  });

  const [isMobile, setIsMobile] = useState<boolean>(() => {
    if (typeof window === "undefined") return false;
    return window.innerWidth < 768;
  });

  // Track viewport width (for mobile particle density) & reduced-motion preference cleanly
  useEffect(() => {
    if (typeof window === "undefined") return;
    const motionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");

    const updateMode = () => {
      setReducedMotion(motionQuery.matches);
      setIsMobile(window.innerWidth < 768);
    };

    updateMode();
    motionQuery.addEventListener("change", updateMode);
    window.addEventListener("resize", updateMode);

    return () => {
      motionQuery.removeEventListener("change", updateMode);
      window.removeEventListener("resize", updateMode);
    };
  }, []);

  // Coordinated single-timeline scroll choreography driving the persistent particle DNA system
  useGSAP(
    () => {
      const container = pageRef.current;
      if (!container) return;

      const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      if (reduced) {
        return;
      }

      // Reset to Hero resting pose before timeline initialization
      Object.assign(motionStateRef.current, INITIAL_CINEMATIC_STATE);
      requestRenderRef.current?.();

      // Master continuous scroll-controlled timeline driving the GPGPU particle swarm
      const tl = gsap.timeline({
        defaults: { ease: "none" },
        scrollTrigger: {
          trigger: container,
          start: "top top",
          end: "bottom bottom",
          scrub: 1.1,
          invalidateOnRefresh: true,
          onUpdate: () => {
            requestRenderRef.current?.();
          },
        },
      });

      // Scene 01 -> Scene 02 (The Paradox / Problem):
      // As user scrolls down, DNA double-helix smoothly dissolves and merges into the ambient particle swarm.
      // Position remains centered and tranquil without jarring lateral jumping.
      tl.to(motionStateRef.current, {
        helixBlend: 1.0,
        objX: 0,
        objY: 0,
        objZ: 0,
        rotX: 0.08,
        rotY: 0.28,
        rotZ: -0.06,
        scale: 1.02,
        camX: 0,
        camY: 0,
        camZ: 102,
        lookX: 0,
        lookY: 0,
        lookZ: 0,
        turbulence: 0.04,
        stiffness: 1.9,
        bloomIntensity: 0.44,
        brightness: 0.95,
        duration: 0.22,
      });

      // Scene 02 -> Scene 03A (Methodology):
      // Continues as a serene, space-filling ambient field of drifting particles that lets content shine
      tl.to(motionStateRef.current, {
        helixBlend: 1.0,
        objX: 0,
        objY: 0,
        objZ: 0,
        rotX: 0.06,
        rotY: 0.58,
        rotZ: 0.02,
        scale: 1.03,
        camX: 0,
        camY: 0,
        camZ: 100,
        lookX: 0,
        lookY: 0,
        lookZ: 0,
        turbulence: 0.06,
        stiffness: 1.8,
        bloomIntensity: 0.42,
        brightness: 0.92,
        duration: 0.22,
      });

      // Scene 03A -> Scene 03B (Biological Universe):
      // Particles softly expand into an expansive, gentle biological cosmic cloud
      tl.to(motionStateRef.current, {
        helixBlend: 1.0,
        objX: 0,
        objY: 0,
        objZ: -2,
        rotX: 0.08,
        rotY: 0.9,
        rotZ: -0.04,
        scale: 1.05,
        camX: 0,
        camY: 0,
        camZ: 98,
        lookX: 0,
        lookY: 0,
        lookZ: 0,
        turbulence: 0.12,
        stiffness: 1.6,
        bloomIntensity: 0.45,
        brightness: 0.92,
        duration: 0.2,
      });

      // Scene 03B -> Scene 04 (GNN Intelligence):
      // Peaceful biological particle currents framing the model cards
      tl.to(motionStateRef.current, {
        helixBlend: 1.0,
        objX: 0,
        objY: 0,
        objZ: -4,
        rotX: 0.06,
        rotY: 1.2,
        rotZ: 0.0,
        scale: 1.0,
        camX: 0,
        camY: 0,
        camZ: 102,
        lookX: 0,
        lookY: 0,
        lookZ: 0,
        turbulence: 0.04,
        stiffness: 2.0,
        bloomIntensity: 0.4,
        brightness: 0.88,
        duration: 0.18,
      });

      // Scene 04 -> Scene 05 (Platform Preview & Closing):
      // Camera pulls back gently into the deep midnight background
      tl.to(motionStateRef.current, {
        helixBlend: 1.0,
        objX: 0,
        objY: 4,
        objZ: -15,
        rotX: 0.05,
        rotY: 1.5,
        rotZ: 0.0,
        scale: 0.88,
        camX: 0,
        camY: 0,
        camZ: 118,
        lookX: 0,
        lookY: 0,
        lookZ: 0,
        turbulence: 0.02,
        stiffness: 2.2,
        bloomIntensity: 0.28,
        brightness: 0.45,
        duration: 0.18,
      });

      // Ensure ScrollTrigger recalculates cleanly once fonts and layout settle
      const refreshTimer = window.setTimeout(() => {
        ScrollTrigger.refresh();
      }, 250);

      return () => {
        window.clearTimeout(refreshTimer);
      };
    },
    { scope: pageRef, dependencies: [reducedMotion] }
  );

  return (
    <div
      ref={pageRef}
      className="relative min-h-screen bg-[#020409] text-[#F1F5F2] selection:bg-[#22D3EE]/30 selection:text-[#F1F5F2]"
    >
      {/* Persistent Single-Subject Holographic Particle DNA Scene */}
      <div className="hero-canvas-layer fixed inset-0 pointer-events-none z-0 overflow-hidden">
        {reducedMotion ? (
          <StaticMolecularFallback />
        ) : (
          <Suspense fallback={<StaticMolecularFallback />}>
            <CinematicMolecularCanvas
              motionStateRef={motionStateRef}
              requestRenderRef={requestRenderRef}
              isMobile={isMobile}
            />
          </Suspense>
        )}
      </div>

      {/* Global Navigation */}
      <LandingNav />

      {/* ====================================================================
          SCENE 01 — HERO (0–18%)
          Centered DNA Double Helix as Primary Subject; Space-Filling Nebula Clouds
          Typography centered with high-clarity scrim (matches reference design)
      ==================================================================== */}
      <section className="relative z-10 flex min-h-screen flex-col items-center justify-center overflow-hidden pt-28 pb-20">
        {/* Soft centered dark radial scrim ensuring crystal-clear typography contrast */}
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0"
          style={{
            background:
              "radial-gradient(62% 62% at 50% 50%, rgba(2, 4, 9, 0.78) 0%, rgba(2, 4, 9, 0.38) 60%, rgba(2, 4, 9, 0) 100%)",
          }}
        />

        <div className="relative mx-auto flex w-full max-w-5xl flex-col items-center px-6 text-center lg:px-10">
          <div className="mb-7 inline-flex items-center gap-2.5 rounded-full border border-[#20343C] bg-[#0B141A]/85 px-4 py-1.5 backdrop-blur-md shadow-sm">
            <span className="h-2 w-2 rounded-full bg-[#00D6A0] animate-pulse" />
            <span className="font-mono text-[11px] font-semibold uppercase tracking-[0.2em] text-[#8AE8CC]">
              Oncology Computational Pharmacology
            </span>
          </div>

          <h1 className="max-w-4xl text-4xl font-semibold leading-[1.08] tracking-tight text-[#F1F5F2] sm:text-5xl md:text-6xl lg:text-[66px]">
            Discover the connections that change the future of cancer research.
          </h1>

          <p className="mt-7 max-w-2xl text-base leading-relaxed text-[#94A5A6] sm:text-lg">
            SynThera unifies inductive graph neural networks over PrimeKG with
            evidence-grounded literature synthesis to discover actionable
            therapeutic drug combinations.
          </p>

          <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
            <Link
              to="/bench"
              className="st-btn-primary inline-flex items-center gap-2.5 rounded-lg px-7 py-3.5 text-sm font-semibold shadow-lg shadow-[#00D6A0]/15"
            >
              Explore Platform <ArrowRight size={16} />
            </Link>
            <a
              href="#methodology"
              className="st-btn-ghost inline-flex items-center gap-2 rounded-lg bg-[#05090D]/70 px-6 py-3.5 text-sm font-semibold backdrop-blur-md border border-[#20343C]/80 hover:border-[#35C9D5]/60 hover:text-[#E8F8FF] transition-all"
            >
              See How It Works
            </a>
          </div>

          <div className="mt-12 flex flex-wrap items-center justify-center gap-x-8 gap-y-3 border-t border-[#20343C]/50 pt-7 text-xs font-medium text-[#60747A]">
            <span className="flex items-center gap-2">
              <ShieldCheck size={14} className="text-[#00D6A0]" />
              PrimeKG Biological Network
            </span>
            <span className="flex items-center gap-2">
              <GitBranch size={14} className="text-[#35C9D5]" />
              Leave-Drugs-Out Cold GNN
            </span>
            <span className="flex items-center gap-2">
              <CheckCircle2 size={14} className="text-[#00D6A0]" />
              In-Silico Faithfulness
            </span>
          </div>

          {/* Centered Scroll Indicator */}
          <div className="mt-12 flex flex-col items-center gap-1.5 opacity-60 hover:opacity-100 transition-opacity">
            <span className="font-mono text-[10px] uppercase tracking-[0.25em] text-[#8AE8CC]">
              Scroll to Explore
            </span>
            <ChevronRight size={14} className="rotate-90 text-[#35C9D5] animate-bounce" />
          </div>
        </div>
      </section>

      {/* ====================================================================
          SCENE 02 — THE THERAPEUTIC PARADOX (#problem)
          Subject glides toward center-left; content shifts right in asymmetric rhythm
      ==================================================================== */}
      <section
        id="problem"
        className="relative z-10 flex min-h-screen items-center border-t border-[#20343C]/35 py-28 lg:py-36"
      >
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0"
          style={{
            background:
              "radial-gradient(58% 65% at 76% 52%, rgba(5, 9, 13, 0.86) 0%, rgba(5, 9, 13, 0.42) 60%, rgba(5, 9, 13, 0) 100%)",
          }}
        />

        <div className="relative mx-auto grid w-full max-w-7xl grid-cols-1 gap-12 px-6 lg:grid-cols-12 lg:px-10">
          {/* Negative space on the left lets the rotating molecular cleft breathe */}
          <div className="hidden lg:col-span-5 lg:block" />

          <div className="lg:col-span-7">
            <div className="rounded-2xl border border-[#20343C]/80 bg-[#070E14]/82 p-8 shadow-2xl backdrop-blur-md sm:p-11">
              <div className="section-label mb-3">01 · The Therapeutic Paradox</div>
              <h2 className="text-3xl font-semibold tracking-tight text-[#F1F5F2] sm:text-4xl lg:text-[42px]">
                One drug tells only part of the story.
              </h2>

              <p className="mt-6 text-base leading-relaxed text-[#94A5A6]">
                Cancer thrives on redundant signaling pathways and adaptive bypass
                circuits. Traditional single-agent therapies often trigger acquired
                resistance within months.
              </p>
              <p className="mt-4 text-base leading-relaxed text-[#94A5A6]">
                Yet screening every candidate pair across cellular models is
                combinatorially intractable. Most neural models memorize training
                compounds rather than generalizing to unseen drugs or targets.
              </p>

              <div className="mt-9 grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div className="rounded-xl border border-[#20343C] bg-[#0B141B]/90 p-5">
                  <div className="font-mono text-2xl font-bold text-[#00D6A0]">
                    17,000+
                  </div>
                  <div className="mt-1 text-xs font-medium uppercase tracking-wider text-[#94A5A6]">
                    PrimeKG Target Phenotypes
                  </div>
                </div>
                <div className="rounded-xl border border-[#20343C] bg-[#0B141B]/90 p-5">
                  <div className="font-mono text-2xl font-bold text-[#35C9D5]">
                    37,700+
                  </div>
                  <div className="mt-1 text-xs font-medium uppercase tracking-wider text-[#94A5A6]">
                    Cold Benchmark Pairs
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ====================================================================
          SCENE 03A — DISCOVERY PROCESS (#methodology)
          Camera focuses close on the ligand-binding cleft on the left;
          4 methodology pillars cascade along the right rail
      ==================================================================== */}
      <section
        id="methodology"
        className="relative z-10 border-t border-[#20343C]/35 py-28 lg:py-36"
      >
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0"
          style={{
            background:
              "linear-gradient(90deg, rgba(5, 9, 13, 0.15) 0%, rgba(5, 9, 13, 0.65) 48%, rgba(5, 9, 13, 0.9) 100%)",
          }}
        />

        <div className="relative mx-auto grid w-full max-w-7xl grid-cols-1 gap-12 px-6 lg:grid-cols-12 lg:px-10">
          {/* Left column anchors the section title sparsely above the zoomed binding site */}
          <div className="lg:col-span-5 lg:sticky lg:top-32 lg:self-start">
            <div className="rounded-2xl border border-[#20343C]/70 bg-[#05090D]/72 p-6 backdrop-blur-md">
              <div className="section-label mb-3">02 · End-to-End Methodology</div>
              <h2 className="text-3xl font-semibold tracking-tight text-[#F1F5F2] sm:text-4xl">
                Four connected modules for translational discovery.
              </h2>
              <p className="mt-4 text-sm leading-relaxed text-[#94A5A6]">
                As paired drug scaffolds converge around shared oncogenic hubs,
                each module interrogates complementary structural, topological,
                and clinical evidence layers.
              </p>
            </div>
          </div>

          {/* Right rail: clean architectural module stack */}
          <div className="space-y-5 lg:col-span-7">
            {[
              {
                num: "01",
                icon: Microscope,
                color: "#00D6A0",
                title: "Drug Pair Analysis",
                desc: "Score synergy probability, selectivity, and toxicity risk for any candidate drug pair in an explicit oncology cell context.",
                route: "/bench",
              },
              {
                num: "02",
                icon: Target,
                color: "#35C9D5",
                title: "Indication Discovery",
                desc: "Identify optimal drug partners and responsive tumor cell lines for an anchor therapeutic agent via global candidate sweeps.",
                route: "/indication",
              },
              {
                num: "03",
                icon: FileSearch,
                color: "#8AE8CC",
                title: "Scientific Evidence",
                desc: "Synthesize mechanistic hypotheses and PubMed clinical support with strict citation grounding verification.",
                route: "/literature",
              },
              {
                num: "04",
                icon: Network,
                color: "#C7A76A",
                title: "Biological Neighborhoods",
                desc: "Traverse shared target proteins, pathway crosstalk, and topological bridges inside PrimeKG knowledge graphs.",
                route: "/neighborhood",
              },
            ].map((stage) => {
              const Icon = stage.icon;
              return (
                <Link
                  key={stage.num}
                  to={stage.route}
                  className="group block rounded-2xl border border-[#20343C] bg-[#081016]/85 p-7 backdrop-blur-md transition-colors hover:border-[#35C9D5]/60 hover:bg-[#0D1820]/90"
                >
                  <div className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
                    <div className="flex items-start gap-5">
                      <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-[#20343C] bg-[#0D1A22]">
                        <Icon size={20} style={{ color: stage.color }} />
                      </div>
                      <div>
                        <span className="font-mono text-[11px] font-bold tracking-widest text-[#60747A]">
                          STAGE {stage.num}
                        </span>
                        <h3 className="mt-1 text-xl font-semibold text-[#F1F5F2] transition-colors group-hover:text-[#00D6A0]">
                          {stage.title}
                        </h3>
                        <p className="mt-2.5 text-sm leading-relaxed text-[#94A5A6]">
                          {stage.desc}
                        </p>
                      </div>
                    </div>

                    <div className="inline-flex shrink-0 items-center gap-1.5 self-start font-mono text-xs font-semibold text-[#35C9D5] sm:mt-1">
                      Open <ChevronRight size={14} className="transition-transform group-hover:translate-x-0.5" />
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        </div>
      </section>

      {/* ====================================================================
          SCENE 03B — PRIMEKG TOPOLOGICAL SPACE (#universe)
          Expansive center framing letting the rotating protein-ligand structure breathe
      ==================================================================== */}
      <section
        id="universe"
        className="relative z-10 flex min-h-screen flex-col justify-between border-t border-[#20343C]/35 py-24 lg:py-32"
      >
        {/* Soft vignette only around the upper and lower edges so center stays luminous */}
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0"
          style={{
            background:
              "linear-gradient(180deg, rgba(5, 9, 13, 0.78) 0%, rgba(5, 9, 13, 0.12) 45%, rgba(5, 9, 13, 0.12) 60%, rgba(5, 9, 13, 0.85) 100%)",
          }}
        />

        <div className="relative mx-auto w-full max-w-7xl px-6 lg:px-10">
          <div className="max-w-2xl rounded-2xl border border-[#20343C]/65 bg-[#05090D]/72 p-7 backdrop-blur-md">
            <div className="section-label mb-3">03 · PrimeKG Topological Space</div>
            <h2 className="text-3xl font-semibold tracking-tight text-[#F1F5F2] sm:text-4xl lg:text-5xl">
              Biology is a network. Discovery starts with its connections.
            </h2>
          </div>
        </div>

        <div className="relative mx-auto mt-64 w-full max-w-7xl px-6 lg:mt-80 lg:px-10">
          <div className="ml-auto max-w-xl rounded-2xl border border-[#20343C]/75 bg-[#060C11]/82 p-7 backdrop-blur-md">
            <p className="text-base leading-relaxed text-[#94A5A6]">
              SynThera maps compound perturbation profiles onto multi-relational
              biological subgraphs—connecting drugs, protein targets, pathway
              cascades, and cellular phenotypes in a unified latent manifold.
            </p>
            <div className="mt-5 flex flex-wrap gap-3 font-mono text-[11px] uppercase tracking-wider text-[#8AE8CC]">
              <span className="rounded-md border border-[#20343C] bg-[#0B141A] px-3 py-1">
                Structural Motif Clefts
              </span>
              <span className="rounded-md border border-[#20343C] bg-[#0B141A] px-3 py-1">
                Pathway Bridge Distance
              </span>
              <span className="rounded-md border border-[#20343C] bg-[#0B141A] px-3 py-1">
                Cell-Line Gene Context
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* ====================================================================
          SCENE 04 — BIOLOGICAL INTELLIGENCE (#intelligence)
          Subject shifts left into an expansive backlit silhouette;
          benchmark metrics anchor on the right
      ==================================================================== */}
      <section
        id="intelligence"
        className="relative z-10 flex min-h-screen items-center border-t border-[#20343C]/35 py-28 lg:py-36"
      >
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0"
          style={{
            background:
              "radial-gradient(62% 70% at 72% 50%, rgba(5, 9, 13, 0.88) 0%, rgba(5, 9, 13, 0.45) 58%, rgba(5, 9, 13, 0) 100%)",
          }}
        />

        <div className="relative mx-auto grid w-full max-w-7xl grid-cols-1 items-center gap-12 px-6 lg:grid-cols-12 lg:px-10">
          {/* Open space on left for the rim-lit macromolecular complex */}
          <div className="hidden lg:col-span-5 lg:block" />

          <div className="space-y-8 lg:col-span-7">
            <div className="rounded-2xl border border-[#20343C]/70 bg-[#060C11]/78 p-7 backdrop-blur-md sm:p-9">
              <div className="section-label mb-3">04 · Rigorous Generalization</div>
              <h2 className="text-3xl font-semibold tracking-tight text-[#F1F5F2] sm:text-4xl">
                Beyond isolated predictions.
              </h2>
              <p className="mt-4 text-base leading-relaxed text-[#94A5A6]">
                Most computational models fail when evaluated on completely unseen
                drugs. SynThera is engineered and benchmarked under strict
                leave-drugs-out cold generalization, paired with mechanistic
                faithfulness auditing.
              </p>

              <div className="mt-7 grid grid-cols-1 gap-4 sm:grid-cols-3">
                {[
                  {
                    title: "Leave-Drugs-Out Cold Testing",
                    desc: "Disjoint drug pools between training and evaluation ensure structural novelty generalization.",
                  },
                  {
                    title: "Faithfulness Guardrails",
                    desc: "Automated verification checks ensure chat hypotheses align with graph topology.",
                  },
                  {
                    title: "PubMed Provenance",
                    desc: "Direct evidence synthesis matching mechanistic targets with peer-reviewed citations.",
                  },
                ].map((item) => (
                  <div
                    key={item.title}
                    className="rounded-xl border border-[#20343C]/80 bg-[#0A131A]/85 p-4"
                  >
                    <h4 className="text-xs font-semibold text-[#F1F5F2]">
                      {item.title}
                    </h4>
                    <p className="mt-1.5 text-xs leading-relaxed text-[#94A5A6]">
                      {item.desc}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            {/* Verified Benchmark Metric Suite */}
            <div className="rounded-2xl border border-[#20343C] bg-[#081016]/90 p-7 backdrop-blur-md">
              <div className="mb-5 flex items-center justify-between border-b border-[#20343C] pb-4">
                <span className="font-mono text-xs font-semibold uppercase tracking-widest text-[#35C9D5]">
                  SynergyGNN Cold Inductive Metric Suite
                </span>
                <span className="rounded bg-[#00D6A0]/15 px-2.5 py-1 font-mono text-[10px] font-bold text-[#00D6A0]">
                  VERIFIED
                </span>
              </div>

              <div className="grid grid-cols-2 gap-4">
                {[
                  {
                    label: "Test Cold AUROC",
                    val: "0.64",
                    sub: "Disjoint Drug Pools (37.7k pairs)",
                    color: "#00D6A0",
                  },
                  {
                    label: "Test Cold AUPR",
                    val: "0.44",
                    sub: "Random baseline: ~0.16",
                    color: "#35C9D5",
                  },
                  {
                    label: "Random Split AUROC",
                    val: "0.87",
                    sub: "Transductive Pair Split",
                    color: "#8AE8CC",
                  },
                  {
                    label: "Chat Grounding",
                    val: "100%",
                    sub: "Zero ungrounded assertions",
                    color: "#C7A76A",
                  },
                ].map((metric) => (
                  <div
                    key={metric.label}
                    className="rounded-xl border border-[#20343C]/80 bg-[#060C11]/90 p-4"
                  >
                    <div className="text-[11px] font-semibold uppercase tracking-wider text-[#60747A]">
                      {metric.label}
                    </div>
                    <div
                      className="mt-1.5 font-mono text-2xl font-bold"
                      style={{ color: metric.color }}
                    >
                      {metric.val}
                    </div>
                    <div className="mt-1 text-[11px] text-[#94A5A6]">
                      {metric.sub}
                    </div>
                  </div>
                ))}
              </div>
              <p className="mt-5 border-t border-[#20343C]/60 pt-4 font-mono text-[11px] text-[#60747A]">
                Note: The background B-DNA double-helix visualization is an illustrative structural graphic; metrics above report empirical leave-drugs-out benchmark evaluation.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ====================================================================
          SCENE 05 — PLATFORM PREVIEW (#preview)
          Subject recedes softly into the deep background; UI becomes primary focus
      ==================================================================== */}
      <section
        id="preview"
        className="relative z-10 border-t border-[#20343C]/45 bg-[#020612]/60 py-28 backdrop-blur-[2px] lg:py-36"
      >
        <div className="mx-auto max-w-7xl px-6 lg:px-10">
          <div className="mx-auto mb-14 max-w-2xl text-center">
            <div className="section-label mb-3">05 · Interactive Instrument</div>
            <h2 className="text-3xl font-semibold tracking-tight text-[#F1F5F2] sm:text-4xl lg:text-5xl">
              Enter the Research Workspace
            </h2>
            <p className="mt-4 text-base text-[#94A5A6]">
              Explore synergy landscapes, pathway neighborhoods, and cited
              mechanistic hypotheses directly inside the SynThera instrument.
            </p>
          </div>

          {/* Browser Mockup Frame */}
          <div className="overflow-hidden rounded-2xl border border-[#20343C] bg-[#0B1218]/95 shadow-2xl shadow-black/80">
            {/* Mockup Top Chrome */}
            <div className="flex items-center justify-between border-b border-[#20343C] bg-[#101C23] px-5 py-3.5">
              <div className="flex items-center gap-2">
                <div className="h-2.5 w-2.5 rounded-full bg-[#E06C75]/75" />
                <div className="h-2.5 w-2.5 rounded-full bg-[#C7A76A]/75" />
                <div className="h-2.5 w-2.5 rounded-full bg-[#00D6A0]/75" />
                <span className="ml-3 font-mono text-[11px] text-[#60747A]">
                  app.synthera.science/bench
                </span>
              </div>
              <Link
                to="/bench"
                className="font-mono text-[11px] font-semibold text-[#00D6A0] hover:underline"
              >
                Launch Live Workspace →
              </Link>
            </div>

            {/* Mockup Interior Layout */}
            <div className="grid grid-cols-1 gap-6 p-6 md:p-8 lg:grid-cols-12">
              {/* Left Sidebar Sim */}
              <div className="space-y-4 rounded-xl border border-[#20343C] bg-[#0E161E] p-5 lg:col-span-4">
                <div className="font-mono text-[10px] font-bold uppercase tracking-widest text-[#60747A]">
                  Configuration
                </div>
                <div className="space-y-3">
                  <div className="rounded-lg border border-[#20343C] bg-[#080E14] px-3 py-2.5">
                    <div className="text-[10px] text-[#60747A]">Drug A</div>
                    <div className="text-xs font-semibold text-[#F1F5F2]">
                      Temozolomide
                    </div>
                  </div>
                  <div className="rounded-lg border border-[#20343C] bg-[#080E14] px-3 py-2.5">
                    <div className="text-[10px] text-[#60747A]">Drug B</div>
                    <div className="text-xs font-semibold text-[#F1F5F2]">
                      Cyclophosphamide
                    </div>
                  </div>
                  <div className="rounded-lg border border-[#20343C] bg-[#080E14] px-3 py-2.5">
                    <div className="text-[10px] text-[#60747A]">Cell Line</div>
                    <div className="text-xs font-semibold text-[#35C9D5]">
                      T98G (Glioblastoma)
                    </div>
                  </div>
                </div>
              </div>

              {/* Main Canvas Sim */}
              <div className="space-y-5 lg:col-span-8">
                <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-[#20343C] bg-[#0E161E] p-5">
                  <div>
                    <span className="rounded bg-[#00D6A0]/15 px-2.5 py-1 font-mono text-[10px] font-bold uppercase text-[#00D6A0]">
                      SYNERGY
                    </span>
                    <div className="mt-2 text-sm font-semibold text-[#F1F5F2]">
                      Temozolomide + Cyclophosphamide in T98G
                    </div>
                  </div>
                  <div className="flex gap-6 font-mono text-xs">
                    <div>
                      <div className="text-[10px] text-[#60747A]">P(Synergy)</div>
                      <div className="text-base font-bold text-[#00D6A0]">0.76</div>
                    </div>
                    <div>
                      <div className="text-[10px] text-[#60747A]">
                        Multi-Objective V
                      </div>
                      <div className="text-base font-bold text-[#35C9D5]">0.50</div>
                    </div>
                    <div>
                      <div className="text-[10px] text-[#60747A]">
                        Faithfulness
                      </div>
                      <div className="text-base font-bold text-[#8AE8CC]">
                        VERIFIED
                      </div>
                    </div>
                  </div>
                </div>

                <div className="rounded-xl border border-[#20343C] bg-[#0E161E] p-5">
                  <div className="mb-3 flex items-center justify-between">
                    <span className="font-mono text-[10px] font-bold uppercase tracking-widest text-[#35C9D5]">
                      Mechanistic Summary & Literature Evidence
                    </span>
                    <span className="font-mono text-[10px] text-[#60747A]">
                      PMID: 35837107
                    </span>
                  </div>
                  <p className="text-xs leading-relaxed text-[#94A5A6]">
                    Dual alkylating regimen shows complementary DNA damage and
                    checkpoint stress in glioblastoma context. SynergyGNN ranks
                    top topological target connectivity through DNA repair
                    modulation and apoptosis crosstalk.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ====================================================================
          CLOSING CTA & FOOTER
      ==================================================================== */}
      <section className="relative z-10 border-t border-[#20343C]/60 bg-[#05090D]/80 py-28 backdrop-blur-sm lg:py-36">
        <div className="mx-auto max-w-4xl px-6 text-center">
          <div className="section-label mb-4">Launch SynThera</div>
          <h2 className="text-3xl font-semibold tracking-tight text-[#F1F5F2] sm:text-5xl">
            Every connection holds a possibility.
          </h2>
          <p className="mx-auto mt-6 max-w-xl text-base text-[#94A5A6]">
            Begin discovering cold-generalizing oncology combinations backed by
            knowledge-graph mechanics and cited clinical literature.
          </p>
          <div className="mt-10 flex flex-wrap justify-center gap-4">
            <Link
              to="/bench"
              className="st-btn-primary inline-flex items-center gap-2.5 rounded-lg px-8 py-4 text-sm font-semibold shadow-lg shadow-[#00D6A0]/15"
            >
              Launch Research Workspace <ArrowRight size={16} />
            </Link>
            <Link
              to="/indication"
              className="st-btn-ghost inline-flex items-center gap-2 rounded-lg px-7 py-4 text-sm font-semibold"
            >
              Run Indication Sweep
            </Link>
          </div>
        </div>
      </section>

      <footer className="relative z-10 border-t border-[#20343C] bg-[#04070B] py-12 text-xs text-[#60747A]">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-6 px-6 md:flex-row lg:px-10">
          <div className="flex items-center gap-3">
            <span className="font-semibold tracking-tight text-[#F1F5F2]">
              SynThera Platform
            </span>
            <span>·</span>
            <span>Computational Drug Combination Discovery</span>
          </div>
          <div className="flex flex-wrap items-center gap-6">
            <Link to="/bench" className="transition-colors hover:text-[#F1F5F2]">
              Discovery Bench
            </Link>
            <Link
              to="/indication"
              className="transition-colors hover:text-[#F1F5F2]"
            >
              Indication Sweep
            </Link>
            <Link
              to="/literature"
              className="transition-colors hover:text-[#F1F5F2]"
            >
              Literature Synthesis
            </Link>
            <Link
              to="/neighborhood"
              className="transition-colors hover:text-[#F1F5F2]"
            >
              Biological Neighborhoods
            </Link>
          </div>
          <div className="font-mono text-[11px]">
            © {new Date().getFullYear()} SynThera Platform
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
