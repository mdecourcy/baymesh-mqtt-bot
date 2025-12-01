import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';

const Layout = () => (
  <div className="flex min-h-screen bg-slate-50 dark:bg-slate-950">
    <Sidebar />
    <div className="flex flex-1 flex-col">
      <Header />
      <main className="flex-1 space-y-6 bg-slate-50 p-6 dark:bg-slate-950">
        <Outlet />
      </main>
    </div>
  </div>
);

export default Layout;
