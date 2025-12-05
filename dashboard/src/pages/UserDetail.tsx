import { useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import { UserMessageLog } from '@/components/users/UserMessageLog';
import { UserGatewayHistory } from '@/components/users/UserGatewayHistory';
import { UserGatewayPercentiles } from '@/components/users/UserGatewayPercentiles';
import { useUserDetails } from '@/hooks/useUserDetails';
import { Card } from '@/components/common/Card';

const formatMeshId = (userId?: number | null) => {
  if (userId === undefined || userId === null) return 'Unknown';
  return '!' + userId.toString(16).padStart(8, '0');
};

const UserDetail = () => {
  const { userId } = useParams();
  const parsedId = useMemo(() => {
    const num = Number(userId);
    return Number.isFinite(num) ? num : null;
  }, [userId]);

  const { messages, gateways, percentiles, loading, error } = useUserDetails(parsedId, {
    messageLimit: 100,
    gatewayLimit: 50,
    percentileLimit: 500,
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">
            User Details
          </h1>
          <p className="text-sm text-slate-500">
            Mesh ID: {formatMeshId(parsedId)}
          </p>
        </div>
        <Link
          to="/"
          className="text-sm text-emerald-600 dark:text-emerald-400 hover:underline"
        >
          ← Back to dashboard
        </Link>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <div className="xl:col-span-2">
          <UserMessageLog messages={messages} loading={loading} error={error} />
        </div>
        <div>
          <UserGatewayPercentiles data={percentiles} loading={loading} error={error} />
          <div className="mt-4">
          <UserGatewayHistory gateways={gateways} loading={loading} error={error} />
          </div>
        </div>
      </div>

      {error && (
        <Card title="Error">
          <div className="text-sm text-red-500">{error}</div>
        </Card>
      )}
    </div>
  );
};

export default UserDetail;

