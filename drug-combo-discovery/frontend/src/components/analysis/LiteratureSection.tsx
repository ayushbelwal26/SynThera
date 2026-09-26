import type { LiteratureCitation, LiteratureResult } from "../../types/api";

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
      <p className="meta-text leading-relaxed">
        {literature?.no_literature_reason ||
          "No matching PubMed records for this pair. Mechanism may be novel relative to indexed literature."}
        {literature?.query_used && (
          <span className="block mt-1.5 id-text">Query: {literature.query_used}</span>
        )}
      </p>
    );
  }

  return (
    <div className="divide-y divide-[#CFC9BC] border-y border-[#CFC9BC]">
      {activeCitations.map((cite, idx) => (
        <article
          key={cite.pmid || idx}
          className="py-3.5 grid grid-cols-1 md:grid-cols-12 gap-3"
        >
          <div className="md:col-span-3 id-text space-y-0.5">
            <a
              href={cite.url}
              target="_blank"
              rel="noopener noreferrer"
              className="underline underline-offset-2 decoration-[#CFC9BC] hover:decoration-[#1A535C] text-[#1A1F1C]"
            >
              PMID {cite.pmid}
            </a>
            {cite.journal && <div className="meta-text">{cite.journal}</div>}
            {cite.year && <div className="meta-text">{cite.year}</div>}
          </div>
          <div className="md:col-span-9">
            <h4 className="font-serif text-[16px] text-[#1A1F1C] leading-snug font-semibold">
              {cite.title}
            </h4>
            {cite.snippet && (
              <p className="mt-1.5 text-[13px] text-[#4A524C] italic leading-relaxed">
                “{cite.snippet}”
              </p>
            )}
            <div className="mt-2 flex flex-wrap gap-x-3 gap-y-0.5 meta-text">
              {cite.match_reason && <span>Match · {cite.match_reason}</span>}
              {drugAName && drugBName && (
                <span>
                  {drugAName} + {drugBName}
                </span>
              )}
              {cite.evidence_type && <span>{cite.evidence_type}</span>}
            </div>
          </div>
        </article>
      ))}
    </div>
  );
};
