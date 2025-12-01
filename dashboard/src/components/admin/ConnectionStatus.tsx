import type { HealthResponse } from '@/types/api';
import { Card } from '@/components/common/Card';

interface ConnectionStatusProps {
  health: HealthResponse | null;
}

export const ConnectionStatus = ({ health }: ConnectionStatusProps) => {
  const mqtt = health?.details?.mqtt;
  return (
    <Card title="MQTT connection">
      {mqtt ? (
        <div className="space-y-2 text-sm text-slate-600 dark:text-slate-300">
          <p>Server: {mqtt.server ?? 'mqtt.bayme.sh'}</p>
          <p>Topic: {mqtt.topic ?? 'msh/US/bayarea/#'}</p>
          <p>
            Status: <span className={mqtt.connected ? 'text-success' : 'text-danger'}>{mqtt.connected ? 'Connected' : 'Disconnected'}</span>
          </p>
          <p>Messages today: {mqtt.message_count ?? '—'}</p>
          <p>Uptime: {mqtt.uptime ?? '—'}</p>
          <p>Reconnects: {mqtt.reconnects ?? 0}</p>
        </div>
      ) : (
        <p className="text-slate-500">No MQTT stats available.</p>
      )}
    </Card>
  );
};
