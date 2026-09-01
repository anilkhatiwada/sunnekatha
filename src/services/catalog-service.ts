import { genres, moods, tracks } from "@/data";
import { environment } from "@/config/environment";
import { apiClient } from "@/services/api-client";
import {
  DEFAULT_ARTWORK_PATH,
  mapAuthorSummary,
  mapCompactTrack,
  mapCompactLiteraryWork,
  mapTaxonomy,
} from "@/services/api-mappers";
import { mockApiResponse } from "@/services/mock-api";
import { unwrapPage } from "@/services/public-api-utils";
import { nullOnNotFound } from "@/services/public-api-utils";
import type {
  ApiAlbum,
  ApiLiteraryWork,
  ApiTaxonomy,
  ApiTrackPage,
  ApiCatalogItemPage,
} from "@/types/backend-api";
import type {
  Album,
  ContentType,
  ContentCategory,
  Genre,
  LiteraryWork,
  Mood,
  CatalogItem,
} from "@/types";

export async function getExploreTracks(
  filters: {
    contentType?: ContentType;
    genre?: string;
    mood?: string;
    language?: string;
    author?: string;
    narrator?: string;
    premium?: boolean;
    explicit?: boolean;
    ordering?: string;
  } = {},
): Promise<CatalogItem[]> {
  if (environment.apiMode === "remote") {
    const payload = await apiClient.get<ApiCatalogItemPage>("/catalog/items/", {
      query: {
        category: filters.contentType,
        genre: filters.genre,
        mood: filters.mood,
        language: filters.language,
        author: filters.author,
        narrator: filters.narrator,
        premium: filters.premium,
        explicit: filters.explicit,
        ordering: filters.ordering ?? "-published_at",
        pageSize: 40,
      },
    });
    return unwrapPage(payload).map((item) => item.kind === "track"
      ? { kind: "track" as const, content: mapCompactTrack(item.content) }
      : { kind: "work" as const, content: mapCompactLiteraryWork(item.content) });
  }
  const filteredTracks = tracks.filter(
    (track) =>
      (!filters.contentType || track.contentType === filters.contentType) &&
      (!filters.genre || track.genres.includes(filters.genre)) &&
      (!filters.mood || track.moods.includes(filters.mood)),
  );
  const newestTracks = [...filteredTracks].sort(
    (a, b) =>
      new Date(b.publishedAt).getTime() - new Date(a.publishedAt).getTime(),
  );

  return mockApiResponse(
    newestTracks.map((track) => ({ kind: "track" as const, content: track })),
  );
}

export async function getGenres(): Promise<Genre[]> {
  if (environment.apiMode === "remote") {
    const payload = await apiClient.get<ApiTaxonomy[]>("/genres/", {
      query: { active: true },
    });
    return payload.map(mapTaxonomy);
  }
  return mockApiResponse(genres);
}

export async function getContentCategories(): Promise<ContentCategory[]> {
  if (environment.apiMode === "remote") {
    const payload = await apiClient.get<ApiTaxonomy[]>("/content-categories/", {
      query: { active: true },
    });
    return payload.map(mapTaxonomy);
  }
  const slugs = [...new Set(tracks.map((track) => track.contentType))];
  return mockApiResponse(
    slugs.map((slug) => ({
      id: slug,
      slug,
      name: slug,
      description: "",
    })),
  );
}

export async function getMoods(): Promise<Mood[]> {
  if (environment.apiMode === "remote") {
    const payload = await apiClient.get<ApiTaxonomy[]>("/moods/", {
      query: { active: true },
    });
    return payload.map(mapTaxonomy);
  }
  return mockApiResponse(moods);
}

export async function getLiteraryWorkBySlug(
  slug: string,
): Promise<LiteraryWork | null> {
  if (environment.apiMode !== "remote") return null;
  const value = await nullOnNotFound(
    apiClient.get<ApiLiteraryWork>(`/works/${slug}/`),
  );
  if (!value) return null;
  return {
    ...mapCompactLiteraryWork(value),
    description: value.description || value.descriptionEnglish,
    copyrightStatus: value.copyrightStatus,
    tracks: value.chapters.map(mapCompactTrack),
  };
}

export async function getCatalogItems(filters: {
  category?: string;
  tag?: string;
  author?: string;
  genre?: string;
  mood?: string;
} = {}): Promise<CatalogItem[]> {
  const payload = await apiClient.get<ApiCatalogItemPage>("/catalog/items/", {
    query: { ...filters, pageSize: 40 },
  });
  return unwrapPage(payload).map((item) => item.kind === "track"
    ? { kind: "track" as const, content: mapCompactTrack(item.content) }
    : { kind: "work" as const, content: mapCompactLiteraryWork(item.content) });
}

export async function getAlbumBySlug(slug: string): Promise<Album | null> {
  if (environment.apiMode !== "remote") return null;
  const value = await nullOnNotFound(
    apiClient.get<ApiAlbum>(`/albums/${slug}/`),
  );
  if (!value) return null;
  const tracks = await getCatalogTracks({ album: slug });
  return {
    id: value.id,
    slug: value.slug,
    title: value.title,
    titleEnglish: value.titleEnglish || undefined,
    description: value.description || value.descriptionEnglish,
    coverImage: value.coverImage || DEFAULT_ARTWORK_PATH,
    author: mapAuthorSummary(value.author),
    albumType: value.albumType,
    genres: value.genres,
    moods: value.moods,
    releaseDate: value.releaseDate ?? undefined,
    tracks,
  };
}

export async function getCatalogTracks(filters: {
  work?: string;
  album?: string;
  genre?: string;
  mood?: string;
}) {
  const payload = await apiClient.get<ApiTrackPage>("/tracks/", {
    query: {
      ...filters,
      pageSize: 100,
      ordering: "track_number",
    },
  });
  return unwrapPage(payload).map(mapCompactTrack);
}

export async function getGenreBySlug(slug: string) {
  return (await getGenres()).find((item) => item.slug === slug) ?? null;
}

export async function getMoodBySlug(slug: string) {
  return (await getMoods()).find((item) => item.slug === slug) ?? null;
}
