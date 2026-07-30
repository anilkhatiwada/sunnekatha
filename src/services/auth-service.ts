import { apiClient } from "@/services/api-client";
import {
  clearAuthSession,
  getAuthSessionAdapter,
  setAuthTokens,
} from "@/services/auth-session";
import {
  mapAuthenticatedUser,
  type AuthenticatedUserDomain,
} from "@/services/api-mappers";
import type { ApiAuthenticatedUser, LoginResponse } from "@/types";

export async function loginWithGoogle(
  credential: string,
): Promise<LoginResponse["user"]> {
  const response = await apiClient.post<
    LoginResponse,
    { credential: string }
  >("/auth/google/", {
    body: { credential },
    headers: { "X-SunneKatha-Auth": "google" },
  });
  setAuthTokens({
    access: response.access,
    refresh: response.refresh,
  });
  return response.user;
}

export async function loginWithPassword(input: {
  email: string;
  password: string;
}) {
  const response = await apiClient.post<LoginResponse, typeof input>(
    "/auth/login/",
    { body: input },
  );
  setAuthTokens({
    access: response.access,
    refresh: response.refresh,
  });
  return response.user;
}

export async function registerAccount(input: {
  email: string;
  username: string;
  displayName: string;
  password: string;
  passwordConfirm: string;
}) {
  const response = await apiClient.post<LoginResponse, typeof input>(
    "/auth/register/",
    { body: input },
  );
  setAuthTokens({
    access: response.access,
    refresh: response.refresh,
  });
  return response.user;
}

export function hasStoredSession() {
  return Boolean(getAuthSessionAdapter().getRefreshToken());
}

export async function getCurrentUser(): Promise<AuthenticatedUserDomain> {
  return mapAuthenticatedUser(
    await apiClient.get<ApiAuthenticatedUser>("/auth/me/", {
      requiresAuth: true,
    }),
  );
}

export async function updateProfile(input: {
  displayName: string;
  email: string;
}) {
  return mapAuthenticatedUser(
    await apiClient.patch<ApiAuthenticatedUser, typeof input>("/auth/profile/", {
      body: input,
      requiresAuth: true,
    }),
  );
}

export async function updateAccountPreferences(input: {
  preferredLanguage: "ne" | "en";
  defaultPlaybackSpeed: number;
  autoplayEnabled: boolean;
  explicitContentEnabled: boolean;
}) {
  return mapAuthenticatedUser(
    await apiClient.patch<ApiAuthenticatedUser, typeof input>(
      "/auth/preferences/",
      { body: input, requiresAuth: true },
    ),
  );
}

export async function logoutCurrentUser() {
  const refresh = getAuthSessionAdapter().getRefreshToken();
  try {
    if (refresh) {
      await apiClient.post<void, { refresh: string }>("/auth/logout/", {
        body: { refresh },
        requiresAuth: true,
      });
    }
  } finally {
    clearAuthSession();
  }
}

export function changePassword(input: {
  currentPassword: string;
  newPassword: string;
  newPasswordConfirm: string;
}) {
  return apiClient.post<void, typeof input>("/auth/change-password/", {
    body: input,
    requiresAuth: true,
  });
}
