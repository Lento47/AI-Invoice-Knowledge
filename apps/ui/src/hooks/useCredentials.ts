import { useCallback, useEffect, useState } from 'react';
import {
  StoredCredentials,
  clearStoredCredentials,
  credentialsStorageKey,
  readStoredCredentials,
  writeStoredCredentials
} from '../lib/credentials';

type CredentialsState = StoredCredentials;

type CredentialsHook = {
  credentials: CredentialsState;
  setCredentials: (next: StoredCredentials) => void;
  clearCredentials: () => void;
};

export const useCredentials = (): CredentialsHook => {
  const [credentials, setCredentialsState] = useState<CredentialsState>(() => readStoredCredentials());

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    const handleStorage = (event: StorageEvent) => {
      if (event.key === credentialsStorageKey) {
        setCredentialsState(readStoredCredentials());
      }
    };

    window.addEventListener('storage', handleStorage);
    return () => {
      window.removeEventListener('storage', handleStorage);
    };
  }, []);

  const setCredentials = useCallback((next: StoredCredentials) => {
    const normalized = writeStoredCredentials(next);
    setCredentialsState(normalized);
  }, []);

  const clearCredentialsFn = useCallback(() => {
    clearStoredCredentials();
    setCredentialsState({});
  }, []);

  return {
    credentials,
    setCredentials,
    clearCredentials: clearCredentialsFn
  };
};
