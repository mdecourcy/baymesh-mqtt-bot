import { useEffect, useState } from 'react';
import { Card } from '@/components/common/Card';

interface NetworkStatsData {
  total_nodes: number;
  total_gateways: number;
  active_24h: {
    nodes: number;
    gateways: number;
  };
  active_7d: {
    nodes: number;
    gateways: number;
  };
  active_30d: {
    nodes: number;
    gateways: number;
  };
}

export const NetworkStats = () => {
  const [data, setData] = useState<NetworkStatsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedRange, setSelectedRange] = useState<'24h' | '7d' | '30d'>('24h');

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch('/network/stats');
        if (!response.ok) {
          const text = await response.text();
          throw new Error(`HTTP ${response.status}: ${text}`);
        }
        const stats = await response.json();
        setData(stats);
        setError(null);
      } catch (err) {
        console.error('Error fetching network stats:', err);
        setError(err instanceof Error ? err.message : 'Failed to load network stats');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 60000); // Refresh every minute
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <Card title="Network Overview">
        <div className="text-center py-8 text-slate-500">Loading...</div>
      </Card>
    );
  }

  if (error || !data) {
    return (
      <Card title="Network Overview">
        <div className="text-center py-8 text-red-500">
          {error || 'No data available'}
        </div>
      </Card>
    );
  }

  const timeframes = [
    { key: '24h' as const, label: 'Last 24 Hours', data: data.active_24h, color: 'text-blue-600 dark:text-blue-400' },
    { key: '7d' as const, label: 'Last 7 Days', data: data.active_7d, color: 'text-green-600 dark:text-green-400' },
    { key: '30d' as const, label: 'Last 30 Days', data: data.active_30d, color: 'text-purple-600 dark:text-purple-400' },
  ];

  return (
    <Card title="Network Overview" subtitle="Total and active nodes/gateways">
      <div className="space-y-6">
        {/* Timeframe chips (to visually match Gateway Distribution card) */}
        <div className="flex items-center justify-between">
          <div className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
            Time Window
          </div>
          <div className="flex gap-2">
            {timeframes.map((tf) => (
              <button
                key={tf.key}
                type="button"
                onClick={() => setSelectedRange(tf.key)}
                className={`px-2 py-1 text-xs rounded-full border transition-colors ${
                  selectedRange === tf.key
                    ? 'bg-slate-900 text-white border-slate-900'
                    : 'text-slate-600 dark:text-slate-300 border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800'
                }`}
              >
                {tf.label.replace('Last ', '')}
              </button>
            ))}
          </div>
        </div>
        {/* Total Stats */}
        <div className="grid grid-cols-2 gap-4">
          <div className="text-center p-4 bg-slate-50 dark:bg-slate-900 rounded-lg">
            <div className="text-3xl font-bold text-slate-900 dark:text-white">
              {data.total_nodes.toLocaleString()}
            </div>
            <div className="text-sm text-slate-500 mt-1">Total Nodes</div>
          </div>
          <div className="text-center p-4 bg-slate-50 dark:bg-slate-900 rounded-lg">
            <div className="text-3xl font-bold text-slate-900 dark:text-white">
              {data.total_gateways.toLocaleString()}
            </div>
            <div className="text-sm text-slate-500 mt-1">Total Gateways</div>
          </div>
        </div>

        {/* Active Stats for selected timeframe only (keeps card height aligned with neighbor) */}
        <div className="mt-2">
          {(() => {
            const tf = timeframes.find((t) => t.key === selectedRange) ?? timeframes[0];
            return (
              <div className="border-t border-slate-200 dark:border-slate-800 pt-4">
                <div className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">
                  {tf.label}
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-600 dark:text-slate-400">Active Nodes</span>
                    <span className={`text-2xl font-bold ${tf.color}`}>
                      {tf.data.nodes}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-600 dark:text-slate-400">Active Gateways</span>
                    <span className={`text-2xl font-bold ${tf.color}`}>
                      {tf.data.gateways}
                    </span>
                  </div>
                </div>
              </div>
            );
          })()}
        </div>
      </div>
    </Card>
  );
};

