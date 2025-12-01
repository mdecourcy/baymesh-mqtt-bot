import { api } from './api';
import type { HealthResponse } from '@/types/api';

interface MockMessagePayload {
  sender_id: number;
  sender_name: string;
  gateway_count: number;
  rssi: number;
  snr: number;
  payload?: string;
  timestamp: string;
}

export interface DatabaseInfo {
  size_bytes: number;
  size_mb: number;
  records: {
    messages: number;
    users: number;
    gateways: number;
    subscriptions: number;
    cache: number;
    command_logs: number;
    total: number;
  };
  date_range: {
    oldest: string | null;
    newest: string | null;
  };
}

export interface ExpireDataResponse {
  status: string;
  cutoff_date: string;
  days: number;
  deleted: {
    messages: number;
    cache_entries: number;
    command_logs: number;
  };
}

export const adminService = {
  getHealth: async () => {
    const { data } = await api.get<HealthResponse>('/health');
    return data;
  },
  createMockMessage: async (payload: MockMessagePayload) => {
    const { data } = await api.post('/mock/message', payload);
    return data;
  },
  getDatabaseInfo: async () => {
    const { data } = await api.get<DatabaseInfo>('/admin/database/info');
    return data;
  },
  expireOldData: async (days: number) => {
    const { data } = await api.delete<ExpireDataResponse>(
      `/admin/database/expire?days=${days}`
    );
    return data;
  },
};
