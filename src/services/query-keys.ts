import type { ContentType, SearchResultType } from "@/types";

export const queryKeys = {
  home: {
    all: ["home"] as const,
    detail: () => [...queryKeys.home.all, "detail"] as const,
    featuredPlaylists: () =>
      [...queryKeys.home.all, "featured-playlists"] as const,
    continueListening: () =>
      [...queryKeys.home.all, "continue-listening"] as const,
    trendingTracks: () =>
      [...queryKeys.home.all, "trending-tracks"] as const,
    recentlyAdded: () =>
      [...queryKeys.home.all, "recently-added"] as const,
    popularAuthors: () =>
      [...queryKeys.home.all, "popular-authors"] as const,
    popularNarrators: () =>
      [...queryKeys.home.all, "popular-narrators"] as const,
    moodPlaylists: () =>
      [...queryKeys.home.all, "mood-playlists"] as const,
  },
  explore: {
    all: ["explore"] as const,
    releases: (filters: {
      contentType?: ContentType;
      genre?: string;
      mood?: string;
    }) => [...queryKeys.explore.all, "releases", filters] as const,
    moods: () => [...queryKeys.explore.all, "moods"] as const,
    genres: () => [...queryKeys.explore.all, "genres"] as const,
    featuredPlaylists: () =>
      [...queryKeys.explore.all, "featured-playlists"] as const,
    popularAuthors: () =>
      [...queryKeys.explore.all, "popular-authors"] as const,
    popularNarrators: () =>
      [...queryKeys.explore.all, "popular-narrators"] as const,
  },
  search: {
    all: ["search"] as const,
    results: (query: string, resultType: SearchResultType) =>
      [...queryKeys.search.all, "results", { query, resultType }] as const,
    autocomplete: (query: string) =>
      [...queryKeys.search.all, "autocomplete", query] as const,
    trending: () => [...queryKeys.search.all, "trending"] as const,
  },
  tracks: {
    all: ["tracks"] as const,
    detail: (slug: string) =>
      [...queryKeys.tracks.all, "detail", slug] as const,
    similar: (trackId?: string) =>
      [...queryKeys.tracks.all, "similar", trackId] as const,
  },
  playlists: {
    all: ["playlists"] as const,
    detail: (slug: string) =>
      [...queryKeys.playlists.all, "detail", slug] as const,
  },
  authors: {
    all: ["authors"] as const,
    detail: (slug: string) =>
      [...queryKeys.authors.all, "detail", slug] as const,
    tracks: (authorId?: string) =>
      [...queryKeys.authors.all, "tracks", authorId] as const,
    collections: (authorId?: string) =>
      [...queryKeys.authors.all, "collections", authorId] as const,
    related: (authorId?: string) =>
      [...queryKeys.authors.all, "related", authorId] as const,
  },
  narrators: {
    all: ["narrators"] as const,
    detail: (slug: string) =>
      [...queryKeys.narrators.all, "detail", slug] as const,
    tracks: (narratorId?: string) =>
      [...queryKeys.narrators.all, "tracks", narratorId] as const,
    playlists: (narratorId?: string) =>
      [...queryKeys.narrators.all, "playlists", narratorId] as const,
  },
  library: {
    all: ["library"] as const,
    initial: () => [...queryKeys.library.all, "initial"] as const,
    catalog: () => [...queryKeys.library.all, "catalog"] as const,
  },
  profile: {
    all: ["profile"] as const,
    listeningStatistics: () =>
      [...queryKeys.profile.all, "listening-statistics"] as const,
  },
} as const;
