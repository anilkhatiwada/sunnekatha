import { beforeEach, describe, expect, it, vi } from "vitest";

const { clearAuthSession, get, getRefreshToken, patch, post, setAuthTokens } = vi.hoisted(
  () => ({
    clearAuthSession: vi.fn(),
    get: vi.fn(),
    getRefreshToken: vi.fn(),
    patch: vi.fn(),
    post: vi.fn(),
    setAuthTokens: vi.fn(),
  }),
);

vi.mock("@/services/api-client", () => ({
  apiClient: { get, patch, post },
}));

vi.mock("@/services/auth-session", () => ({
  clearAuthSession,
  getAuthSessionAdapter: () => ({ getRefreshToken }),
  setAuthTokens,
}));

import {
  getCurrentUser,
  loginWithPassword,
  logoutCurrentUser,
  registerAccount,
  changePassword,
  updateAccountPreferences,
  updateProfile,
} from "@/services/auth-service";

const apiUser = {
  id: "user-id",
  email: "listener@example.com",
  username: "listener",
  displayName: "आरती गुरुङ",
  avatar: null,
  preferredLanguage: "ne",
  defaultPlaybackSpeed: 1,
  autoplayEnabled: true,
  explicitContentEnabled: false,
  isCreator: false,
  createdAt: "2026-07-30T12:00:00Z",
  updatedAt: "2026-07-30T12:00:00Z",
};

describe("authentication service", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("loads and maps the authenticated Django user", async () => {
    get.mockResolvedValue(apiUser);

    await expect(getCurrentUser()).resolves.toMatchObject({
      id: "user-id",
      displayName: "आरती गुरुङ",
      avatar: "/icons/pwa-192.png",
    });
    expect(get).toHaveBeenCalledWith("/auth/me/", { requiresAuth: true });
  });

  it("logs in and registers with the exact account payloads", async () => {
    post.mockResolvedValue({
      access: "access",
      refresh: "refresh",
      user: apiUser,
    });

    await loginWithPassword({
      email: "listener@example.com",
      password: "StrongPass!234",
    });
    await registerAccount({
      email: "new@example.com",
      username: "new-listener",
      displayName: "नयाँ श्रोता",
      password: "StrongPass!234",
      passwordConfirm: "StrongPass!234",
    });

    expect(post).toHaveBeenNthCalledWith(1, "/auth/login/", {
      body: {
        email: "listener@example.com",
        password: "StrongPass!234",
      },
    });
    expect(post).toHaveBeenNthCalledWith(2, "/auth/register/", {
      body: {
        email: "new@example.com",
        username: "new-listener",
        displayName: "नयाँ श्रोता",
        password: "StrongPass!234",
        passwordConfirm: "StrongPass!234",
      },
    });
    expect(setAuthTokens).toHaveBeenCalledTimes(2);
  });

  it("uses the protected password-change endpoint", async () => {
    post.mockResolvedValue(undefined);
    const payload = {
      currentPassword: "OldPass!234",
      newPassword: "NewPass!234",
      newPasswordConfirm: "NewPass!234",
    };

    await changePassword(payload);

    expect(post).toHaveBeenCalledWith("/auth/change-password/", {
      body: payload,
      requiresAuth: true,
    });
  });

  it("uses the profile and preference account endpoints", async () => {
    patch.mockResolvedValue(apiUser);

    await updateProfile({
      displayName: "आरती गुरुङ",
      email: "listener@example.com",
    });
    await updateAccountPreferences({
      preferredLanguage: "ne",
      defaultPlaybackSpeed: 1.25,
      autoplayEnabled: false,
      explicitContentEnabled: false,
    });

    expect(patch).toHaveBeenNthCalledWith(1, "/auth/profile/", {
      body: {
        displayName: "आरती गुरुङ",
        email: "listener@example.com",
      },
      requiresAuth: true,
    });
    expect(patch).toHaveBeenNthCalledWith(2, "/auth/preferences/", {
      body: {
        preferredLanguage: "ne",
        defaultPlaybackSpeed: 1.25,
        autoplayEnabled: false,
        explicitContentEnabled: false,
      },
      requiresAuth: true,
    });
  });

  it("blacklists the refresh token and always clears the browser session", async () => {
    getRefreshToken.mockReturnValue("refresh-token");
    post.mockRejectedValue(new Error("Network unavailable"));

    await expect(logoutCurrentUser()).rejects.toThrow("Network unavailable");

    expect(post).toHaveBeenCalledWith("/auth/logout/", {
      body: { refresh: "refresh-token" },
      requiresAuth: true,
    });
    expect(clearAuthSession).toHaveBeenCalledOnce();
  });
});
