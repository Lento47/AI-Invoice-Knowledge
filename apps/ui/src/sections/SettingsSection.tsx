import { type FormEvent, useEffect, useMemo, useState } from 'react';
import { Card } from '../components/Card';
import { useCredentials } from '../hooks/useCredentials';
import { ThemeMode, useTheme } from '../hooks/useTheme';
import { accentSwatches, settingToggles } from '../data/settings';

export const SettingsSection = () => {
  const { mode, setMode, effectiveTheme } = useTheme();
  const { credentials, setCredentials, clearCredentials } = useCredentials();
  const [apiKeyInput, setApiKeyInput] = useState(credentials.apiKey ?? '');
  const [licenseInput, setLicenseInput] = useState(credentials.licenseToken ?? '');
  const [feedback, setFeedback] = useState<'idle' | 'saved' | 'cleared'>('idle');

  useEffect(() => {
    setApiKeyInput(credentials.apiKey ?? '');
    setLicenseInput(credentials.licenseToken ?? '');
  }, [credentials]);

  useEffect(() => {
    if (feedback === 'idle' || typeof window === 'undefined') {
      return;
    }
    const timer = window.setTimeout(() => setFeedback('idle'), 4000);
    return () => window.clearTimeout(timer);
  }, [feedback]);

  const hasStoredCredentials = Boolean(credentials.apiKey || credentials.licenseToken);

  const { baseDisplay, baseDescription } = useMemo(() => {
    const envBase = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim();
    if (envBase) {
      return {
        baseDisplay: envBase,
        baseDescription: 'Configured via VITE_API_BASE_URL. Update your .env file to point at a different FastAPI host.'
      };
    }
    if (typeof window !== 'undefined') {
      return {
        baseDisplay: `${window.location.origin} (relative)`,
        baseDescription:
          'No VITE_API_BASE_URL supplied. Requests default to relative paths on the same host as this UI.'
      };
    }
    return {
      baseDisplay: 'Relative to current origin',
      baseDescription: 'Requests default to relative paths on the same host as this UI.'
    };
  }, []);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setCredentials({ apiKey: apiKeyInput, licenseToken: licenseInput });
    setFeedback(apiKeyInput || licenseInput ? 'saved' : 'cleared');
  };

  const handleClear = () => {
    setApiKeyInput('');
    setLicenseInput('');
    clearCredentials();
    setFeedback('cleared');
  };

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Card title="API access" eyebrow="Backend connection" className="lg:col-span-2">
        <form onSubmit={handleSubmit} className="space-y-4">
          <p>
            Provide the credentials issued for your workspace so the console can authenticate with the FastAPI service. They stay
            in this browser only and can be cleared at any time.
          </p>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
              API key
            </label>
            <input
              type="password"
              autoComplete="off"
              value={apiKeyInput}
              onChange={(event) => {
                setApiKeyInput(event.target.value);
                setFeedback('idle');
              }}
              placeholder="X-API-Key header"
              className="mt-1 w-full rounded-xl border border-slate-200 bg-white/90 px-3 py-2 text-sm text-slate-700 shadow-sm focus:border-indigoBrand focus:outline-none focus:ring-2 focus:ring-indigoBrand/40 dark:border-slate-700 dark:bg-slate-900/70 dark:text-slate-100"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
              License token
            </label>
            <input
              type="password"
              autoComplete="off"
              value={licenseInput}
              onChange={(event) => {
                setLicenseInput(event.target.value);
                setFeedback('idle');
              }}
              placeholder="X-License header"
              className="mt-1 w-full rounded-xl border border-slate-200 bg-white/90 px-3 py-2 text-sm text-slate-700 shadow-sm focus:border-indigoBrand focus:outline-none focus:ring-2 focus:ring-indigoBrand/40 dark:border-slate-700 dark:bg-slate-900/70 dark:text-slate-100"
            />
          </div>

          <div className="flex flex-wrap gap-3">
            <button
              type="submit"
              className="rounded-full bg-indigoBrand px-4 py-2 text-sm font-semibold text-white transition hover:bg-indigoBrand/90 focus:outline-none focus:ring-2 focus:ring-indigoBrand/40 disabled:cursor-not-allowed disabled:bg-indigoBrand/50"
            >
              Save credentials
            </button>
            <button
              type="button"
              onClick={handleClear}
              disabled={!hasStoredCredentials && !apiKeyInput && !licenseInput}
              className="rounded-full border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-600 transition hover:border-slate-400 hover:text-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-300 disabled:cursor-not-allowed disabled:border-slate-200 disabled:text-slate-400 dark:border-slate-700 dark:text-slate-300 dark:hover:border-slate-500 dark:hover:text-white"
            >
              Clear
            </button>
          </div>

          <div className="space-y-1 text-xs text-slate-500 dark:text-slate-400">
            <p>
              API base URL: <code className="rounded bg-slate-200 px-1 py-0.5 text-[0.7rem] dark:bg-slate-800">{baseDisplay}</code>
            </p>
            <p>{baseDescription}</p>
            {feedback === 'saved' && (
              <p className="font-semibold text-crGreen dark:text-crGreen">Credentials saved. New requests will include them automatically.</p>
            )}
            {feedback === 'cleared' && (
              <p className="font-semibold text-slate-600 dark:text-slate-300">Stored credentials removed for this browser.</p>
            )}
          </div>
        </form>
      </Card>

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
