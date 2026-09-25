import {
  createContext,
  use,
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { getBaseUrl, persistBaseUrl, pingServer } from '@/api/client';

const KEY = 'greenpulse.settings.v2';

interface PersistedSettings {
  // Let GreenPulse drive the actuators, rather than only advising.
  autopilot: boolean;
}

const DEFAULTS: PersistedSettings = { autopilot: true };

export type ServerStatus = 'unknown' | 'checking' | 'online' | 'offline';

interface SettingsContextValue extends PersistedSettings {
  ready: boolean;
  serverUrl: string;
  serverStatus: ServerStatus;
  setServerUrl: (url: string) => Promise<void>;
  setAutopilot: (v: boolean) => void;
  checkServer: () => Promise<boolean>;
}

const SettingsContext = createContext<SettingsContextValue | null>(null);

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<PersistedSettings>(DEFAULTS);
  const [ready, setReady] = useState(false);
  const [serverUrl, setServerUrlState] = useState(getBaseUrl());
  const [serverStatus, setServerStatus] = useState<ServerStatus>('unknown');

  useEffect(() => {
    AsyncStorage.getItem(KEY)
      .then((raw) => {
        if (raw) setSettings({ ...DEFAULTS, ...JSON.parse(raw) });
      })
      .catch(() => {})
      .finally(() => setReady(true));
  }, []);

  const persist = useCallback((next: PersistedSettings) => {
    setSettings(next);
    AsyncStorage.setItem(KEY, JSON.stringify(next)).catch(() => {});
  }, []);

  const checkServer = useCallback(async () => {
    setServerStatus('checking');
    const ok = await pingServer();
    setServerStatus(ok ? 'online' : 'offline');
    return ok;
  }, []);

  const setServerUrl = useCallback(
    async (url: string) => {
      await persistBaseUrl(url);
      setServerUrlState(getBaseUrl());
      await checkServer();
    },
    [checkServer]
  );

  // One reachability check at startup, so the settings screen can say something
  // useful before the grower touches anything.
  useEffect(() => {
    if (ready) checkServer();
  }, [ready, checkServer]);

  const value = useMemo<SettingsContextValue>(
    () => ({
      ...settings,
      ready,
      serverUrl,
      serverStatus,
      setServerUrl,
      setAutopilot: (v) => persist({ ...settings, autopilot: v }),
      checkServer,
    }),
    [settings, ready, serverUrl, serverStatus, setServerUrl, persist, checkServer]
  );

  return <SettingsContext value={value}>{children}</SettingsContext>;
}

export function useSettings(): SettingsContextValue {
  const ctx = use(SettingsContext);
  if (!ctx) throw new Error('useSettings must be used within SettingsProvider');
  return ctx;
}
