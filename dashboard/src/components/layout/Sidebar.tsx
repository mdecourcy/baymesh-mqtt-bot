import { NAV_LINKS } from '@/utils/constants';
import { NavLink } from 'react-router-dom';
import { useState } from 'react';

export const Sidebar = () => {
  const [open, setOpen] = useState(false);
  return (
    <aside className="border-r border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900 lg:w-64">
      <div className="flex items-center justify-between p-6 lg:hidden">
        <h2 className="text-xl font-semibold">Meshtastic</h2>
        <button onClick={() => setOpen((prev) => !prev)} aria-label="Toggle menu">
          ☰
        </button>
      </div>
      <nav className={`${open ? 'block' : 'hidden'} lg:block`}>
        <ul className="space-y-1 px-4 pb-6">
          {NAV_LINKS.map((link) => (
            <li key={link.path}>
              <NavLink
                to={link.path}
                className={({ isActive }) =>
                  `block rounded-xl px-4 py-2 font-medium transition-colors ${
                    isActive
                      ? 'bg-primary/10 text-primary'
                      : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800'
                  }`
                }
              >
                {link.label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
    </aside>
  );
};
