import type { ContentType, SearchResultType } from "@/types";

export const queryKeys = {
  auth: {
    all: ["auth"] as const,
    currentUser: () => [...queryKeys.auth.all, "current-user"] as const,
  },
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
      language?: string;
      premium?: boolean;
      explicit?: boolean;
      ordering?: string;
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
  works: {
    all: ["works"] as const,
    detail: (slug: string) =>
      [...queryKeys.works.all, "detail", slug] as const,
  },
  albums: {
    all: ["albums"] as const,
    detail: (slug: string) =>
      [...queryKeys.albums.all, "detail", slug] as const,
  },
  taxonomy: {
    all: ["taxonomy"] as const,
    genre: (slug: string) =>
      [...queryKeys.taxonomy.all, "genre", slug] as const,
    mood: (slug: string) =>
      [...queryKeys.taxonomy.all, "mood", slug] as const,
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
    public: () => [...queryKeys.playlists.all, "public"] as const,
    mine: () => [...queryKeys.playlists.all, "mine"] as const,
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
    remote: () => [...queryKeys.library.all, "remote"] as const,
  },
  progress: {
    all: ["progress"] as const,
    track: (trackId: string) =>
      [...queryKeys.progress.all, "track", trackId] as const,
    continueListening: () =>
      [...queryKeys.progress.all, "continue-listening"] as const,
    recentlyPlayed: () =>
      [...queryKeys.progress.all, "recently-played"] as const,
    history: () => [...queryKeys.progress.all, "history"] as const,
  },
  queue: {
    all: ["queue"] as const,
    current: () => [...queryKeys.queue.all, "current"] as const,
  },
  notifications: {
    all: ["notifications"] as const,
    list: () => [...queryKeys.notifications.all, "list"] as const,
    unread: () => [...queryKeys.notifications.all, "unread"] as const,
  },
  creator: {
    all: ["creator"] as const,
    profile: () => [...queryKeys.creator.all, "profile"] as const,
    drafts: () => [...queryKeys.creator.all, "drafts"] as const,
    uploads: () => [...queryKeys.creator.all, "uploads"] as const,
  },
  profile: {
    all: ["profile"] as const,
    listeningStatistics: () =>
      [...queryKeys.profile.all, "listening-statistics"] as const,
  },
} as const;
