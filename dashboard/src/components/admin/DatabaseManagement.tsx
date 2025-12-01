import { useState, useEffect } from 'react';
import { Card } from '@/components/common/Card';
import { adminService, type DatabaseInfo } from '@/services/adminService';

export const DatabaseManagement = () => {
  const [dbInfo, setDbInfo] = useState<DatabaseInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expireDays, setExpireDays] = useState<number>(90);
  const [expiring, setExpiring] = useState(false);
  const [expireResult, setExpireResult] = useState<string | null>(null);

  const fetchDatabaseInfo = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await adminService.getDatabaseInfo();
      setDbInfo(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch database info');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDatabaseInfo();
  }, []);

  const handleExpireData = async () => {
    if (!expireDays || expireDays < 1) {
      setExpireResult('Please enter a valid number of days (minimum 1)');
      return;
    }

    if (!confirm(`Are you sure you want to delete all data older than ${expireDays} days? This action cannot be undone.`)) {
      return;
    }

    try {
      setExpiring(true);
      setExpireResult(null);
      const result = await adminService.expireOldData(expireDays);
      setExpireResult(
        `Successfully deleted: ${result.deleted.messages} messages, ${result.deleted.cache_entries} cache entries, ${result.deleted.command_logs} command logs`
      );
      // Refresh database info after deletion
      await fetchDatabaseInfo();
    } catch (err) {
      setExpireResult(err instanceof Error ? err.message : 'Failed to expire old data');
    } finally {
      setExpiring(false);
    }
  };

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
  };

  const formatDate = (isoString: string | null): string => {
    if (!isoString) return 'N/A';
    return new Date(isoString).toLocaleString();
  };

  return (
    <Card
      title="Database management"
      action={
        <button onClick={fetchDatabaseInfo} disabled={loading} className="text-sm text-primary">
          Refresh
        </button>
      }
    >
      {loading ? (
        <p>Loading database information...</p>
      ) : error ? (
        <p className="text-red-500">{error}</p>
      ) : dbInfo ? (
        <div className="space-y-6">
          {/* Database size section */}
          <div>
            <h3 className="text-lg font-semibold mb-3">Database size</h3>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <p className="text-sm text-slate-500">Size</p>
                <p className="text-2xl font-bold">{dbInfo.size_mb} MB</p>
                <p className="text-xs text-slate-400">{formatBytes(dbInfo.size_bytes)}</p>
              </div>
              <div>
                <p className="text-sm text-slate-500">Total records</p>
                <p className="text-2xl font-bold">{dbInfo.records.total.toLocaleString()}</p>
              </div>
            </div>
          </div>

          {/* Record counts section */}
          <div>
            <h3 className="text-lg font-semibold mb-3">Record counts</h3>
            <div className="grid gap-3 md:grid-cols-3">
              <div>
                <p className="text-sm text-slate-500">Messages</p>
                <p className="text-lg font-semibold">{dbInfo.records.messages.toLocaleString()}</p>
              </div>
              <div>
                <p className="text-sm text-slate-500">Users</p>
                <p className="text-lg font-semibold">{dbInfo.records.users.toLocaleString()}</p>
              </div>
              <div>
                <p className="text-sm text-slate-500">Gateways</p>
                <p className="text-lg font-semibold">{dbInfo.records.gateways.toLocaleString()}</p>
              </div>
              <div>
                <p className="text-sm text-slate-500">Subscriptions</p>
                <p className="text-lg font-semibold">{dbInfo.records.subscriptions.toLocaleString()}</p>
              </div>
              <div>
                <p className="text-sm text-slate-500">Cache entries</p>
                <p className="text-lg font-semibold">{dbInfo.records.cache.toLocaleString()}</p>
              </div>
              <div>
                <p className="text-sm text-slate-500">Command logs</p>
                <p className="text-lg font-semibold">{dbInfo.records.command_logs.toLocaleString()}</p>
              </div>
            </div>
          </div>

          {/* Date range section */}
          <div>
            <h3 className="text-lg font-semibold mb-3">Data range</h3>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <p className="text-sm text-slate-500">Oldest message</p>
                <p className="text-sm">{formatDate(dbInfo.date_range.oldest)}</p>
              </div>
              <div>
                <p className="text-sm text-slate-500">Newest message</p>
                <p className="text-sm">{formatDate(dbInfo.date_range.newest)}</p>
              </div>
            </div>
          </div>

          {/* Expire old data section */}
          <div className="border-t border-slate-200 pt-6">
            <h3 className="text-lg font-semibold mb-3">Expire old data</h3>
            <p className="text-sm text-slate-500 mb-4">
              Delete messages, cache entries, and command logs older than a specified number of days.
            </p>
            <div className="flex gap-3 items-start">
              <div className="flex-1 max-w-xs">
                <label htmlFor="expire-days" className="block text-sm font-medium text-slate-700 mb-1">
                  Delete data older than (days)
                </label>
                <input
                  id="expire-days"
                  type="number"
                  min="1"
                  max="3650"
                  value={expireDays}
                  onChange={(e) => setExpireDays(parseInt(e.target.value) || 0)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
              <div className="pt-7">
                <button
                  onClick={handleExpireData}
                  disabled={expiring || !expireDays}
                  className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:bg-slate-300 disabled:cursor-not-allowed"
                >
                  {expiring ? 'Deleting...' : 'Delete old data'}
                </button>
              </div>
            </div>
            {expireResult && (
              <div className={`mt-3 p-3 rounded-md text-sm ${
                expireResult.startsWith('Successfully')
                  ? 'bg-green-50 text-green-800'
                  : 'bg-red-50 text-red-800'
              }`}>
                {expireResult}
              </div>
            )}
          </div>
        </div>
      ) : (
        <p className="text-slate-500">No database information available.</p>
      )}
    </Card>
  );
};
