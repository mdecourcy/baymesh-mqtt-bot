import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import type { DailyStatsResponse } from '@/types/api';
import { Card } from '@/components/common/Card';

interface GatewayTrendProps {
  data: DailyStatsResponse[];
}

export const GatewayTrend = ({ data }: GatewayTrendProps) => {
  // Filter out days with no messages to avoid showing empty charts
  const filteredData = data.filter(d => d.message_count > 0);
  
  if (filteredData.length === 0) {
    return (
      <Card title="Average gateways over time">
        <div className="h-72 flex items-center justify-center text-slate-500">
          No data available for the selected date range
        </div>
      </Card>
    );
  }
  
  return (
    <Card title="Average gateways over time">
      <div className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={filteredData.map((d) => ({ ...d, label: d.date }))}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
            <XAxis dataKey="label" />
            <YAxis />
            <Tooltip />
            <Line type="monotone" dataKey="average_gateways" stroke="#3B82F6" strokeWidth={2} dot />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
};
