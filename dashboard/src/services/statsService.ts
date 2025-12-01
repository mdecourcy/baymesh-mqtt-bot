import { api } from './api';
import type { DailyStatsResponse, HourlyStat } from '@/types/api';
import type { Message } from '@/types/message';
import { addDays, differenceInCalendarDays, formatISO } from 'date-fns';

export const statsService = {
  getLastMessage: async () => {
    const { data } = await api.get<Message>('/stats/last');
    return data;
  },
  getLastMessages: async (count = 10) => {
    const { data } = await api.get<Message[]>(`/stats/last/${count}`);
    return data;
  },
  getTodayStats: async () => {
    const { data } = await api.get<DailyStatsResponse>('/stats/today');
    return data;
  },
  getTodayDetailed: async () => {
    const { data } = await api.get<HourlyStat[]>('/stats/today/detailed');
    return data;
  },
  getStatsByDate: async (date: string) => {
    const { data } = await api.get<DailyStatsResponse>(`/stats/${date}`);
    return data;
  },
  getStatsForRange: async (start: string, end: string) => {
    const startDate = new Date(start);
    const endDate = new Date(end);
    const days = differenceInCalendarDays(endDate, startDate);
    if (days > 60) throw new Error('Range too large (max 60 days)');
    const requests = Array.from({ length: days + 1 }, (_, idx) => {
      const current = addDays(startDate, idx);
      return statsService.getStatsByDate(formatISO(current, { representation: 'date' }));
    });
    return Promise.all(requests);
  },
};
