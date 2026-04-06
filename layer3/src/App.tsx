import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { CompanyStats } from "./pages/CompanyStats";
import { ExploreGraph } from "./pages/ExploreGraph";
import { Home } from "./pages/Home";
import { OptimizeProfit } from "./pages/OptimizeProfit";
import { Upload } from "./pages/Upload";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Home />} />
          <Route path="/explore" element={<ExploreGraph />} />
          <Route path="/upload" element={<Upload />} />
          <Route path="/stats" element={<CompanyStats />} />
          <Route path="/optimize" element={<OptimizeProfit />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
