import { BrowserRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { DebugPanel } from "@/components/DebugPanel";
import { Layout } from "@/components/Layout";
import { BomEditorPage } from "@/pages/BomEditorPage";
import { ImportPage } from "@/pages/ImportPage";
import { NotebooksPage } from "@/pages/NotebooksPage";
import { DebugProvider } from "@/lib/debug";
import { ThemeProvider } from "@/lib/theme";

const queryClient = new QueryClient();

export default function App() {
  return (
    <ThemeProvider>
      <DebugProvider>
        <QueryClientProvider client={queryClient}>
          <BrowserRouter>
            <Layout>
              <Routes>
                <Route path="/" element={<ImportPage />} />
                <Route path="/bom/:projectId" element={<BomEditorPage />} />
                <Route path="/notebooks" element={<NotebooksPage />} />
              </Routes>
            </Layout>
            <DebugPanel />
          </BrowserRouter>
        </QueryClientProvider>
      </DebugProvider>
    </ThemeProvider>
  );
}
