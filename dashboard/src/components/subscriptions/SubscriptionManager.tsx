import { useState } from 'react';
import type { Subscription, SubscriptionType } from '@/types/subscription';
import { Card } from '@/components/common/Card';
import { Button } from '@/components/common/Button';
import { SubscriptionForm } from './SubscriptionForm';

interface SubscriptionManagerProps {
  subscriptions: Subscription[];
  loading: boolean;
  onAdd: (userId: number, type: SubscriptionType) => Promise<void>;
}

export const SubscriptionManager = ({ subscriptions, loading, onAdd }: SubscriptionManagerProps) => {
  const [modalOpen, setModalOpen] = useState(false);

  return (
    <Card
      title="Manage subscriptions"
      action={
        <Button variant="primary" onClick={() => setModalOpen(true)}>
          Add subscription
        </Button>
      }
    >
      <p className="text-slate-600 dark:text-slate-300">
        Total subscribers: <strong>{loading ? '—' : subscriptions.length}</strong>
      </p>
      <p className="text-sm text-slate-500">Use the button above to add new users to the daily reports.</p>
      <SubscriptionForm open={modalOpen} onClose={() => setModalOpen(false)} onSubmit={onAdd} />
    </Card>
  );
};
