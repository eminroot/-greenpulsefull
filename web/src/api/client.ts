// Talks to the GreenPulse server.
//
// The browser twin of the mobile app's src/api/client.ts: same endpoints, same
// error codes, same refresh behaviour. The panel is normally served from the
// same origin as the API, so the base url is empty and every request is
// relative; set VITE_GREENPULSE_API to point a build somewhere else.

import type { TokenPair } from './types';

const ACCESS_KEY = 'gp.access';
const REFRESH_KEY = 'gp.refresh';
const REQUEST_TIMEOUT_MS = 20000;

function initialBaseUrl(): string {
  const configured = import.meta.env.VITE_GREENPULSE_API as string | undefined;
  if (!configured) return ''; // same origin
  return configured.replace(/\/+$/, '');
}

let baseUrl = initialBaseUrl();
let accessToken: string | null = null;
let refreshToken: string | null = null;
let onSessionLost: (() => void) | null = null;

export class ApiError extends Error {
  readonly code: string;
  readonly status: number;

  constructor(code: string, status: number, message?: string) {
    super(message ?? code);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
  }
}

export function getBaseUrl(): string {
  return baseUrl;
}

export function onSessionExpired(handler: (() => void) | null): void {
  onSessionLost = handler;
}

// --- session ---------------------------------------------------------------

export function loadStoredSession(): boolean {
  try {
    accessToken = localStorage.getItem(ACCESS_KEY);
    refreshToken = localStorage.getItem(REFRESH_KEY);
  } catch {
    // private mode with storage disabled: the operator just signs in again
    accessToken = null;
    refreshToken = null;
  }
  return !!refreshToken;
}

export function storeSession(tokens: TokenPair): void {
  accessToken = tokens.access_token;
  refreshToken = tokens.refresh_token;
  try {
    localStorage.setItem(ACCESS_KEY, tokens.access_token);
    localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
  } catch {
    // keep the in-memory session; it lasts until the tab closes
  }
}

export function clearSession(): void {
  accessToken = null;
  refreshToken = null;
  try {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  } catch {
    // nothing to clear
  }
}

export function getRefreshToken(): string | null {
  return refreshToken;
}

export function getAccessToken(): string | null {
  return accessToken;
}

// --- requests --------------------------------------------------------------

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE';
  body?: unknown;
  auth?: boolean;
  timeoutMs?: number;
  retryOn401?: boolean;
  signal?: AbortSignal;
}

async function rawRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const {
    method = 'GET',
    body,
    auth = true,
    timeoutMs = REQUEST_TIMEOUT_MS,
    retryOn401 = true,
    signal,
  } = options;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  // A caller that aborts (a superseded slider drag, say) must cancel this too.
  const onAbort = () => controller.abort();
  signal?.addEventListener('abort', onAbort);

  const headers: Record<string, string> = {};
  if (auth && accessToken) headers.Authorization = `Bearer ${accessToken}`;
  if (body !== undefined) headers['Content-Type'] = 'application/json';

  let response: Response;
  try {
    response = await fetch(`${baseUrl}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });
  } catch (err) {
    if (signal?.aborted) throw new ApiError('aborted', 0);
    const timedOut = err instanceof Error && err.name === 'AbortError';
    throw new ApiError(timedOut ? 'timeout' : 'network', 0);
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener('abort', onAbort);
  }

  if (response.status === 401 && auth && retryOn401 && refreshToken) {
    if (await refreshSession()) {
      return rawRequest<T>(path, { ...options, retryOn401: false });
    }
    onSessionLost?.();
    throw new ApiError('session_expired', 401);
  }

  if (!response.ok) {
    let code = `http_${response.status}`;
    try {
      const payload = await response.json();
      if (typeof payload?.detail === 'string') code = payload.detail;
      else if (Array.isArray(payload?.detail)) code = 'invalid_request';
    } catch {
      // no json body
    }
    throw new ApiError(code, response.status);
  }

  if (response.status === 204) return undefined as T;
  const text = await response.text();
  return text ? (JSON.parse(text) as T) : (undefined as T);
}

// One refresh at a time, however many requests hit 401 together.
let refreshInFlight: Promise<boolean> | null = null;

async function refreshSession(): Promise<boolean> {
  if (!refreshToken) return false;
  if (refreshInFlight) return refreshInFlight;

  refreshInFlight = (async () => {
    try {
      const tokens = await rawRequest<TokenPair>('/api/v1/auth/refresh', {
        method: 'POST',
        body: { refresh_token: refreshToken },
        auth: false,
        retryOn401: false,
      });
      storeSession(tokens);
      return true;
    } catch {
      clearSession();
      return false;
    } finally {
      refreshInFlight = null;
    }
  })();

  return refreshInFlight;
}

export const api = {
  get: <T>(path: string, options?: RequestOptions) =>
    rawRequest<T>(path, { ...options, method: 'GET' }),
  post: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    rawRequest<T>(path, { ...options, method: 'POST', body }),
  patch: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    rawRequest<T>(path, { ...options, method: 'PATCH', body }),
  delete: <T>(path: string, options?: RequestOptions) =>
    rawRequest<T>(path, { ...options, method: 'DELETE' }),
};

// --- images ----------------------------------------------------------------

const blobCache = new Map<string, string>();
const MAX_CACHED_IMAGES = 120;

/**
 * Fetches a leaf photo and returns an object url the browser can render.
 *
 * Leaf images sit behind the same authentication as everything else, and an
 * <img> tag sends no Authorization header, so the bytes have to be fetched
 * here. Doing it this way also keeps the access token out of URLs, and so out
 * of the reverse proxy's access log.
 */
export async function fetchImageUrl(path: string): Promise<string> {
  const cached = blobCache.get(path);
  if (cached) return cached;

  const res = await fetch(`${baseUrl}${path}`, {
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : undefined,
  });
  if (!res.ok) throw new ApiError(`http_${res.status}`, res.status);

  const url = URL.createObjectURL(await res.blob());

  // Bounded, so a long gallery session cannot hold every photo in memory.
  if (blobCache.size >= MAX_CACHED_IMAGES) {
    const oldest = blobCache.keys().next().value;
    if (oldest) {
      URL.revokeObjectURL(blobCache.get(oldest)!);
      blobCache.delete(oldest);
    }
  }
  blobCache.set(path, url);
  return url;
}

export function clearImageCache(): void {
  for (const url of blobCache.values()) URL.revokeObjectURL(url);
  blobCache.clear();
}

// --- live stream -----------------------------------------------------------

/**
 * A websocket url for this greenhouse, carrying a single use ticket.
 *
 * A websocket cannot take an Authorization header, so the credential has to go
 * in the query string, where the reverse proxy logs it. A ticket lives for a
 * minute and works once, so a copy in a log file is already useless; the access
 * token would have been good for half an hour.
 */
export async function streamUrl(siteId: string): Promise<string | null> {
  if (!accessToken) return null;
  const { ticket } = await api.post<{ ticket: string; expires_in: number }>(
    `/api/v1/sites/${siteId}/stream/ticket`
  );
  const origin = baseUrl || window.location.origin;
  const ws = origin.replace(/^http/i, 'ws');
  return `${ws}/api/v1/sites/${siteId}/stream?ticket=${encodeURIComponent(ticket)}`;
}

export async function pingServer(): Promise<boolean> {
  try {
    const res = await fetch(`${baseUrl}/health`);
    return res.ok;
  } catch {
    return false;
  }
}
