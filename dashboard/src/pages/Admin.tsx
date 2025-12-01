import { useHealth } from '@/hooks/useHealth';
import { SystemHealth } from '@/components/admin/SystemHealth';
import { ConnectionStatus } from '@/components/admin/ConnectionStatus';
import { SchedulerStatus } from '@/components/admin/SchedulerStatus';
import { MockMessageForm } from '@/components/admin/MockMessageForm';
import { DatabaseManagement } from '@/components/admin/DatabaseManagement';
import { ErrorState } from '@/components/common/Error';

const Admin = () => {
  const { health, loading, error, refetch } = useHealth();

  if (error) {
    return <ErrorState message={error} onRetry={refetch} />;
  }

  return (
    <div className="space-y-6">
      <SystemHealth health={health} loading={loading} onRefresh={refetch} />
      <div className="grid gap-6 lg:grid-cols-2">
        <ConnectionStatus health={health} />
        <SchedulerStatus health={health} />
      </div>
      <DatabaseManagement />
      <MockMessageForm />
    </div>
  );
};

export default Admin;
