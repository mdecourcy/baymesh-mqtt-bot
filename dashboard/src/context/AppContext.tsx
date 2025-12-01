import { createContext, useContext, useMemo } from 'react';
import type { ReactNode } from 'react';
import { useLocalStorage } from '@/hooks/useLocalStorage';

interface AppContextValue {
  apiBaseUrl: string;
  refreshRate: number;
  timezone: 'UTC' | 'local';
  setTimezone: (tz: 'UTC' | 'local') => void;
}

const AppContext = createContext<AppContextValue | undefined>(undefined);

const getEnv = (key: string, fallback: string) => import.meta.env[key] ?? fallback;

export const AppProvider = ({ children }: { children: ReactNode }) => {
  const apiBaseUrl = (getEnv('VITE_API_BASE_URL', '') as string) || window.location.origin;
  const refreshRate = Number(getEnv('VITE_REFRESH_RATE', '30000')) || 30000;
  const [timezone, setTimezone] = useLocalStorage<'UTC' | 'local'>('timezone', 'UTC');

  const value = useMemo(() => ({ 
    apiBaseUrl, 
    refreshRate,
    timezone,
    setTimezone 
  }), [apiBaseUrl, refreshRate, timezone, setTimezone]);

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
};

export const useAppContext = () => {
  const ctx = useContext(AppContext);
  if (!ctx) {
    throw new Error('useAppContext must be used within AppProvider');
  }
  return ctx;
};
