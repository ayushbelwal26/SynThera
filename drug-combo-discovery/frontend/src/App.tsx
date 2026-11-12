import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AppProvider } from "./services/AppContext";
import { AppLayout } from "./layouts/AppLayout";
import { LandingPage } from "./pages/LandingPage";
import { BenchPage } from "./pages/DiscoverPage";
import { IndicationPage } from "./pages/IndicationPage";
import { LiteraturePage } from "./pages/EvidencePage";
import { NeighborhoodPage } from "./pages/KnowledgeGraphPage";
import { PredictionReportPage } from "./pages/PredictionReportPage";

export function App() {
  return (
    <AppProvider>
      <BrowserRouter>
        <Routes>
          {/* Public Landing Experience */}
          <Route path="/" element={<LandingPage />} />

          {/* Research Workspace Shell */}
          <Route element={<AppLayout />}>
            <Route path="bench" element={<BenchPage />} />
            <Route path="indication" element={<IndicationPage />} />
            <Route path="literature" element={<LiteraturePage />} />
            <Route path="neighborhood" element={<NeighborhoodPage />} />
            <Route path="results/:id" element={<PredictionReportPage />} />

            {/* Aliases for convenience and backward compatibility */}
            <Route path="discover" element={<Navigate to="/bench" replace />} />
            <Route path="analysis" element={<Navigate to="/results/active" replace />} />
            <Route path="evidence" element={<Navigate to="/literature" replace />} />
            <Route path="graph" element={<Navigate to="/neighborhood" replace />} />
          </Route>

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AppProvider>
  );
}

export default App;
