import { useEffect, useState } from 'react';
import type { DetailedMessage, GatewayHistory, GatewayPercentiles } from '@/types/message';
import { userService } from '@/services/userService';

interface UseUserDetailsOptions {
  messageLimit?: number;
  gatewayLimit?: number;
  percentileLimit?: number;
}

export const useUserDetails = (
  userId: number | null,
  { messageLimit = 100, gatewayLimit = 50, percentileLimit = 500 }: UseUserDetailsOptions = {},
) => {
  const [messages, setMessages] = useState<DetailedMessage[]>([]);
  const [gateways, setGateways] = useState<GatewayHistory[]>([]);
  const [percentiles, setPercentiles] = useState<GatewayPercentiles | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!userId) return;
    const fetchData = async () => {
      setLoading(true);
      try {
        const [msgs, gws, pct] = await Promise.all([
          userService.getUserMessages(userId, messageLimit),
          userService.getUserGatewayHistory(userId, gatewayLimit),
          userService.getUserGatewayPercentiles(userId, percentileLimit),
        ]);
        setMessages(msgs);
        setGateways(gws);
        setPercentiles(pct);
        setError(null);
      } catch (err) {
        console.error('Failed to load user details', err);
        setError('Failed to load user details');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [userId, messageLimit, gatewayLimit, percentileLimit]);

  return { messages, gateways, percentiles, loading, error };
};

