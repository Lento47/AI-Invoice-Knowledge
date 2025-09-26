const STORAGE_KEY = 'ai-invoice-portal.credentials';

export type StoredCredentials = {
  apiKey?: string;
  licenseToken?: string;
};

const normalize = (value: StoredCredentials): StoredCredentials => ({
  apiKey: value.apiKey?.trim() || undefined,
  licenseToken: value.licenseToken?.trim() || undefined
});

export const readStoredCredentials = (): StoredCredentials => {
  if (typeof window === 'undefined' || !window.localStorage) {
    return {};
  }
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as StoredCredentials;
    return normalize(parsed);
  } catch {
    return {};
  }
};

export const writeStoredCredentials = (value: StoredCredentials): StoredCredentials => {
  const normalized = normalize(value);
  if (typeof window !== 'undefined' && window.localStorage) {
    try {
      if (normalized.apiKey || normalized.licenseToken) {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(normalized));
      } else {
        window.localStorage.removeItem(STORAGE_KEY);
      }
    } catch {
      // Ignore storage errors (private mode, quotas, etc.)
    }
  }
  return normalized;
};

export const clearStoredCredentials = (): void => {
  if (typeof window !== 'undefined' && window.localStorage) {
    try {
      window.localStorage.removeItem(STORAGE_KEY);
    } catch {
      // ignore
    }
  }
};

export const credentialsStorageKey = STORAGE_KEY;
