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

const AUTH_REFRESH_LOCK = "sunnekatha:auth-refresh";

export class AuthRefreshUnavailableError extends Error {
  constructor(options?: ErrorOptions) {
    super("Authentication refresh is temporarily unavailable.", options);
    this.name = "AuthRefreshUnavailableError";
  }
}

function getPersistentStorage() {
  return typeof window === "undefined" ? null : window.localStorage;
}

function getLegacySessionStorage() {
  return typeof window === "undefined" ? null : window.sessionStorage;
}

function parseStoredTokens(value: string | null): StoredTokens | null {
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

function readStoredTokens(): StoredTokens | null {
  const persistentStorage = getPersistentStorage();
  const persistent = parseStoredTokens(
    persistentStorage?.getItem(AUTH_STORAGE_KEY) ?? null,
  );
  if (persistent) return persistent;

  const legacyStorage = getLegacySessionStorage();
  const legacy = parseStoredTokens(
    legacyStorage?.getItem(AUTH_STORAGE_KEY) ?? null,
  );
  if (!legacy) return null;

  persistentStorage?.setItem(AUTH_STORAGE_KEY, JSON.stringify(legacy));
  legacyStorage?.removeItem(AUTH_STORAGE_KEY);
  return legacy;
}

function writeStoredTokens(tokens: StoredTokens | null) {
  const storage = getPersistentStorage();
  const legacyStorage = getLegacySessionStorage();
  legacyStorage?.removeItem(AUTH_STORAGE_KEY);
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
    if (response.status === 400 || response.status === 401) return null;
    if (!response.ok) {
      throw new AuthRefreshUnavailableError();
    }

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
  } catch (error) {
    if (error instanceof AuthRefreshUnavailableError) throw error;
    throw new AuthRefreshUnavailableError({ cause: error });
  } finally {
    window.clearTimeout(timeoutId);
  }
}

async function withAuthenticationRefreshLock<T>(callback: () => Promise<T>) {
  if (typeof navigator === "undefined" || !navigator.locks) {
    return callback();
  }

  return navigator.locks.request(AUTH_REFRESH_LOCK, callback);
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
      const initial = readStoredTokens();
      if (!initial?.refresh) return null;

      return withAuthenticationRefreshLock(async () => {
        const current = readStoredTokens();
        if (!current?.refresh) return null;

        if (
          current.access !== initial.access ||
          current.refresh !== initial.refresh
        ) {
          return current;
        }

        const refreshed = await refreshRequest(current.refresh);
        if (!refreshed?.access) return null;
        const tokens = {
          access: refreshed.access,
          refresh: refreshed.refresh ?? current.refresh,
        };
        writeStoredTokens(tokens);
        return tokens;
      });
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
