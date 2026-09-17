import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppProvider } from './services/AppContext';
import { AppLayout } from './layouts/AppLayout';
import { DiscoverPage } from './pages/DiscoverPage';
import { AnalysisPage } from './pages/AnalysisPage';
import { EvidencePage } from './pages/EvidencePage';
import { KnowledgeGraphPage } from './pages/KnowledgeGraphPage';

export function App() {
  return (
    <AppProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<AppLayout />}>
            <Route index element={<Navigate to="/discover" replace />} />
            <Route path="discover" element={<DiscoverPage />} />
            <Route path="analysis" element={<AnalysisPage />} />
            <Route path="evidence" element={<EvidencePage />} />
            <Route path="graph" element={<KnowledgeGraphPage />} />
            <Route path="*" element={<Navigate to="/discover" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AppProvider>
  );
}

export default App;
