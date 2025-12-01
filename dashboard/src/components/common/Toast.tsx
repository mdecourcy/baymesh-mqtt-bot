import clsx from 'clsx';

interface ToastProps {
  message: string;
  type?: 'success' | 'error' | 'info';
}

export const Toast = ({ message, type = 'info' }: ToastProps) => (
  <div className={clsx('rounded-xl px-4 py-3 text-sm shadow-lg ring-1', {
    'bg-success/10 text-success ring-success/40': type === 'success',
    'bg-danger/10 text-danger ring-danger/40': type === 'error',
    'bg-primary/10 text-primary ring-primary/40': type === 'info',
  })}
  >
    {message}
  </div>
);
