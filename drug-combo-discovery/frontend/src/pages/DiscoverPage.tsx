import React, { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useApp } from "../services/AppContext";
import { predictCombination, searchCombinations } from "../services/api";
import type { Drug, PredictionResult, SearchResponse } from "../types/api";
import { DrugSelectInput } from "../components/discover/DrugSelectInput";
import { CellLineDropdown } from "../components/discover/CellLineDropdown";
import { BenchmarkPresets } from "../components/discover/BenchmarkPresets";
import type { BenchmarkPreset } from "../components/discover/BenchmarkPresets";
import { DiscoveryMode } from "../components/discover/DiscoveryMode";
import { WhyNotSection } from "../components/discover/WhyNotSection";
import { LoadingStages } from "../components/common/LoadingStages";
import { AlertNotice } from "../components/common/AlertNotice";

function classColor(cls: string): string {
  if (cls === "synergy") return "#1A535C";
  if (cls === "antagonism") return "#A84B4B";
  return "#8B7355";
}

function DistBar({
  pSyn,
  pAdd,
  pAnt,
}: {
  pSyn: number;
  pAdd: number;
  pAnt: number;
}) {
  const total = pSyn + pAdd + pAnt || 1;
  return (
    <div className="w-full max-w-[120px]">
      <span className="bench-label block mb-1">Distribution</span>
      <div className="flex h-2 w-full overflow-hidden">
        <div
          style={{ width: `${(pSyn / total) * 100}%`, background: "#1A535C" }}
        />
        <div
          style={{ width: `${(pAdd / total) * 100}%`, background: "#C4A882" }}
        />
        <div
          style={{ width: `${(pAnt / total) * 100}%`, background: "#A84B4B" }}
        />
      </div>
    </div>
  );
}

export const DiscoverPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const {
    drugs,
    cellLineStatus,
    setCurrentPrediction,
    addRecentPrediction,
    recentPredictions,
    currentPrediction,
  } = useApp();

  const activeTab =
    searchParams.get("mode") === "indication" ? "search" : "pair";

  const [drugA, setDrugA] = useState<Drug | null>(null);
  const [drugB, setDrugB] = useState<Drug | null>(null);
  const [cellLine, setCellLine] = useState<string>("T98G");
  const [diseaseContext, setDiseaseContext] = useState<string>("");

  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const [searchDisease, setSearchDisease] = useState<string>(
    "non-small cell lung carcinoma",
  );
  const [searchResults, setSearchResults] = useState<SearchResponse | null>(
    null,
  );
  const [inspectingPairIdx, setInspectingPairIdx] = useState<number | null>(
    null,
  );

  useEffect(() => {
    if (cellLineStatus.cellLines.length > 0 && !cellLineStatus.cellLines.includes(cellLine)) {
      setCellLine(cellLineStatus.cellLines[0]);
    }
  }, [cellLineStatus.cellLines, cellLine]);

  useEffect(() => {
    setErrorMsg(null);
  }, [activeTab]);

  const handleSelectPreset = (preset: BenchmarkPreset) => {
    setDrugA(preset.drugA);
    setDrugB(preset.drugB);
    setCellLine(preset.cellLine);
    setDiseaseContext(preset.indication);
    setErrorMsg(null);
  };

  const handleAnalyzePair = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!drugA || !drugB || !cellLine) {
      setErrorMsg("Select Drug A, Drug B, and a cell line.");
      return;
    }
    if (drugA.id === drugB.id) {
      setErrorMsg("Select two distinct compounds.");
      return;
    }

    setIsLoading(true);
    setErrorMsg(null);

    try {
      const result = await predictCombination({
        drug_a: drugA.id,
        drug_b: drugB.id,
        cell_line: cellLine,
        disease: diseaseContext.trim() || undefined,
      });
      setCurrentPrediction(result);
      addRecentPrediction(result);
      navigate("/analysis");
    } catch (err: any) {
      setErrorMsg(err.message || "Prediction failed.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleRunSearch = async (
    disease: string,
    targetCellLine: string,
    maxCandidates: number,
    topK: number,
    searchMethod: "beam" | "greedy" | "mcts" = "beam",
    nSimulations: number = 50,
    mctsC: number = 1.414,
  ) => {
    setSearchDisease(disease);
    setIsLoading(true);
    setErrorMsg(null);
    setSearchResults(null);

    try {
      const res = await searchCombinations({
        disease,
        cell_line: targetCellLine,
        max_candidates: maxCandidates,
        top_k: topK,
        search_method: searchMethod,
        n_simulations: nSimulations,
        mcts_c: mctsC,
      });
      setSearchResults(res);
    } catch (err: any) {
      setErrorMsg(err.message || "Indication search failed.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectDiscoveredPair = async (
    pair: PredictionResult,
    idx: number,
  ) => {
    setInspectingPairIdx(idx);
    try {
      const full = await predictCombination({
        drug_a: pair.drug_a,
        drug_b: pair.drug_b,
        cell_line: pair.cell_line,
      });
      setCurrentPrediction(full);
      addRecentPrediction(full);
      navigate("/analysis");
    } catch {
      setCurrentPrediction(pair);
      addRecentPrediction(pair);
      navigate("/analysis");
    } finally {
      setInspectingPairIdx(null);
    }
  };

  const handleInspectWhyNotPair = async (
    drugAId: string,
    drugBId: string,
    cl: string,
  ) => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const full = await predictCombination({
        drug_a: drugAId,
        drug_b: drugBId,
        cell_line: cl,
      });
      setCurrentPrediction(full);
      addRecentPrediction(full);
      navigate("/analysis");
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to inspect combination.");
    } finally {
      setIsLoading(false);
    }
  };

  const registerEntries = recentPredictions.length
    ? recentPredictions
    : currentPrediction
      ? [currentPrediction]
      : [];

  return (
    <div className="space-y-0">
      {errorMsg && (
        <div className="mb-5">
          <AlertNotice type="error" title="Notice">
            {errorMsg}
          </AlertNotice>
        </div>
      )}

      {isLoading && (
        <div className="py-8">
          <LoadingStages
            title={
              activeTab === "pair"
                ? "Scoring pair"
                : "Searching candidate space"
            }
            subtitle={
              activeTab === "pair"
                ? `${drugA?.name || "Drug A"} + ${drugB?.name || "Drug B"} · ${cellLine}`
                : `Indication neighbors · ${searchDisease}`
            }
          />
        </div>
      )}

      {/* ── Bench: Score a pair ── */}
      {!isLoading && activeTab === "pair" && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 lg:gap-8">
          <div className="lg:col-span-5 space-y-4">
            <div>
              <p className="page-kicker">Pair analysis</p>
              <h2 className="page-title">Score a pair</h2>
              <p className="page-lede">
                Enter two DrugBank compounds, a cell line, and optional disease
                context. Returns class probabilities, V(pair), and attributed
                edges.
              </p>
            </div>

            <div className="bench-panel space-y-4">
              <form onSubmit={handleAnalyzePair} className="space-y-4">
                <DrugSelectInput
                  label="Drug A — DrugBank"
                  selectedDrug={drugA}
                  onSelect={setDrugA}
                  drugs={drugs}
                  placeholder="Osimertinib"
                />
                <DrugSelectInput
                  label="Drug B — DrugBank"
                  selectedDrug={drugB}
                  onSelect={setDrugB}
                  drugs={drugs}
                  placeholder="Crizotinib"
                />
                <CellLineDropdown
                  status={cellLineStatus}
                  selectedCellLine={cellLine}
                  onSelect={setCellLine}
                />
                <div>
                  <label className="bench-label block mb-1">
                    Disease context (optional)
                  </label>
                  <input
                    type="text"
                    value={diseaseContext}
                    onChange={(e) => setDiseaseContext(e.target.value)}
                    placeholder="non-small cell lung carcinoma"
                    className="bench-input"
                  />
                </div>
                <button
                  type="submit"
                  disabled={!drugA || !drugB}
                  className="bench-btn mt-1"
                >
                  Run prediction
                </button>
              </form>
            </div>
          </div>

          <div className="lg:col-span-7">
            <div className="flex items-baseline justify-between border-b border-[#CFC9BC] pb-2 mb-1">
              <h3 className="section-title">
                {registerEntries.length > 0
                  ? "Record register"
                  : "Reference pairs"}
              </h3>
              <span className="meta-text">
                {registerEntries.length > 0
                  ? `${registerEntries.length} ${registerEntries.length === 1 ? "entry" : "entries"}`
                  : "Load to begin"}
              </span>
            </div>

            {registerEntries.length > 0 ? (
              <div className="divide-y divide-[#CFC9BC] border-b border-[#CFC9BC]">
                {registerEntries.map((p, idx) => {
                  const cls = p.predicted_class || "additive";
                  const color = classColor(cls);
                  const pSyn =
                    p.p_synergy ?? p.ranking?.p_synergy ?? p.score ?? 0;
                  const v =
                    p.v_score ?? p.ranking?.v_score ?? p.score ?? 0;
                  return (
                    <button
                      key={`${p.drug_a}_${p.drug_b}_${p.cell_line}_${idx}`}
                      type="button"
                      onClick={() => {
                        setCurrentPrediction(p);
                        navigate("/analysis");
                      }}
                      className="w-full text-left py-3 flex items-stretch gap-3 hover:bg-[#E8EDE0]/35"
                    >
                      <div
                        className="w-0.5 shrink-0 self-stretch"
                        style={{ background: color }}
                      />
                      <div className="flex-1 min-w-0">
                        <span className="font-serif text-[15px] text-[#1A1F1C]">
                          {p.drug_a_name} + {p.drug_b_name}
                        </span>
                        <span className="block id-text mt-0.5">
                          {p.drug_a} · {p.drug_b} · {p.cell_line}
                        </span>
                        <span
                          className="inline-block text-[12px] mt-1 capitalize"
                          style={{ color }}
                        >
                          {cls}
                        </span>
                      </div>
                      <div className="shrink-0 text-right space-y-1">
                        <div>
                          <span className="bench-label block">P(syn)</span>
                          <span className="metric-value text-[14px]">
                            {Number(pSyn).toFixed(2)}
                          </span>
                        </div>
                        <div>
                          <span className="bench-label block">V</span>
                          <span className="metric-value text-[14px]">
                            {Number(v).toFixed(2)}
                          </span>
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            ) : (
              <div>
                <p className="meta-text py-3">
                  No scored pairs yet. Load a reference case, or run a
                  prediction from the form.
                </p>
                <BenchmarkPresets onSelect={handleSelectPreset} />
              </div>
            )}

            {registerEntries.length > 0 && (
              <div className="mt-6">
                <BenchmarkPresets onSelect={handleSelectPreset} />
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Indication search ── */}
      {!isLoading && activeTab === "search" && (
        <div className="space-y-5">
          <div>
            <p className="page-kicker">Indication search</p>
            <h2 className="page-title">Ranked candidates for an indication</h2>
            <p className="page-lede">
              Traverse disease neighborhood in PrimeKG, score candidate pairs,
              and rank by V(pair). Open a row for the Result inspector.
            </p>
          </div>

          <div className="bench-panel">
            <DiscoveryMode
              cellLineStatus={cellLineStatus}
              selectedCellLine={cellLine}
              onSelectCellLine={setCellLine}
              onRunSearch={handleRunSearch}
              isLoading={isLoading}
              initialDisease={searchDisease}
            />
          </div>

          {searchResults && (
            <div>
              <div className="flex items-baseline justify-between border-b border-[#CFC9BC] pb-2 mb-0">
                <span className="bench-label">
                  {searchResults.results.length} candidate pairs ·{" "}
                  {searchResults.search_method || "beam"}
                  {searchResults.truncated ? " · truncated" : ""}
                </span>
                <span className="font-mono text-[12px] text-[#6B746C]">
                  {searchResults.disease} · {searchResults.cell_line}
                </span>
              </div>

              <div className="divide-y divide-[#CFC9BC]">
                {searchResults.results.map((pair, idx) => {
                  const rank = pair.rank ?? idx + 1;
                  const cls = pair.predicted_class || "additive";
                  const color = classColor(cls);
                  const pSyn =
                    pair.p_synergy ?? pair.ranking?.p_synergy ?? pair.score ?? 0;
                  const pAdd = (pair as any).p_additive ?? 0;
                  const pAnt = (pair as any).p_antagonism ?? 0;
                  const v =
                    pair.v_score ?? pair.ranking?.v_score ?? pair.score ?? 0;
                  const tox = pair.ranking?.toxicity_penalty;

                  return (
                    <div
                      key={`${pair.drug_a}_${pair.drug_b}_${idx}`}
                      className="py-2.5 flex flex-col md:flex-row md:items-center gap-3"
                    >
                      <span className="id-text text-[15px] text-[#A8A294] w-8 shrink-0 leading-none">
                        {String(rank).padStart(2, "0")}
                      </span>

                      <div className="flex-1 min-w-0">
                        <button
                          type="button"
                          disabled={inspectingPairIdx !== null}
                          onClick={() => handleSelectDiscoveredPair(pair, idx)}
                          className="font-serif text-[15px] text-[#1A1F1C] underline underline-offset-2 decoration-[#CFC9BC] hover:decoration-[#1A535C] text-left"
                        >
                          {pair.drug_a_name} + {pair.drug_b_name}
                        </button>
                        <span className="block font-mono text-[12px] text-[#6B746C] mt-0.5">
                          {pair.cell_line} ·{" "}
                          {pair.search_method ||
                            searchResults.search_method ||
                            "beam"}
                        </span>
                      </div>

                      <div className="flex items-center gap-3 shrink-0">
                        {tox !== undefined && tox !== null && (
                          <span className="font-mono text-[13px] text-[#6B746C]">
                            Tox {Number(tox).toFixed(2)}
                          </span>
                        )}
                        <button
                          type="button"
                          className="bench-btn-ghost border border-[#CFC9BC] px-2 py-1 font-mono text-[12px] text-[#4A524C] hover:bg-[#1A1F1C] hover:text-[#F5F5ED] hover:border-[#1A1F1C]"
                          onClick={() =>
                            document
                              .getElementById("why-not-section")
                              ?.scrollIntoView({ behavior: "smooth" })
                          }
                        >
                          Why not?
                        </button>
                      </div>

                      <DistBar
                        pSyn={Number(pSyn)}
                        pAdd={Number(pAdd) || Math.max(0, 1 - Number(pSyn) - 0.05)}
                        pAnt={Number(pAnt) || 0.05}
                      />

                      <div className="shrink-0 text-right min-w-[72px]">
                        <span className="bench-label block">Class</span>
                        <span
                          className="font-mono text-[14px] capitalize"
                          style={{ color }}
                        >
                          {cls}
                        </span>
                      </div>

                      <div className="shrink-0 text-right min-w-[56px]">
                        <span className="bench-label block">V</span>
                        <span className="font-mono text-[14px] text-[#1A1F1C]">
                          {Number(v).toFixed(2)}
                        </span>
                      </div>

                      {inspectingPairIdx === idx && (
                        <span className="font-mono text-[12px] text-[#1A535C]">
                          Loading…
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

      <div className="border-t border-[#CFC9BC] pt-6">
        <WhyNotSection
          disease={
            searchResults?.disease ||
            searchDisease ||
            diseaseContext ||
            "glioblastoma"
          }
          cellLine={searchResults?.cell_line || cellLine}
          searchMethod={(searchResults?.search_method as any) || "beam"}
          onInspectPair={handleInspectWhyNotPair}
        />
      </div>
        </div>
      )}
    </div>
  );
};
