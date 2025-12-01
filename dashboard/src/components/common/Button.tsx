import clsx from 'clsx';
import type { ButtonHTMLAttributes } from 'react';

const baseStyles = 'inline-flex items-center justify-center rounded-lg font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed';
const variants: Record<string, string> = {
  primary: 'bg-primary text-white hover:bg-primary/90 focus:ring-primary',
  secondary: 'bg-slate-100 text-slate-800 hover:bg-slate-200 focus:ring-slate-300 dark:bg-slate-700 dark:text-white dark:hover:bg-slate-600',
  danger: 'bg-danger text-white hover:bg-danger/90 focus:ring-danger',
};
const sizes: Record<string, string> = {
  sm: 'px-3 py-1.5 text-sm',
  md: 'px-4 py-2 text-base',
  lg: 'px-6 py-3 text-lg',
};

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: keyof typeof variants;
  size?: keyof typeof sizes;
  loading?: boolean;
}

export const Button = ({ variant = 'primary', size = 'md', loading, className, children, ...props }: ButtonProps) => (
  <button className={clsx(baseStyles, variants[variant], sizes[size], className)} disabled={loading || props.disabled} {...props}>
    {loading ? 'Loading...' : children}
  </button>
);
