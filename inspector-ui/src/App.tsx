import { Routes, Route, Navigate } from 'react-router-dom';
import { Suspense, lazy } from 'react';
import { Layout } from './components/layout/Layout';
import { Toaster } from './components/ui/toaster';
import {
  ErrorBoundary,
  useKeyboardShortcuts,
  KeyboardShortcutsHelp,
  PendingKeyIndicator,
  Spinner
} from './components/common';
import { useProjectChangeHandler } from './hooks/use-memories';

// Lazy load pages
const BrowserPage = lazy(() => import('./pages/BrowserPage'));
const SearchPage = lazy(() => import('./pages/SearchPage'));
const GraphPage = lazy(() => import('./pages/GraphPage'));
const MaintenancePage = lazy(() => import('./pages/MaintenancePage'));
const SettingsPage = lazy(() => import('./pages/SettingsPage'));

// Loading fallback
function PageLoader() {
  return (
    <div className="flex items-center justify-center h-full">
      <Spinner size="lg" />
    </div>
  );
}

// 404 page
function NotFoundPage() {
  return (
    <div className="flex flex-col items-center justify-center h-full">
      <h2 className="text-2xl font-semibold mb-2">Page Not Found</h2>
      <p className="text-muted-foreground mb-4">
        The page you are looking for does not exist.
      </p>
      <a href="/browser" className="text-primary hover:underline">
        Go to Browser
      </a>
    </div>
  );
}

function AppContent() {
  const { pendingKey } = useKeyboardShortcuts();
  // REQ-007-FN-030 to FN-033: Handle project switching and cache invalidation
  useProjectChangeHandler();

  return (
    <>
      <Layout>
        <ErrorBoundary>
          <Suspense fallback={<PageLoader />}>
            <Routes>
              <Route path="/" element={<Navigate to="/browser" replace />} />
              <Route path="/browser" element={<BrowserPage />} />
              <Route path="/browser/:type" element={<BrowserPage />} />
              <Route path="/search" element={<SearchPage />} />
              <Route path="/graph" element={<GraphPage />} />
              <Route path="/maintenance" element={<MaintenancePage />} />
              <Route path="/settings" element={<SettingsPage />} />
              <Route path="*" element={<NotFoundPage />} />
            </Routes>
          </Suspense>
        </ErrorBoundary>
      </Layout>
      <Toaster />
      <KeyboardShortcutsHelp />
      <PendingKeyIndicator pendingKey={pendingKey} />
    </>
  );
}

function App() {
  return (
    <ErrorBoundary>
      <AppContent />
    </ErrorBoundary>
  );
}

export default App;
