import { lazy, Suspense } from 'react';
import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import ErrorBoundary from './components/ErrorBoundary';

const Dashboard = lazy(() => import('./pages/Dashboard'));
const Builds = lazy(() => import('./pages/Builds'));
const Analytics = lazy(() => import('./pages/Analytics'));
const Characters = lazy(() => import('./pages/Characters'));
const Recommendations = lazy(() => import('./pages/Recommendations'));

function App() {
  return (
    <ErrorBoundary>
      <Suspense fallback={<div className="flex items-center justify-center h-screen text-gray-400">Loading...</div>}>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="builds" element={<Builds />} />
            <Route path="analytics" element={<Analytics />} />
            <Route path="characters" element={<Characters />} />
            <Route path="recommendations" element={<Recommendations />} />
          </Route>
        </Routes>
      </Suspense>
    </ErrorBoundary>
  );
}

export default App;
