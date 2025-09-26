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
    light: 'Light mode',
    dark: 'Dark mode',
    system: 'Match system'
  };

  return (
    <button
      onClick={() => setMode(nextMode)}
      className={clsx(
        'inline-flex items-center justify-center gap-2 rounded-md border border-slate-200 px-3 py-2 text-sm font-medium text-slate-600 transition hover:border-indigoBrand hover:text-indigoBrand dark:border-slate-700 dark:text-slate-300 dark:hover:border-indigoBrand dark:hover:text-indigoBrand',
        className
      )}
    >
      <span className="flex h-5 w-5 items-center justify-center">
        {mode === 'dark' ? (
          <span aria-hidden className="text-base">🌙</span>
        ) : mode === 'light' ? (
          <span aria-hidden className="text-base">☀️</span>
        ) : (
          <span aria-hidden className="text-base">🌓</span>
        )}
      </span>
      <span className="text-xs uppercase tracking-wide">{labelMap[mode]}</span>
    </button>
  );
};
