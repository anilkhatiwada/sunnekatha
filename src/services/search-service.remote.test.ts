import { beforeEach, describe, expect, it, vi } from "vitest";

const { get } = vi.hoisted(() => ({
  get: vi.fn(),
}));

vi.mock("@/config/environment", () => ({
  environment: {
    apiMode: "remote",
  },
}));

vi.mock("@/services/api-client", () => ({
  apiClient: { get },
}));

import {
  getSearchSuggestions,
  getTrendingSearches,
  searchContent,
} from "@/services/search-service";

const author = {
  id: "author-id",
  slug: "author",
  name: "लेखक",
  nameEnglish: "Author",
  image: null,
};

const narrator = {
  id: "narrator-id",
  slug: "narrator",
  name: "वाचक",
  nameEnglish: "Narrator",
  image: null,
  followerCount: 12,
};

const track = {
  id: "track-id",
  slug: "track",
  title: "वर्षाको साँझ",
  titleEnglish: "Rainy Evening",
  subtitle: "",
  contentType: "story",
  author,
  narrator,
  coverImage: null,
  duration: 180,
  language: "ne",
  genres: ["कथा"],
  moods: ["वर्षा"],
  playCount: 20,
  isPremium: false,
  isExplicit: false,
  isFeatured: true,
  publishedAt: "2026-07-30T12:00:00Z",
};

describe("remote search service", () => {
  beforeEach(() => {
    get.mockReset();
  });

  it("maps grouped Django search responses to frontend models", async () => {
    get.mockResolvedValue({
      query: "वर्षा",
      tracks: [track],
      literaryWorks: [],
      playlists: [],
      albums: [],
      authors: [author],
      narrators: [narrator],
      genres: [],
      moods: [],
    });

    const results = await searchContent({ query: " वर्षा " });

    expect(get).toHaveBeenCalledWith("/search/", {
      query: { q: "वर्षा", type: "all" },
      signal: undefined,
    });
    expect(results.tracks[0]).toMatchObject({
      id: "track-id",
      coverImage: "/icons/pwa-512.png",
    });
    expect(results.authors[0]).toMatchObject({
      id: "author-id",
      biography: "",
    });
    expect(results.narrators[0]).toMatchObject({
      id: "narrator-id",
      followerCount: 12,
    });
  });

  it("uses and unwraps the paginated track-only endpoint", async () => {
    get.mockResolvedValue({
      count: 1,
      next: null,
      previous: null,
      results: [track],
    });

    const results = await searchContent({
      query: "कथा",
      resultType: "tracks",
    });

    expect(get).toHaveBeenCalledWith("/search/tracks/", {
      query: { q: "कथा", page: 1 },
      signal: undefined,
    });
    expect(results.tracks).toHaveLength(1);
    expect(results.playlists).toEqual([]);
  });

  it("maps autocomplete and trending responses", async () => {
    get
      .mockResolvedValueOnce([
        {
          type: "track",
          id: "track-id",
          slug: "track",
          label: "वर्षाको साँझ",
          labelEnglish: "Rainy Evening",
        },
      ])
      .mockResolvedValueOnce({ searches: ["प्रेमका कविता"] });

    await expect(getSearchSuggestions("वर्षा")).resolves.toEqual([
      {
        type: "track",
        id: "track-id",
        slug: "track",
        label: "वर्षाको साँझ",
        labelEnglish: "Rainy Evening",
      },
    ]);
    await expect(getTrendingSearches()).resolves.toEqual([
      "प्रेमका कविता",
    ]);
  });
});
