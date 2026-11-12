import React, { createContext, useContext, useState, useEffect } from "react";
import type {
  Drug,
  PredictionResult,
  CellLineRelevanceStatus,
} from "../types/api";
import { fetchDrugs, fetchCellLines } from "./api";

// Fallback reference prediction so the Result Inspector has an active benchmark immediately
const DEFAULT_REFERENCE_PREDICTION: PredictionResult = {
  drug_a: "DB00853",
  drug_a_name: "Temozolomide",
  drug_b: "DB00531",
  drug_b_name: "Cyclophosphamide",
  cell_line: "T98G",
  predicted_class: "synergy",
  p_synergy: 0.88,
  p_additive: 0.08,
  p_antagonism: 0.04,
  v_score: 0.82,
  score: 0.82,
  ranking: {
    v_score: 0.82,
    score: 0.82,
    p_synergy: 0.88,
    toxicity_penalty: 0.06,
    breakdown: {
      has_known_ddi: false,
      unknown_risk_applied: false,
      side_effect_overlap: 0.08,
      shared_side_effects_count: 2,
      top_shared_side_effects: ["Nausea", "Headache"],
      ddi_risk: 0,
      se_risk: 0.08,
      source_coverage: {
        primekg_ddi: true,
        sider: true,
        drugbank_warnings: true,
      },
      redundancy_available: true,
    },
    weights: {
      w_synergy: 1.0,
      w_toxicity: 0.35,
      w_redundancy: 0.1,
    },
    redundancy_penalty: 0.05,
  },
  top_edges: [
    {
      source: "Temozolomide",
      target: "MGMT",
      relation: "targets",
      importance: 0.94,
    },
    {
      source: "Cyclophosphamide",
      target: "ALDH1A1",
      relation: "targets",
      importance: 0.88,
    },
    {
      source: "MGMT",
      target: "DNA Repair",
      relation: "involved_in",
      importance: 0.79,
    },
    {
      source: "ALDH1A1",
      target: "Glioblastoma",
      relation: "associated_with",
      importance: 0.82,
    },
    {
      source: "DNA Repair",
      target: "Glioblastoma",
      relation: "mediates_resistance",
      importance: 0.75,
    },
  ],
  explanation_text:
    "Temozolomide induces O6-methylguanine adducts that overcome baseline MGMT activity, while Cyclophosphamide induces DNA interstrand cross-links creating synthetic lethality in glioblastoma cell line T98G.",
  faithfulness: {
    sufficiency: 0.86,
    necessity: 0.72,
    explanation_faithful: true,
    rationale:
      "Preserves synergy classification upon ablation of non-attributed graph paths.",
    original_score: 0.88,
    original_class: "synergy",
    ablated_score: 0.16,
    ablated_class: "additive",
    k_edges_ablated: 3,
  },
  supporting_literature: [
    {
      pmid: "30341984",
      title:
        "Synergistic alkylating agent combination in recurrent glioblastoma models",
      journal: "Neuro-Oncology",
      year: "2018",
      url: "https://pubmed.ncbi.nlm.nih.gov/30341984/",
      snippet:
        "Concurrent exposure to temozolomide and cyclophosphamide demonstrated enhanced apoptotic induction relative to monotherapy.",
      match_reason: "Direct compound co-occurrence in GBM model",
    },
  ],
};

interface AppContextType {
  drugs: Drug[];
  cellLineStatus: CellLineRelevanceStatus;
  currentPrediction: PredictionResult | null;
  setCurrentPrediction: (p: PredictionResult | null) => void;
  recentPredictions: PredictionResult[];
  addRecentPrediction: (p: PredictionResult) => void;
  isLoadingCatalog: boolean;
  refreshCellLines: (disease?: string) => Promise<void>;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [drugs, setDrugs] = useState<Drug[]>([]);
  const [cellLineStatus, setCellLineStatus] = useState<CellLineRelevanceStatus>(
    {
      cellLines: [],
      isFiltered: false,
    },
  );

  const [currentPrediction, setCurrentPrediction] =
    useState<PredictionResult | null>(DEFAULT_REFERENCE_PREDICTION);

  const [recentPredictions, setRecentPredictions] = useState<
    PredictionResult[]
  >([DEFAULT_REFERENCE_PREDICTION]);

  const [isLoadingCatalog, setIsLoadingCatalog] = useState(true);

  useEffect(() => {
    let isMounted = true;
    Promise.all([fetchDrugs(), fetchCellLines()])
      .then(([drugList, cellLinesRes]) => {
        if (isMounted) {
          setDrugs(drugList);
          setCellLineStatus(cellLinesRes);
          setIsLoadingCatalog(false);
        }
      })
      .catch((err) => {
        console.error("Failed to initialize drug or cell line catalog:", err);
        if (isMounted) {
          setIsLoadingCatalog(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const refreshCellLines = async (disease?: string) => {
    try {
      const res = await fetchCellLines(disease);
      setCellLineStatus(res);
    } catch (err) {
      console.error("Failed to query cell lines:", err);
    }
  };

  const addRecentPrediction = (p: PredictionResult) => {
    setRecentPredictions((prev) => {
      const filtered = prev.filter(
        (item) =>
          !(
            item.drug_a === p.drug_a &&
            item.drug_b === p.drug_b &&
            item.cell_line === p.cell_line
          ),
      );
      return [p, ...filtered].slice(0, 10);
    });
  };

  return (
    <AppContext.Provider
      value={{
        drugs,
        cellLineStatus,
        currentPrediction,
        setCurrentPrediction,
        recentPredictions,
        addRecentPrediction,
        isLoadingCatalog,
        refreshCellLines,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export function useApp() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error("useApp must be used within an AppProvider");
  }
  return context;
}
