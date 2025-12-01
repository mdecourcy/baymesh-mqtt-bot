import { useCallback, useEffect, useState } from 'react';
import { statsService } from '@/services/statsService';
import { useAppContext } from '@/context/AppContext';
import type { Message } from '@/types/message';
import type { DailyStatsResponse, HourlyStat } from '@/types/api';

export const useStats = () => {
  const { refreshRate } = useAppContext();
  const [lastMessage, setLastMessage] = useState<Message | null>(null);
  const [todayStats, setTodayStats] = useState<DailyStatsResponse | null>(null);
  const [hourlyStats, setHourlyStats] = useState<HourlyStat[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async (isInitial = false) => {
    try {
      // Only show loading spinner on initial fetch
      if (isInitial) setLoading(true);
      const [last, today, hourly] = await Promise.all([
        statsService.getLastMessage(),
        statsService.getTodayStats(),
        statsService.getTodayDetailed(),
      ]);
      setLastMessage(last);
      setTodayStats(today);
      setHourlyStats(hourly);
      setError(null);
    } catch (err) {
      console.error(err);
      setError('Unable to load statistics');
    } finally {
      if (isInitial) setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData(true); // Initial fetch
    const id = setInterval(() => fetchData(false), refreshRate); // Background updates
    return () => clearInterval(id);
  }, [fetchData, refreshRate]);

  return {
    lastMessage,
    todayStats,
    hourlyStats,
    loading,
    error,
    refetch: () => fetchData(true),
  };
};
