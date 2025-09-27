import { clsx } from 'clsx';
import { useTheme } from '../hooks/useTheme';

type ThemeToggleProps = {
  className?: string;
};

export const ThemeToggle = ({ className }: ThemeToggleProps) => {
  const { mode, setMode } = useTheme();
  const order: Array<'light' | 'dark' | 'system'> = ['light', 'dark', 'system'];
  const nextMode = order[(order.indexOf(mode) + 1) % order.length];
  const labelMap: Record<typeof order[number], string> = {
    light: 'LIGHT',
    dark: 'DARK',
    system: 'AUTO'
  };
  const icon = mode === 'dark' ? '🌙' : mode === 'light' ? '☀️' : '🌤️';

  return (
    <button
      onClick={() => setMode(nextMode)}
      className={clsx(
        'group relative inline-flex items-center gap-3 rounded-full border border-indigoBrand/20 bg-white/75 px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.38em] text-slate-600 shadow-[0_18px_45px_-35px_rgba(0,43,127,0.9)] transition duration-300 hover:border-indigoBrand/40 hover:text-indigoBrand dark:border-slate-700/60 dark:bg-slate-900/70 dark:text-slate-200 dark:hover:border-crSun/40 dark:hover:text-crSun',
        className
      )}
    >
      <span className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-indigoBrand via-crBlue to-crSun text-base text-white shadow-inner shadow-indigoBrand/30">
        <span aria-hidden>{icon}</span>
      </span>
      <span className="flex items-center gap-2">
        <span>{labelMap[mode]}</span>
        <span className="h-1 w-8 rounded-full bg-gradient-to-r from-crBlue via-white to-crRed opacity-70 transition group-hover:opacity-100" aria-hidden></span>
      </span>
    </button>
  );
};
