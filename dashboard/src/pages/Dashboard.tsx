import { useStats } from '@/hooks/useStats';
import { useMessages } from '@/hooks/useMessages';
import { useDetailedMessages } from '@/hooks/useDetailedMessages';
import { StatsOverview } from '@/components/dashboard/StatsOverview';
import { MessageChart } from '@/components/dashboard/MessageChart';
import { HourlyBreakdown } from '@/components/dashboard/HourlyBreakdown';
import { MessageDistribution } from '@/components/dashboard/MessageDistribution';
import { RecentMessages } from '@/components/dashboard/RecentMessages';
import { TopSenders } from '@/components/dashboard/TopSenders';
import { NetworkHealth } from '@/components/dashboard/NetworkHealth';
import { GatewayDistribution } from '@/components/dashboard/GatewayDistribution';
import { ActiveGateways } from '@/components/dashboard/ActiveGateways';
import { TrendComparisons } from '@/components/dashboard/TrendComparisons';
import { PercentileStats } from '@/components/dashboard/PercentileStats';
import { NetworkStats } from '@/components/dashboard/NetworkStats';
import { ErrorState } from '@/components/common/Error';
import { Loading } from '@/components/common/Loading';

const Dashboard = () => {
  const stats = useStats();
  const { messages } = useMessages(100);
  const { messages: detailedMessages, loading: detailedLoading, error: detailedError } = useDetailedMessages(100);

  if (stats.error) {
    return <ErrorState message={stats.error} onRetry={stats.refetch} />;
  }

  return (
    <div className="space-y-6">
      <StatsOverview lastMessage={stats.lastMessage} todayStats={stats.todayStats} loading={stats.loading} />
      
      <div className="grid gap-6 lg:grid-cols-2 xl:grid-cols-4">
        <NetworkHealth messages={messages} todayStats={stats.todayStats} />
        <TrendComparisons />
        <div className="lg:col-span-2">
          {stats.loading ? (
            <Loading label="Loading charts..." />
          ) : (
            <MessageChart data={stats.hourlyStats} loading={stats.loading} />
          )}
        </div>
      </div>
      
      <div className="grid gap-6 lg:grid-cols-2">
        <PercentileStats todayStats={stats.todayStats} />
        <NetworkStats />
      </div>
      
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          {detailedError ? (
            <ErrorState message={detailedError} onRetry={() => {}} />
          ) : (
            <RecentMessages messages={detailedMessages} loading={detailedLoading} />
          )}
        </div>
        <div className="space-y-6">
          <TopSenders messages={messages} />
          <GatewayDistribution messages={messages} />
        </div>
      </div>
      
      <div className="grid gap-6 lg:grid-cols-3">
        <HourlyBreakdown data={stats.hourlyStats} />
        <MessageDistribution messages={messages} />
        <ActiveGateways messages={messages} />
      </div>
    </div>
  );
};

export default Dashboard;
