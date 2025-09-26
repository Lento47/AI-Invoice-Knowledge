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
    <aside className="hidden w-64 flex-col border-r border-slate-200 bg-white/80 p-4 backdrop-blur dark:border-slate-800 dark:bg-slate-900/60 lg:flex">
      <div className="flex items-center gap-2 px-2 py-3 text-sm font-semibold tracking-wide text-slate-700 dark:text-slate-200">
        <span className="flex h-10 w-10 items-center justify-center rounded-full bg-indigoBrand/10 text-indigoBrand">
          AI
        </span>
        <span>Invoice Console</span>
      </div>
      <nav className="mt-6 flex-1 space-y-1 text-sm">
        {sections.map((section) => {
          const isActive = section.id === active;
          return (
            <button
              key={section.id}
              onClick={() => onSelect(section.id)}
              className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left transition ${
                isActive
                  ? 'bg-indigoBrand/10 font-semibold text-indigoBrand'
                  : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800'
              }`}
            >
              <span className={isActive ? 'text-indigoBrand' : 'text-slate-400'}>{navIcons[section.id]}</span>
              <span>{section.label}</span>
            </button>
          );
        })}
      </nav>
      <div className="mt-auto space-y-2 rounded-lg border border-slate-200 p-3 dark:border-slate-800">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
          Theme
        </p>
        <div className="flex gap-2">
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
              className={`flex-1 rounded-md border px-2 py-1 text-xs font-medium transition ${
                mode === option.id
                  ? 'border-indigoBrand bg-indigoBrand/10 text-indigoBrand'
                  : 'border-slate-200 text-slate-500 hover:border-slate-300 dark:border-slate-700 dark:text-slate-300'
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
        <ThemeToggle className="w-full" />
      </div>
    </aside>
  );
};
