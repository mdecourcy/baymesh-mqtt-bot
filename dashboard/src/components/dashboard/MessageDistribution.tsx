import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import type { Message } from '@/types/message';
import { Card } from '@/components/common/Card';

const COLORS = ['#10B981', '#F59E0B', '#EF4444'];

const mapMessagesToDistribution = (messages: Message[]) => {
  const buckets = { low: 0, medium: 0, high: 0 };
  messages.forEach((msg) => {
    if (msg.gateway_count <= 2) buckets.low += 1;
    else if (msg.gateway_count <= 5) buckets.medium += 1;
    else buckets.high += 1;
  });
  return [
    { name: '1-2 gateways', value: buckets.low },
    { name: '3-5 gateways', value: buckets.medium },
    { name: '6+ gateways', value: buckets.high },
  ];
};

interface MessageDistributionProps {
  messages: Message[];
}

export const MessageDistribution = ({ messages }: MessageDistributionProps) => (
  <Card title="Gateway distribution" subtitle="Recent messages">
    <div className="h-64">
      <ResponsiveContainer>
        <PieChart>
          <Pie data={mapMessagesToDistribution(messages)} dataKey="value" nameKey="name" innerRadius={60} outerRadius={80} label>
            {mapMessagesToDistribution(messages).map((_, idx) => (
              <Cell key={`cell-${idx}`} fill={COLORS[idx % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip />
        </PieChart>
      </ResponsiveContainer>
    </div>
  </Card>
);
