import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { ApiError, api, streamUrl } from './api/client';
import type { Capture, Live, Site, StreamEvent } from './api/types';
import { useAuth } from './auth';

const CAPTURE_PAGE = 100;
const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 30000;

export type LinkState = 'connecting' | 'live' | 'offline';

interface GreenhouseValue {
  sites: Site[];
  site: Site | null;
  live: Live | null;
  captures: Capture[];
  loading: boolean;
  /** i18n key for the last failure, or null. */
  error: string | null;
  link: LinkState;
  selectSite: (siteId: string) => void;
  refresh: () => Promise<void>;
  removeCapture: (id: string) => Promise<void>;
  subscribe: (handler: (capture: Capture) => void) => () => void;
}

const Ctx = createContext<GreenhouseValue | null>(null);

/**
 * Everything the panel shows, straight from the server.
 *
 * The same endpoints the phone uses: an initial fetch, then a websocket that
 * pushes each reading as the greenhouse node uploads it. Nothing here computes
 * a value of its own; when there is no data, the fields are null and the pages
 * say so.
 */
export function GreenhouseProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();

  const [sites, setSites] = useState<Site[]>([]);
  const [siteId, setSiteId] = useState<string | null>(null);
  const [live, setLive] = useState<Live | null>(null);
  const [captures, setCaptures] = useState<Capture[]>([]);
  const [loading, setLoading] = useState(true);
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
  // Keyed off the id, not the object: reloading the site list returns a new
  // object with the same id and must not drop the live connection.
  const activeSiteId = site?.id ?? null;
  // Read inside async work to tell whether the site changed while it ran.
  const activeSiteIdRef = useRef(activeSiteId);
  activeSiteIdRef.current = activeSiteId;

  // --- sites ---------------------------------------------------------------

  useEffect(() => {
    if (!user) {
      setSites([]);
      setSiteId(null);
      setLive(null);
      setCaptures([]);
      setLink('offline');
      setLoading(false);
      return;
    }

    let cancelled = false;
    (async () => {
      try {
        const list = await api.get<Site[]>('/api/v1/sites');
        if (cancelled) return;
        setSites(list);
        setSiteId((current) => {
          if (current && list.some((s) => s.id === current)) return current;
          const saved = safeRead('gp.site');
          if (saved && list.some((s) => s.id === saved)) return saved;
          return list[0]?.id ?? null;
        });
        setError(null);
      } catch (err) {
        if (!cancelled) setError(errorKey(err));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [user]);

  const selectSite = useCallback((next: string) => {
    setSiteId(next);
    safeWrite('gp.site', next);
  }, []);

  // --- snapshot + history --------------------------------------------------

  const refresh = useCallback(async () => {
    if (!activeSiteId) return;
    setLoading(true);
    try {
      const [snapshot, list] = await Promise.all([
        api.get<Live>(`/api/v1/sites/${activeSiteId}/live`),
        api.get<Capture[]>(`/api/v1/sites/${activeSiteId}/captures?limit=${CAPTURE_PAGE}`),
      ]);
      setLive(snapshot);
      setCaptures(list);
      setError(null);
    } catch (err) {
      setError(errorKey(err));
    } finally {
      setLoading(false);
    }
  }, [activeSiteId]);

  const refreshRef = useRef(refresh);
  refreshRef.current = refresh;

  useEffect(() => {
    if (!activeSiteId) {
      setLive(null);
      setCaptures([]);
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
    setCaptures((current) =>
      current.some((c) => c.id === capture.id)
        ? current
        : [capture, ...current].slice(0, CAPTURE_PAGE)
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

    // The site may have changed, or the panel navigated away, while that was in
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
        // "ping" only keeps an idle connection from being dropped.
      } catch {
        // one malformed frame is not worth tearing the connection down
      }
    };

    socket.onclose = () => {
      socketRef.current = null;
      if (closingRef.current) return;

      setLink('offline');
      // Back off so a server restart is not hammered, and pull a fresh snapshot
      // on the way back up in case readings were missed while disconnected.
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

  // A panel left open on a wall display should catch up when the laptop wakes.
  useEffect(() => {
    const onVisible = () => {
      if (document.visibilityState !== 'visible' || !activeSiteId || !user) return;
      refreshRef.current();
      if (!socketRef.current) {
        retryRef.current = RECONNECT_BASE_MS;
        void connect();
      }
    };
    document.addEventListener('visibilitychange', onVisible);
    return () => document.removeEventListener('visibilitychange', onVisible);
  }, [activeSiteId, user, connect]);

  const subscribe = useCallback((handler: (capture: Capture) => void) => {
    listenersRef.current.add(handler);
    return () => {
      listenersRef.current.delete(handler);
    };
  }, []);

  const removeCapture = useCallback(async (id: string) => {
    const previous = captures;
    setCaptures((current) => current.filter((c) => c.id !== id));
    try {
      await api.delete(`/api/v1/captures/${id}`);
    } catch (err) {
      setCaptures(previous);
      throw err;
    }
  }, [captures]);

  const value = useMemo<GreenhouseValue>(
    () => ({
      sites,
      site,
      live,
      captures,
      loading,
      error,
      link,
      selectSite,
      refresh,
      removeCapture,
      subscribe,
    }),
    [sites, site, live, captures, loading, error, link, selectSite, refresh, removeCapture, subscribe]
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

function errorKey(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.code === 'network') return 'err.serverUnreachable';
    if (err.code === 'timeout') return 'err.timeout';
  }
  return 'err.generic';
}

function safeRead(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function safeWrite(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {
    // a remembered choice is a convenience, not a requirement
  }
}

export function useGreenhouse(): GreenhouseValue {
  const v = useContext(Ctx);
  if (!v) throw new Error('useGreenhouse outside provider');
  return v;
}
