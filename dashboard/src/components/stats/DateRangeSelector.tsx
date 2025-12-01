import { format } from 'date-fns';

interface DateRangeSelectorProps {
  startDate: string;
  endDate: string;
  onChange: (range: { startDate: string; endDate: string }) => void;
}

export const DateRangeSelector = ({ startDate, endDate, onChange }: DateRangeSelectorProps) => (
  <div className="flex flex-wrap items-end gap-4">
    <div>
      <label className="text-sm text-slate-500">Start date</label>
      <input
        type="date"
        value={startDate}
        max={format(new Date(endDate), 'yyyy-MM-dd')}
        onChange={(e) => onChange({ startDate: e.target.value, endDate })}
        className="mt-1 rounded-lg border border-slate-200 bg-white p-2 dark:bg-slate-900"
      />
    </div>
    <div>
      <label className="text-sm text-slate-500">End date</label>
      <input
        type="date"
        value={endDate}
        min={startDate}
        max={format(new Date(), 'yyyy-MM-dd')}
        onChange={(e) => onChange({ startDate, endDate: e.target.value })}
        className="mt-1 rounded-lg border border-slate-200 bg-white p-2 dark:bg-slate-900"
      />
    </div>
  </div>
);
