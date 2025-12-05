import type { GatewayPercentiles } from '@/types/message';
import { Card } from '@/components/common/Card';
import { formatNumber } from '@/utils/formatters';

interface Props {
  data: GatewayPercentiles | null;
  loading?: boolean;
  error?: string | null;
}

const percentilesMeta = [
  { label: 'p50 (Median)', key: 'p50', color: 'text-blue-600 dark:text-blue-400' },
  { label: 'p90', key: 'p90', color: 'text-green-600 dark:text-green-400' },
  { label: 'p95', key: 'p95', color: 'text-yellow-600 dark:text-yellow-400' },
  { label: 'p99', key: 'p99', color: 'text-orange-600 dark:text-orange-400' },
];

export const UserGatewayPercentiles = ({ data, loading, error }: Props) => (
  <Card title="Gateway Distribution (Percentiles)" subtitle="Recent per-user gateway counts">
    {loading && <div className="text-sm text-slate-500">Loading percentile data...</div>}
    {error && <div className="text-sm text-red-500">{error}</div>}

    {!loading && !error && data && (
      <div className="space-y-4">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {percentilesMeta.map((p) => (
            <div key={p.key} className="text-center">
              <div className={`text-3xl font-bold ${p.color}`}>
                {data[p.key as keyof GatewayPercentiles] !== null &&
                data[p.key as keyof GatewayPercentiles] !== undefined
                  ? formatNumber(data[p.key as keyof GatewayPercentiles] as number, 1)
                  : '—'}
              </div>
              <div className="text-xs text-slate-500 mt-1">{p.label}</div>
            </div>
          ))}
        </div>

        <div className="text-xs text-slate-500 text-center">
          Sample size: {formatNumber(data.sample_size)}
        </div>
      </div>
    )}

    {!loading && !error && !data && (
      <div className="text-sm text-slate-500">No percentile data.</div>
    )}
  </Card>
);

