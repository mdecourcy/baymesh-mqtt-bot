import { Card } from '@/components/common/Card';
import { Loading } from '@/components/common/Loading';
import { useEffect, useState } from 'react';
import { useAppContext } from '@/context/AppContext';

interface ComparisonData {
  today: {
    message_count: number;
    average_gateways: number;
    max_gateways: number;
  };
  yesterday: {
    message_count: number;
    average_gateways: number;
  };
  last_week: {
    message_count: number;
    average_gateways: number;
  };
  last_month: {
    message_count: number;
    average_gateways: number;
  };
  comparisons: {
    day_over_day: number;
    week_over_week: number;
    month_over_month: number;
    gateway_day_over_day: number;
  };
}

const formatPercentage = (value: number) => {
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(1)}%`;
};

const getChangeColor = (value: number) => {
  if (value > 0) return 'text-emerald-600 dark:text-emerald-400';
  if (value < 0) return 'text-red-600 dark:text-red-400';
  return 'text-slate-600 dark:text-slate-400';
};

const getChangeIcon = (value: number) => {
  if (value > 0) return '↑';
  if (value < 0) return '↓';
  return '→';
};

export const TrendComparisons = () => {
  const { apiBaseUrl, refreshRate } = useAppContext();
  const [data, setData] = useState<ComparisonData | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      const response = await fetch(`${apiBaseUrl}/stats/comparisons`);
      const result = await response.json();
      setData(result);
    } catch (error) {
      console.error('Failed to fetch comparison stats:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, refreshRate);
    return () => clearInterval(interval);
  }, [apiBaseUrl, refreshRate]);

  if (loading) return <Loading label="Loading trends..." />;
  if (!data) return null;

  const comparisons = [
    {
      label: 'vs Yesterday',
      value: data.comparisons.day_over_day,
      detail: `${data.yesterday.message_count} msgs`,
    },
    {
      label: 'vs Last Week',
      value: data.comparisons.week_over_week,
      detail: `${data.last_week.message_count} msgs`,
    },
    {
      label: 'vs Last Month',
      value: data.comparisons.month_over_month,
      detail: `${data.last_month.message_count} msgs`,
    },
  ];

  return (
    <Card title="Activity Trends">
      <div className="space-y-3">
        {comparisons.map((comp) => (
          <div key={comp.label} className="flex items-center justify-between py-2 border-b border-slate-100 dark:border-slate-800 last:border-0">
            <div>
              <div className="text-sm font-medium text-slate-700 dark:text-slate-300">
                {comp.label}
              </div>
              <div className="text-xs text-slate-500">{comp.detail}</div>
            </div>
            <div className={`text-lg font-bold ${getChangeColor(comp.value)}`}>
              {getChangeIcon(comp.value)} {formatPercentage(comp.value)}
            </div>
          </div>
        ))}
        
        <div className="pt-3 border-t border-slate-200 dark:border-slate-700">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-medium text-slate-700 dark:text-slate-300">
                Gateway Coverage
              </div>
              <div className="text-xs text-slate-500">
                Today: {data.today.average_gateways.toFixed(1)} · Yesterday: {data.yesterday.average_gateways.toFixed(1)}
              </div>
            </div>
            <div className={`text-lg font-bold ${getChangeColor(data.comparisons.gateway_day_over_day)}`}>
              {getChangeIcon(data.comparisons.gateway_day_over_day)} {formatPercentage(data.comparisons.gateway_day_over_day)}
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
};

