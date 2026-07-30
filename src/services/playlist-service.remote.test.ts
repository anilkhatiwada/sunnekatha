import { beforeEach, describe, expect, it, vi } from "vitest";

const { get, post, patch, remove } = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn(),
  remove: vi.fn(),
}));

vi.mock("@/config/environment", () => ({
  environment: { apiMode: "remote" },
}));
vi.mock("@/services/api-client", () => ({
  apiClient: { get, post, patch, delete: remove },
}));

import {
  addTrackToPlaylist,
  createPlaylist,
  deletePlaylist,
  getMyPlaylists,
  reorderPlaylistTracks,
} from "@/services/playlist-service";

const playlist = {
  id: "playlist-id",
  slug: "mero-sangraha",
  title: "मेरो सङ्ग्रह",
  titleEnglish: "",
  description: "",
  descriptionEnglish: "",
  coverImage: null,
  curatorName: "Listener",
  trackCount: 0,
  totalDuration: 0,
  category: "user",
  playlistType: "user",
  visibility: "private",
  isFeatured: false,
  isPublished: true,
  createdAt: "2026-07-30T00:00:00Z",
  updatedAt: "2026-07-30T00:00:00Z",
  isOwnedByCurrentUser: true,
  tracks: [],
};

describe("remote playlist service", () => {
  beforeEach(() => vi.clearAllMocks());

  it("lists only the authenticated user's playlists", async () => {
    get.mockResolvedValue({
      count: 1,
      next: null,
      previous: null,
      results: [playlist],
    });

    const result = await getMyPlaylists();

    expect(get).toHaveBeenCalledWith("/playlists/", {
      query: { mine: true, pageSize: 100 },
      requiresAuth: true,
    });
    expect(result[0]).toMatchObject({
      id: "playlist-id",
      isOwnedByCurrentUser: true,
    });
  });

  it("uses the write, add, reorder, and delete contracts", async () => {
    post.mockResolvedValue(playlist);
    patch.mockResolvedValue(playlist);
    remove.mockResolvedValue(undefined);

    await createPlaylist({ titleNe: "मेरो सङ्ग्रह", visibility: "private" });
    await addTrackToPlaylist("mero-sangraha", "track-id");
    await reorderPlaylistTracks("mero-sangraha", ["two", "one"]);
    await deletePlaylist("mero-sangraha");

    expect(post).toHaveBeenNthCalledWith(1, "/playlists/", {
      body: { titleNe: "मेरो सङ्ग्रह", visibility: "private" },
      requiresAuth: true,
    });
    expect(post).toHaveBeenNthCalledWith(
      2,
      "/playlists/mero-sangraha/tracks/add/",
      { body: { trackId: "track-id" }, requiresAuth: true },
    );
    expect(patch).toHaveBeenCalledWith(
      "/playlists/mero-sangraha/tracks/reorder/",
      { body: { trackIds: ["two", "one"] }, requiresAuth: true },
    );
    expect(remove).toHaveBeenCalledWith("/playlists/mero-sangraha/", {
      requiresAuth: true,
    });
  });
});
