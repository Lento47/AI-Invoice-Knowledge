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
        'group relative overflow-hidden rounded-3xl border border-slate-200/70 bg-white/75 px-6 pb-6 pt-7 text-sm shadow-card backdrop-blur dark:border-slate-800/70 dark:bg-slate-900/60',
        "before:pointer-events-none before:absolute before:-right-16 before:-top-24 before:h-48 before:w-48 before:rounded-full before:bg-[radial-gradient(circle_at_50%_50%,rgba(63,81,181,0.32),rgba(63,81,181,0))] before:opacity-0 before:transition before:duration-500 before:content-[''] before:blur-3xl group-hover:before:opacity-60",
        "after:pointer-events-none after:absolute after:bottom-0 after:left-0 after:h-1 after:w-full after:bg-[linear-gradient(90deg,rgba(0,43,127,0.65),rgba(63,81,181,0.45),rgba(244,167,29,0.45),rgba(206,17,38,0.65))] after:content-['']",
        className
      )}
    >
      {(eyebrow || title || actions) && (
        <header className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            {eyebrow && (
              <p className="text-[11px] font-semibold uppercase tracking-[0.4em] text-indigoBrand">
                {eyebrow}
              </p>
            )}
            {title && <h2 className="mt-1 text-base font-semibold text-slate-800 dark:text-slate-100">{title}</h2>}
          </div>
          {actions}
        </header>
      )}
      <div className="relative z-10 text-sm text-slate-600 dark:text-slate-300">{children}</div>
    </section>
  );
};
