import { Card } from '../components/Card';
import { ThemeMode, useTheme } from '../hooks/useTheme';
import { accentSwatches, settingToggles } from '../data/mockData';

export const SettingsSection = () => {
  const { mode, setMode, effectiveTheme } = useTheme();

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Card title="Appearance" eyebrow="Personalize">
        <p className="text-sm">
          Choose between light, dark, or match the system setting. Preferences persist across sessions.
        </p>
        <div className="mt-4 flex gap-3">
          {(
            [
              { id: 'light', label: 'Light' },
              { id: 'system', label: 'Auto' },
              { id: 'dark', label: 'Dark' }
            ] as Array<{ id: ThemeMode; label: string }>
          ).map((option) => (
            <button
              key={option.id}
              onClick={() => setMode(option.id)}
              className={`flex-1 rounded-2xl border px-4 py-3 text-sm font-semibold transition ${
                mode === option.id
                  ? 'border-indigoBrand bg-indigoBrand/10 text-indigoBrand'
                  : 'border-slate-200 text-slate-500 hover:border-indigoBrand/40 dark:border-slate-700 dark:text-slate-300'
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
        <p className="mt-4 text-xs text-slate-500 dark:text-slate-400">
          Currently displaying in <span className="font-semibold text-indigoBrand">{effectiveTheme}</span> theme.
        </p>
      </Card>

      <Card title="Notification rules" eyebrow="Automation">
        <div className="space-y-4">
          {settingToggles.map((toggle) => (
            <label
              key={toggle.id}
              className="flex cursor-pointer items-start gap-3 rounded-2xl border border-slate-200/80 bg-white/70 p-4 transition hover:border-indigoBrand/60 dark:border-slate-800/80 dark:bg-slate-900/40"
            >
              <input type="checkbox" defaultChecked className="mt-1 h-4 w-4 rounded border-slate-300 text-indigoBrand focus:ring-indigoBrand" />
              <div>
                <p className="text-sm font-semibold text-slate-700 dark:text-slate-200">{toggle.label}</p>
                <p className="text-xs text-slate-500 dark:text-slate-400">{toggle.description}</p>
              </div>
            </label>
          ))}
        </div>
      </Card>

      <Card title="Accent palette" eyebrow="Costa Rica inspired" className="lg:col-span-2">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {accentSwatches.map((swatch) => (
            <div
              key={swatch.id}
              className="flex flex-col items-center gap-3 rounded-2xl border border-slate-200/80 bg-white/70 p-4 dark:border-slate-800/80 dark:bg-slate-900/40"
            >
              <span className="h-16 w-16 rounded-full shadow-inner" style={{ backgroundColor: swatch.value }} aria-hidden></span>
              <div className="text-center text-sm font-semibold text-slate-700 dark:text-slate-200">{swatch.label}</div>
              <div className="text-xs text-slate-500 dark:text-slate-400">{swatch.value}</div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
};
