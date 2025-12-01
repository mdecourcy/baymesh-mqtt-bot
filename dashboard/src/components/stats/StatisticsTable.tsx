import type { DailyStatsResponse } from '@/types/api';
import { formatNumber } from '@/utils/formatters';
import { Card } from '@/components/common/Card';

interface StatisticsTableProps {
  data: DailyStatsResponse[];
}

export const StatisticsTable = ({ data }: StatisticsTableProps) => {
  // Filter out days with no messages
  const filteredData = data.filter(d => d.message_count > 0);
  
  if (filteredData.length === 0) {
    return (
      <Card title="Daily breakdown">
        <div className="p-8 text-center text-slate-500">
          No data available for the selected date range
        </div>
      </Card>
    );
  }
  
  return (
    <Card title="Daily breakdown">
      <div className="overflow-auto">
        <table className="min-w-full text-sm">
          <thead className="text-slate-500">
            <tr>
              <th className="py-2 text-left">Date</th>
              <th className="text-left">Avg</th>
              <th className="text-left">High</th>
              <th className="text-left">Low</th>
              <th className="text-left">Messages</th>
            </tr>
          </thead>
          <tbody>
            {filteredData.map((row) => (
              <tr key={row.date} className="border-t border-slate-100 text-slate-700 dark:border-slate-800 dark:text-slate-200">
                <td className="py-2">{row.date}</td>
                <td>{formatNumber(row.average_gateways, 1)}</td>
                <td>{row.max_gateways}</td>
                <td>{row.min_gateways}</td>
                <td>{row.message_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
};
