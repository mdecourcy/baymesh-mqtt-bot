import { useState } from 'react';
import { useSubscriptions } from '@/hooks/useSubscriptions';
import type { SubscriptionType } from '@/types/subscription';
import { SubscriptionManager } from '@/components/subscriptions/SubscriptionManager';
import { SubscriptionList } from '@/components/subscriptions/SubscriptionList';
import { ErrorState } from '@/components/common/Error';

const Subscriptions = () => {
  const { subscriptions, loading, error, subscribe, unsubscribe } = useSubscriptions();
  const [filter, setFilter] = useState<'all' | SubscriptionType>('all');

  const filtered = filter === 'all' ? subscriptions : subscriptions.filter((sub) => sub.subscription_type === filter);

  if (error) {
    return <ErrorState message={error} onRetry={() => window.location.reload()} />;
  }

  return (
    <div className="space-y-6">
      <SubscriptionManager subscriptions={subscriptions} loading={loading} onAdd={subscribe} />
      <div className="flex items-center gap-4">
        <label className="text-sm text-slate-500">Filter by type</label>
        <select value={filter} onChange={(e) => setFilter(e.target.value as typeof filter)} className="rounded-lg border border-slate-200 p-2 dark:bg-slate-900">
          <option value="all">All</option>
          <option value="daily_low">Daily low</option>
          <option value="daily_avg">Daily average</option>
          <option value="daily_high">Daily high</option>
        </select>
      </div>
      <SubscriptionList subscriptions={filtered} loading={loading} onUnsubscribe={unsubscribe} />
    </div>
  );
};

export default Subscriptions;
