import React, { useState, useId } from 'react';
import { ChevronDown } from 'lucide-react';

interface AccordionSectionProps {
  title: string;
  subtitle?: string;
  badge?: React.ReactNode;
  defaultOpen?: boolean;
  children: React.ReactNode;
  /** Accent applied to the left border when open */
  accentColor?: string;
  icon?: React.ReactNode;
}

export const AccordionSection: React.FC<AccordionSectionProps> = ({
  title,
  subtitle,
  badge,
  defaultOpen = false,
  children,
  accentColor = 'var(--accent)',
  icon,
}) => {
  const [open, setOpen] = useState(defaultOpen);
  const id = useId();

  return (
    <div
      style={{
        backgroundColor: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: 8,
        overflow: 'hidden',
        boxShadow: 'var(--shadow-xs)',
        borderLeft: open ? `3px solid ${accentColor}` : '3px solid transparent',
        transition: 'border-left-color 200ms',
      }}
    >
      <button
        type="button"
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen((o) => !o)}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 12,
          padding: '14px 18px',
          cursor: 'pointer',
          backgroundColor: 'transparent',
          border: 'none',
          textAlign: 'left',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0 }}>
          {icon && (
            <span style={{ color: open ? accentColor : 'var(--text-muted)', flexShrink: 0, transition: 'color 200ms' }}>
              {icon}
            </span>
          )}
          <div style={{ minWidth: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
              <span style={{
                fontSize: 13,
                fontWeight: 600,
                color: open ? 'var(--text-primary)' : 'var(--text-secondary)',
                transition: 'color 200ms',
                letterSpacing: '-0.01em',
              }}>
                {title}
              </span>
              {badge}
            </div>
            {subtitle && (
              <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
                {subtitle}
              </p>
            )}
          </div>
        </div>

        <ChevronDown
          size={16}
          style={{
            color: 'var(--text-muted)',
            flexShrink: 0,
            transform: open ? 'rotate(180deg)' : 'rotate(0deg)',
            transition: 'transform 220ms ease',
          }}
        />
      </button>

      <div id={id} className={`accordion-content ${open ? 'open' : ''}`}>
        <div className="accordion-inner">
          <div style={{ borderTop: '1px solid var(--border)', padding: '18px 18px 20px' }}>
            {children}
          </div>
        </div>
      </div>
    </div>
  );
};
