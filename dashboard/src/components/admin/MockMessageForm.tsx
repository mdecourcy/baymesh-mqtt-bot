import { useState } from 'react';
import { Card } from '@/components/common/Card';
import { Button } from '@/components/common/Button';
import { adminService } from '@/services/adminService';

export const MockMessageForm = () => {
  const [form, setForm] = useState({
    sender_id: '',
    sender_name: '',
    gateway_count: 3,
    hop_start: '',
    hop_limit: '',
    rssi: -100,
    snr: 5,
    payload: 'Test message',
    timestamp: new Date().toISOString().slice(0, 16),
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const updateField = (name: string, value: string) => setForm((prev) => ({ ...prev, [name]: value }));

  const handleSubmit = async () => {
    try {
      setLoading(true);
      await adminService.createMockMessage({
        sender_id: Number(form.sender_id),
        sender_name: form.sender_name,
        gateway_count: Number(form.gateway_count),
        hop_start: form.hop_start ? Number(form.hop_start) : undefined,
        hop_limit: form.hop_limit ? Number(form.hop_limit) : undefined,
        rssi: Number(form.rssi),
        snr: Number(form.snr),
        payload: form.payload,
        timestamp: new Date(form.timestamp).toISOString(),
      });
      setMessage('Mock message sent successfully');
    } catch (err) {
      console.error(err);
      setMessage('Failed to send mock message');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card title="Mock message" subtitle="Send a test payload into the system">
      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <label className="text-sm text-slate-500">Sender ID</label>
          <input value={form.sender_id} onChange={(e) => updateField('sender_id', e.target.value)} className="mt-1 w-full rounded-lg border border-slate-200 p-2 dark:bg-slate-900" />
        </div>
        <div>
          <label className="text-sm text-slate-500">Sender name</label>
          <input value={form.sender_name} onChange={(e) => updateField('sender_name', e.target.value)} className="mt-1 w-full rounded-lg border border-slate-200 p-2 dark:bg-slate-900" />
        </div>
        <div>
          <label className="text-sm text-slate-500">Gateway count</label>
          <input type="number" value={form.gateway_count} onChange={(e) => updateField('gateway_count', e.target.value)} className="mt-1 w-full rounded-lg border border-slate-200 p-2 dark:bg-slate-900" />
        </div>
        <div>
          <label className="text-sm text-slate-500">Hop start</label>
          <input type="number" value={form.hop_start} onChange={(e) => updateField('hop_start', e.target.value)} className="mt-1 w-full rounded-lg border border-slate-200 p-2 dark:bg-slate-900" />
        </div>
        <div>
          <label className="text-sm text-slate-500">Hop limit</label>
          <input type="number" value={form.hop_limit} onChange={(e) => updateField('hop_limit', e.target.value)} className="mt-1 w-full rounded-lg border border-slate-200 p-2 dark:bg-slate-900" />
        </div>
        <div>
          <label className="text-sm text-slate-500">RSSI</label>
          <input type="number" value={form.rssi} onChange={(e) => updateField('rssi', e.target.value)} className="mt-1 w-full rounded-lg border border-slate-200 p-2 dark:bg-slate-900" />
        </div>
        <div>
          <label className="text-sm text-slate-500">SNR</label>
          <input type="number" step="0.1" value={form.snr} onChange={(e) => updateField('snr', e.target.value)} className="mt-1 w-full rounded-lg border border-slate-200 p-2 dark:bg-slate-900" />
        </div>
        <div>
          <label className="text-sm text-slate-500">Timestamp</label>
          <input type="datetime-local" value={form.timestamp} onChange={(e) => updateField('timestamp', e.target.value)} className="mt-1 w-full rounded-lg border border-slate-200 p-2 dark:bg-slate-900" />
        </div>
        <div className="md:col-span-2">
          <label className="text-sm text-slate-500">Payload</label>
          <textarea value={form.payload} onChange={(e) => updateField('payload', e.target.value)} className="mt-1 w-full rounded-lg border border-slate-200 p-2 dark:bg-slate-900" />
        </div>
      </div>
      <div className="mt-4 flex items-center gap-4">
        <Button onClick={handleSubmit} loading={loading}>
          Send mock message
        </Button>
        {message && <p className="text-sm text-slate-500">{message}</p>}
      </div>
    </Card>
  );
};
