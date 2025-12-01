import { useTheme } from '@/context/ThemeContext';
import { format } from 'date-fns';
import { useMemo } from 'react';
import { Button } from '@/components/common/Button';
import { useAppContext } from '@/context/AppContext';

export const Header = () => {
  const { isDarkMode, toggleTheme } = useTheme();
  const { refreshRate, timezone, setTimezone } = useAppContext();
  const now = useMemo(() => format(new Date(), 'PPpp'), []);
  
  const toggleTimezone = () => {
    setTimezone(timezone === 'UTC' ? 'local' : 'UTC');
  };
  
  return (
    <header className="flex flex-col gap-2 border-b border-slate-200 bg-white/80 p-6 backdrop-blur dark:border-slate-700 dark:bg-slate-900/70 lg:flex-row lg:items-center lg:justify-between">
      <div>
        <p className="text-sm uppercase tracking-wide text-slate-500">Meshtastic statistics bot</p>
        <h1 className="text-3xl font-bold text-slate-900 dark:text-white">Dashboard</h1>
        <p className="text-sm text-slate-500">Last refreshed {now} · Auto refresh {refreshRate / 1000}s · Timezone: {timezone}</p>
      </div>
      <div className="flex items-center gap-3">
        <Button variant="secondary" onClick={toggleTimezone}>
          🌍 {timezone === 'UTC' ? 'Show Local Time' : 'Show UTC'}
        </Button>
        <Button variant="secondary" onClick={toggleTheme}>
          {isDarkMode ? '☀️ Light Mode' : '🌙 Dark Mode'}
        </Button>
      </div>
    </header>
  );
};
