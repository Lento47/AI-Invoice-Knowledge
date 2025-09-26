import { ThemeToggle } from './ThemeToggle';

type TopBarProps = {
  title: string;
  description: string;
};

export const TopBar = ({ title, description }: TopBarProps) => {
  return (
    <header className="border-b border-slate-200 bg-white/70 backdrop-blur dark:border-slate-800 dark:bg-slate-900/60">
      <div className="h-1 w-full bg-gradient-to-r from-crBlue via-white to-crRed" aria-hidden></div>
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5 sm:px-10">
        <div>
          <h1 className="text-lg font-semibold text-slate-800 dark:text-slate-100">{title}</h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{description}</p>
        </div>
        <div className="hidden sm:block">
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
};
