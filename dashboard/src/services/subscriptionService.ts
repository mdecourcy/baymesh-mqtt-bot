import { api } from './api';
import type { Subscription, SubscriptionType } from '@/types/subscription';

export const subscriptionService = {
  getAll: async () => {
    const { data } = await api.get<Subscription[]>('/subscriptions');
    return data;
  },
  subscribe: async (userId: number, type: SubscriptionType) => {
    const { data } = await api.post(`/subscribe/${userId}/${type}`);
    return data as Subscription;
  },
  unsubscribe: async (userId: number) => {
    await api.delete(`/subscribe/${userId}`);
  },
};
