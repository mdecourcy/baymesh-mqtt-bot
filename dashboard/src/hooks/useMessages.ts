import { useCallback, useEffect, useState } from 'react';
import { statsService } from '@/services/statsService';
import { useAppContext } from '@/context/AppContext';
import type { Message } from '@/types/message';

export const useMessages = (count = 20) => {
  const { refreshRate } = useAppContext();
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchMessages = useCallback(async (isInitial = false) => {
    try {
      // Only show loading spinner on initial fetch
      if (isInitial) setLoading(true);
      const data = await statsService.getLastMessages(count);
      setMessages(data);
      setError(null);
    } catch (err) {
      console.error(err);
      setError('Unable to load messages');
    } finally {
      if (isInitial) setLoading(false);
    }
  }, [count]);

  useEffect(() => {
    fetchMessages(true); // Initial fetch
    const id = setInterval(() => fetchMessages(false), refreshRate); // Background updates
    return () => clearInterval(id);
  }, [fetchMessages, refreshRate]);

  return { messages, loading, error, refetch: () => fetchMessages(true) };
};
