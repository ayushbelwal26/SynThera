import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { ArrowUpRight, Menu, X } from "lucide-react";

export const LandingNav: React.FC = () => {
  const [isScrolled, setIsScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 40);
    };
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const scrollTo = (id: string) => {
    setMobileMenuOpen(false);
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: "smooth" });
    }
  };

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 px-6 py-4 flex items-center justify-between ${
        isScrolled
          ? "bg-[#05090D]/85 backdrop-blur-md border-b border-[#20343C]/80 py-3 shadow-xl"
          : "bg-transparent"
      }`}
    >
      <div className="w-full max-w-7xl mx-auto flex items-center justify-between">
        {/* Brand Monogram */}
        <Link to="/" className="flex items-center gap-2.5 group">
          <div className="w-8 h-8 rounded-lg bg-[#101C23] border border-[#00D6A0]/40 flex items-center justify-center font-serif text-[17px] font-bold text-[#F1F5F2] group-hover:border-[#00D6A0] transition-colors shadow-sm">
            <span className="w-2 h-2 rounded-full bg-[#00D6A0] inline-block mr-0.5 animate-pulse" />
            ST
          </div>
          <div className="flex flex-col">
            <span className="font-serif text-[20px] font-bold tracking-tight text-[#F1F5F2] leading-none">
              SynThera
            </span>
            <span className="text-[9.5px] font-mono uppercase tracking-widest text-[#60747A] mt-0.5">
              Computational Oncology
            </span>
          </div>
        </Link>

        {/* Center Anchors */}
        <nav className="hidden md:flex items-center gap-8 text-[13px] font-sans text-[#94A5A6]">
          <button
            type="button"
            onClick={() => scrollTo("problem")}
            className="hover:text-[#F1F5F2] transition-colors cursor-pointer"
          >
            The Paradox
          </button>
          <button
            type="button"
            onClick={() => scrollTo("methodology")}
            className="hover:text-[#F1F5F2] transition-colors cursor-pointer"
          >
            Methodology
          </button>
          <button
            type="button"
            onClick={() => scrollTo("universe")}
            className="hover:text-[#F1F5F2] transition-colors cursor-pointer"
          >
            Biological Universe
          </button>
          <button
            type="button"
            onClick={() => scrollTo("intelligence")}
            className="hover:text-[#F1F5F2] transition-colors cursor-pointer"
          >
            GNN Intelligence
          </button>
          <button
            type="button"
            onClick={() => scrollTo("preview")}
            className="hover:text-[#F1F5F2] transition-colors cursor-pointer"
          >
            Platform Preview
          </button>
        </nav>

        {/* Right Action CTA */}
        <div className="hidden md:flex items-center gap-4">
          <Link
            to="/bench"
            className="text-[13px] font-mono text-[#94A5A6] hover:text-[#F1F5F2] transition-colors"
          >
            Direct Access
          </Link>
          <Link
            to="/bench"
            className="st-btn-primary !py-2 !px-4 text-[12.5px] font-medium"
          >
            <span>Explore Platform</span>
            <ArrowUpRight size={14} />
          </Link>
        </div>

        {/* Mobile menu trigger */}
        <button
          type="button"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="md:hidden p-2 text-[#94A5A6] hover:text-[#F1F5F2]"
        >
          {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="md:hidden absolute top-full left-0 right-0 bg-[#091218] border-b border-[#20343C] p-6 space-y-4 font-sans text-[14px]">
          <button
            type="button"
            onClick={() => scrollTo("problem")}
            className="block text-left w-full text-[#94A5A6] hover:text-[#F1F5F2]"
          >
            The Paradox
          </button>
          <button
            type="button"
            onClick={() => scrollTo("methodology")}
            className="block text-left w-full text-[#94A5A6] hover:text-[#F1F5F2]"
          >
            Methodology
          </button>
          <button
            type="button"
            onClick={() => scrollTo("universe")}
            className="block text-left w-full text-[#94A5A6] hover:text-[#F1F5F2]"
          >
            Biological Universe
          </button>
          <button
            type="button"
            onClick={() => scrollTo("intelligence")}
            className="block text-left w-full text-[#94A5A6] hover:text-[#F1F5F2]"
          >
            GNN Intelligence
          </button>
          <div className="pt-3 border-t border-[#20343C]">
            <Link
              to="/bench"
              className="st-btn-primary w-full text-center justify-center"
            >
              Enter Research Platform
            </Link>
          </div>
        </div>
      )}
    </header>
  );
};
