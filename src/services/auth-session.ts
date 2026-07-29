import type { AuthTokens } from "@/types";

export interface AuthSessionAdapter {
  getAccessToken: () => string | null;
  setTokens: (tokens: AuthTokens) => void;
  refreshAccessToken: () => Promise<AuthTokens | null>;
  onAuthenticationFailure: () => void;
}

let accessToken: string | null = null;

const placeholderAdapter: AuthSessionAdapter = {
  getAccessToken: () => accessToken,
  setTokens: (tokens) => {
    accessToken = tokens.access;
  },
  // Future integration should call POST /auth/token/refresh/ and update tokens.
  refreshAccessToken: async () => null,
  onAuthenticationFailure: () => {
    accessToken = null;
  },
};

let authSessionAdapter = placeholderAdapter;

export function getAuthSessionAdapter() {
  return authSessionAdapter;
}

export function configureAuthSession(
  adapter: Partial<AuthSessionAdapter>,
) {
  authSessionAdapter = { ...placeholderAdapter, ...adapter };
}

export function setAccessToken(token: string | null) {
  accessToken = token;
}

export function clearAuthSession() {
  accessToken = null;
  authSessionAdapter = placeholderAdapter;
}
