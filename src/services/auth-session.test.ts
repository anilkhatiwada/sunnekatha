import { afterEach, describe, expect, it, vi } from "vitest";

import { createBrowserAuthSession } from "@/services/auth-session";

const originalLocksDescriptor = Object.getOwnPropertyDescriptor(
  navigator,
  "locks",
);

describe("browser JWT session", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    if (originalLocksDescriptor) {
      Object.defineProperty(navigator, "locks", originalLocksDescriptor);
    } else {
      Reflect.deleteProperty(navigator, "locks");
    }
  });

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

  it("coordinates refresh rotation across browser tabs", async () => {
    let lockQueue = Promise.resolve();
    const request = vi.fn(
      <T>(_name: string, callback: () => Promise<T>): Promise<T> => {
        const result = lockQueue.then(callback);
        lockQueue = result.then(
          () => undefined,
          () => undefined,
        );
        return result;
      },
    );
    Object.defineProperty(navigator, "locks", {
      configurable: true,
      value: { request },
    });
    const refreshRequest = vi.fn().mockResolvedValue({
      access: "access-2",
      refresh: "refresh-2",
    });
    const firstTab = createBrowserAuthSession(refreshRequest);
    const secondTab = createBrowserAuthSession(refreshRequest);
    firstTab.setTokens({ access: "access-1", refresh: "refresh-1" });

    const [firstTokens, secondTokens] = await Promise.all([
      firstTab.refreshAccessToken(),
      secondTab.refreshAccessToken(),
    ]);

    expect(firstTokens).toEqual({ access: "access-2", refresh: "refresh-2" });
    expect(secondTokens).toEqual({ access: "access-2", refresh: "refresh-2" });
    expect(refreshRequest).toHaveBeenCalledOnce();
    expect(refreshRequest).toHaveBeenCalledWith("refresh-1");
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
