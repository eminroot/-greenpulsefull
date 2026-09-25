import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import {
  ApiError,
  api,
  clearImageCache,
  clearSession,
  getRefreshToken,
  loadStoredSession,
  onSessionExpired,
  storeSession,
} from './api/client';
import type { TokenPair, User } from './api/types';

interface AuthValue {
  user: User | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signInWithGoogle: (idToken: string) => Promise<void>;
  signOut: () => Promise<void>;
}

const Ctx = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  // Restore the saved session, then confirm the server still accepts it.
  useEffect(() => {
    let cancelled = false;

    (async () => {
      if (!loadStoredSession()) {
        if (!cancelled) setLoading(false);
        return;
      }
      try {
        const me = await api.get<User>('/api/v1/auth/me');
        if (!cancelled) setUser(me);
      } catch (err) {
        // A network blip should not sign the operator out; a rejected session should.
        if (err instanceof ApiError && err.status === 401) clearSession();
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    onSessionExpired(() => setUser(null));
    return () => onSessionExpired(null);
  }, []);

  const adopt = useCallback((tokens: TokenPair) => {
    storeSession(tokens);
    setUser(tokens.user);
  }, []);

  const value = useMemo<AuthValue>(
    () => ({
      user,
      loading,

      signIn: async (email, password) => {
        const tokens = await api.post<TokenPair>(
          '/api/v1/auth/login',
          { email: email.trim(), password },
          { auth: false }
        );
        adopt(tokens);
      },

      signInWithGoogle: async (idToken) => {
        const tokens = await api.post<TokenPair>(
          '/api/v1/auth/google',
          { id_token: idToken },
          { auth: false }
        );
        adopt(tokens);
      },

      signOut: async () => {
        const refresh = getRefreshToken();
        if (refresh) {
          await api
            .post('/api/v1/auth/logout', { refresh_token: refresh }, { auth: false })
            .catch(() => {});
        }
        clearSession();
        // Signed-out photos must not stay readable in memory.
        clearImageCache();
        setUser(null);
      },
    }),
    [user, loading, adopt]
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth(): AuthValue {
  const v = useContext(Ctx);
  if (!v) throw new Error('useAuth outside provider');
  return v;
}

// Maps the server's error codes to i18n keys. The server answers with short
// stable codes rather than sentences, so the wording stays here.
export function friendlyAuthError(error: unknown): string {
  const code = error instanceof ApiError ? error.code : undefined;
  switch (code) {
    case 'invalid_credentials':
      return 'err.wrongCred';
    case 'too_many_attempts':
      return 'err.tooMany';
    case 'account_disabled':
      return 'err.disabled';
    case 'network':
      return 'err.network';
    case 'timeout':
      return 'err.timeout';
    case 'session_expired':
    case 'refresh_invalid':
    case 'refresh_expired':
      return 'err.sessionExpired';
    case 'google_not_configured':
      return 'err.googleNotConfigured';
    case 'google_token_invalid':
      return 'err.googleFailed';
    case 'google_email_unverified':
      return 'err.googleUnverified';
    case 'invalid_request':
      return 'err.invalidEmail';
    default:
      return 'err.generic';
  }
}
