import React from "react";
import { NavLink } from "react-router-dom";
import {
  FlaskConical,
  Target,
  BookOpen,
  GitFork,
  Search,
} from "lucide-react";

interface OrbitalNavProps {
  onOpenCommand: () => void;
}

export const OrbitalNavigation: React.FC<OrbitalNavProps> = ({
  onOpenCommand,
}) => {
  const destinations = [
    {
      to: "/bench",
      num: "01",
      label: "BENCH",
      desc: "Drug Pair Analysis",
      icon: FlaskConical,
    },
    {
      to: "/indication",
      num: "02",
      label: "INDICATION",
      desc: "Disease Discovery",
      icon: Target,
    },
    {
      to: "/literature",
      num: "03",
      label: "LITERATURE",
      desc: "Scientific Evidence",
      icon: BookOpen,
    },
    {
      to: "/neighborhood",
      num: "04",
      label: "NEIGHBORHOOD",
      desc: "Biological Intelligence",
      icon: GitFork,
    },
  ];

  return (
    <div className="flex items-center gap-2 bg-[#091218]/90 backdrop-blur-md border border-[#20343C] p-1.5 rounded-full shadow-2xl">
      {/* Brand Monogram Motif */}
      <div className="flex items-center gap-2 pl-3 pr-2 border-r border-[#20343C]">
        <div className="relative flex items-center justify-center w-6 h-6 rounded-full bg-[#101C23] border border-[#00D6A0]/40">
          <span className="w-2 h-2 rounded-full bg-[#00D6A0] animate-pulse" />
        </div>
        <span className="font-serif text-[15px] font-bold text-[#F1F5F2] tracking-tight">
          SynThera
        </span>
      </div>

      {/* Primary 4 Orbital Destinations */}
      <nav className="flex items-center gap-1" aria-label="Orbital Navigation">
        {destinations.map((dest) => {
          const Icon = dest.icon;
          return (
            <NavLink
              key={dest.to}
              to={dest.to}
              className={({ isActive }) =>
                `group relative flex items-center gap-2 px-3.5 py-1.5 rounded-full text-[12px] font-mono transition-all duration-200 cursor-pointer ${
                  isActive
                    ? "bg-[#14242B] text-[#00D6A0] border border-[#00D6A0]/40 shadow-xs font-semibold"
                    : "text-[#94A5A6] hover:text-[#F1F5F2] hover:bg-[#101C23]"
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <Icon
                    size={13}
                    className={`transition-colors ${
                      isActive ? "text-[#00D6A0]" : "text-[#60747A] group-hover:text-[#F1F5F2]"
                    }`}
                  />
                  <span className="tracking-wide">{dest.label}</span>
                  <span className="text-[10px] text-[#60747A] opacity-70">
                    {dest.num}
                  </span>

                  {/* Contextual Tooltip */}
                  <span className="pointer-events-none absolute -bottom-8 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity bg-[#101C23] text-[#F1F5F2] text-[10.5px] font-sans px-2 py-0.5 rounded border border-[#20343C] whitespace-nowrap shadow-lg z-30">
                    {dest.desc}
                  </span>
                </>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* Global Cmd+K Search Trigger */}
      <button
        type="button"
        onClick={onOpenCommand}
        className="flex items-center gap-1.5 px-3 py-1.5 ml-1 rounded-full text-[11px] font-mono text-[#60747A] bg-[#101C23] border border-[#20343C] hover:text-[#00D6A0] hover:border-[#00D6A0]/30 transition-all cursor-pointer"
        title="Open Command Palette (Cmd+K)"
      >
        <Search size={11} />
        <span>Cmd K</span>
      </button>
    </div>
  );
};

