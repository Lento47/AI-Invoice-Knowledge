import { ThemeToggle } from './ThemeToggle';

type TopBarProps = {
  title: string;
  description: string;
};

export const TopBar = ({ title, description }: TopBarProps) => {
  return (
    <header className="relative z-20 border-b border-transparent bg-white/75 backdrop-blur-xl shadow-[0_1px_0_rgba(15,23,42,0.08)] dark:bg-slate-950/60">
      <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-crBlue via-crSun to-crRed opacity-70" aria-hidden></div>
      <div className="mx-auto flex max-w-6xl flex-col gap-4 px-6 py-6 sm:flex-row sm:items-center sm:justify-between sm:px-10">
        <div className="flex items-start gap-4">
          <span className="relative mt-1 flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-indigoBrand via-crBlue to-crSun text-xs font-bold uppercase tracking-[0.4em] text-white shadow-lg shadow-indigoBrand/30">
            AIK
            <span className="absolute -bottom-1 h-1 w-12 rounded-full bg-gradient-to-r from-crBlue via-white to-crRed" aria-hidden></span>
          </span>
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.45em] text-crSun/80">PuraFlow Insights</p>
            <h1 className="mt-1 text-2xl font-semibold text-slate-800 dark:text-slate-50">{title}</h1>
            <p className="mt-1 max-w-xl text-sm text-slate-500 dark:text-slate-400">{description}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="hidden text-[10px] font-semibold uppercase tracking-[0.45em] text-slate-400 dark:text-slate-500 sm:block">
            crafted uniquely for your team
          </span>
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
};
