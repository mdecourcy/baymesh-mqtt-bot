import type { Message } from '@/types/message';
import { Card } from '@/components/common/Card';
import { useMemo } from 'react';

interface GatewayDistributionProps {
  messages: Message[];
}

export const GatewayDistribution = ({ messages }: GatewayDistributionProps) => {
  const distribution = useMemo(() => {
    if (!messages.length) return [];
    
    const buckets = [
      { min: 0, max: 5, label: '0-5' },
      { min: 6, max: 10, label: '6-10' },
      { min: 11, max: 20, label: '11-20' },
      { min: 21, max: 40, label: '21-40' },
      { min: 41, max: 60, label: '41-60' },
      { min: 61, max: Infinity, label: '60+' },
    ];
    
    const counts = buckets.map((bucket) => ({
      range: bucket.label,
      count: messages.filter(
        (m) => m.gateway_count >= bucket.min && m.gateway_count <= bucket.max
      ).length,
      percentage: 0,
    }));
    
    const total = messages.length;
    counts.forEach((c) => {
      c.percentage = (c.count / total) * 100;
    });
    
    return counts;
  }, [messages]);
  
  const maxCount = Math.max(...distribution.map((b) => b.count), 1);

  return (
    <Card title="Gateway Distribution">
      <div className="space-y-3">
        {distribution.map((bucket) => (
          <div key={bucket.range}>
            <div className="flex justify-between text-sm mb-1">
              <span className="text-slate-700 dark:text-slate-300 font-medium">
                {bucket.range} gateways
              </span>
              <span className="text-slate-500">
                {bucket.count} ({bucket.percentage.toFixed(1)}%)
              </span>
            </div>
            <div className="w-full bg-slate-100 dark:bg-slate-800 rounded-full h-2">
              <div
                className="bg-gradient-to-r from-blue-500 to-emerald-500 h-2 rounded-full transition-all duration-300"
                style={{ width: `${(bucket.count / maxCount) * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
};

