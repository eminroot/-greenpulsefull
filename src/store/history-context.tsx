import {
  createContext,
  use,
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { ApiError, api } from '@/api/client';
import type { Capture } from '@/api/types';
import { useAuth } from '@/auth/auth-context';
import { useGreenhouse } from '@/store/greenhouse-context';

const PAGE_SIZE = 100;

interface HistoryContextValue {
  records: Capture[];
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  remove: (id: string) => Promise<void>;
  clearAll: () => Promise<void>;
}

const HistoryContext = createContext<HistoryContextValue | null>(null);

/**
 * The greenhouse's stored readings, newest first.
 *
 * Everything comes from the server, so the same history appears on any phone
 * the grower signs in on. New readings arrive over the live connection and are
 * prepended without a refetch.
 */
export function HistoryProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const { site, subscribe } = useGreenhouse();
  const [records, setRecords] = useState<Capture[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!site) {
      setRecords([]);
      return;
    }
    setLoading(true);
    try {
      const list = await api.get<Capture[]>(
        `/api/v1/sites/${site.id}/captures?limit=${PAGE_SIZE}`
      );
      setRecords(list);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError && err.code === 'network' ? 'err.serverUnreachable' : 'err.generic');
    } finally {
      setLoading(false);
    }
  }, [site?.id]);

  useEffect(() => {
    if (!user) {
      setRecords([]);
      return;
    }
    refresh();
  }, [user, site?.id, refresh]);

  // A reading pushed to the dashboard belongs at the top of the history too.
  useEffect(
    () =>
      subscribe((capture) => {
        setRecords((current) =>
          current.some((r) => r.id === capture.id)
            ? current
            : [capture, ...current].slice(0, PAGE_SIZE)
        );
      }),
    [subscribe]
  );

  const value = useMemo<HistoryContextValue>(
    () => ({
      records,
      loading,
      error,
      refresh,

      async remove(id) {
        // Drop it locally first so the list responds immediately, and put it
        // back if the server disagrees.
        const previous = records;
        setRecords((current) => current.filter((r) => r.id !== id));
        try {
          await api.delete(`/api/v1/captures/${id}`);
        } catch {
          setRecords(previous);
          throw new Error('delete_failed');
        }
      },

      async clearAll() {
        if (!site) return;
        const previous = records;
        setRecords([]);
        try {
          await api.delete(`/api/v1/sites/${site.id}/captures`);
        } catch {
          setRecords(previous);
          throw new Error('delete_failed');
        }
      },
    }),
    [records, loading, error, refresh, site?.id]
  );

  return <HistoryContext value={value}>{children}</HistoryContext>;
}

export function useHistory(): HistoryContextValue {
  const ctx = use(HistoryContext);
  if (!ctx) throw new Error('useHistory must be used within HistoryProvider');
  return ctx;
}
