import React from "react";
import { NavLink } from "react-router-dom";
import { Compass, Activity, BookOpen, Network } from "lucide-react";

export const Navigation: React.FC = () => {
  const links = [
    { to: "/discover", label: "Discover & Query", icon: Compass },
    { to: "/analysis", label: "Mechanistic Analysis", icon: Activity },
    { to: "/evidence", label: "Literature Evidence", icon: BookOpen },
    { to: "/graph", label: "Knowledge Graph Explorer", icon: Network },
  ];

  return (
    <nav className="flex items-center gap-1 border-b border-[#E5E2DC] bg-[#FFFEFB] px-6">
      {links.map((link) => {
        const Icon = link.icon;
        return (
          <NavLink
            key={link.to}
            to={link.to}
            className={({ isActive }) =>
              `flex items-center gap-2 py-2.5 px-3 text-xs tracking-wide border-b-2 transition-all ${
                isActive
                  ? "border-[#2F6B5E] text-[#25564B] bg-[#E8F0ED]/50 font-semibold"
                  : "border-transparent text-[#6B746F] hover:text-[#1C2421] hover:bg-[#F3F1EC] font-medium"
              }`
            }
          >
            <Icon className="w-4 h-4" />
            <span>{link.label}</span>
          </NavLink>
        );
      })}
    </nav>
  );
};
