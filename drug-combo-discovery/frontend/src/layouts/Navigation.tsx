import React from "react";
import { NavLink } from "react-router-dom";
import { FlaskConical, Target, BookOpen, GitFork } from "lucide-react";

interface NavItem {
  to: string;
  num: string;
  label: string;
  sub: string;
  icon: React.ComponentType<{ className?: string; size?: number }>;
}

const navItems: NavItem[] = [
  {
    to: "/bench",
    num: "01",
    label: "Bench",
    sub: "Drug Pair Analysis",
    icon: FlaskConical,
  },
  {
    to: "/indication",
    num: "02",
    label: "Indication",
    sub: "Disease-Specific Discovery",
    icon: Target,
  },
  {
    to: "/literature",
    num: "03",
    label: "Literature",
    sub: "PubMed Scientific Evidence",
    icon: BookOpen,
  },
  {
    to: "/neighborhood",
    num: "04",
    label: "Neighborhood",
    sub: "Biological Knowledge Graph",
    icon: GitFork,
  },
];

export const Navigation: React.FC = () => {
  return (
    <nav className="flex flex-col gap-1.5 px-3 py-4 flex-1" aria-label="Primary Navigation">
      <div className="px-3 pb-2 text-[10px] font-mono uppercase tracking-wider text-[var(--color-text-muted)]">
        Research Modules
      </div>
      {navItems.map((item) => {
        const Icon = item.icon;
        return (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `group relative flex items-start gap-3 px-3 py-2.5 rounded-lg text-[13.5px] transition-all duration-200 ${
                isActive
                  ? "bg-[var(--color-surface)] text-[var(--color-accent)] border border-[var(--color-accent)] shadow-[0_0_12px_var(--color-accent-glow)] font-semibold"
                  : "text-[var(--color-text-secondary)] hover:bg-[var(--color-accent-soft)]/60 hover:text-[var(--color-text-primary)] border border-transparent"
              }`
            }
          >
            {({ isActive }) => (
              <>
                <div
                  className={`mt-0.5 p-1 rounded-md transition-colors ${
                    isActive
                      ? "text-[var(--color-accent)]"
                      : "text-[var(--color-text-muted)] group-hover:text-[var(--color-accent)]"
                  }`}
                >
                  <Icon size={16} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <span className="font-medium tracking-tight text-[var(--color-text-primary)]">
                      {item.label}
                    </span>
                    <span
                      className={`text-[10px] font-mono font-bold ${
                        isActive
                          ? "text-[var(--color-accent)]"
                          : "text-[var(--color-text-muted)]"
                      }`}
                    >
                      {item.num}
                    </span>
                  </div>
                  <p
                    className={`text-[11px] truncate mt-0.5 ${
                      isActive ? "text-[var(--color-accent)] font-medium" : "text-[var(--color-text-muted)]"
                    }`}
                  >
                    {item.sub}
                  </p>
                </div>
              </>
            )}
          </NavLink>
        );
      })}
    </nav>
  );
};
