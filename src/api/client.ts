// Talks to the GreenPulse server.
//
// Holds the session tokens, attaches them, and refreshes them when the short
// lived access token expires. Screens never see any of that; they call
// api.get/post and either get data or an ApiError with a code they can
// translate.

import AsyncStorage from '@react-native-async-storage/async-storage';
import * as SecureStore from 'expo-secure-store';
import { DEFAULT_API_URL } from '@/config/env';
import type { TokenPair } from './types';

const ACCESS_KEY = 'greenpulse.access';
const REFRESH_KEY = 'greenpulse.refresh';
const BASE_URL_KEY = 'greenpulse.apiUrl';
const REQUEST_TIMEOUT_MS = 20000;

let baseUrl = DEFAULT_API_URL;
let accessToken: string | null = null;
let refreshToken: string | null = null;

// Set when a refresh fails: the session is gone and the app must sign out.
let onSessionLost: (() => void) | null = null;

export class ApiError extends Error {
  // A short stable string from the server ("invalid_credentials"), or a local
  // code like "network" / "timeout". Screens map these to translated text.
  readonly code: string;
  readonly status: number;

  constructor(code: string, status: number, message?: string) {
    super(message ?? code);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
  }
}

// --- configuration ---------------------------------------------------------

export function normalizeBaseUrl(url: string): string {
  let u = url.trim();
  if (!u) return '';
  if (!/^https?:\/\//i.test(u)) u = `http://${u}`;
  return u.replace(/\/+$/, '');
}

export function setBaseUrl(url: string): void {
  baseUrl = normalizeBaseUrl(url) || DEFAULT_API_URL;
}

export function getBaseUrl(): string {
  return baseUrl;
}

// Loaded once at startup, before anything can make a request. Screens change it
// through the settings screen, which calls persistBaseUrl.
export async function loadStoredBaseUrl(): Promise<string> {
  try {
    const saved = await AsyncStorage.getItem(BASE_URL_KEY);
    if (saved) setBaseUrl(saved);
  } catch {
    // fall back to the build time default
  }
  return baseUrl;
}

export async function persistBaseUrl(url: string): Promise<void> {
  setBaseUrl(url);
  await AsyncStorage.setItem(BASE_URL_KEY, baseUrl).catch(() => {});
}

// Turns a relative path the server handed us (image urls, for instance) into
// something the phone can fetch.
export function absoluteUrl(path: string | null | undefined): string | null {
  if (!path) return null;
  if (/^https?:\/\//i.test(path)) return path;
  return `${baseUrl}${path.startsWith('/') ? '' : '/'}${path}`;
}

/**
 * An image source for a leaf photo held on the server.
 *
 * Leaf images sit behind the same authentication as everything else, and an
 * <Image> tag does a plain GET with no token, so the header has to be attached
 * here or every photo comes back 401. A local file uri is passed through
 * untouched.
 */
export function imageSource(
  path: string | null | undefined
): { uri: string; headers?: Record<string, string> } | undefined {
  if (!path) return undefined;
  if (path.startsWith('file:') || path.startsWith('data:')) return { uri: path };

  const uri = absoluteUrl(path);
  if (!uri) return undefined;
  return accessToken
    ? { uri, headers: { Authorization: `Bearer ${accessToken}` } }
    : { uri };
}

export function getAccessToken(): string | null {
  return accessToken;
}

export function onSessionExpired(handler: (() => void) | null): void {
  onSessionLost = handler;
}

// --- token storage ---------------------------------------------------------

export async function loadStoredSession(): Promise<boolean> {
  try {
    const [a, r] = await Promise.all([
      SecureStore.getItemAsync(ACCESS_KEY),
      SecureStore.getItemAsync(REFRESH_KEY),
    ]);
    accessToken = a;
    refreshToken = r;
    return !!r;
  } catch {
    return false;
  }
}

export async function storeSession(tokens: TokenPair): Promise<void> {
  accessToken = tokens.access_token;
  refreshToken = tokens.refresh_token;
  await Promise.all([
    SecureStore.setItemAsync(ACCESS_KEY, tokens.access_token),
    SecureStore.setItemAsync(REFRESH_KEY, tokens.refresh_token),
  ]).catch(() => {});
}

export async function clearSession(): Promise<void> {
  accessToken = null;
  refreshToken = null;
  await Promise.all([
    SecureStore.deleteItemAsync(ACCESS_KEY),
    SecureStore.deleteItemAsync(REFRESH_KEY),
  ]).catch(() => {});
}

export function getRefreshToken(): string | null {
  return refreshToken;
}

// --- requests --------------------------------------------------------------

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE';
  body?: unknown;
  form?: FormData;
  auth?: boolean;
  timeoutMs?: number;
  // Used by the refresh call itself so a failed refresh cannot recurse.
  retryOn401?: boolean;
}

async function rawRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const {
    method = 'GET',
    body,
    form,
    auth = true,
    timeoutMs = REQUEST_TIMEOUT_MS,
    retryOn401 = true,
  } = options;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  const headers: Record<string, string> = {};
  if (auth && accessToken) headers.Authorization = `Bearer ${accessToken}`;
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  // FormData sets its own boundary; setting it by hand breaks the upload.

  let response: Response;
  try {
    response = await fetch(`${baseUrl}${path}`, {
      method,
      headers,
      body: form ?? (body !== undefined ? JSON.stringify(body) : undefined),
      signal: controller.signal,
    });
  } catch (err) {
    const aborted = err instanceof Error && err.name === 'AbortError';
    throw new ApiError(aborted ? 'timeout' : 'network', 0);
  } finally {
    clearTimeout(timer);
  }

  if (response.status === 401 && auth && retryOn401 && refreshToken) {
    const refreshed = await refreshSession();
    if (refreshed) {
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
      else if (Array.isArray(payload?.detail) && payload.detail[0]?.msg) {
        // FastAPI validation errors arrive as a list.
        code = 'invalid_request';
      }
    } catch {
      // no json body, keep the status based code
    }
    throw new ApiError(code, response.status);
  }

  if (response.status === 204) return undefined as T;

  const text = await response.text();
  if (!text) return undefined as T;
  return JSON.parse(text) as T;
}

// Only one refresh runs at a time, however many requests hit 401 together.
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
      await storeSession(tokens);
      return true;
    } catch {
      await clearSession();
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
  postForm: <T>(path: string, form: FormData, options?: RequestOptions) =>
    rawRequest<T>(path, { ...options, method: 'POST', form }),
  patch: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    rawRequest<T>(path, { ...options, method: 'PATCH', body }),
  delete: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    rawRequest<T>(path, { ...options, method: 'DELETE', body }),
};

// --- reachability ----------------------------------------------------------

export async function pingServer(url?: string): Promise<boolean> {
  const target = url ? normalizeBaseUrl(url) : baseUrl;
  if (!target) return false;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 6000);
  try {
    const res = await fetch(`${target}/health`, { signal: controller.signal });
    return res.ok;
  } catch {
    return false;
  } finally {
    clearTimeout(timer);
  }
}

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
  const ws = baseUrl.replace(/^http/i, 'ws');
  return `${ws}/api/v1/sites/${siteId}/stream?ticket=${encodeURIComponent(ticket)}`;
}
