import { beforeEach, describe, expect, it, vi } from "vitest";

const { clearAuthSession, get, getRefreshToken, patch, post } = vi.hoisted(
  () => ({
    clearAuthSession: vi.fn(),
    get: vi.fn(),
    getRefreshToken: vi.fn(),
    patch: vi.fn(),
    post: vi.fn(),
  }),
);

vi.mock("@/services/api-client", () => ({
  apiClient: { get, patch, post },
}));

vi.mock("@/services/auth-session", () => ({
  clearAuthSession,
  getAuthSessionAdapter: () => ({ getRefreshToken }),
  setAuthTokens: vi.fn(),
}));

import {
  getCurrentUser,
  logoutCurrentUser,
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
