import { useState } from 'react';
import { Modal } from '@/components/common/Modal';
import type { SubscriptionType } from '@/types/subscription';
import { isValidUserId } from '@/utils/validators';

interface SubscriptionFormProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (userId: number, type: SubscriptionType) => Promise<void>;
}

const typeOptions: { label: string; value: SubscriptionType; preview: string }[] = [
  { label: 'Daily Low', value: 'daily_low', preview: '🔵 Minimum gateways today: 12 (from 234 messages)' },
  { label: 'Daily Average', value: 'daily_avg', preview: '🟡 Average gateways today: 48.5 (from 234 messages)' },
  { label: 'Daily High', value: 'daily_high', preview: '🔴 Peak gateways today: 85 (from 234 messages)' },
];

export const SubscriptionForm = ({ open, onClose, onSubmit }: SubscriptionFormProps) => {
  const [userId, setUserId] = useState('');
  const [type, setType] = useState<SubscriptionType>('daily_avg');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    const parsed = Number(userId);
    if (!isValidUserId(parsed)) {
      setError('Please enter a valid numeric user ID');
      return;
    }
    try {
      setSaving(true);
      await onSubmit(parsed, type);
      setError(null);
      setUserId('');
      onClose();
    } catch (err) {
      console.error(err);
      setError('Unable to save subscription');
    } finally {
      setSaving(false);
    }
  };

  const currentPreview = typeOptions.find((opt) => opt.value === type)?.preview;

  return (
    <Modal isOpen={open} title="Add subscription" onClose={onClose} onConfirm={handleSubmit} confirmText={saving ? 'Saving...' : 'Save'}>
      <div className="space-y-4">
        <div>
          <label className="text-sm text-slate-500">User ID</label>
          <input value={userId} onChange={(e) => setUserId(e.target.value)} placeholder="e.g. 101" className="mt-1 w-full rounded-lg border border-slate-200 p-2 dark:bg-slate-900" />
        </div>
        <div>
          <p className="text-sm text-slate-500">Subscription type</p>
          <div className="mt-2 grid gap-2 md:grid-cols-3">
            {typeOptions.map((opt) => (
              <button key={opt.value} type="button" onClick={() => setType(opt.value)} className={`rounded-xl border p-3 text-left ${type === opt.value ? 'border-primary bg-primary/10' : 'border-slate-200 dark:border-slate-700'}`}>
                <p className="font-semibold">{opt.label}</p>
                <p className="text-xs text-slate-500">{opt.preview}</p>
              </button>
            ))}
          </div>
        </div>
        {currentPreview && (
          <div className="rounded-xl bg-slate-100 p-3 text-sm text-slate-600 dark:bg-slate-800 dark:text-slate-200">{currentPreview}</div>
        )}
        {error && <p className="text-sm text-danger">{error}</p>}
      </div>
    </Modal>
  );
};
