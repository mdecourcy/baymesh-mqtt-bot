import type { Message } from '@/types/message';
import { Card } from '@/components/common/Card';
import { useMemo } from 'react';

interface ActiveGatewaysProps {
  messages: Message[];
}

export const ActiveGateways = ({ messages }: ActiveGatewaysProps) => {
  // This component would be more useful once we expose gateway IDs from the API
  // For now, we'll show a placeholder or generic stats
  
  const stats = useMemo(() => {
    const uniqueGateways = new Set<number>();
    messages.forEach((m) => {
      if (m.gateway_count > 0) {
        // In a real implementation, we'd track individual gateway IDs
        uniqueGateways.add(m.gateway_count);
      }
    });
    
    return {
      estimatedActive: messages.length > 0 ? Math.max(...messages.map((m) => m.gateway_count)) : 0,
      totalMessages: messages.length,
      avgGateways: messages.length > 0 
        ? messages.reduce((acc, m) => acc + m.gateway_count, 0) / messages.length 
        : 0,
    };
  }, [messages]);

  return (
    <Card title="Network Coverage">
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900/20 dark:to-blue-800/20 p-4 rounded-lg">
            <div className="text-3xl font-bold text-blue-600 dark:text-blue-400">
              {stats.estimatedActive}
            </div>
            <div className="text-xs text-blue-700 dark:text-blue-300 mt-1">
              Peak Gateway Count
            </div>
          </div>
          
          <div className="bg-gradient-to-br from-emerald-50 to-emerald-100 dark:from-emerald-900/20 dark:to-emerald-800/20 p-4 rounded-lg">
            <div className="text-3xl font-bold text-emerald-600 dark:text-emerald-400">
              {stats.avgGateways.toFixed(1)}
            </div>
            <div className="text-xs text-emerald-700 dark:text-emerald-300 mt-1">
              Avg Coverage
            </div>
          </div>
        </div>
        
        <div className="pt-4 border-t border-slate-200 dark:border-slate-700">
          <div className="text-sm text-slate-600 dark:text-slate-400">
            Network mesh density indicates strong regional coverage. Messages are being 
            relayed through {stats.estimatedActive}+ gateways on average.
          </div>
        </div>
      </div>
    </Card>
  );
};

