import { LineChart, Line, CartesianGrid, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import type { HourlyStat } from '@/types/api';
import { Card } from '@/components/common/Card';
import { Loading } from '@/components/common/Loading';
import { useAppContext } from '@/context/AppContext';
import { useMemo } from 'react';

interface MessageChartProps {
  data: HourlyStat[];
  loading: boolean;
}

export const MessageChart = ({ data, loading }: MessageChartProps) => {
  const { timezone } = useAppContext();
  
  const chartData = useMemo(() => {
    if (timezone === 'local') {
      const offset = -new Date().getTimezoneOffset() / 60;
      return data.map((entry) => {
        const localHour = (entry.hour + offset + 24) % 24;
        return {
          ...entry,
          label: `${localHour.toString().padStart(2, '0')}:00`,
        };
      });
    }
    return data.map((entry) => ({ ...entry, label: `${entry.hour}:00` }));
  }, [data, timezone]);
  
  return (
  <Card title="Gateway Coverage Trend" subtitle={`Last 24 hours (${timezone})`}>
    {loading ? (
      <Loading label="Loading chart..." />
    ) : data.length === 0 ? (
      <div className="h-64 flex items-center justify-center text-slate-500">
        No data available yet
      </div>
    ) : (
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" className="dark:stroke-slate-700" />
            <XAxis 
              dataKey="label" 
              tick={{ fontSize: 12, fill: '#64748b' }} 
              stroke="#94a3b8"
            />
            <YAxis 
              tick={{ fontSize: 12, fill: '#64748b' }} 
              stroke="#94a3b8"
              label={{ value: 'Gateways', angle: -90, position: 'insideLeft', style: { fill: '#64748b' } }}
            />
            <Tooltip 
              contentStyle={{ 
                backgroundColor: '#1e293b', 
                border: 'none', 
                borderRadius: '0.5rem',
                color: '#f1f5f9'
              }}
            />
            <Line 
              type="monotone" 
              dataKey="average_gateways" 
              stroke="#3B82F6" 
              strokeWidth={3} 
              dot={false} 
              name="Average" 
            />
            <Line 
              type="monotone" 
              dataKey="max_gateways" 
              stroke="#10B981" 
              strokeWidth={2} 
              dot={false} 
              name="Peak" 
              strokeDasharray="5 5"
            />
            <Line 
              type="monotone" 
              dataKey="min_gateways" 
              stroke="#F59E0B" 
              strokeWidth={1.5} 
              dot={false} 
              name="Minimum" 
              strokeDasharray="3 3"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    )}
  </Card>
  );
};
