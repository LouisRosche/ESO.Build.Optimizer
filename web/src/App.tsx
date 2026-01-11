import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Builds from './pages/Builds';
import Analytics from './pages/Analytics';
import Characters from './pages/Characters';
import Recommendations from './pages/Recommendations';

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="builds" element={<Builds />} />
        <Route path="analytics" element={<Analytics />} />
        <Route path="characters" element={<Characters />} />
        <Route path="recommendations" element={<Recommendations />} />
      </Route>
    </Routes>
  );
}

export default App;
