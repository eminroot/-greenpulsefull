import {
  createContext,
  use,
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import {
  ApiError,
  api,
  clearSession,
  getRefreshToken,
  loadStoredSession,
  onSessionExpired,
  storeSession,
} from '@/api/client';
import type { TokenPair, User } from '@/api/types';

interface AuthContextValue {
  user: User | null;
  initializing: boolean;
  signUp: (email: string, password: string, name: string) => Promise<void>;
  signIn: (email: string, password: string) => Promise<void>;
  signInWithGoogle: (idToken: string) => Promise<void>;
  signOut: () => Promise<void>;
  setDisplayName: (name: string) => Promise<void>;
  changePassword: (current: string | null, next: string) => Promise<void>;
  deleteAccount: () => Promise<void>;
  reload: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [initializing, setInitializing] = useState(true);

  // Restore the session saved in the device keychain, then confirm it is still
  // good. A phone that has been offline for a month should land on the sign in
  // screen rather than an empty dashboard.
  useEffect(() => {
    let cancelled = false;

    (async () => {
      const hasSession = await loadStoredSession();
      if (!hasSession) {
        if (!cancelled) setInitializing(false);
        return;
      }
      try {
        const me = await api.get<User>('/api/v1/auth/me');
        if (!cancelled) setUser(me);
      } catch (err) {
        // A network problem should not sign the grower out; only a rejected
        // session should.
        if (err instanceof ApiError && err.status === 401) {
          await clearSession();
        }
      } finally {
        if (!cancelled) setInitializing(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  // The client tells us when a refresh failed for good.
  useEffect(() => {
    onSessionExpired(() => setUser(null));
    return () => onSessionExpired(null);
  }, []);

  const adopt = useCallback(async (tokens: TokenPair) => {
    await storeSession(tokens);
    setUser(tokens.user);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      initializing,

      async signUp(email, password, name) {
        const tokens = await api.post<TokenPair>(
          '/api/v1/auth/register',
          { email: email.trim(), password, name: name.trim() || null },
          { auth: false }
        );
        await adopt(tokens);
      },

      async signIn(email, password) {
        const tokens = await api.post<TokenPair>(
          '/api/v1/auth/login',
          { email: email.trim(), password },
          { auth: false }
        );
        await adopt(tokens);
      },

      async signInWithGoogle(idToken) {
        const tokens = await api.post<TokenPair>(
          '/api/v1/auth/google',
          { id_token: idToken },
          { auth: false }
        );
        await adopt(tokens);
      },

      async signOut() {
        const refresh = getRefreshToken();
        if (refresh) {
          // Best effort: the local session goes either way.
          await api
            .post('/api/v1/auth/logout', { refresh_token: refresh })
            .catch(() => {});
        }
        await clearSession();
        setUser(null);
      },

      async setDisplayName(name) {
        const updated = await api.patch<User>('/api/v1/auth/me', {
          name: name.trim(),
        });
        setUser(updated);
      },

      async changePassword(current, next) {
        await api.post('/api/v1/auth/me/password', {
          current_password: current,
          new_password: next,
        });
      },

      async deleteAccount() {
        await api.delete('/api/v1/auth/me');
        await clearSession();
        setUser(null);
      },

      async reload() {
        try {
          setUser(await api.get<User>('/api/v1/auth/me'));
        } catch {
          // keep whatever we had; the next request will surface a real problem
        }
      },
    }),
    [user, initializing, adopt]
  );

  return <AuthContext value={value}>{children}</AuthContext>;
}

export function useAuth(): AuthContextValue {
  const ctx = use(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
