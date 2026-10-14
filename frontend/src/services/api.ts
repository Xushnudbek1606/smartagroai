import axios, { AxiosError } from 'axios';
import type { ApiErrorBody, TokenPair } from '../types';

export const API_BASE = import.meta.env.VITE_API_URL || '/api/v1';

// Origin of the API host. Empty in development, where the Vite dev server
// proxies /api and /static to the local backend; in production (Vercel) the
// app and the API live on different domains, so asset URLs need the host.
export const API_ORIGIN = (() => {
  if (!/^https?:\/\//i.test(API_BASE)) return '';
  try {
    return new URL(API_BASE).origin;
  } catch {
    return '';
  }
})();

// Uploads are stored as backend-relative paths (/static/...), so they must be
// resolved against the API host instead of the page host.
export function assetUrl(path: string | null | undefined): string {
  if (!path) return '';
  if (/^(https?:|data:|blob:)/i.test(path)) return path;
  return `${API_ORIGIN}${path}`;
}

const STORAGE_ACCESS = 'smartagro_access';
const STORAGE_REFRESH = 'smartagro_refresh';

export function getStoredTokens(): TokenPair | null {
  try {
    const raw = localStorage.getItem(STORAGE_ACCESS);
    const refresh = localStorage.getItem(STORAGE_REFRESH);
    if (!raw || !refresh) return null;
    return { access_token: raw, refresh_token: refresh, token_type: 'bearer', expires_in: 0 };
  } catch {
    return null;
  }
}

export function storeTokens(tokens: TokenPair): void {
  localStorage.setItem(STORAGE_ACCESS, tokens.access_token);
  localStorage.setItem(STORAGE_REFRESH, tokens.refresh_token);
}

export function clearTokens(): void {
  localStorage.removeItem(STORAGE_ACCESS);
  localStorage.removeItem(STORAGE_REFRESH);
}

export const api = axios.create({ baseURL: API_BASE, timeout: 30000 });

api.interceptors.request.use((config) => {
  const tokens = getStoredTokens();
  if (tokens?.access_token) {
    config.headers.Authorization = `Bearer ${tokens.access_token}`;
  }
  return config;
});

let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const tokens = getStoredTokens();
  if (!tokens?.refresh_token) return null;
  try {
    const resp = await axios.post<TokenPair>(`${API_BASE}/auth/refresh`, {
      refresh_token: tokens.refresh_token,
    });
    storeTokens(resp.data);
    return resp.data.access_token;
  } catch {
    clearTokens();
    return null;
  }
}

api.interceptors.response.use(
  (resp) => resp,
  async (error: AxiosError<ApiErrorBody>) => {
    const original = error.config as
      | (typeof error.config & { _retry?: boolean })
      | undefined;
    const url = original?.url || '';
    if (error.response?.status === 401 && original && !original._retry && !url.includes('/auth/login') && !url.includes('/auth/refresh')) {
      original._retry = true;
      refreshPromise = refreshPromise ?? refreshAccessToken();
      const newToken = await refreshPromise;
      refreshPromise = null;
      if (newToken) {
        original.headers = original.headers || {};
        original.headers.Authorization = `Bearer ${newToken}`;
        return api(original);
      }
      // session over: send user to login, preserving the intended page
      if (!window.location.pathname.startsWith('/login')) {
        clearTokens();
        window.location.href = `/login?next=${encodeURIComponent(window.location.pathname)}`;
      }
    }
    return Promise.reject(error);
  },
);

export function extractError(err: unknown): { code: string; message: string; details?: unknown } {
  if (axios.isAxiosError(err)) {
    const body = err.response?.data;
    if (body?.error) return body.error;
    return { code: 'network_error', message: err.message };
  }
  return { code: 'unknown', message: String(err) };
}

export function wsUrl(conversationId: string): string {
  const token = getStoredTokens()?.access_token || '';
  const base = import.meta.env.VITE_WS_URL
    || (window.location.origin.replace(/^http/, 'ws') + (API_BASE.replace('/api/v1', '') || ''));
  return `${base}/ws/chat/${conversationId}?token=${encodeURIComponent(token)}`;
}
