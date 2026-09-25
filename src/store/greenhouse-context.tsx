import {
  createContext,
  use,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { AppState, type AppStateStatus } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { ApiError, api, streamUrl } from '@/api/client';
import type { Capture, Live, Site, StreamEvent } from '@/api/types';
import { useAuth } from '@/auth/auth-context';

const ACTIVE_SITE_KEY = 'greenpulse.activeSite';
const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 30000;

export type LinkState = 'connecting' | 'live' | 'offline';

interface GreenhouseContextValue {
  sites: Site[];
  site: Site | null;
  live: Live | null;
  loading: boolean;
  /** Set when the last load failed, as an i18n key. */
  error: string | null;
  /** Whether the phone currently holds a live connection to the server. */
  link: LinkState;
  selectSite: (siteId: string) => void;
  refresh: () => Promise<void>;
  reloadSites: () => Promise<void>;
  /** Fired whenever a new reading arrives, so a screen can react to it. */
  subscribe: (handler: (capture: Capture) => void) => () => void;
}

const GreenhouseContext = createContext<GreenhouseContextValue | null>(null);

/**
 * Owns everything the dashboard shows.
 *
 * All of it comes from the server: an initial fetch, then a websocket that
 * pushes each new reading as the greenhouse node uploads it. Nothing here
 * generates a value. When there is no data yet, the fields are null and the
 * screens say so.
 */
export function GreenhouseProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();

  const [sites, setSites] = useState<Site[]>([]);
  const [siteId, setSiteId] = useState<string | null>(null);
  const [live, setLive] = useState<Live | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [link, setLink] = useState<LinkState>('offline');

  const socketRef = useRef<WebSocket | null>(null);
  const retryRef = useRef(RECONNECT_BASE_MS);
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const listenersRef = useRef(new Set<(capture: Capture) => void>());
  const closingRef = useRef(false);

  const site = useMemo(
    () => sites.find((s) => s.id === siteId) ?? sites[0] ?? null,
    [sites, siteId]
  );

  // Everything below keys off the id, not the site object. Reloading the site
  // list hands back a new object with the same id, and that must not be a
  // reason to drop and reopen the live connection.
  const activeSiteId = site?.id ?? null;
  // Read inside async work to tell whether the site changed while it ran.
  const activeSiteIdRef = useRef(activeSiteId);
  activeSiteIdRef.current = activeSiteId;

  // --- sites ---------------------------------------------------------------

  const reloadSites = useCallback(async () => {
    if (!user) return;
    try {
      const list = await api.get<Site[]>('/api/v1/sites');
      setSites(list);
      setError(null);

      const saved = await AsyncStorage.getItem(ACTIVE_SITE_KEY);
      setSiteId((current) => {
        if (current && list.some((s) => s.id === current)) return current;
        if (saved && list.some((s) => s.id === saved)) return saved;
        return list[0]?.id ?? null;
      });
    } catch (err) {
      setError(err instanceof ApiError ? errorKey(err) : 'err.generic');
    }
  }, [user]);

  useEffect(() => {
    if (!user) {
      setSites([]);
      setSiteId(null);
      setLive(null);
      setLink('offline');
      return;
    }
    reloadSites();
  }, [user, reloadSites]);

  const selectSite = useCallback((next: string) => {
    setSiteId(next);
    AsyncStorage.setItem(ACTIVE_SITE_KEY, next).catch(() => {});
  }, []);

  // --- the current snapshot ------------------------------------------------

  const refresh = useCallback(async () => {
    if (!activeSiteId) return;
    setLoading(true);
    try {
      setLive(await api.get<Live>(`/api/v1/sites/${activeSiteId}/live`));
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? errorKey(err) : 'err.generic');
    } finally {
      setLoading(false);
    }
  }, [activeSiteId]);

  // Reconnect logic calls refresh without wanting to be rebuilt when it changes.
  const refreshRef = useRef(refresh);
  refreshRef.current = refresh;

  useEffect(() => {
    if (!activeSiteId) {
      setLive(null);
      return;
    }
    refresh();
  }, [activeSiteId, refresh]);

  // --- live push -----------------------------------------------------------

  const applyCapture = useCallback((capture: Capture) => {
    setLive((current) =>
      current
        ? {
            ...current,
            capture,
            // Same rule as the server's live snapshot: a frame with no leaf
            // verdict keeps the last one that had one on screen.
            last_leaf_capture:
              capture.risk_score != null
                ? null
                : current.capture?.risk_score != null
                  ? current.capture
                  : current.last_leaf_capture,
            reading: capture.reading ?? current.reading,
            stale: false,
            seconds_since_reading: 0,
            online: true,
          }
        : current
    );
    listenersRef.current.forEach((fn) => fn(capture));
  }, []);

  const connect = useCallback(async () => {
    if (!activeSiteId || !user) return;

    closingRef.current = false;
    setLink('connecting');

    // A single use ticket, fetched over the authenticated API, keeps the access
    // token out of the websocket URL and so out of the proxy's access log.
    let url: string | null;
    try {
      url = await streamUrl(activeSiteId);
    } catch {
      url = null;
    }

    // The site may have changed, or the screen closed, while that was in
    // flight. Dropping the stale socket here avoids a leak.
    if (!url || closingRef.current || activeSiteId !== activeSiteIdRef.current) {
      setLink('offline');
      return;
    }

    const socket = new WebSocket(url);
    socketRef.current = socket;

    socket.onopen = () => {
      retryRef.current = RECONNECT_BASE_MS;
    };

    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data as string) as StreamEvent;
        if (payload.type === 'ready') setLink('live');
        else if (payload.type === 'capture') applyCapture(payload.capture);
        // "ping" only keeps the connection from being dropped while idle.
      } catch {
        // a malformed frame is not worth tearing the connection down for
      }
    };

    socket.onerror = () => {
      // onclose always follows, which is where the retry lives.
    };

    socket.onclose = () => {
      socketRef.current = null;
      if (closingRef.current) return;

      setLink('offline');
      // Back off so a server restart does not get hammered, and pull a fresh
      // snapshot on the way back up in case readings were missed.
      const delay = retryRef.current;
      retryRef.current = Math.min(delay * 2, RECONNECT_MAX_MS);
      retryTimerRef.current = setTimeout(() => {
        refreshRef.current();
        void connect();
      }, delay);
    };
  }, [activeSiteId, user, applyCapture]);

  const disconnect = useCallback(() => {
    closingRef.current = true;
    if (retryTimerRef.current) {
      clearTimeout(retryTimerRef.current);
      retryTimerRef.current = null;
    }
    socketRef.current?.close();
    socketRef.current = null;
    setLink('offline');
  }, []);

  useEffect(() => {
    if (!activeSiteId || !user) {
      disconnect();
      return;
    }
    void connect();
    return disconnect;
  }, [activeSiteId, user, connect, disconnect]);

  // Phones suspend sockets in the background. Coming back to the app should
  // show current numbers immediately, not whatever was on screen an hour ago.
  useEffect(() => {
    const onChange = (state: AppStateStatus) => {
      if (state !== 'active' || !activeSiteId || !user) return;
      refreshRef.current();
      if (!socketRef.current) {
        retryRef.current = RECONNECT_BASE_MS;
        void connect();
      }
    };
    const sub = AppState.addEventListener('change', onChange);
    return () => sub.remove();
  }, [activeSiteId, user, connect]);

  const subscribe = useCallback((handler: (capture: Capture) => void) => {
    listenersRef.current.add(handler);
    return () => {
      listenersRef.current.delete(handler);
    };
  }, []);

  const value = useMemo<GreenhouseContextValue>(
    () => ({
      sites,
      site,
      live,
      loading,
      error,
      link,
      selectSite,
      refresh,
      reloadSites,
      subscribe,
    }),
    [sites, site, live, loading, error, link, selectSite, refresh, reloadSites, subscribe]
  );

  return <GreenhouseContext value={value}>{children}</GreenhouseContext>;
}

function errorKey(err: ApiError): string {
  if (err.code === 'network') return 'err.serverUnreachable';
  if (err.code === 'timeout') return 'err.timeout';
  return 'err.generic';
}

export function useGreenhouse(): GreenhouseContextValue {
  const ctx = use(GreenhouseContext);
  if (!ctx) throw new Error('useGreenhouse must be used within GreenhouseProvider');
  return ctx;
}
