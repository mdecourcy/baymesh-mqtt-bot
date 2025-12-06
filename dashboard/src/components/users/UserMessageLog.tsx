import type { DetailedMessage } from '@/types/message';
import { Card } from '@/components/common/Card';
import { formatDateTime } from '@/utils/formatters';

interface Props {
  messages: DetailedMessage[];
  loading?: boolean;
  error?: string | null;
}

export const UserMessageLog = ({ messages, loading, error }: Props) => (
  <Card title="Message Log">
    {loading && <div className="text-sm text-slate-500">Loading messages...</div>}
    {error && <div className="text-sm text-red-500">{error}</div>}
    {!loading && !error && messages.length === 0 && (
      <div className="text-sm text-slate-500">No messages yet.</div>
    )}
    {!loading && !error && messages.length > 0 && (
      <div className="overflow-auto">
        <table className="min-w-full text-sm text-left">
          <thead className="text-slate-500">
            <tr>
              <th className="py-2">Time</th>
              <th className="text-right">Gateways</th>
              <th className="text-right">Hops</th>
              <th className="text-right">RSSI</th>
              <th className="text-right">SNR</th>
              <th>Payload</th>
            </tr>
          </thead>
          <tbody>
            {messages.map((msg) => (
              <tr
                key={msg.id}
                className="border-t border-slate-100 dark:border-slate-800 align-top"
              >
                <td className="py-2 text-slate-900 dark:text-white whitespace-nowrap">
                  {formatDateTime(msg.timestamp)}
                </td>
                <td className="text-right font-semibold text-slate-900 dark:text-white">
                  {msg.gateway_count}
                </td>
                <td className="text-right text-slate-700 dark:text-slate-300">
                  {msg.hops_travelled ?? '—'}
                </td>
                <td className="text-right text-slate-700 dark:text-slate-300">
                  {msg.rssi ?? '—'}
                </td>
                <td className="text-right text-slate-700 dark:text-slate-300">
                  {msg.snr ?? '—'}
                </td>
                <td className="text-slate-900 dark:text-white">
                  <div className="line-clamp-3 break-all">{msg.payload || '—'}</div>
                  {msg.gateways && msg.gateways.length > 0 && (
                    <div className="mt-1 text-xs text-slate-500">
                      Gateways: {msg.gateways.map((gw) => gw.gateway_name || gw.gateway_id).join(', ')}
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )}
  </Card>
);

