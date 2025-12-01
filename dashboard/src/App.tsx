import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from '@/components/layout/Layout';
import Dashboard from '@/pages/Dashboard';
import Stats from '@/pages/Stats';
import Subscriptions from '@/pages/Subscriptions';
import BotStats from '@/pages/BotStats';
import Admin from '@/pages/Admin';
import NotFound from '@/pages/NotFound';

const App = () => (
  <BrowserRouter>
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/stats" element={<Stats />} />
        <Route path="/subscriptions" element={<Subscriptions />} />
        <Route path="/bot" element={<BotStats />} />
        <Route path="/admin" element={<Admin />} />
      </Route>
      <Route path="*" element={<NotFound />} />
    </Routes>
  </BrowserRouter>
);

export default App;
