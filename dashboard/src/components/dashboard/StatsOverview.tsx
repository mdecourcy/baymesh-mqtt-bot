import type { DailyStatsResponse } from '@/types/api';
import type { Message } from '@/types/message';
import { Card } from '@/components/common/Card';
import { formatDateTime } from '@/utils/formatters';
import { Loading } from '@/components/common/Loading';
import { useAppContext } from '@/context/AppContext';

interface StatsOverviewProps {
  lastMessage: Message | null;
  todayStats: DailyStatsResponse | null;
  loading: boolean;
}

export const StatsOverview = ({ lastMessage, todayStats, loading }: StatsOverviewProps) => {
  const { timezone } = useAppContext();
  
  if (loading && !todayStats) return <Loading label="Loading overview..." />;

  const formatMeshId = (id?: number | null) => {
    if (id === undefined || id === null) return null;
    return '!' + id.toString(16).padStart(8, '0');
  };

  const cards = [
    {
      title: 'Last message',
      value: lastMessage ? lastMessage.sender_name : '—',
      sub: lastMessage
        ? `${formatMeshId(lastMessage.sender_user_id) || 'Unknown'} · ${lastMessage.gateway_count} gateways`
        : 'Awaiting data',
    },
    {
      title: "Today's average",
      value: todayStats ? todayStats.average_gateways.toFixed(1) : '—',
      sub: `Average gateways per message`,
    },
    {
      title: 'Peak gateways',
      value: todayStats ? todayStats.max_gateways : '—',
      sub: 'Highest gateway count today',
    },
    {
      title: 'Messages today',
      value: todayStats ? todayStats.message_count.toLocaleString() : '—',
      sub: lastMessage ? formatDateTime(lastMessage.timestamp, timezone) : 'No messages yet',
    },
  ];

  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      {cards.map((stat) => (
        <Card key={stat.title} title={stat.title}>
          <p className="text-3xl font-semibold text-slate-900 dark:text-white">{stat.value}</p>
          <p className="text-sm text-slate-500">{stat.sub}</p>
        </Card>
      ))}
    </div>
  );
};
