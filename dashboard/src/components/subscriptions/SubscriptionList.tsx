import type { Subscription } from '@/types/subscription';
import { Card } from '@/components/common/Card';
import { Button } from '@/components/common/Button';
import { formatDateTime } from '@/utils/formatters';

interface SubscriptionListProps {
  subscriptions: Subscription[];
  loading: boolean;
  onUnsubscribe: (userId: number) => Promise<void>;
}

export const SubscriptionList = ({ subscriptions, loading, onUnsubscribe }: SubscriptionListProps) => (
  <Card title="Active subscriptions" subtitle={`${subscriptions.length} users`}>
    {loading ? (
      <p>Loading...</p>
    ) : subscriptions.length === 0 ? (
      <p className="text-slate-500">No subscriptions yet.</p>
    ) : (
      <div className="overflow-auto">
        <table className="min-w-full text-sm">
          <thead className="text-slate-500">
            <tr>
              <th className="py-2 text-left">User ID</th>
              <th className="text-left">Type</th>
              <th className="text-left">Created</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {subscriptions.map((sub) => (
              <tr key={sub.id} className="border-t border-slate-100 text-slate-700 dark:border-slate-800 dark:text-slate-200">
                <td className="py-2">{sub.user_id}</td>
                <td>{sub.subscription_type}</td>
                <td>{formatDateTime(sub.created_at)}</td>
                <td className="text-right">
                  <Button variant="secondary" size="sm" onClick={() => onUnsubscribe(sub.user_id)}>
                    Remove
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )}
  </Card>
);
