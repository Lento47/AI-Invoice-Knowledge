import { clsx } from 'clsx';
import { PropsWithChildren } from 'react';

type CardProps = PropsWithChildren<{
  title?: string;
  eyebrow?: string;
  actions?: React.ReactNode;
  className?: string;
}>;

export const Card = ({ title, eyebrow, actions, children, className }: CardProps) => {
  return (
    <section
      className={clsx(
        'rounded-2xl border border-slate-200 bg-white/80 p-5 shadow-card backdrop-blur dark:border-slate-800 dark:bg-slate-900/60',
        className
      )}
    >
      {(eyebrow || title || actions) && (
        <header className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            {eyebrow && <p className="text-xs font-semibold uppercase tracking-wide text-indigoBrand">{eyebrow}</p>}
            {title && <h2 className="mt-1 text-base font-semibold text-slate-800 dark:text-slate-100">{title}</h2>}
          </div>
          {actions}
        </header>
      )}
      <div className="text-sm text-slate-600 dark:text-slate-300">{children}</div>
    </section>
  );
};
