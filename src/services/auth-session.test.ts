import { describe, expect, it, vi } from "vitest";

import { createBrowserAuthSession } from "@/services/auth-session";

describe("browser JWT session", () => {
  it("persists tokens across browser sessions and preserves refresh on access-only updates", () => {
    const session = createBrowserAuthSession();

    session.setTokens({ access: "access-1", refresh: "refresh-1" });
    session.setTokens({ access: "access-2" });

    expect(window.localStorage.getItem("sunnekatha:auth-tokens")).toContain(
      '"refresh":"refresh-1"',
    );
    expect(window.sessionStorage.getItem("sunnekatha:auth-tokens")).toBeNull();
    expect(session.getAccessToken()).toBe("access-2");
    expect(session.getRefreshToken()).toBe("refresh-1");
  });

  it("migrates an existing tab session to persistent storage", () => {
    window.sessionStorage.setItem(
      "sunnekatha:auth-tokens",
      JSON.stringify({ access: "legacy-access", refresh: "legacy-refresh" }),
    );

    const session = createBrowserAuthSession();

    expect(session.getAccessToken()).toBe("legacy-access");
    expect(window.localStorage.getItem("sunnekatha:auth-tokens")).toContain(
      '"refresh":"legacy-refresh"',
    );
    expect(window.sessionStorage.getItem("sunnekatha:auth-tokens")).toBeNull();
  });

  it("persists rotated refresh tokens", async () => {
    const refreshRequest = vi.fn().mockResolvedValue({
      access: "access-2",
      refresh: "refresh-2",
    });
    const session = createBrowserAuthSession(refreshRequest);
    session.setTokens({ access: "access-1", refresh: "refresh-1" });

    await expect(session.refreshAccessToken()).resolves.toEqual({
      access: "access-2",
      refresh: "refresh-2",
    });
    expect(refreshRequest).toHaveBeenCalledWith("refresh-1");
    expect(session.getRefreshToken()).toBe("refresh-2");
  });

  it("clears the session after authentication failure", () => {
    const session = createBrowserAuthSession();
    session.setTokens({ access: "access", refresh: "refresh" });

    session.onAuthenticationFailure();

    expect(session.getAccessToken()).toBeNull();
    expect(session.getRefreshToken()).toBeNull();
    expect(window.localStorage.getItem("sunnekatha:auth-tokens")).toBeNull();
    expect(window.sessionStorage.getItem("sunnekatha:auth-tokens")).toBeNull();
  });
});
