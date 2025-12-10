import type { GatewayHistory } from '@/types/message';
import { Card } from '@/components/common/Card';
import { formatDateTime, formatNumber } from '@/utils/formatters';

interface Props {
  gateways: GatewayHistory[];
  loading?: boolean;
  error?: string | null;
}

const formatMeshId = (gatewayId: string) => gatewayId?.startsWith('!') ? gatewayId : `!${gatewayId}`;

export const UserGatewayHistory = ({ gateways, loading, error }: Props) => (
  <Card title="Gateway History">
    {loading && <div className="text-sm text-slate-500">Loading gateways...</div>}
    {error && <div className="text-sm text-red-500">{error}</div>}
    {!loading && !error && gateways.length === 0 && (
      <div className="text-sm text-slate-500">No gateway history yet.</div>
    )}
    {!loading && !error && gateways.length > 0 && (
      <div className="overflow-auto">
        <table className="min-w-full text-sm text-left">
          <thead className="text-slate-500">
            <tr>
              <th className="py-2">Gateway</th>
              <th className="text-right">Messages</th>
              <th className="text-right">First Seen</th>
              <th className="text-right">Last Seen</th>
            </tr>
          </thead>
          <tbody>
            {gateways.map((gw) => (
              <tr
                key={gw.gateway_id}
                className="border-t border-slate-100 dark:border-slate-800"
              >
                <td className="py-2">
                  <div className="font-medium text-slate-900 dark:text-white">
                    {gw.gateway_name || 'Unknown'}
                  </div>
                  <div className="text-xs text-slate-500 font-mono">
                    {formatMeshId(gw.gateway_id)}
                  </div>
                </td>
                <td className="text-right font-semibold text-slate-900 dark:text-white">
                  {formatNumber(gw.message_count)}
                </td>
                <td className="text-right text-slate-700 dark:text-slate-300">
                  {formatDateTime(gw.first_seen)}
                </td>
                <td className="text-right text-slate-700 dark:text-slate-300">
                  {formatDateTime(gw.last_seen)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )}
  </Card>
);


