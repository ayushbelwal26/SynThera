import React from 'react';
import { NavLink } from 'react-router-dom';
import { FlaskConical, BarChart3, BookOpen, Network } from 'lucide-react';

const links = [
  { to: '/discover', label: 'Discover', icon: FlaskConical },
  { to: '/analysis', label: 'Analysis', icon: BarChart3 },
  { to: '/evidence', label: 'Evidence', icon: BookOpen },
  { to: '/graph', label: 'Graph Explorer', icon: Network },
];

export const Navigation: React.FC = () => (
  <nav style={{
    backgroundColor: 'var(--surface)',
    borderBottom: '1px solid var(--border)',
  }}>
    <div className="max-w-screen-xl mx-auto px-5 sm:px-8 flex items-center gap-1">
      {links.map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          style={({ isActive }) => ({
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            padding: '10px 14px',
            fontSize: 13,
            fontWeight: 600,
            color: isActive ? 'var(--accent)' : 'var(--text-secondary)',
            borderBottom: `2px solid ${isActive ? 'var(--accent)' : 'transparent'}`,
            transition: 'color 150ms, border-color 150ms, background-color 150ms',
            textDecoration: 'none',
            letterSpacing: '-0.01em',
            whiteSpace: 'nowrap',
            borderRadius: isActive ? '0' : '0',
          })}
          className={({ isActive }) =>
            !isActive ? 'hover:text-[color:var(--text-primary)] hover:bg-[color:var(--surface-subtle)]' : ''
          }
        >
          <Icon size={14} strokeWidth={2} />
          <span>{label}</span>
        </NavLink>
      ))}
    </div>
  </nav>
);
