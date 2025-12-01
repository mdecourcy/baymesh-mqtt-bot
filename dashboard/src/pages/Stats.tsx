import { useEffect, useState } from 'react';
import { formatISO, subDays } from 'date-fns';
import { statsService } from '@/services/statsService';
import type { DailyStatsResponse } from '@/types/api';
import { DateRangeSelector } from '@/components/stats/DateRangeSelector';
import { GatewayTrend } from '@/components/stats/GatewayTrend';
import { StatisticsTable } from '@/components/stats/StatisticsTable';
import { Loading } from '@/components/common/Loading';
import { ErrorState } from '@/components/common/Error';

const Stats = () => {
  const now = new Date();
  const today = formatISO(now, { representation: 'date' });
  const weekAgo = formatISO(subDays(now, 6), { representation: 'date' });
  const [range, setRange] = useState({ startDate: weekAgo, endDate: today });
  const [data, setData] = useState<DailyStatsResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        const stats = await statsService.getStatsForRange(range.startDate, range.endDate);
        setData(stats);
        setError(null);
      } catch (err) {
        console.error(err);
        setError('Failed to load statistics for range');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [range]);

  if (error) {
    return <ErrorState message={error} onRetry={() => setRange({ ...range })} />;
  }

  return (
    <div className="space-y-6">
      <DateRangeSelector startDate={range.startDate} endDate={range.endDate} onChange={setRange} />
      {loading ? (
        <Loading label="Loading statistics..." />
      ) : (
        <>
          <GatewayTrend data={data} />
          <StatisticsTable data={data} />
        </>
      )}
    </div>
  );
};

export default Stats;
