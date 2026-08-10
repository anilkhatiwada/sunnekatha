import { authors, playlists, tracks } from "@/data";
import { environment } from "@/config/environment";
import { apiClient } from "@/services/api-client";
import {
  mapAuthor,
  mapAuthorSummary,
  mapCompactTrack,
} from "@/services/api-mappers";
import { mockApiResponse } from "@/services/mock-api";
import { nullOnNotFound, unwrapPage } from "@/services/public-api-utils";
import type {
  ApiAuthor,
  ApiAuthorSummary,
  ApiTrackPage,
} from "@/types/backend-api";
import type { Author, CatalogPlaylist, CatalogTrack } from "@/types";

export async function getPopularAuthors(): Promise<Author[]> {
  if (environment.apiMode === "remote") {
    const payload = await apiClient.get<{
      count: number;
      next: string | null;
      previous: string | null;
      results: ApiAuthorSummary[];
    }>("/authors/featured/", { query: { pageSize: 8 } });
    return unwrapPage(payload).map((value) => ({
      ...mapAuthorSummary(value),
      biography: "",
      genres: [],
      popularTracks: [],
    }));
  }
  const popularAuthors = [...authors]
    .sort(
      (a, b) =>
        b.popularTracks.reduce((total, track) => total + track.playCount, 0) -
        a.popularTracks.reduce((total, track) => total + track.playCount, 0),
    )
    .slice(0, 8);

  return mockApiResponse(popularAuthors);
}

export interface AuthorPage {
  count: number;
  next: boolean;
  previous: boolean;
  results: Author[];
}

export async function getAuthors(search = "", page = 1): Promise<AuthorPage> {
  if (environment.apiMode === "remote") {
    const payload = await apiClient.get<{
      count: number;
      next: string | null;
      previous: string | null;
      results: ApiAuthorSummary[];
    }>("/authors/", {
      query: { search: search || undefined, page, pageSize: 24 },
    });
    return {
      count: payload.count,
      next: Boolean(payload.next),
      previous: Boolean(payload.previous),
      results: unwrapPage(payload).map((value) => ({
        ...mapAuthorSummary(value),
        biography: "",
        genres: [],
        popularTracks: [],
      })),
    };
  }
  const normalized = search.trim().toLocaleLowerCase();
  const filtered = authors.filter((author) =>
      !normalized
        ? true
        : [author.name, author.nameEnglish].some((name) =>
            name?.toLocaleLowerCase().includes(normalized),
          ),
    );
  const start = (page - 1) * 24;
  return mockApiResponse({
    count: filtered.length,
    next: start + 24 < filtered.length,
    previous: page > 1,
    results: filtered.slice(start, start + 24),
  });
}

export async function getAuthorBySlug(slug: string): Promise<Author | null> {
  if (environment.apiMode === "remote") {
    const payload = await nullOnNotFound(
      apiClient.get<ApiAuthor>(`/authors/${slug}/`),
    );
    return payload ? mapAuthor(payload) : null;
  }
  const author = authors.find((item) => item.slug === slug) ?? null;
  return mockApiResponse(author, undefined, null);
}

export async function getAuthorTracks(authorId: string): Promise<CatalogTrack[]> {
  if (environment.apiMode === "remote") {
    const payload = await apiClient.get<ApiTrackPage>(
      `/tracks/author/${authorId}/`,
      { query: { ordering: "-play_count_cache", pageSize: 40 } },
    );
    return unwrapPage(payload).map(mapCompactTrack);
  }
  const authorTracks = tracks
    .filter((track) => track.author.id === authorId)
    .sort((a, b) => b.playCount - a.playCount);

  return mockApiResponse(authorTracks);
}

export async function getAuthorFeaturedCollections(
  authorId: string,
): Promise<CatalogPlaylist[]> {
  if (environment.apiMode === "remote") return [];
  const collections = playlists
    .map((playlist) => ({
      playlist,
      authoredTrackCount: playlist.tracks.filter(
        (track) => track.author.id === authorId,
      ).length,
    }))
    .filter(({ authoredTrackCount }) => authoredTrackCount > 0)
    .sort(
      (a, b) =>
        b.authoredTrackCount - a.authoredTrackCount ||
        Number(b.playlist.isFeatured) - Number(a.playlist.isFeatured),
    )
    .slice(0, 6)
    .map(({ playlist }) => playlist);

  return mockApiResponse(collections);
}

export async function getRelatedAuthors(
  authorId: string,
  limit = 6,
): Promise<Author[]> {
  if (environment.apiMode === "remote") return [];
  const sourceAuthor = authors.find((author) => author.id === authorId);

  if (!sourceAuthor) {
    return mockApiResponse([]);
  }

  const relatedAuthors = authors
    .filter((author) => author.id !== authorId)
    .map((author) => ({
      author,
      sharedGenres: author.genres.filter((genre) =>
        sourceAuthor.genres.includes(genre),
      ).length,
    }))
    .filter(({ sharedGenres }) => sharedGenres > 0)
    .sort(
      (a, b) =>
        b.sharedGenres - a.sharedGenres ||
        b.author.popularTracks.reduce(
          (total, track) => total + track.playCount,
          0,
        ) -
          a.author.popularTracks.reduce(
            (total, track) => total + track.playCount,
            0,
          ),
    )
    .slice(0, limit)
    .map(({ author }) => author);

  return mockApiResponse(relatedAuthors);
}
