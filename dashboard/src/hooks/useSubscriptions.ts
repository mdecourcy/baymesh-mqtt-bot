import { useCallback, useEffect, useState } from 'react';
import { subscriptionService } from '@/services/subscriptionService';
import type { Subscription, SubscriptionType } from '@/types/subscription';

export const useSubscriptions = () => {
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchSubscriptions = useCallback(async () => {
    try {
      setLoading(true);
      const data = await subscriptionService.getAll();
      setSubscriptions(data);
      setError(null);
    } catch (err) {
      console.error(err);
      setError('Unable to load subscriptions');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSubscriptions();
  }, [fetchSubscriptions]);

  const subscribe = async (userId: number, type: SubscriptionType) => {
    await subscriptionService.subscribe(userId, type);
    fetchSubscriptions();
  };

  const unsubscribe = async (userId: number) => {
    await subscriptionService.unsubscribe(userId);
    fetchSubscriptions();
  };

  return { subscriptions, loading, error, subscribe, unsubscribe, refetch: fetchSubscriptions };
};
