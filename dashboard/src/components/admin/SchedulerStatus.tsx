import type { HealthResponse } from '@/types/api';
import { Card } from '@/components/common/Card';

interface SchedulerStatusProps {
  health: HealthResponse | null;
}

export const SchedulerStatus = ({ health }: SchedulerStatusProps) => {
  const scheduler = health?.details?.scheduler;
  return (
    <Card title="Scheduler">
      {scheduler ? (
        <div className="space-y-2 text-sm text-slate-600 dark:text-slate-300">
          <p>Next run: {scheduler.next_run ?? '—'}</p>
          <p>Last run: {scheduler.last_run ?? '—'}</p>
          <p>Recipients: {scheduler.recipients ?? 0}</p>
          <p>Last error: {scheduler.last_error ?? 'None'}</p>
        </div>
      ) : (
        <p className="text-slate-500">Scheduler metrics unavailable.</p>
      )}
    </Card>
  );
};
