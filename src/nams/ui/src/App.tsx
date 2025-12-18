import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Layout } from './components/layout/Layout';
import { ContentExplorer } from './pages/ContentExplorer';
import { Dashboard } from './pages/Dashboard';
import { Files } from './pages/Files';
import { Groups } from './pages/Groups';
import { Patterns } from './pages/Patterns';
import { Settings } from './pages/Settings';
import { Entries } from './pages/Entries';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      refetchOnWindowFocus: false,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<ContentExplorer />} />
            <Route path="/explorer" element={<ContentExplorer />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/files" element={<Files />} />
            <Route path="/groups" element={<Groups />} />
            <Route path="/entries" element={<Entries />} />
            <Route path="/patterns" element={<Patterns />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
