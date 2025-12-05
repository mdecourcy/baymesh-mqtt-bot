import { api } from './api';
import type { DetailedMessage, GatewayHistory, GatewayPercentiles } from '@/types/message';

export const userService = {
  getUserMessages: async (userId: number, limit = 100) => {
    const { data } = await api.get<DetailedMessage[]>(`/users/${userId}/messages`, {
      params: { limit },
    });
    return data;
  },
  getUserGatewayHistory: async (userId: number, limit = 50) => {
    const { data } = await api.get<GatewayHistory[]>(`/users/${userId}/gateways`, {
      params: { limit },
    });
    return data;
  },
  getUserGatewayPercentiles: async (userId: number, limit = 500) => {
    const { data } = await api.get<GatewayPercentiles>(
      `/users/${userId}/gateway_percentiles`,
      { params: { limit } },
    );
    return data;
  },
};

