import React, { createContext, useContext, useState, useEffect } from 'react';
import type { Drug, PredictionResult, CellLineRelevanceStatus } from '../types/api';
import { fetchDrugs, fetchCellLines } from './api';

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

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [drugs, setDrugs] = useState<Drug[]>([]);
  const [cellLineStatus, setCellLineStatus] = useState<CellLineRelevanceStatus>({
    cellLines: [],
    isFiltered: false,
  });
  const [currentPrediction, setCurrentPrediction] = useState<PredictionResult | null>(null);
  const [recentPredictions, setRecentPredictions] = useState<PredictionResult[]>([]);
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
        console.error('Failed to initialize drug or cell line catalog:', err);
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
      console.error('Failed to query cell lines:', err);
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
          )
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
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
}
