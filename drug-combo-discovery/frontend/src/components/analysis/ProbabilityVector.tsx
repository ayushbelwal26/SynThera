import type { PredictionResult } from "../../types/api";

interface ProbabilityVectorProps {
  prediction: PredictionResult;
}

function classLabel(cls: string): string {
  if (cls === "synergy") return "Synergy";
  if (cls === "antagonism") return "Antagonism";
  return "Additive";
}

export const ProbabilityVector: React.FC<ProbabilityVectorProps> = ({
  prediction,
}) => {
  const pSyn = prediction.p_synergy ?? 0;
  const pAdd = prediction.p_additive ?? 0;
  const pAnt = prediction.p_antagonism ?? 0;
  const total = pSyn + pAdd + pAnt || 1;
  const v =
    prediction.v_score ?? prediction.ranking?.v_score ?? prediction.score ?? 0;
  const tox = prediction.ranking?.toxicity_penalty;
  const method = prediction.search_method || "beam";

  const primaryP =
    prediction.predicted_class === "antagonism"
      ? pAnt
      : prediction.predicted_class === "additive"
        ? pAdd
        : pSyn;

  return (
    <div className="bench-panel">
      <p className="font-serif text-[22px] text-[#1A535C] font-semibold leading-snug">
        {classLabel(prediction.predicted_class)}{" "}
        <span className="metric-value text-[20px] text-[#1A535C]">
          p = {primaryP.toFixed(2)}
        </span>
      </p>

      <div className="mt-4 flex h-2.5 w-full overflow-hidden">
        <div
          style={{
            width: `${(pSyn / total) * 100}%`,
            background: "#1A535C",
          }}
          title={`Synergy ${pSyn.toFixed(2)}`}
        />
        <div
          style={{
            width: `${(pAdd / total) * 100}%`,
            background: "#C4A882",
          }}
          title={`Additive ${pAdd.toFixed(2)}`}
        />
        <div
          style={{
            width: `${(pAnt / total) * 100}%`,
            background: "#D4A0A0",
          }}
          title={`Antagonism ${pAnt.toFixed(2)}`}
        />
      </div>

      <div className="mt-2.5 flex flex-wrap gap-x-6 gap-y-1 text-[13px] text-[#4A524C]">
        <span>
          Synergy{" "}
          <span className="id-text text-[#1A535C]">{pSyn.toFixed(2)}</span>
        </span>
        <span>
          Additive{" "}
          <span className="id-text text-[#8B7355]">{pAdd.toFixed(2)}</span>
        </span>
        <span>
          Antagonism{" "}
          <span className="id-text text-[#A84B4B]">{pAnt.toFixed(2)}</span>
        </span>
      </div>

      <div className="mt-5 grid grid-cols-2 sm:grid-cols-4 border border-[#CFC9BC] divide-x divide-y sm:divide-y-0 divide-[#CFC9BC]">
        <div className="px-3 py-2.5">
          <span className="bench-label block">V(pair)</span>
          <span className="metric-value">{Number(v).toFixed(2)}</span>
        </div>
        <div className="px-3 py-2.5">
          <span className="bench-label block">Toxicity</span>
          <span className="metric-value">
            {tox != null ? Number(tox).toFixed(2) : "—"}
          </span>
        </div>
        <div className="px-3 py-2.5">
          <span className="bench-label block">Rank</span>
          <span className="metric-value">
            {prediction.rank != null ? `#${prediction.rank}` : "—"}
          </span>
        </div>
        <div className="px-3 py-2.5">
          <span className="bench-label block">Method</span>
          <span className="metric-value lowercase">{method}</span>
        </div>
      </div>
    </div>
  );
};
