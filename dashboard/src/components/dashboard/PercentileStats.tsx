import type { DailyStatsResponse } from '@/types/api';
import { Card } from '@/components/common/Card';
import { formatNumber } from '@/utils/formatters';

interface PercentileStatsProps {
  todayStats: DailyStatsResponse | null;
}

export const PercentileStats = ({ todayStats }: PercentileStatsProps) => {
  if (!todayStats || todayStats.message_count === 0) {
    return (
      <Card title="Gateway Distribution (Percentiles)">
        <div className="text-center py-8 text-slate-500">
          No data available yet
        </div>
      </Card>
    );
  }

  const percentiles = [
    { label: 'p50 (Median)', value: todayStats.p50_gateways, color: 'text-blue-600 dark:text-blue-400' },
    { label: 'p90', value: todayStats.p90_gateways, color: 'text-green-600 dark:text-green-400' },
    { label: 'p95', value: todayStats.p95_gateways, color: 'text-yellow-600 dark:text-yellow-400' },
    { label: 'p99', value: todayStats.p99_gateways, color: 'text-orange-600 dark:text-orange-400' },
  ];

  return (
    <Card title="Gateway Distribution (Percentiles)" subtitle="Today's gateway count distribution">
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
              {todayStats.min_gateways}
            </div>
          </div>
          <div>
            <div className="text-slate-600 dark:text-slate-400">Average</div>
            <div className="font-semibold text-slate-900 dark:text-white">
              {formatNumber(todayStats.average_gateways, 1)}
            </div>
          </div>
          <div>
            <div className="text-slate-600 dark:text-slate-400">Max</div>
            <div className="font-semibold text-slate-900 dark:text-white">
              {todayStats.max_gateways}
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
};

