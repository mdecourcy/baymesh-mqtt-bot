import { useEffect, useState } from 'react';
import { Card } from '@/components/common/Card';
import { Loading } from '@/components/common/Loading';
import { ErrorState } from '@/components/common/Error';
import { formatDateTime } from '@/utils/formatters';
import { useAppContext } from '@/context/AppContext';

interface BotStats {
  total_commands: number;
  unique_users: number;
  rate_limited_count: number;
  rate_limited_percentage: number;
  top_commands: Array<{ command: string; count: number }>;
  top_users: Array<{ user_id: number; username: string; count: number }>;
  daily_commands: Array<{ date: string; count: number }>;
  period_days: number;
}

interface CommandLog {
  id: number;
  user_id: number;
  username: string;
  mesh_id: string | null;
  command: string;
  response_sent: boolean;
  rate_limited: boolean;
  timestamp: string;
}

const BotStats = () => {
  const { timezone } = useAppContext();
  const [stats, setStats] = useState<BotStats | null>(null);
  const [recentCommands, setRecentCommands] = useState<CommandLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [days, setDays] = useState(30);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [statsRes, commandsRes] = await Promise.all([
          fetch(`/bot/stats?days=${days}`),
          fetch('/bot/commands/recent?limit=50'),
        ]);

        if (!statsRes.ok || !commandsRes.ok) {
          throw new Error('Failed to fetch bot stats');
        }

        const statsData = await statsRes.json();
        const commandsData = await commandsRes.json();

        setStats(statsData);
        setRecentCommands(commandsData);
        setError(null);
      } catch (err) {
        console.error(err);
        setError('Failed to load bot statistics');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, [days]);

  if (loading && !stats) {
    return <Loading label="Loading bot statistics..." />;
  }

  if (error) {
    return <ErrorState message={error} onRetry={() => window.location.reload()} />;
  }

  if (!stats) {
    return <ErrorState message="No data available" onRetry={() => window.location.reload()} />;
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Bot Statistics</h1>
        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
        >
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
        </select>
      </div>

      {/* Overview Cards */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        <Card title="Total Commands">
          <div className="text-4xl font-bold text-blue-600 dark:text-blue-400">
            {stats.total_commands.toLocaleString()}
          </div>
          <div className="text-sm text-slate-500 mt-1">Last {stats.period_days} days</div>
        </Card>

        <Card title="Unique Users">
          <div className="text-4xl font-bold text-green-600 dark:text-green-400">
            {stats.unique_users}
          </div>
          <div className="text-sm text-slate-500 mt-1">Active command users</div>
        </Card>

        <Card title="Rate Limited">
          <div className="text-4xl font-bold text-orange-600 dark:text-orange-400">
            {stats.rate_limited_count}
          </div>
          <div className="text-sm text-slate-500 mt-1">
            {stats.rate_limited_percentage.toFixed(1)}% of total
          </div>
        </Card>

        <Card title="Avg Per Day">
          <div className="text-4xl font-bold text-purple-600 dark:text-purple-400">
            {(stats.total_commands / stats.period_days).toFixed(0)}
          </div>
          <div className="text-sm text-slate-500 mt-1">Commands per day</div>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Top Commands */}
        <Card title="Top Commands" subtitle={`Most used commands (last ${stats.period_days} days)`}>
          <div className="space-y-2">
            {stats.top_commands.map((cmd, idx) => (
              <div key={cmd.command} className="flex items-center justify-between py-2 border-b border-slate-100 dark:border-slate-800 last:border-0">
                <div className="flex items-center gap-3">
                  <div className="text-lg font-semibold text-slate-400 dark:text-slate-600 w-6">
                    #{idx + 1}
                  </div>
                  <code className="text-sm font-mono bg-slate-100 dark:bg-slate-800 px-2 py-1 rounded">
                    {cmd.command}
                  </code>
                </div>
                <div className="text-lg font-bold text-slate-900 dark:text-white">
                  {cmd.count}
                </div>
              </div>
            ))}
            {stats.top_commands.length === 0 && (
              <div className="text-center py-8 text-slate-500">No commands recorded yet</div>
            )}
          </div>
        </Card>

        {/* Top Users */}
        <Card title="Top Users" subtitle={`Most active command users (last ${stats.period_days} days)`}>
          <div className="space-y-2">
            {stats.top_users.map((user, idx) => (
              <div key={user.user_id} className="flex items-center justify-between py-2 border-b border-slate-100 dark:border-slate-800 last:border-0">
                <div className="flex items-center gap-3">
                  <div className="text-lg font-semibold text-slate-400 dark:text-slate-600 w-6">
                    #{idx + 1}
                  </div>
                  <div>
                    <div className="font-medium text-slate-900 dark:text-white">
                      {user.username}
                    </div>
                    <div className="text-xs text-slate-500">
                      ID: {user.user_id.toString(16).padStart(8, '0')}
                    </div>
                  </div>
                </div>
                <div className="text-lg font-bold text-slate-900 dark:text-white">
                  {user.count}
                </div>
              </div>
            ))}
            {stats.top_users.length === 0 && (
              <div className="text-center py-8 text-slate-500">No users recorded yet</div>
            )}
          </div>
        </Card>
      </div>

      {/* Recent Commands Log */}
      <Card title="Recent Commands" subtitle="Last 50 command executions">
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="text-slate-500 border-b border-slate-200 dark:border-slate-700">
              <tr>
                <th className="py-2 text-left">Time</th>
                <th className="text-left">User</th>
                <th className="text-left">Command</th>
                <th className="text-left">Status</th>
              </tr>
            </thead>
            <tbody>
              {recentCommands.map((log) => (
                <tr key={log.id} className="border-t border-slate-100 dark:border-slate-800">
                  <td className="py-2 text-slate-700 dark:text-slate-300">
                    {formatDateTime(log.timestamp, timezone)}
                  </td>
                  <td className="text-slate-700 dark:text-slate-300">
                    <div className="font-medium">{log.username}</div>
                    <div className="text-xs text-slate-500">
                      {log.user_id.toString(16).padStart(8, '0')}
                    </div>
                  </td>
                  <td>
                    <code className="text-xs font-mono bg-slate-100 dark:bg-slate-800 px-2 py-1 rounded">
                      {log.command}
                    </code>
                  </td>
                  <td>
                    {log.rate_limited ? (
                      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-orange-100 dark:bg-orange-900 text-orange-800 dark:text-orange-200">
                        Rate Limited
                      </span>
                    ) : log.response_sent ? (
                      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200">
                        Success
                      </span>
                    ) : (
                      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200">
                        No Response
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {recentCommands.length === 0 && (
            <div className="text-center py-8 text-slate-500">No commands recorded yet</div>
          )}
        </div>
      </Card>
    </div>
  );
};

export default BotStats;


