import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import type { HourlyStat } from '@/types/api';
import { Card } from '@/components/common/Card';
import { useAppContext } from '@/context/AppContext';
import { useMemo } from 'react';

interface HourlyBreakdownProps {
  data: HourlyStat[];
}

export const HourlyBreakdown = ({ data }: HourlyBreakdownProps) => {
  const { timezone } = useAppContext();
  
  const chartData = useMemo(() => {
    if (timezone === 'local') {
      // Convert UTC hours to local timezone hours
      const offset = -new Date().getTimezoneOffset() / 60; // Offset in hours
      
      return data.map((entry) => {
        const localHour = (entry.hour + offset + 24) % 24;
        return {
          label: `${localHour.toString().padStart(2, '0')}:00`,
          message_count: entry.message_count,
        };
      });
    }
    
    return data.map((entry) => ({
      label: `${entry.hour.toString().padStart(2, '0')}:00`,
      message_count: entry.message_count,
    }));
  }, [data, timezone]);
  
  return (
    <Card title="Message volume by hour" subtitle={`Count of messages per hour (${timezone})`}>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData}>
            <XAxis dataKey="label" tick={{ fontSize: 12 }} interval={2} />
            <YAxis />
            <Tooltip />
            <Bar dataKey="message_count" fill="#3B82F6" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
};
