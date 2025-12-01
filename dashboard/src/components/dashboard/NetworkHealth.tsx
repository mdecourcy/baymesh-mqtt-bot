import type { Message } from '@/types/message';
import type { DailyStatsResponse } from '@/types/api';
import { Card } from '@/components/common/Card';
import { useMemo } from 'react';

interface NetworkHealthProps {
  messages: Message[];
  todayStats: DailyStatsResponse | null;
}

export const NetworkHealth = ({ messages, todayStats }: NetworkHealthProps) => {
  const recentMessages = useMemo(() => {
    const now = new Date();
    const oneHourAgo = new Date(now.getTime() - 60 * 60 * 1000);
    return messages.filter((m) => new Date(m.timestamp) > oneHourAgo);
  }, [messages]);
  
  const avgGatewaysRecent = useMemo(() => {
    if (!recentMessages.length) return 0;
    const sum = recentMessages.reduce((acc, m) => acc + m.gateway_count, 0);
    return sum / recentMessages.length;
  }, [recentMessages]);
  
  const uniqueSendersRecent = useMemo(() => {
    const senders = new Set(recentMessages.map((m) => m.sender_user_id || m.sender_name));
    return senders.size;
  }, [recentMessages]);
  
  // Calculate baseline from all messages (historical average)
  const historicalAvgGateways = useMemo(() => {
    if (!messages.length) return 0;
    const sum = messages.reduce((acc, m) => acc + m.gateway_count, 0);
    return sum / messages.length;
  }, [messages]);
  
  const historicalMsgPerHour = useMemo(() => {
    if (!messages.length || !todayStats) return 0;
    // Estimate messages per hour from today's total
    const hoursElapsed = new Date().getHours() + 1; // +1 to avoid division by zero
    return todayStats.message_count / hoursElapsed;
  }, [messages.length, todayStats]);
  
  const healthScore = useMemo(() => {
    // Score based on comparison to historical performance
    if (!recentMessages.length) return 0;
    
    // Activity score: compare recent message rate to historical average
    // Use sigmoid curve for smooth scaling: score = 100 / (1 + e^(-k*(x-1)))
    const activityRatio = historicalMsgPerHour > 0 
      ? recentMessages.length / historicalMsgPerHour 
      : 1;
    const activityScore = 100 / (1 + Math.exp(-3 * (activityRatio - 1)));
    
    // Gateway score: compare recent gateway coverage to historical average
    const gatewayRatio = historicalAvgGateways > 0 
      ? avgGatewaysRecent / historicalAvgGateways 
      : 1;
    const gatewayScore = 100 / (1 + Math.exp(-3 * (gatewayRatio - 1)));
    
    // Weighted average: 60% activity, 40% gateway coverage
    return Math.round(activityScore * 0.6 + gatewayScore * 0.4);
  }, [recentMessages.length, avgGatewaysRecent, historicalMsgPerHour, historicalAvgGateways]);
  
  const getHealthColor = (score: number) => {
    if (score >= 80) return 'text-emerald-600 dark:text-emerald-400';
    if (score >= 60) return 'text-blue-600 dark:text-blue-400';
    if (score >= 40) return 'text-yellow-600 dark:text-yellow-400';
    if (score >= 20) return 'text-orange-600 dark:text-orange-400';
    return 'text-red-600 dark:text-red-400';
  };
  
  const getHealthLabel = (score: number) => {
    if (score >= 80) return 'Excellent';
    if (score >= 60) return 'Above Average';
    if (score >= 40) return 'Average';
    if (score >= 20) return 'Below Average';
    return 'Poor';
  };

  return (
    <Card title="Network Activity (Last Hour)">
      <div className="space-y-4">
        <div className="text-center">
          <div className={`text-5xl font-bold ${getHealthColor(healthScore)}`}>
            {healthScore}
          </div>
          <div className="text-sm text-slate-500 mt-1">
            {getHealthLabel(healthScore)}
          </div>
        </div>
        
        <div className="grid grid-cols-2 gap-4 pt-4 border-t border-slate-200 dark:border-slate-700">
          <div>
            <div className="text-2xl font-semibold text-slate-900 dark:text-white">
              {recentMessages.length}
            </div>
            <div className="text-xs text-slate-500">Messages</div>
          </div>
          
          <div>
            <div className="text-2xl font-semibold text-slate-900 dark:text-white">
              {uniqueSendersRecent}
            </div>
            <div className="text-xs text-slate-500">Active Nodes</div>
          </div>
          
          <div>
            <div className="text-2xl font-semibold text-slate-900 dark:text-white">
              {avgGatewaysRecent.toFixed(1)}
            </div>
            <div className="text-xs text-slate-500">Avg Gateways</div>
          </div>
          
          <div>
            <div className="text-2xl font-semibold text-slate-900 dark:text-white">
              {todayStats?.message_count ?? 0}
            </div>
            <div className="text-xs text-slate-500">Total Today</div>
          </div>
        </div>
      </div>
    </Card>
  );
};

