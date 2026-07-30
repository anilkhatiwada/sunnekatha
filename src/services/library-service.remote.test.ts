import { beforeEach, describe, expect, it, vi } from "vitest";

const { get, post, remove } = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  remove: vi.fn(),
}));

vi.mock("@/config/environment", () => ({
  environment: { apiMode: "remote" },
}));
vi.mock("@/services/api-client", () => ({
  apiClient: { get, post, delete: remove },
}));

import {
  getRemoteUserLibrary,
  updateLibraryRelationship,
} from "@/services/library-service";

describe("remote library service", () => {
  beforeEach(() => vi.clearAllMocks());

  it("loads every authenticated library section in parallel", async () => {
    get
      .mockResolvedValueOnce({ results: [] })
      .mockResolvedValueOnce({ results: [] })
      .mockResolvedValueOnce({ results: [] })
      .mockResolvedValueOnce({ results: [] })
      .mockResolvedValueOnce({ results: [] })
      .mockResolvedValueOnce({ results: [] });

    await getRemoteUserLibrary();

    expect(get.mock.calls.map(([path]) => path)).toEqual([
      "/library/tracks/",
      "/library/playlists/",
      "/library/authors/",
      "/library/narrators/",
      "/me/recently-played/",
      "/me/continue-listening/",
    ]);
    for (const [, options] of get.mock.calls) {
      expect(options).toMatchObject({ requiresAuth: true });
    }
  });

  it("uses idempotent relationship create and delete endpoints", async () => {
    post.mockResolvedValue({ isFavorited: true });
    remove.mockResolvedValue(undefined);

    await updateLibraryRelationship("favoriteTrack", "track", true);
    await updateLibraryRelationship("favoriteTrack", "track", false);

    expect(post).toHaveBeenCalledWith("/library/tracks/track/favorite/", {
      requiresAuth: true,
    });
    expect(remove).toHaveBeenCalledWith("/library/tracks/track/favorite/", {
      requiresAuth: true,
    });
  });
});
