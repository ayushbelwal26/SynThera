import React from 'react';
import { NavLink } from 'react-router-dom';
import { Compass, Activity, BookOpen, Network } from 'lucide-react';

export const Navigation: React.FC = () => {
  const links = [
    { to: '/discover', label: 'Discover & Query', icon: Compass },
    { to: '/analysis', label: 'Mechanistic Analysis', icon: Activity },
    { to: '/evidence', label: 'Literature Evidence', icon: BookOpen },
    { to: '/graph', label: 'Knowledge Graph Explorer', icon: Network },
  ];

  return (
    <nav className="flex items-center gap-1 border-b border-[#E5E5E0] bg-[#FFFFFF] px-6">
      {links.map((link) => {
        const Icon = link.icon;
        return (
          <NavLink
            key={link.to}
            to={link.to}
            className={({ isActive }) =>
              `flex items-center gap-2 py-3 px-3.5 text-xs font-semibold tracking-wide border-b-2 transition-all ${
                isActive
                  ? 'border-[#0D9488] text-[#0F766E] bg-[#F0FDFA]/50'
                  : 'border-transparent text-[#64748B] hover:text-[#0F172A] hover:bg-[#F8FAFC]'
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
