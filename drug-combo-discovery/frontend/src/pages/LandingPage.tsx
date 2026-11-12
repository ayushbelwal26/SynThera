import React, { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { LandingNav } from "../components/landing/LandingNav";
import { HeroMolecularScene } from "../components/landing/HeroMolecularScene";
import { MolecularConvergenceCanvas } from "../components/landing/MolecularConvergenceCanvas";
import { BiologicalUniverseCanvas } from "../components/landing/BiologicalUniverseCanvas";
import {
  ArrowRight,
  ArrowUpRight,
  FlaskConical,
  Target,
  BookOpen,
  GitFork,
  Database,
  Cpu,
  ShieldCheck,
  Activity,
  CheckCircle2,
} from "lucide-react";

gsap.registerPlugin(ScrollTrigger);

export const LandingPage: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);

  // Section Refs for GSAP timelines
  const heroEyebrowRef = useRef<HTMLDivElement>(null);
  const heroTitleRef = useRef<HTMLHeadingElement>(null);
  const heroSubRef = useRef<HTMLParagraphElement>(null);
  const heroCtasRef = useRef<HTMLDivElement>(null);
  const heroVisualRef = useRef<HTMLDivElement>(null);

  const [convergenceProgress, setConvergenceProgress] = useState(0.2);

  useEffect(() => {
    const ctx = gsap.context(() => {
      // ── 1. Hero Entrance Timeline ──
      const tl = gsap.timeline({ defaults: { ease: "power3.out" } });

      tl.fromTo(
        heroEyebrowRef.current,
        { opacity: 0, y: 15 },
        { opacity: 1, y: 0, duration: 0.6, delay: 0.1 },
      )
        .fromTo(
          heroTitleRef.current,
          { opacity: 0, y: 25 },
          { opacity: 1, y: 0, duration: 0.8 },
          "-=0.4",
        )
        .fromTo(
          heroSubRef.current,
          { opacity: 0, y: 20 },
          { opacity: 1, y: 0, duration: 0.7 },
          "-=0.5",
        )
        .fromTo(
          heroCtasRef.current,
          { opacity: 0, y: 15 },
          { opacity: 1, y: 0, duration: 0.6 },
          "-=0.4",
        )
        .fromTo(
          heroVisualRef.current,
          { opacity: 0, scale: 0.95 },
          { opacity: 1, scale: 1, duration: 1.0, ease: "power2.out" },
          "-=0.7",
        );

      // ── 2. ScrollTrigger Convergence Section ──
      ScrollTrigger.create({
        trigger: "#problem",
        start: "top center",
        end: "bottom center",
        scrub: 1,
        onUpdate: (self) => {
          setConvergenceProgress(self.progress);
        },
      });

      // ── 3. Staggered Methodology Reveal ──
      gsap.fromTo(
        ".methodology-card",
        { opacity: 0, y: 30 },
        {
          opacity: 1,
          y: 0,
          duration: 0.6,
          stagger: 0.15,
          ease: "power2.out",
          scrollTrigger: {
            trigger: "#methodology",
            start: "top 75%",
          },
        },
      );
    }, containerRef);

    return () => ctx.revert();
  }, []);

  return (
    <div
      ref={containerRef}
      className="min-h-screen bg-[#05090D] text-[#F1F5F2] font-sans selection:bg-[#00D6A0]/20 selection:text-[#F1F5F2] overflow-x-hidden relative"
    >
      {/* ── Fixed Floating Landing Navigation ── */}
      <LandingNav />

      {/* ═══════════════════════════════════════════════════════════
          SECTION 1: HERO — CINEMATIC FULL VIEWPORT
      ═══════════════════════════════════════════════════════════ */}
      <section className="relative min-h-screen flex items-center pt-24 pb-16 px-6 lg:px-12 max-w-7xl mx-auto overflow-hidden">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center w-full">
          {/* Left Hero Narrative */}
          <div className="lg:col-span-7 space-y-7 z-10">
            <div ref={heroEyebrowRef} className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-[#00D6A0] shadow-[0_0_8px_rgba(0,214,160,0.8)]" />
              <span className="font-mono text-[11px] uppercase tracking-widest text-[#00D6A0] font-semibold">
                Computational Oncology / Drug Discovery
              </span>
            </div>

            <h1
              ref={heroTitleRef}
              className="font-serif text-[42px] sm:text-[56px] lg:text-[68px] leading-[1.08] font-normal tracking-tight text-[#F1F5F2]"
            >
              Discover the <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#00D6A0] via-[#35C9D5] to-[#8AE8CC]">
                connections
              </span>{" "}
              that change the future of cancer research.
            </h1>

            <p
              ref={heroSubRef}
              className="font-sans text-[16px] sm:text-[18px] text-[#94A5A6] max-w-xl leading-relaxed"
            >
              Exploring drug combinations through biological knowledge graphs, Heterogeneous
              Graph Transformers, and clinically verified peer-reviewed literature.
            </p>

            <div
              ref={heroCtasRef}
              className="flex flex-wrap items-center gap-4 pt-3 font-sans"
            >
              <Link
                to="/bench"
                className="st-btn-primary !py-3.5 !px-7 text-[14px] font-medium group"
              >
                <span>Explore SynThera</span>
                <ArrowRight
                  size={16}
                  className="group-hover:translate-x-1 transition-transform"
                />
              </Link>
              <a
                href="#problem"
                className="st-btn-ghost !py-3.5 !px-6 text-[14px]"
              >
                Discover the Science
              </a>
            </div>

            {/* Quick Scientific Trust Badges */}
            <div className="pt-6 border-t border-[#20343C]/40 flex flex-wrap items-center gap-6 font-mono text-[11px] text-[#60747A]">
              <span className="flex items-center gap-1.5">
                <Database size={12} className="text-[#35C9D5]" />
                PrimeKG Biological Network
              </span>
              <span>•</span>
              <span className="flex items-center gap-1.5">
                <Cpu size={12} className="text-[#00D6A0]" />
                Leave-Drugs-Out Cold GNN
              </span>
              <span>•</span>
              <span className="flex items-center gap-1.5">
                <ShieldCheck size={12} className="text-[#C7A76A]" />
                In-Silico Faithfulness
              </span>
            </div>
          </div>

          {/* Right Hero Interactive 3D Molecular Canvas */}
          <div
            ref={heroVisualRef}
            className="lg:col-span-5 h-[480px] lg:h-[620px] w-full relative"
          >
            <HeroMolecularScene />
            {/* Interactive hint badge */}
            <div className="absolute bottom-4 right-4 pointer-events-none bg-[#101C23]/80 backdrop-blur-xs border border-[#20343C] px-3 py-1 rounded-full text-[10.5px] font-mono text-[#60747A]">
              Interactive WebGL Molecule · Drag to orbit
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════
          SECTION 2: THE PROBLEM — "ONE DRUG TELLS ONLY PART..."
      ═══════════════════════════════════════════════════════════ */}
      <section
        id="problem"
        className="py-24 px-6 lg:px-12 max-w-7xl mx-auto border-t border-[#20343C]/60"
      >
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
          <div className="lg:col-span-6 space-y-6">
            <span className="section-label">The Therapeutic Paradox</span>
            <h2 className="font-serif text-[36px] sm:text-[46px] leading-tight text-[#F1F5F2]">
              One drug tells only part of the story.
            </h2>
            <p className="text-[16px] text-[#94A5A6] leading-relaxed">
              Monotherapy in oncology frequently encounters compensatory signaling pathways,
              metabolic bypasses, and acquired therapeutic resistance.
            </p>
            <p className="text-[14px] text-[#60747A] leading-relaxed">
              When two compounds are administered concurrently, their molecular targets interact across
              cellular cascades. SynThera maps these latent synergies—revealing where combined
              intervention induces potent synthetic lethality while minimizing toxic redundancy.
            </p>
            <div className="grid grid-cols-2 gap-4 pt-2 font-mono text-xs">
              <div className="p-4 rounded-xl bg-[#091218] border border-[#20343C]">
                <div className="text-[#00D6A0] font-bold text-[18px]">17,000+</div>
                <div className="text-[#60747A] mt-0.5">PrimeKG Target Phenotypes</div>
              </div>
              <div className="p-4 rounded-xl bg-[#091218] border border-[#20343C]">
                <div className="text-[#35C9D5] font-bold text-[18px]">37,700+</div>
                <div className="text-[#60747A] mt-0.5">Cold Benchmark Pairs</div>
              </div>
            </div>
          </div>

          <div className="lg:col-span-6 h-[440px] rounded-2xl border border-[#20343C] bg-[#091218] overflow-hidden relative shadow-2xl">
            <MolecularConvergenceCanvas progress={convergenceProgress} />
            <div className="absolute top-4 left-4 font-mono text-[11px] text-[#60747A] bg-[#101C23]/90 px-3 py-1.5 rounded-lg border border-[#20343C]">
              Scroll to observe compound target convergence
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════
          SECTION 3: HOW SYNTHERA WORKS — 4 CORE STAGES
      ═══════════════════════════════════════════════════════════ */}
      <section
        id="methodology"
        className="py-24 px-6 lg:px-12 max-w-7xl mx-auto border-t border-[#20343C]/60 space-y-16"
      >
        <div className="text-center max-w-2xl mx-auto space-y-3">
          <span className="section-label">End-to-End Methodology</span>
          <h2 className="font-serif text-[36px] sm:text-[46px] text-[#F1F5F2]">
            From molecular relationships to computational discovery.
          </h2>
          <p className="text-[15px] text-[#94A5A6]">
            Four interconnected research modules designed for oncology scientists, medicinal chemists, and translational biologists.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {/* Stage 01 */}
          <div className="methodology-card st-panel p-6 space-y-4 hover:border-[#00D6A0]/60 transition-all flex flex-col justify-between">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="font-mono text-[22px] font-bold text-[#00D6A0]">01</span>
                <FlaskConical size={18} className="text-[#00D6A0]" />
              </div>
              <h3 className="font-serif text-[20px] text-[#F1F5F2]">
                Drug Pair Analysis
              </h3>
              <p className="text-[13px] text-[#94A5A6] leading-relaxed">
                Evaluate two candidate compounds with calibrated GNN synergy probabilities,
                ablation faithfulness metrics, and multi-objective value scoring.
              </p>
            </div>
            <Link
              to="/bench"
              className="pt-4 border-t border-[#20343C] text-[12px] font-mono text-[#00D6A0] flex items-center justify-between hover:underline"
            >
              <span>Launch Bench</span>
              <ArrowRight size={13} />
            </Link>
          </div>

          {/* Stage 02 */}
          <div className="methodology-card st-panel p-6 space-y-4 hover:border-[#35C9D5]/60 transition-all flex flex-col justify-between">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="font-mono text-[22px] font-bold text-[#35C9D5]">02</span>
                <Target size={18} className="text-[#35C9D5]" />
              </div>
              <h3 className="font-serif text-[20px] text-[#F1F5F2]">
                Indication Discovery
              </h3>
              <p className="text-[13px] text-[#94A5A6] leading-relaxed">
                Traverse PrimeKG disease neighborhoods to score and rank candidate combinations
                using Beam Search or Monte Carlo Tree Search (MCTS).
              </p>
            </div>
            <Link
              to="/indication"
              className="pt-4 border-t border-[#20343C] text-[12px] font-mono text-[#35C9D5] flex items-center justify-between hover:underline"
            >
              <span>Explore Indications</span>
              <ArrowRight size={13} />
            </Link>
          </div>

          {/* Stage 03 */}
          <div className="methodology-card st-panel p-6 space-y-4 hover:border-[#C7A76A]/60 transition-all flex flex-col justify-between">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="font-mono text-[22px] font-bold text-[#C7A76A]">03</span>
                <BookOpen size={18} className="text-[#C7A76A]" />
              </div>
              <h3 className="font-serif text-[20px] text-[#F1F5F2]">
                Scientific Evidence
              </h3>
              <p className="text-[13px] text-[#94A5A6] leading-relaxed">
                Automatically query and cite peer-reviewed clinical studies from NCBI PubMed,
                matching retained mechanistic edges to verified publications.
              </p>
            </div>
            <Link
              to="/literature"
              className="pt-4 border-t border-[#20343C] text-[12px] font-mono text-[#C7A76A] flex items-center justify-between hover:underline"
            >
              <span>View PubMed Evidence</span>
              <ArrowRight size={13} />
            </Link>
          </div>

          {/* Stage 04 */}
          <div className="methodology-card st-panel p-6 space-y-4 hover:border-[#8AE8CC]/60 transition-all flex flex-col justify-between">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="font-mono text-[22px] font-bold text-[#8AE8CC]">04</span>
                <GitFork size={18} className="text-[#8AE8CC]" />
              </div>
              <h3 className="font-serif text-[20px] text-[#F1F5F2]">
                Biological Neighborhoods
              </h3>
              <p className="text-[13px] text-[#94A5A6] leading-relaxed">
                Interactive knowledge graph navigation across multi-relational drug, target,
                enzymatic, and oncological phenotype connections.
              </p>
            </div>
            <Link
              to="/neighborhood"
              className="pt-4 border-t border-[#20343C] text-[12px] font-mono text-[#8AE8CC] flex items-center justify-between hover:underline"
            >
              <span>Open Knowledge Graph</span>
              <ArrowRight size={13} />
            </Link>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════
          SECTION 4: THE BIOLOGICAL UNIVERSE — 3D GRAPH CONSTELLATION
      ═══════════════════════════════════════════════════════════ */}
      <section
        id="universe"
        className="py-24 px-6 lg:px-12 max-w-7xl mx-auto border-t border-[#20343C]/60 space-y-8"
      >
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div>
            <span className="section-label">PrimeKG Topological Space</span>
            <h2 className="font-serif text-[36px] sm:text-[46px] text-[#F1F5F2] mt-1">
              Biology is a network. <br />
              Discovery starts with its connections.
            </h2>
          </div>
          <p className="text-[14px] text-[#94A5A6] max-w-md font-sans">
            Hover over nodes in the interactive constellation below to inspect biological entity taxonomy:
            Drugs (Emerald), Targets (Gold), Pathways (Cyan), and Diseases (Ruby).
          </p>
        </div>

        <div className="h-[520px] rounded-2xl border border-[#20343C] bg-[#091218] overflow-hidden relative shadow-2xl">
          <BiologicalUniverseCanvas />
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════
          SECTION 5: THE INTELLIGENCE BEHIND DISCOVERY
      ═══════════════════════════════════════════════════════════ */}
      <section
        id="intelligence"
        className="py-24 px-6 lg:px-12 max-w-7xl mx-auto border-t border-[#20343C]/60 space-y-12"
      >
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
          <div className="lg:col-span-6 space-y-6">
            <span className="section-label">Rigorous Generalization</span>
            <h2 className="font-serif text-[36px] sm:text-[44px] text-[#F1F5F2] leading-tight">
              Beyond isolated predictions.
            </h2>
            <p className="text-[15px] text-[#94A5A6] leading-relaxed">
              Most combination models rely on transductive pair-splitting, creating massive data leakage
              by testing pairs of drugs already seen during training.
            </p>
            <p className="text-[14px] text-[#60747A] leading-relaxed">
              SynThera enforces strict <strong>Cold-Drug (Leave-Drugs-Out)</strong> inductive splitting.
              A held-out 15% of compounds are never seen during training, ensuring that predicted
              synergy reflects true biological generalization across PrimeKG biomedical networks.
            </p>

            <div className="space-y-2.5 pt-2 font-mono text-xs">
              <div className="flex items-center gap-3 p-3 rounded-lg bg-[#091218] border border-[#20343C]">
                <CheckCircle2 size={16} className="text-[#00D6A0] shrink-0" />
                <span>Inductive leave-drugs-out cold evaluation protocol</span>
              </div>
              <div className="flex items-center gap-3 p-3 rounded-lg bg-[#091218] border border-[#20343C]">
                <CheckCircle2 size={16} className="text-[#00D6A0] shrink-0" />
                <span>Multi-objective ranking penalized by known DDI and side-effect overlap</span>
              </div>
              <div className="flex items-center gap-3 p-3 rounded-lg bg-[#091218] border border-[#20343C]">
                <CheckCircle2 size={16} className="text-[#00D6A0] shrink-0" />
                <span>In-silico sufficiency & necessity graph edge ablation verification</span>
              </div>
            </div>
          </div>

          {/* Interactive Metric Architecture Block */}
          <div className="lg:col-span-6 st-panel p-8 space-y-6">
            <div className="border-b border-[#20343C] pb-4 flex items-center justify-between">
              <div>
                <span className="text-[10.5px] font-mono text-[#00D6A0] uppercase tracking-wider block">
                  Model Benchmark Highlights
                </span>
                <h4 className="font-serif text-[20px] text-[#F1F5F2] mt-0.5">
                  SynergyGNN Cold Inductive Metric Suite
                </h4>
              </div>
              <span className="font-mono text-[11px] px-2.5 py-1 rounded bg-[#14242B] text-[#35C9D5]">
                PrimeKG + DrugComb
              </span>
            </div>

            <div className="grid grid-cols-2 gap-4 font-mono">
              <div className="p-4 rounded-xl bg-[#091218] border border-[#20343C]">
                <span className="text-[10px] text-[#60747A] uppercase block">Test Cold AUROC</span>
                <span className="text-[26px] font-bold text-[#00D6A0] block mt-1">0.64</span>
                <span className="text-[10.5px] text-[#60747A]">Disjoint Drug Pools (37.7k pairs)</span>
              </div>

              <div className="p-4 rounded-xl bg-[#091218] border border-[#20343C]">
                <span className="text-[10px] text-[#60747A] uppercase block">Test Cold AUPR</span>
                <span className="text-[26px] font-bold text-[#35C9D5] block mt-1">0.44</span>
                <span className="text-[10.5px] text-[#60747A]">Random baseline: ~0.16</span>
              </div>

              <div className="p-4 rounded-xl bg-[#091218] border border-[#20343C]">
                <span className="text-[10px] text-[#60747A] uppercase block">Random Split AUROC</span>
                <span className="text-[26px] font-bold text-[#C7A76A] block mt-1">0.87</span>
                <span className="text-[10.5px] text-[#60747A]">Transductive Pair Split</span>
              </div>

              <div className="p-4 rounded-xl bg-[#091218] border border-[#20343C]">
                <span className="text-[10px] text-[#60747A] uppercase block">Chat Grounding</span>
                <span className="text-[26px] font-bold text-[#8AE8CC] block mt-1">100%</span>
                <span className="text-[10.5px] text-[#60747A]">Zero ungrounded assertions</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════
          SECTION 6: PLATFORM PREVIEW — CINEMATIC BROWSER MOCKUP
      ═══════════════════════════════════════════════════════════ */}
      <section
        id="preview"
        className="py-24 px-6 lg:px-12 max-w-7xl mx-auto border-t border-[#20343C]/60 space-y-10"
      >
        <div className="text-center max-w-xl mx-auto space-y-2">
          <span className="section-label">Interactive Instrument</span>
          <h2 className="font-serif text-[36px] sm:text-[46px] text-[#F1F5F2]">
            Enter the Research Workspace
          </h2>
          <p className="text-[14px] text-[#94A5A6]">
            A unified computational oncology workbench integrating pairwise prediction, indication traversal, and biological graph topology.
          </p>
        </div>

        {/* Browser Shell Frame */}
        <div className="rounded-2xl border border-[#20343C] bg-[#091218] shadow-2xl overflow-hidden">
          {/* Browser Top Controls */}
          <div className="px-5 py-3 border-b border-[#20343C] bg-[#05090D] flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-[#E05260]/60 inline-block" />
              <span className="w-3 h-3 rounded-full bg-[#C7A76A]/60 inline-block" />
              <span className="w-3 h-3 rounded-full bg-[#00D6A0]/60 inline-block" />
            </div>
            <div className="font-mono text-[11px] text-[#60747A] bg-[#101C23] px-6 py-1 rounded-full border border-[#20343C]">
              synthera.app/bench
            </div>
            <div className="w-12" />
          </div>

          {/* Interactive Preview Surface */}
          <div className="p-8 lg:p-12 grid grid-cols-1 md:grid-cols-12 gap-8 items-center bg-gradient-to-b from-[#091218] to-[#05090D]">
            <div className="md:col-span-7 space-y-5">
              <div className="flex items-center gap-2 text-xs font-mono text-[#00D6A0]">
                <Activity size={14} />
                <span>Live Scientific Environment</span>
              </div>
              <h3 className="font-serif text-[28px] text-[#F1F5F2]">
                Temozolomide + Cyclophosphamide in T98G
              </h3>
              <p className="text-[14px] text-[#94A5A6] leading-relaxed">
                In silico evaluation predicts synergy probability of 0.88, driven by MGMT target engagement
                and downstream synthetic lethality cross-links. Supported by clinical trials indexed in PubMed (PMID: 30341984).
              </p>
              <div className="pt-2">
                <Link to="/bench" className="st-btn-primary">
                  <span>Open Interactive Bench</span>
                  <ArrowUpRight size={14} />
                </Link>
              </div>
            </div>

            <div className="md:col-span-5 p-5 rounded-xl border border-[#20343C] bg-[#101C23] space-y-3 font-mono text-xs">
              <div className="flex justify-between border-b border-[#20343C] pb-2 text-[#94A5A6]">
                <span>Classification:</span>
                <span className="text-[#00D6A0] font-bold">SYNERGY</span>
              </div>
              <div className="flex justify-between border-b border-[#20343C] pb-2 text-[#94A5A6]">
                <span>P(Synergy):</span>
                <span className="text-[#F1F5F2]">0.88</span>
              </div>
              <div className="flex justify-between border-b border-[#20343C] pb-2 text-[#94A5A6]">
                <span>Multi-Objective V:</span>
                <span className="text-[#35C9D5]">0.82</span>
              </div>
              <div className="flex justify-between text-[#94A5A6]">
                <span>Faithfulness:</span>
                <span className="text-[#00D6A0]">VERIFIED</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════
          SECTION 7: CLOSING CALL TO ACTION & FOOTER
      ═══════════════════════════════════════════════════════════ */}
      <section className="py-28 px-6 lg:px-12 max-w-7xl mx-auto border-t border-[#20343C]/60 text-center space-y-8 relative overflow-hidden">
        <div className="max-w-2xl mx-auto space-y-4 relative z-10">
          <h2 className="font-serif text-[42px] sm:text-[54px] text-[#F1F5F2] leading-tight tracking-tight">
            Every connection holds a possibility.
          </h2>
          <p className="text-[16px] text-[#94A5A6] leading-relaxed">
            Explore the intersection of computational intelligence and cancer biology with SynThera.
          </p>
          <div className="pt-4">
            <Link
              to="/bench"
              className="st-btn-primary !py-4 !px-8 text-[15px] font-medium"
            >
              <span>Explore SynThera</span>
              <ArrowRight size={16} />
            </Link>
          </div>
        </div>
      </section>

      {/* ── Refined Footer ── */}
      <footer className="border-t border-[#20343C] bg-[#05090D] py-12 px-6 lg:px-12 text-xs font-mono text-[#60747A]">
        <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-4 gap-8">
          <div className="space-y-3">
            <div className="font-serif text-[18px] text-[#F1F5F2] font-bold">SynThera</div>
            <p className="text-[12px] leading-relaxed text-[#94A5A6] font-sans">
              Artificial intelligence platform for discovering, ranking, and explaining synergistic oncology drug combinations.
            </p>
          </div>

          <div>
            <div className="text-[11px] uppercase tracking-wider text-[#F1F5F2] mb-3">Workspaces</div>
            <ul className="space-y-2">
              <li><Link to="/bench" className="hover:text-[#00D6A0]">01 · Bench</Link></li>
              <li><Link to="/indication" className="hover:text-[#00D6A0]">02 · Indication</Link></li>
              <li><Link to="/literature" className="hover:text-[#00D6A0]">03 · Literature</Link></li>
              <li><Link to="/neighborhood" className="hover:text-[#00D6A0]">04 · Neighborhood</Link></li>
            </ul>
          </div>

          <div>
            <div className="text-[11px] uppercase tracking-wider text-[#F1F5F2] mb-3">Data Sources</div>
            <ul className="space-y-2">
              <li>Harvard PrimeKG Biomedical Graph</li>
              <li>DrugComb Experimental Synergies</li>
              <li>NCBI PubMed E-Utilities RAG</li>
              <li>Morgan 2048-bit Fingerprints</li>
            </ul>
          </div>

          <div>
            <div className="text-[11px] uppercase tracking-wider text-[#F1F5F2] mb-3">Notice</div>
            <p className="leading-relaxed text-[#60747A] font-sans">
              For investigational and hypothesis-generation purposes only. Not intended for direct clinical prescription without wet-lab verification.
            </p>
          </div>
        </div>

        <div className="max-w-7xl mx-auto pt-8 mt-8 border-t border-[#20343C]/40 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div>© {new Date().getFullYear()} SynThera Platform. All rights reserved.</div>
          <div className="text-[#00D6A0]">Midnight Scientific Intelligence</div>
        </div>
      </footer>
    </div>
  );
};
