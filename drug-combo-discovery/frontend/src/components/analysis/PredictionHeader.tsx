import type { PredictionResult } from "../../types/api";

interface PredictionHeaderProps {
  prediction: PredictionResult;
  disease?: string;
}

export const PredictionHeader: React.FC<PredictionHeaderProps> = ({
  prediction,
  disease,
}) => {
  const handleExportJson = () => {
    const dataStr =
      "data:text/json;charset=utf-8," +
      encodeURIComponent(JSON.stringify(prediction, null, 2));
    const a = document.createElement("a");
    a.setAttribute("href", dataStr);
    a.setAttribute(
      "download",
      `synthera_${prediction.drug_a_name}_${prediction.drug_b_name}_${prediction.cell_line}.json`,
    );
    document.body.appendChild(a);
    a.click();
    a.remove();
  };

  return (
    <div className="border-b border-[#CFC9BC] pb-3 mb-0">
      <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-3">
        <div>
          <p className="page-kicker">Pair record</p>
          <h2 className="page-title mt-0.5">
            {prediction.drug_a_name} + {prediction.drug_b_name}
          </h2>
          <p className="id-text mt-1">
            {prediction.drug_a}
            {prediction.top_edges?.[0]?.target
              ? ` · ${String(prediction.top_edges[0].target)}`
              : ""}{" "}
            / {prediction.drug_b}
            {prediction.top_edges?.[1]?.target
              ? ` · ${String(prediction.top_edges[1].target)}`
              : ""}
          </p>
        </div>

        <div className="flex flex-col sm:flex-row gap-4 shrink-0 lg:text-right">
          <div>
            <span className="bench-label block">Cell line</span>
            <span className="text-[13px] text-[#1A1F1C]">{prediction.cell_line}</span>
          </div>
          {disease && (
            <div>
              <span className="bench-label block">Disease context</span>
              <span className="text-[13px] text-[#1A1F1C]">{disease}</span>
            </div>
          )}
          <div className="flex gap-2 items-start">
            <button
              type="button"
              onClick={handleExportJson}
              className="bench-btn-ghost border border-[#CFC9BC] px-2.5 py-1 text-[12px]"
            >
              Export JSON
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
