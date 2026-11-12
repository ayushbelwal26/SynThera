import type { LiteratureCitation, LiteratureResult } from "../../types/api";
import { ExternalLink } from "lucide-react";

interface LiteratureSectionProps {
  citations?: LiteratureCitation[];
  literature?: LiteratureResult | null;
  drugAName?: string;
  drugBName?: string;
}

export const LiteratureSection: React.FC<LiteratureSectionProps> = ({
  citations = [],
  literature,
  drugAName,
  drugBName,
}) => {
  const activeCitations =
    literature?.citations && literature.citations.length > 0
      ? literature.citations
      : citations && citations.length > 0
        ? citations
        : [];

  if (!activeCitations.length) {
    return (
      <div className="p-4 rounded-lg bg-[var(--color-surface)] border border-[var(--color-rule)]">
        <p className="meta-text leading-relaxed text-[var(--color-text-secondary)]">
          {literature?.no_literature_reason ||
            "No matching PubMed co-occurrence records for this combination. Mechanism may represent a novel candidate relative to current indexed literature."}
        </p>
        {literature?.query_used && (
          <span className="block mt-2 font-mono text-[11px] text-[var(--color-accent)]">
            PubMed Query: {literature.query_used}
          </span>
        )}
      </div>
    );
  }

  return (
    <div className="divide-y divide-[var(--color-rule)]/60 border-y border-[var(--color-rule)]">
      {activeCitations.map((cite, idx) => (
        <article
          key={cite.pmid || idx}
          className="py-4 grid grid-cols-1 md:grid-cols-12 gap-4"
        >
          <div className="md:col-span-3 space-y-1 font-mono text-[12px]">
            <a
              href={cite.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 font-bold text-[var(--color-accent)] hover:underline"
            >
              <span>PMID {cite.pmid}</span>
              <ExternalLink size={12} />
            </a>
            {cite.journal && (
              <div className="text-[var(--color-text-muted)] truncate">
                {cite.journal}
              </div>
            )}
            {cite.year && (
              <div className="text-[var(--color-text-muted)]">{cite.year}</div>
            )}
          </div>

          <div className="md:col-span-9 space-y-1.5">
            <h4 className="font-serif text-[16px] text-[var(--color-text-primary)] font-semibold leading-snug">
              {cite.title}
            </h4>
            {cite.snippet && (
              <p className="text-[13px] text-[var(--color-text-secondary)] italic leading-relaxed pl-2.5 border-l-2 border-[var(--color-rule-strong)]">
                “{cite.snippet}”
              </p>
            )}
            <div className="flex flex-wrap gap-2 pt-1 font-mono text-[11px]">
              {cite.match_reason && (
                <span className="px-2 py-0.5 rounded bg-[var(--color-accent-soft)] text-[var(--color-accent)] font-medium">
                  {cite.match_reason}
                </span>
              )}
              {drugAName && drugBName && (
                <span className="px-2 py-0.5 rounded bg-[var(--color-panel)] border border-[var(--color-rule)] text-[var(--color-text-muted)]">
                  {drugAName} + {drugBName}
                </span>
              )}
            </div>
          </div>
        </article>
      ))}
    </div>
  );
};
