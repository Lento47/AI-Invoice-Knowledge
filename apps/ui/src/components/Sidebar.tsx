import { AppSectionKey } from '../App';
import { ThemeMode, useTheme } from '../hooks/useTheme';
import { ThemeToggle } from './ThemeToggle';

const navIcons: Record<AppSectionKey, JSX.Element> = {
  dashboard: (
    <svg viewBox="0 0 24 24" className="h-5 w-5" aria-hidden>
      <path
        d="M4 13h7V4H4v9zm0 7h7v-5H4v5zm9 0h7V11h-7v9zm0-16v5h7V4h-7z"
        fill="currentColor"
      />
    </svg>
  ),
  invoices: (
    <svg viewBox="0 0 24 24" className="h-5 w-5" aria-hidden>
      <path
        d="M7 4h10a2 2 0 0 1 2 2v13.5l-4-2-3 2-3-2-4 2V6a2 2 0 0 1 2-2zm2 4v2h6V8H9zm0 4v2h6v-2H9z"
        fill="currentColor"
      />
    </svg>
  ),
  vendors: (
    <svg viewBox="0 0 24 24" className="h-5 w-5" aria-hidden>
      <path
        d="M12 12a4 4 0 1 0-4-4 4 4 0 0 0 4 4zm0 2c-3.31 0-9 1.66-9 5v1h18v-1c0-3.34-5.69-5-9-5z"
        fill="currentColor"
      />
    </svg>
  ),
  reports: (
    <svg viewBox="0 0 24 24" className="h-5 w-5" aria-hidden>
      <path
        d="M5 3h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2zm3 6v10h2V9H8zm4 4v6h2v-6h-2zm4-3v9h2V10h-2z"
        fill="currentColor"
      />
    </svg>
  ),
  approvals: (
    <svg viewBox="0 0 24 24" className="h-5 w-5" aria-hidden>
      <path
        d="M9 16.17 5.83 13l-1.42 1.41L9 19l12-12-1.41-1.41L9 16.17z"
        fill="currentColor"
      />
    </svg>
  ),
  settings: (
    <svg viewBox="0 0 24 24" className="h-5 w-5" aria-hidden>
      <path
        d="M19.14 12.94a7.14 7.14 0 0 0 0-1.88l2.03-1.58-1.92-3.32-2.39.95a7.15 7.15 0 0 0-1.62-.94l-.36-2.54h-3.84l-.36 2.54a7.15 7.15 0 0 0-1.62.94l-2.39-.95-1.92 3.32 2.03 1.58a7.14 7.14 0 0 0 0 1.88L3.53 14.5l1.92 3.32 2.39-.95c.5.38 1.05.69 1.62.94l.36 2.54h3.84l.36-2.54c.57-.25 1.12-.56 1.62-.94l2.39.95 1.92-3.32-2.03-1.56zM12 14.5a2.5 2.5 0 1 1 2.5-2.5A2.5 2.5 0 0 1 12 14.5z"
        fill="currentColor"
      />
    </svg>
  )
};

type SidebarProps = {
  sections: Array<{ id: AppSectionKey; label: string }>;
  active: AppSectionKey;
  onSelect: (id: AppSectionKey) => void;
};

export const Sidebar = ({ sections, active, onSelect }: SidebarProps) => {
  const { mode, setMode } = useTheme();
  const handleModeChange = (value: ThemeMode) => () => setMode(value);

  return (
    <aside className="relative hidden w-72 flex-col overflow-hidden border-r border-slate-200/60 bg-white/70 px-5 pb-10 pt-6 backdrop-blur-xl dark:border-slate-800/60 dark:bg-slate-950/40 lg:flex">
      <div className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(circle_at_top,rgba(63,81,181,0.16),transparent_70%)] dark:bg-[radial-gradient(circle_at_top,rgba(0,43,127,0.28),transparent_75%)]" aria-hidden></div>
      <div className="pointer-events-none absolute inset-y-6 right-2 w-px rounded-full bg-gradient-to-b from-transparent via-white/50 to-transparent dark:via-slate-700/60" aria-hidden></div>
      <div className="rounded-2xl border border-white/60 bg-white/80 p-4 shadow-sm shadow-indigoBrand/10 dark:border-slate-700/60 dark:bg-slate-900/70">
        <p className="text-[10px] font-semibold uppercase tracking-[0.55em] text-crSun/80">Pura Vida</p>
        <p className="mt-2 text-lg font-semibold text-slate-800 dark:text-white">Aurora Invoices</p>
        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Costa Rica–crafted finance intelligence.</p>
      </div>
      <nav className="mt-8 flex-1 space-y-1.5 text-sm">
        {sections.map((section) => {
          const isActive = section.id === active;
          return (
            <button
              key={section.id}
              onClick={() => onSelect(section.id)}
              className={`group relative flex w-full items-center gap-3 rounded-xl px-4 py-3 text-left transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigoBrand/70 ${
                isActive
                  ? 'bg-white/90 font-semibold text-indigoBrand shadow-lg shadow-indigoBrand/10 dark:bg-slate-900/70 dark:text-white'
                  : 'text-slate-600 hover:bg-white/70 dark:text-slate-300 dark:hover:bg-slate-900/50'
              }`}
            >
              <span
                className={`flex h-9 w-9 items-center justify-center rounded-xl border border-transparent bg-white/70 text-slate-500 transition-colors dark:bg-slate-900/60 ${
                  isActive
                    ? 'border-indigoBrand/40 text-indigoBrand dark:border-indigoBrand/50'
                    : 'group-hover:text-indigoBrand'
                }`}
              >
                {navIcons[section.id]}
              </span>
              <span className="flex flex-1 items-center justify-between">
                <span>{section.label}</span>
                <span className="ml-3 h-1 w-6 rounded-full bg-gradient-to-r from-crBlue via-crSun to-crRed opacity-0 transition-opacity duration-300 group-hover:opacity-60" aria-hidden></span>
              </span>
            </button>
          );
        })}
      </nav>
      <div className="mt-10 space-y-3 rounded-2xl border border-slate-200/70 bg-white/70 p-4 text-xs shadow-sm dark:border-slate-800/70 dark:bg-slate-900/60">
        <div className="flex items-center justify-between">
          <p className="font-semibold uppercase tracking-[0.45em] text-slate-500 dark:text-slate-400">Theme</p>
          <span className="h-1 w-12 rounded-full bg-gradient-to-r from-crBlue via-white to-crRed" aria-hidden></span>
        </div>
        <p className="text-[11px] text-slate-500 dark:text-slate-400">
          Tune the console aura to match your workspace vibe.
        </p>
        <div className="grid grid-cols-3 gap-2 text-[11px] uppercase tracking-wide">
          {(
            [
              { id: 'light', label: 'Light' },
              { id: 'system', label: 'Auto' },
              { id: 'dark', label: 'Dark' }
            ] as Array<{ id: ThemeMode; label: string }>
          ).map((option) => (
            <button
              key={option.id}
              onClick={handleModeChange(option.id)}
              className={`rounded-lg border px-2 py-1.5 font-medium transition ${
                mode === option.id
                  ? 'border-indigoBrand/40 bg-indigoBrand/10 text-indigoBrand shadow-sm shadow-indigoBrand/10'
                  : 'border-slate-200 text-slate-500 hover:border-indigoBrand/30 dark:border-slate-700 dark:text-slate-300'
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
        <ThemeToggle className="w-full justify-between" />
      </div>
    </aside>
  );
};
