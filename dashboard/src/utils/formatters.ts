import { parseISO } from 'date-fns';
import { formatInTimeZone } from 'date-fns-tz';

export const formatDateTime = (value?: string, timezone: 'UTC' | 'local' = 'UTC') => {
  if (!value) return 'N/A';
  
  try {
    const date = parseISO(value);
    
    if (timezone === 'local') {
      // Convert to local timezone
      const localTz = Intl.DateTimeFormat().resolvedOptions().timeZone;
      return formatInTimeZone(date, localTz, 'PPpp');
    }
    
    // Display as UTC - explicitly format in UTC timezone
    return formatInTimeZone(date, 'UTC', 'PPpp') + ' UTC';
  } catch {
    return 'Invalid date';
  }
};

export const formatNumber = (value: number, decimals = 0) =>
  new Intl.NumberFormat(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals }).format(value);

export const formatStatusColor = (status: string) => {
  switch (status) {
    case 'ok':
      return 'text-success';
    case 'warning':
      return 'text-warning';
    default:
      return 'text-danger';
  }
};
