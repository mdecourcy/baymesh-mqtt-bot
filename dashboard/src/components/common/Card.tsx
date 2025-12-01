import type { ReactNode } from 'react';
import clsx from 'clsx';

interface CardProps {
  title?: string;
  subtitle?: string;
  icon?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}

export const Card = ({ title, subtitle, icon, action, children, className }: CardProps) => (
  <section className={clsx('rounded-2xl bg-white p-6 shadow-card ring-1 ring-slate-100 dark:bg-slate-800 dark:ring-slate-700', className)}>
    {(title || action) && (
      <header className="mb-4 flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-slate-600 dark:text-slate-300">
            {icon}
            {subtitle && <p className="text-sm uppercase tracking-wide">{subtitle}</p>}
          </div>
          {title && <h3 className="text-xl font-semibold text-slate-900 dark:text-white">{title}</h3>}
        </div>
        {action}
      </header>
    )}
    <div>{children}</div>
  </section>
);
