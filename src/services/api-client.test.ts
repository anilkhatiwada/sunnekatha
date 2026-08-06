import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiClient } from "@/services/api-client";
import type { AuthSessionAdapter } from "@/services/auth-session";

function createAuthSession(
  overrides: Partial<AuthSessionAdapter> = {},
): AuthSessionAdapter {
  return {
    getAccessToken: () => "access-1",
    getRefreshToken: () => "refresh-1",
    setTokens: vi.fn(),
    refreshAccessToken: vi.fn().mockResolvedValue(null),
    onAuthenticationFailure: vi.fn(),
    ...overrides,
  };
}

function asFetch(mock: ReturnType<typeof vi.fn>) {
  return mock as unknown as typeof fetch;
}

describe("ApiClient", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("calls the browser fetch function without an invalid receiver", async () => {
    const fetchMock = vi.fn(function (this: typeof globalThis) {
      if (this !== globalThis) throw new TypeError("Illegal invocation");
      return Promise.resolve(
        new Response(JSON.stringify({ ok: true }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );
    });
    vi.stubGlobal("fetch", fetchMock);
    const client = new ApiClient("https://api.example.com/api/v1", 1000);

    await expect(client.get("/health/")).resolves.toEqual({ ok: true });
    expect(fetchMock).toHaveBeenCalledOnce();
  });

  it("serializes JSON, query parameters, and bearer authentication", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    const client = new ApiClient("https://api.example.com/api/v1", 1000, {
      fetch: asFetch(fetchMock),
      getAuthSession: () => createAuthSession(),
    });

    await client.post<{ ok: boolean }, { title: string }>("/playlists/", {
      body: { title: "कविता" },
      query: { page: 2, tags: ["poem", "new"], empty: null },
      requiresAuth: true,
    });

    const [url, request] = fetchMock.mock.calls[0] as [URL, RequestInit];
    expect(url.toString()).toBe(
      "https://api.example.com/api/v1/playlists/?page=2&tags=poem&tags=new",
    );
    expect(request.headers).toMatchObject({
      Authorization: "Bearer access-1",
      "Content-Type": "application/json",
    });
    expect(request.body).toBe(JSON.stringify({ title: "कविता" }));
  });

  it("does not set a content type for FormData", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(null, { status: 204 }),
    );
    const client = new ApiClient("https://api.example.com/api/v1", 1000, {
      fetch: asFetch(fetchMock),
      getAuthSession: () => createAuthSession(),
    });
    const body = new FormData();
    body.set("key", "value");

    await client.post<void, FormData>("/upload", { body });

    const request = fetchMock.mock.calls[0]?.[1] as RequestInit;
    expect(request.body).toBe(body);
    expect(request.headers).not.toHaveProperty("Content-Type");
  });

  it("refreshes once and retries with the rotated access token", async () => {
    let accessToken = "access-1";
    const authSession = createAuthSession({
      getAccessToken: () => accessToken,
      refreshAccessToken: vi.fn().mockResolvedValue({
        access: "access-2",
        refresh: "refresh-2",
      }),
      setTokens: vi.fn((tokens) => {
        accessToken = tokens.access;
      }),
    });
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: "Unauthorized" }), {
          status: 401,
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ id: "user-id" }), { status: 200 }),
      );
    const client = new ApiClient("https://api.example.com/api/v1", 1000, {
      fetch: asFetch(fetchMock),
      getAuthSession: () => authSession,
    });

    await expect(
      client.get<{ id: string }>("/auth/me/", { requiresAuth: true }),
    ).resolves.toEqual({ id: "user-id" });
    expect(authSession.refreshAccessToken).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock.mock.calls[1]?.[1]?.headers).toMatchObject({
      Authorization: "Bearer access-2",
    });
  });

  it("clears authentication when refresh fails", async () => {
    const authSession = createAuthSession();
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "Unauthorized" }), {
        status: 401,
      }),
    );
    const client = new ApiClient("https://api.example.com/api/v1", 1000, {
      fetch: asFetch(fetchMock),
      getAuthSession: () => authSession,
    });

    await expect(
      client.get("/auth/me/", { requiresAuth: true }),
    ).rejects.toMatchObject({ status: 401 });
    expect(authSession.onAuthenticationFailure).toHaveBeenCalledOnce();
    expect(fetchMock).toHaveBeenCalledOnce();
  });

  it("preserves authentication when refresh is temporarily unavailable", async () => {
    const authSession = createAuthSession({
      refreshAccessToken: vi.fn().mockRejectedValue(new Error("Network error")),
    });
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "Unauthorized" }), {
        status: 401,
      }),
    );
    const client = new ApiClient("https://api.example.com/api/v1", 1000, {
      fetch: asFetch(fetchMock),
      getAuthSession: () => authSession,
    });

    await expect(
      client.get("/auth/me/", { requiresAuth: true }),
    ).rejects.toMatchObject({ status: 401 });
    expect(authSession.onAuthenticationFailure).not.toHaveBeenCalled();
    expect(fetchMock).toHaveBeenCalledOnce();
  });
});
