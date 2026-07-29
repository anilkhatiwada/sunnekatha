import { environment } from "@/config/environment";
import type { AuthTokens } from "@/types";

const AUTH_STORAGE_KEY = "sunnekatha:auth-tokens";

export interface AuthSessionAdapter {
  getAccessToken: () => string | null;
  getRefreshToken: () => string | null;
  setTokens: (tokens: AuthTokens) => void;
  refreshAccessToken: () => Promise<AuthTokens | null>;
  onAuthenticationFailure: () => void;
}

interface StoredTokens {
  access: string;
  refresh: string;
}

type RefreshRequest = (refreshToken: string) => Promise<AuthTokens | null>;

function getSessionStorage() {
  return typeof window === "undefined" ? null : window.sessionStorage;
}

function readStoredTokens(): StoredTokens | null {
  const value = getSessionStorage()?.getItem(AUTH_STORAGE_KEY);
  if (!value) return null;

  try {
    const parsed: unknown = JSON.parse(value);
    if (!parsed || typeof parsed !== "object") return null;
    const candidate = parsed as Record<string, unknown>;
    return typeof candidate.access === "string" &&
      typeof candidate.refresh === "string"
      ? { access: candidate.access, refresh: candidate.refresh }
      : null;
  } catch {
    return null;
  }
}

function writeStoredTokens(tokens: StoredTokens | null) {
  const storage = getSessionStorage();
  if (!storage) return;

  if (tokens) {
    storage.setItem(AUTH_STORAGE_KEY, JSON.stringify(tokens));
  } else {
    storage.removeItem(AUTH_STORAGE_KEY);
  }
}

async function requestTokenRefresh(
  refreshToken: string,
): Promise<AuthTokens | null> {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(
    () => controller.abort(),
    environment.apiTimeoutMs,
  );

  try {
    const response = await fetch(
      `${environment.apiBaseUrl}/auth/token/refresh/`,
      {
        method: "POST",
        signal: controller.signal,
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ refresh: refreshToken }),
      },
    );
    if (!response.ok) return null;

    const payload: unknown = await response.json();
    if (!payload || typeof payload !== "object") return null;
    const candidate = payload as Record<string, unknown>;
    return typeof candidate.access === "string"
      ? {
          access: candidate.access,
          refresh:
            typeof candidate.refresh === "string"
              ? candidate.refresh
              : undefined,
        }
      : null;
  } catch {
    return null;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

export function createBrowserAuthSession(
  refreshRequest: RefreshRequest = requestTokenRefresh,
): AuthSessionAdapter {
  return {
    getAccessToken: () => readStoredTokens()?.access ?? null,
    getRefreshToken: () => readStoredTokens()?.refresh ?? null,
    setTokens: (tokens) => {
      const current = readStoredTokens();
      const refresh = tokens.refresh ?? current?.refresh;
      if (!refresh) {
        throw new Error("A refresh token is required to establish a session.");
      }
      writeStoredTokens({ access: tokens.access, refresh });
    },
    refreshAccessToken: async () => {
      const current = readStoredTokens();
      if (!current?.refresh) return null;

      const refreshed = await refreshRequest(current.refresh);
      if (!refreshed?.access) return null;
      const tokens = {
        access: refreshed.access,
        refresh: refreshed.refresh ?? current.refresh,
      };
      writeStoredTokens(tokens);
      return tokens;
    },
    onAuthenticationFailure: () => writeStoredTokens(null),
  };
}

let authSessionAdapter: AuthSessionAdapter = createBrowserAuthSession();

export function getAuthSessionAdapter() {
  return authSessionAdapter;
}

export function configureAuthSession(adapter: AuthSessionAdapter) {
  authSessionAdapter = adapter;
}

export function setAuthTokens(tokens: AuthTokens) {
  authSessionAdapter.setTokens(tokens);
}

export function clearAuthSession() {
  authSessionAdapter.onAuthenticationFailure();
  authSessionAdapter = createBrowserAuthSession();
}
