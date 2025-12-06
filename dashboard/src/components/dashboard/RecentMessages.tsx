import { useState } from 'react';
import type { DetailedMessage } from '@/types/message';
import { Card } from '@/components/common/Card';
import { Loading } from '@/components/common/Loading';
import { formatDateTime } from '@/utils/formatters';
import { useAppContext } from '@/context/AppContext';

interface RecentMessagesProps {
  messages: DetailedMessage[];
  loading: boolean;
}

const getGatewayBadge = (count: number) => {
  if (count >= 50) return 'bg-emerald-100 dark:bg-emerald-900 text-emerald-800 dark:text-emerald-200';
  if (count >= 20) return 'bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200';
  if (count >= 10) return 'bg-yellow-100 dark:bg-yellow-900 text-yellow-800 dark:text-yellow-200';
  if (count >= 5) return 'bg-orange-100 dark:bg-orange-900 text-orange-800 dark:text-orange-200';
  return 'bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200';
};

const formatMeshId = (id?: number | null) => {
  if (id === undefined || id === null) return null;
  return '!' + id.toString(16).padStart(8, '0');
};

export const RecentMessages = ({ messages, loading }: RecentMessagesProps) => {
  const { timezone } = useAppContext();
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const toggleExpand = (id: number) => {
    setExpandedId(expandedId === id ? null : id);
  };

  return (
    <Card title="Recent messages" subtitle="Click a message to see details and gateways">
      {loading ? (
        <Loading label="Loading messages..." />
      ) : messages.length === 0 ? (
        <div className="text-center py-8 text-slate-500">
          No messages yet. Waiting for Meshtastic traffic...
        </div>
      ) : (
        <div className="space-y-2">
          {messages.slice(0, 20).map((msg) => {
            const isExpanded = expandedId === msg.id;
            return (
              <div
                key={msg.message_id}
                className={`border rounded-lg transition-all ${
                  isExpanded
                    ? 'border-blue-300 dark:border-blue-700 bg-blue-50 dark:bg-blue-950'
                    : 'border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700'
                }`}
              >
                {/* Main row - clickable */}
                <button
                  onClick={() => toggleExpand(msg.id)}
                  className="w-full px-4 py-3 text-left hover:bg-slate-50 dark:hover:bg-slate-900 rounded-lg transition-colors"
                >
                  <div className="flex items-center justify-between gap-4">
                    {/* Sender info */}
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-slate-900 dark:text-white truncate">
                        {msg.sender_name}
                      </div>
                      {formatMeshId(msg.sender_user_id) && (
                        <div className="text-xs text-slate-500 font-mono">
                          {formatMeshId(msg.sender_user_id)}
                        </div>
                      )}
                    </div>

                    {/* Gateway count badge */}
                    <div className={`px-3 py-1 rounded-full text-sm font-semibold ${getGatewayBadge(msg.gateway_count)}`}>
                      {msg.gateway_count} GW
                    </div>

                    {/* RSSI, SNR, Hops */}
                    <div className="hidden sm:flex gap-4 text-sm text-slate-600 dark:text-slate-400">
                      <div>
                        <span className="text-xs text-slate-500">RSSI:</span> {msg.rssi ?? '—'}
                      </div>
                      <div>
                        <span className="text-xs text-slate-500">SNR:</span> {msg.snr ?? '—'}
                      </div>
                      <div>
                        <span className="text-xs text-slate-500">Hops:</span>{' '}
                        {msg.hops_travelled ?? '—'}
                      </div>
                    </div>

                    {/* Timestamp */}
                    <div className="text-xs text-slate-500 text-right">
                      {formatDateTime(msg.timestamp, timezone)}
                    </div>

                    {/* Expand indicator */}
                    <div className="text-slate-400">
                      {isExpanded ? '▼' : '▶'}
                    </div>
                  </div>
                </button>

                {/* Expanded details */}
                {isExpanded && (
                  <div className="px-4 pb-4 pt-2 border-t border-slate-200 dark:border-slate-800">
                    {/* Message payload */}
                    {msg.payload && (
                      <div className="mb-4">
                        <div className="text-xs font-semibold text-slate-500 uppercase mb-1">
                          Message
                        </div>
                        <div className="bg-white dark:bg-slate-900 p-3 rounded border border-slate-200 dark:border-slate-800">
                          <div className="text-sm text-slate-900 dark:text-white whitespace-pre-wrap break-words">
                            {msg.payload}
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Hop metadata */}
                    {(msg.hop_start !== undefined || msg.hop_limit !== undefined || msg.hops_travelled !== undefined) && (
                      <div className="mb-4 grid grid-cols-1 sm:grid-cols-3 gap-3 text-sm text-slate-700 dark:text-slate-300">
                        <div>
                          <div className="text-xs uppercase text-slate-500">Hop start</div>
                          <div className="font-medium">{msg.hop_start ?? '—'}</div>
                        </div>
                        <div>
                          <div className="text-xs uppercase text-slate-500">Hop limit (at receipt)</div>
                          <div className="font-medium">{msg.hop_limit ?? '—'}</div>
                        </div>
                        <div>
                          <div className="text-xs uppercase text-slate-500">Hops travelled</div>
                          <div className="font-medium">{msg.hops_travelled ?? '—'}</div>
                        </div>
                      </div>
                    )}

                    {/* Gateway list */}
                    <div>
                      <div className="text-xs font-semibold text-slate-500 uppercase mb-2">
                        Gateways ({msg.gateways.length})
                      </div>
                      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                        {msg.gateways.map((gw, idx) => (
                          <div
                            key={`${gw.gateway_id}-${idx}`}
                            className="bg-white dark:bg-slate-900 p-3 rounded border border-slate-200 dark:border-slate-800 hover:border-blue-300 dark:hover:border-blue-700 transition-colors"
                          >
                            {gw.gateway_name ? (
                              <>
                                <div className="text-sm font-medium text-slate-900 dark:text-white truncate">
                                  {gw.gateway_name}
                                </div>
                                <div className="font-mono text-xs text-blue-600 dark:text-blue-400">
                                  {gw.gateway_id}
                                </div>
                              </>
                            ) : (
                              <div className="font-mono text-sm font-medium text-blue-600 dark:text-blue-400">
                                {gw.gateway_id}
                              </div>
                            )}
                            <div className="text-xs text-slate-500 mt-1">
                              {formatDateTime(gw.created_at, timezone)}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Message ID */}
                    <div className="mt-3 pt-3 border-t border-slate-200 dark:border-slate-800">
                      <div className="text-xs text-slate-500">
                        <span className="font-semibold">Packet ID:</span>{' '}
                        <span className="font-mono">{msg.message_id}</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
};
