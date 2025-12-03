import { useEffect, useState } from 'react';
import type { DetailedMessage } from '@/types/message';

export const useDetailedMessages = (limit: number = 100, refreshInterval: number = 30000) => {
  const [messages, setMessages] = useState<DetailedMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchMessages = async () => {
      try {
        if (loading && messages.length > 0) {
          // Don't show loading state on refresh to prevent jitter
          setLoading(false);
        }
        
        const response = await fetch(`/messages/detailed?limit=${limit}`);
        if (!response.ok) {
          throw new Error('Failed to fetch messages');
        }
        const data = await response.json();
        setMessages(data);
        setError(null);
      } catch (err) {
        console.error('Error fetching detailed messages:', err);
        setError('Failed to load messages');
      } finally {
        if (messages.length === 0) {
          setLoading(false);
        }
      }
    };

    fetchMessages();
    const interval = setInterval(fetchMessages, refreshInterval);
    return () => clearInterval(interval);
  }, [limit, refreshInterval]);

  return { messages, loading, error };
};


