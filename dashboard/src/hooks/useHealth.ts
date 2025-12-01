import { useEffect, useState } from 'react';
import { adminService } from '@/services/adminService';
import type { HealthResponse } from '@/types/api';

export const useHealth = () => {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchHealth = async () => {
    try {
      setLoading(true);
      const data = await adminService.getHealth();
      setHealth(data);
      setError(null);
    } catch (err) {
      console.error(err);
      setError('Unable to fetch health status');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
  }, []);

  return { health, loading, error, refetch: fetchHealth };
};
