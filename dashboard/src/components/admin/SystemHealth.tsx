import type { HealthResponse } from '@/types/api';
import { Card } from '@/components/common/Card';
import { formatStatusColor } from '@/utils/formatters';

interface SystemHealthProps {
  health: HealthResponse | null;
  loading: boolean;
  onRefresh: () => void;
}

export const SystemHealth = ({ health, loading, onRefresh }: SystemHealthProps) => (
  <Card
    title="System status"
    action={
      <button onClick={onRefresh} className="text-sm text-primary">
        Refresh
      </button>
    }
  >
    {loading ? (
      <p>Checking health...</p>
    ) : health ? (
      <div className="grid gap-4 md:grid-cols-3">
        <div>
          <p className="text-sm text-slate-500">Database</p>
          <p className={`text-lg font-semibold ${formatStatusColor(health.database)}`}>{health.database}</p>
          <p className="text-xs text-slate-400">{health.details?.database?.latency_ms ?? '—'} ms latency</p>
        </div>
        <div>
          <p className="text-sm text-slate-500">MQTT</p>
          <p className={`text-lg font-semibold ${formatStatusColor(health.mqtt)}`}>{health.mqtt}</p>
          <p className="text-xs text-slate-400">Server: {health.details?.mqtt?.server ?? 'n/a'}</p>
        </div>
        <div>
          <p className="text-sm text-slate-500">Overall</p>
          <p className={`text-lg font-semibold ${formatStatusColor(health.status)}`}>{health.status}</p>
          <p className="text-xs text-slate-400">Checked {health.timestamp}</p>
        </div>
      </div>
    ) : (
      <p className="text-slate-500">No health data.</p>
    )}
  </Card>
);
