import type { Message } from '@/types/message';
import { Card } from '@/components/common/Card';
import { useMemo } from 'react';
import { Link } from 'react-router-dom';

interface TopSendersProps {
  messages: Message[];
}

interface SenderStats {
  sender_name: string;
  sender_user_id?: number | null;
  message_count: number;
  avg_gateways: number;
  max_gateways: number;
}

const formatMeshId = (id?: number | null) => {
  if (id === undefined || id === null) return null;
  return '!' + id.toString(16).padStart(8, '0');
};

export const TopSenders = ({ messages }: TopSendersProps) => {
  const topSenders = useMemo(() => {
    const senderMap = new Map<string, SenderStats>();
    
    messages.forEach((msg) => {
      const key = msg.sender_user_id?.toString() || msg.sender_name;
      const existing = senderMap.get(key);
      
      if (existing) {
        existing.message_count += 1;
        existing.avg_gateways = 
          (existing.avg_gateways * (existing.message_count - 1) + msg.gateway_count) / existing.message_count;
        existing.max_gateways = Math.max(existing.max_gateways, msg.gateway_count);
      } else {
        senderMap.set(key, {
          sender_name: msg.sender_name,
          sender_user_id: msg.sender_user_id,
          message_count: 1,
          avg_gateways: msg.gateway_count,
          max_gateways: msg.gateway_count,
        });
      }
    });
    
    return Array.from(senderMap.values())
      .sort((a, b) => b.message_count - a.message_count)
      .slice(0, 10);
  }, [messages]);

  return (
    <Card title="Top Senders">
      <div className="overflow-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="text-slate-500">
            <tr>
              <th className="py-2">Sender</th>
              <th className="text-right">Messages</th>
              <th className="text-right">Avg GW</th>
              <th className="text-right">Max GW</th>
            </tr>
          </thead>
          <tbody>
            {topSenders.map((sender) => (
              <tr 
                key={sender.sender_user_id || sender.sender_name} 
                className="border-t border-slate-100 dark:border-slate-800"
              >
                <td className="py-2">
                  <div className="font-medium text-slate-900 dark:text-white">
                    {sender.sender_user_id ? (
                      <Link
                        to={`/users/${sender.sender_user_id}`}
                        className="text-emerald-600 dark:text-emerald-400 hover:underline"
                      >
                        {sender.sender_name}
                      </Link>
                    ) : (
                      sender.sender_name
                    )}
                  </div>
                  {formatMeshId(sender.sender_user_id) && (
                    <div className="text-xs text-slate-500 font-mono">
                      {formatMeshId(sender.sender_user_id)}
                    </div>
                  )}
                </td>
                <td className="text-right font-semibold text-slate-900 dark:text-white">
                  {sender.message_count}
                </td>
                <td className="text-right text-slate-700 dark:text-slate-300">
                  {sender.avg_gateways.toFixed(1)}
                </td>
                <td className="text-right text-emerald-600 dark:text-emerald-400 font-semibold">
                  {sender.max_gateways}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
};


