import { useEffect, useState } from 'react';
import type { DailyStatsResponse, RollingStatsResponse, WindowStats } from '@/types/api';
import { Card } from '@/components/common/Card';
import { formatNumber } from '@/utils/formatters';
import { statsService } from '@/services/statsService';

interface PercentileStatsProps {
  todayStats: DailyStatsResponse | null;
}

type RangeKey = 'today' | '24h' | '7d' | '30d';

export const PercentileStats = ({ todayStats }: PercentileStatsProps) => {
  const [rollingStats, setRollingStats] = useState<RollingStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedRange, setSelectedRange] = useState<RangeKey>('today');

  useEffect(() => {
    let isMounted = true;

    const fetchRolling = async () => {
      try {
        const data = await statsService.getRollingStats();
        if (!isMounted) return;
        setRollingStats(data);
        setError(null);
      } catch (err) {
        console.error('Failed to load rolling percentile stats', err);
        if (!isMounted) return;
        setError('Unable to load rolling percentile stats');
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    fetchRolling();
    const interval = setInterval(fetchRolling, 60_000);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  const getStatsForRange = (): WindowStats | null => {
    if (selectedRange === 'today') {
      if (!todayStats) return null;
      const { average_gateways, max_gateways, min_gateways, message_count, p50_gateways, p90_gateways, p95_gateways, p99_gateways } =
        todayStats;
      return { average_gateways, max_gateways, min_gateways, message_count, p50_gateways, p90_gateways, p95_gateways, p99_gateways };
    }

    if (!rollingStats) return null;

    if (selectedRange === '24h') return rollingStats.last_24h;
    if (selectedRange === '7d') return rollingStats.last_7d;
    if (selectedRange === '30d') return rollingStats.last_30d;

    return null;
  };

  const currentStats = getStatsForRange();
  const hasData = currentStats && currentStats.message_count > 0;

  const rangeMeta: Record<
    RangeKey,
    {
      label: string;
      subtitle: string;
    }
  > = {
    today: {
      label: 'Today',
      subtitle: "Today's gateway count distribution",
    },
    '24h': {
      label: 'Last 24 Hours',
      subtitle: 'Rolling distribution over the last 24 hours',
    },
    '7d': {
      label: 'Last 7 Days',
      subtitle: 'Rolling distribution over the last 7 days',
    },
    '30d': {
      label: 'Last 30 Days',
      subtitle: 'Rolling distribution over the last 30 days',
    },
  };

  const selectedMeta = rangeMeta[selectedRange];

  if (!hasData && !loading) {
    return (
      <Card title="Gateway Distribution (Percentiles)">
        <div className="flex flex-col items-center justify-center py-8 text-slate-500">
          <div className="mb-2">No data available for the selected range.</div>
          <div className="flex gap-2 mt-2">
            {(Object.keys(rangeMeta) as RangeKey[]).map((key) => (
              <button
                key={key}
                type="button"
                onClick={() => setSelectedRange(key)}
                className={`px-2 py-1 text-xs rounded-full border ${
                  selectedRange === key
                    ? 'bg-slate-900 text-white border-slate-900'
                    : 'text-slate-600 dark:text-slate-300 border-slate-300 dark:border-slate-700'
                }`}
              >
                {rangeMeta[key].label}
              </button>
            ))}
          </div>
          {error && <div className="mt-3 text-xs text-red-500">{error}</div>}
        </div>
      </Card>
    );
  }

  const percentiles = [
    { label: 'p50 (Median)', value: currentStats?.p50_gateways, color: 'text-blue-600 dark:text-blue-400' },
    { label: 'p90', value: currentStats?.p90_gateways, color: 'text-green-600 dark:text-green-400' },
    { label: 'p95', value: currentStats?.p95_gateways, color: 'text-yellow-600 dark:text-yellow-400' },
    { label: 'p99', value: currentStats?.p99_gateways, color: 'text-orange-600 dark:text-orange-400' },
  ];

  return (
    <Card title="Gateway Distribution (Percentiles)" subtitle={selectedMeta.subtitle}>
      <div className="flex items-center justify-between mb-4">
        <div className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
          {selectedMeta.label}
        </div>
        <div className="flex gap-2">
          {(Object.keys(rangeMeta) as RangeKey[]).map((key) => (
            <button
              key={key}
              type="button"
              onClick={() => setSelectedRange(key)}
              className={`px-2 py-1 text-xs rounded-full border transition-colors ${
                selectedRange === key
                  ? 'bg-slate-900 text-white border-slate-900'
                  : 'text-slate-600 dark:text-slate-300 border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800'
              }`}
            >
              {rangeMeta[key].label}
            </button>
          ))}
        </div>
      </div>

      {loading && !currentStats ? (
        <div className="text-center py-8 text-slate-500">Loading percentile data...</div>
      ) : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {percentiles.map((p) => (
              <div key={p.label} className="text-center">
                <div className={`text-3xl font-bold ${p.color}`}>
                  {p.value !== null && p.value !== undefined ? formatNumber(p.value, 1) : '—'}
                </div>
                <div className="text-xs text-slate-500 mt-1">{p.label}</div>
              </div>
            ))}
          </div>

          <div className="mt-4 pt-4 border-t border-slate-200 dark:border-slate-700">
            <div className="grid grid-cols-3 gap-4 text-center text-sm">
              <div>
                <div className="text-slate-600 dark:text-slate-400">Min</div>
                <div className="font-semibold text-slate-900 dark:text-white">
                  {currentStats ? currentStats.min_gateways : '—'}
                </div>
              </div>
              <div>
                <div className="text-slate-600 dark:text-slate-400">Average</div>
                <div className="font-semibold text-slate-900 dark:text-white">
                  {currentStats ? formatNumber(currentStats.average_gateways, 1) : '—'}
                </div>
              </div>
              <div>
                <div className="text-slate-600 dark:text-slate-400">Max</div>
                <div className="font-semibold text-slate-900 dark:text-white">
                  {currentStats ? currentStats.max_gateways : '—'}
                </div>
              </div>
            </div>
          </div>

          {error && (
            <div className="mt-3 text-center text-xs text-red-500">
              {error}
            </div>
          )}
        </>
      )}
    </Card>
  );
};

